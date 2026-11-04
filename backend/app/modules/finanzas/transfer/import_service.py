"""Importar movimientos: preview -> (remap) -> confirm -> (undo).

El servidor es la fuente de verdad: el cliente nunca manda montos ni fechas al
confirmar, solo que filas incluir y overrides de categoria/tipo/descripcion; las
filas se vuelven a calcular desde `raw_table` + el mapeo guardado.
"""

import hashlib
import json
import logging
import re
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional

from fastapi import HTTPException
from sqlalchemy import delete, func, null as sa_null, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.clock import local_today
from app.modules.finanzas.enums import AccountType, PaymentMethod
from app.modules.finanzas.models import BankAccount, Category, Transaction
from app.modules.finanzas.transfer import import_parse as ip
from app.modules.finanzas.transfer import import_presets as presets
from app.modules.finanzas.transfer.import_rules import Suggester, normalize_desc
from app.modules.finanzas.transfer.models import ImportBatch
from app.modules.finanzas.transfer.schemas import (
    ConfirmRequest,
    CurrencyTotal,
    DuplicateOf,
    ImportBatchOut,
    ImportCounts,
    ImportMapping,
    ImportPreview,
    MappingUpdate,
    ParsedRow,
)

logger = logging.getLogger(__name__)

RAW_TABLE_MAX_BYTES = 4 * 1024 * 1024
MAX_OPEN_PREVIEWS = 5
INSERT_CHUNK = 500
HASH_QUERY_CHUNK = 400
DEFAULT_DESCRIPTION = "Movimiento importado"
INFORMATIVE = "Fila informativa del reporte (no es un movimiento)."
MAX_PRODUCT_NAME = 255
ALLOWED_CURRENCIES = {"ARS", "USD", "EUR", "BRL", "UYU", "CLP"}


def _gone() -> HTTPException:
    return HTTPException(status_code=410, detail="La previsualización venció: volvé a subir el archivo.")


def _not_found() -> HTTPException:
    return HTTPException(status_code=404, detail="Importación no encontrada")


def _aware(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is not None and dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def _now() -> datetime:
    return datetime.now(timezone.utc)


def safe_filename(name: Optional[str]) -> str:
    base = re.split(r"[\\/]", name or "")[-1]
    base = ip.sanitize_text(base).replace("..", ".")
    return (base or "archivo")[:255]


def _jaccard(a: set[str], b: set[str]) -> float:
    return len(a & b) / len(a | b) if a and b else 0.0


def _similar(a: str, b: str) -> bool:
    if not a or not b:
        return False
    return a in b or b in a or _jaccard(set(a.split()), set(b.split())) >= 0.5


@dataclass
class Analysis:
    rows: list[ParsedRow]
    warnings: list[str] = field(default_factory=list)

    @property
    def counts(self) -> ImportCounts:
        c = ImportCounts()
        for r in self.rows:
            setattr(c, r.status, getattr(c, r.status) + 1)
        return c


def _cell(row: list[str], idx: Optional[int]) -> str:
    return row[idx] if idx is not None and 0 <= idx < len(row) else ""


def _norm_value(v: str) -> str:
    return ip.normalize_header(v)


class ImportService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ── Acceso a lotes ──────────────────────────────────────────────────────

    async def _get(self, user_id: str, batch_id: str) -> ImportBatch:
        batch = (
            await self.db.execute(
                select(ImportBatch).where(ImportBatch.id == batch_id, ImportBatch.user_id == user_id)
            )
        ).scalar_one_or_none()
        if batch is None:
            raise _not_found()
        return batch

    async def _get_preview(self, user_id: str, batch_id: str) -> ImportBatch:
        batch = await self._get(user_id, batch_id)
        if batch.status != "preview":
            raise HTTPException(status_code=409, detail="Esta importación ya no está en previsualización.")
        if batch.expires_at is not None and _aware(batch.expires_at) < _now():
            raise _gone()
        return batch

    async def _own_account(self, user_id: str, account_id: Optional[str]) -> Optional[BankAccount]:
        if not account_id:
            return None
        acc = (
            await self.db.execute(
                select(BankAccount).where(BankAccount.id == account_id, BankAccount.user_id == user_id)
            )
        ).scalar_one_or_none()
        if acc is None:
            raise HTTPException(status_code=404, detail="Cuenta no encontrada")
        return acc

    # ── Analisis de filas (puro respecto del archivo) ───────────────────────

    def _parse_rows(
        self,
        rows: list[list[str]],
        header_row: int,
        mapping: ImportMapping,
        kind: str,
        default_currency: str,
        today: date,
    ) -> Analysis:
        out = Analysis(rows=[])
        width = len(rows[0]) if rows else 0
        data = rows[header_row + 1 :]
        if not mapping.is_complete():
            out.warnings.append("Elegí qué columna es la fecha y cuál es el monto para ver los movimientos.")
            return out

        # Pistas por columna: orden de fecha y significado de un punto.
        dayfirst = {"dd/mm/yyyy": True, "mm/dd/yyyy": False}.get(mapping.date_format)
        if dayfirst is None:
            dayfirst, ambiguous = ip.detect_dayfirst([_cell(r, mapping.date) for r in data])
            if ambiguous:
                out.warnings.append(
                    "Las fechas son ambiguas (podrían ser día/mes o mes/día): usamos día/mes. "
                    "Si no es así, cambiá el formato de fecha."
                )
        dot_modes: dict[int, str] = {}
        for col in (mapping.amount, mapping.fallback_amount, mapping.debit, mapping.credit):
            if col is not None:
                dot_modes[col] = (
                    "decimal" if kind == "xlsx" else ip.infer_dot_mode([_cell(r, col) for r in data])
                )

        translations = {int(k): v for k, v in mapping.translations.items() if k.isdigit()}
        type_values = {
            t: {_norm_value(v) for v in vals} for t, vals in mapping.type_values.items()
        }
        include_vals = (
            {_norm_value(v) for v in mapping.include_when.values} if mapping.include_when else set()
        )
        skip_vals = {_norm_value(v) for v in mapping.skip_when.values} if mapping.skip_when else set()

        for i, raw in enumerate(data):
            row = ParsedRow(index=i, source_line=header_row + 2 + i, status="ok")
            out.rows.append(row)
            try:
                self._parse_one(
                    row, raw, mapping, dayfirst, dot_modes, translations, type_values,
                    include_vals, skip_vals, default_currency, today,
                )
            except _Skip as s:
                row.status, row.errors = "skipped", [str(s)]
            except ValueError as e:
                row.status, row.errors = "error", [str(e)]
        self._assign_hashes(out.rows)
        return out

    def _parse_one(
        self, row, raw, m: ImportMapping, dayfirst, dot_modes, translations, type_values,
        include_vals, skip_vals, default_currency, today,
    ) -> None:
        if m.include_when and _norm_value(_cell(raw, m.include_when.column)) not in include_vals:
            raise _Skip(INFORMATIVE)
        if m.skip_when and _norm_value(_cell(raw, m.skip_when.column)) in skip_vals:
            raise _Skip("Fila descartada por la regla de exclusión.")
        used = [m.date, m.amount, m.debit, m.credit, m.fallback_amount, *m.description]
        if any(c is not None and _cell(raw, c) == ip.FORMULA_NO_VALUE for c in used):
            raise ValueError("Una celda tiene una fórmula sin valor guardado: abrí el archivo, guardalo y volvé a subirlo.")

        errors: list[str] = []
        # Fecha / hora
        try:
            row.date, t = ip.parse_datetime_cell(_cell(raw, m.date), dayfirst, m.tz_offset_minutes, today)
            row.time = t
            if m.time is not None and _cell(raw, m.time):
                row.time = ip.parse_time_cell(_cell(raw, m.time)) or row.time
        except ValueError as e:
            errors.append(f"Fecha: {e}")

        # Monto y tipo
        try:
            amount, tx_type = self._amount_and_type(raw, m, dot_modes, type_values)
            if m.invert_sign:
                tx_type = "income" if tx_type == "expense" else "expense"
            row.amount, row.type = amount, tx_type
        except _Skip:
            raise
        except ValueError as e:
            errors.append(f"Monto: {e}")

        # Moneda
        try:
            cur = ip.normalize_currency(_cell(raw, m.currency)) if m.currency is not None else None
            row.currency = cur or default_currency
        except ValueError as e:
            errors.append(f"Moneda: {e}")

        # Descripcion y referencia
        parts = []
        for col in m.description:
            text = ip.sanitize_text(_cell(raw, col))
            if not text:
                continue
            table = translations.get(col)
            parts.append(presets.translate(table, text) if table else text)
        row.description = " · ".join(parts) or DEFAULT_DESCRIPTION
        row.reference = ip.sanitize_text(_cell(raw, m.reference))[:100]
        if errors:
            raise ValueError(" ".join(errors))

    def _amount_and_type(self, raw, m: ImportMapping, dot_modes, type_values) -> tuple[Decimal, str]:
        sep = m.decimal_separator

        def parse(col: Optional[int]) -> Optional[Decimal]:
            text = _cell(raw, col)
            if not text.strip():
                return None
            return ip.parse_amount(text, sep, dot_modes.get(col, "thousands"))

        if m.amount_mode == "debit_credit":
            debit, credit = parse(m.debit), parse(m.credit)
            debit = debit if debit else None
            credit = credit if credit else None
            if debit and credit:
                raise ValueError("La fila tiene débito y crédito a la vez.")
            if debit:
                return abs(debit), "expense"
            if credit:
                return abs(credit), "income"
            raise _Skip("Monto cero.")

        if m.amount_mode == "amount_and_type":
            amount = parse(m.amount)
            if amount is None:
                raise ValueError("falta el monto")
            if amount == 0:
                raise _Skip("Monto cero.")
            tv = _norm_value(_cell(raw, m.type_column))
            for kind in ("income", "expense"):
                if tv in type_values.get(kind, set()):
                    return abs(amount), kind
            raise ValueError(f"tipo de operación desconocido: {ip.sanitize_text(tv)[:30]}")

        amount = parse(m.amount)
        if amount is None and m.fallback_amount is not None:
            fb = parse(m.fallback_amount)
            if fb is not None:
                tv = _norm_value(_cell(raw, m.type_column))
                for kind, sign in (("expense", -1), ("income", 1)):
                    if tv in type_values.get(kind, set()):
                        amount = abs(fb) * sign
                        break
                else:
                    raise ValueError(f"tipo de operación desconocido: {ip.sanitize_text(tv)[:30]}")
        if amount is None:
            raise ValueError("falta el monto")
        if amount == 0:
            raise _Skip("Monto cero.")
        return abs(amount), ("expense" if amount < 0 else "income")

    @staticmethod
    def _assign_hashes(rows: list[ParsedRow]) -> None:
        seen: dict[tuple, int] = {}
        for r in rows:
            if r.status != "ok":
                continue
            key = (r.date.isoformat(), r.type, f"{r.amount:.2f}", r.currency,
                   normalize_desc(r.description), r.reference)
            seen[key] = seen.get(key, 0) + 1
            raw_key = "|".join(key) + f"|#{seen[key]}"
            r.row_hash = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()

    # ── Duplicados y sugerencias (consultas por usuario) ────────────────────

    async def _enrich(self, user_id: str, rows: list[ParsedRow], today: date) -> None:
        ok = [r for r in rows if r.status == "ok"]
        if not ok:
            return
        # 1. Ya importadas: misma huella en un movimiento no borrado.
        hashes = [r.row_hash for r in ok]
        existing: dict[str, tuple] = {}
        for i in range(0, len(hashes), HASH_QUERY_CHUNK):
            res = await self.db.execute(
                select(Transaction.import_row_hash, Transaction.id, Transaction.transaction_date,
                       Transaction.product_name)
                .where(
                    Transaction.user_id == user_id,
                    Transaction.is_deleted == False,  # noqa: E712
                    Transaction.import_row_hash.in_(hashes[i : i + HASH_QUERY_CHUNK]),
                )
            )
            for h, tid, d, name in res.all():
                existing.setdefault(h, (tid, d, name))
        # 2. Posibles: misma fecha (+-1 dia), tipo, monto y moneda, descripcion parecida.
        lo = min(r.date for r in ok) - timedelta(days=1)
        hi = max(r.date for r in ok) + timedelta(days=1)
        near = (
            await self.db.execute(
                select(Transaction.id, Transaction.transaction_date, Transaction.type,
                       Transaction.amount, Transaction.currency, Transaction.product_name)
                .where(
                    Transaction.user_id == user_id,
                    Transaction.is_deleted == False,  # noqa: E712
                    Transaction.transaction_date >= lo,
                    Transaction.transaction_date <= hi,
                )
            )
        ).all()
        index: dict[tuple, list[tuple]] = {}
        for tid, d, t, amt, cur, name in near:
            key = (t, Decimal(str(amt)).quantize(Decimal("0.01")), cur)
            index.setdefault(key, []).append((tid, date.fromisoformat(str(d)[:10]), name or ""))

        suggester = await Suggester.load(self.db, user_id, today)
        for r in ok:
            hit = existing.get(r.row_hash)
            if hit:
                tid, d, name = hit
                r.status = "duplicate"
                r.errors = ["Ya importado."]
                r.duplicate_of = DuplicateOf(id=tid, date=date.fromisoformat(str(d)[:10]), description=name or "")
                continue
            norm = normalize_desc(r.description)
            for tid, d, name in index.get((r.type, r.amount, r.currency), []):
                if abs((d - r.date).days) <= 1 and _similar(norm, normalize_desc(name)):
                    r.status = "possible_duplicate"
                    r.errors = ["Se parece a un movimiento que ya tenés."]
                    r.duplicate_of = DuplicateOf(id=tid, date=d, description=name)
                    break
            cid, source, merchant = suggester.suggest(r.description, r.type)
            r.suggested_category_id, r.suggestion_source, r.merchant_category = cid, source, merchant

    async def _analyze(
        self, user_id: str, batch: ImportBatch, mapping: ImportMapping, account: Optional[BankAccount]
    ) -> Analysis:
        raw = batch.raw_table or {}
        rows = raw.get("rows", [])
        today = local_today(mapping.tz_offset_minutes)
        default_currency = (
            account.currency if account is not None and account.currency in ALLOWED_CURRENCIES
            else mapping.default_currency
        )
        analysis = self._parse_rows(
            rows, batch.header_row, mapping, raw.get("kind", "csv"), default_currency, today
        )
        await self._enrich(user_id, analysis.rows, today)
        return analysis

    # ── Preview ─────────────────────────────────────────────────────────────

    async def _cleanup_previews(self, user_id: str) -> None:
        await self.db.execute(
            delete(ImportBatch).where(
                ImportBatch.user_id == user_id,
                ImportBatch.status == "preview",
                ImportBatch.expires_at < _now(),
            )
        )
        open_ids = (
            await self.db.execute(
                select(ImportBatch.id)
                .where(ImportBatch.user_id == user_id, ImportBatch.status == "preview")
                .order_by(ImportBatch.created_at, ImportBatch.id)
            )
        ).scalars().all()
        excess = len(open_ids) - (MAX_OPEN_PREVIEWS - 1)
        if excess > 0:
            await self.db.execute(delete(ImportBatch).where(ImportBatch.id.in_(open_ids[:excess])))

    async def preview(
        self,
        user_id: str,
        data: bytes,
        filename: str,
        preset: Optional[str],
        account_id: Optional[str],
        tz_offset_minutes: int,
    ) -> ImportPreview:
        if preset and preset not in ("auto",) and preset not in presets.PRESET_KEYS:
            raise HTTPException(status_code=422, detail="Origen de importación desconocido.")
        account = await self._own_account(user_id, account_id)
        try:
            table = ip.load_table(data)
        except ip.ImportFileError as e:
            raise HTTPException(status_code=e.status_code, detail=e.detail)

        header_row = ip.find_header_row(table.rows)
        headers = table.rows[header_row]
        norm_headers = [ip.normalize_header(h) for h in headers]
        signature = ip.header_signature(headers)
        file_sha = hashlib.sha256(data).hexdigest()
        warnings: list[str] = []

        detected = presets.detect_preset(norm_headers)
        forced = preset if preset and preset != "auto" else None
        mapping: Optional[ImportMapping] = None
        source = "preset"
        chosen = forced or detected
        if forced:
            mapping = presets.build_mapping(forced, norm_headers)
            if mapping is None:
                raise HTTPException(
                    status_code=422,
                    detail="El archivo no tiene las columnas de ese origen. Elegí otro origen o 'Otro banco o billetera'.",
                )
        else:
            remembered = await self._remembered(user_id, signature)
            if remembered is not None:
                mapping = ImportMapping(**remembered.mapping)
                chosen, source = remembered.preset, "remembered"
                when = (remembered.confirmed_at or remembered.created_at)
                warnings.append(
                    f"Usamos el mapeo de tu importación del {when.strftime('%d/%m/%Y')}." if when
                    else "Usamos el mapeo de tu importación anterior."
                )
            else:
                mapping = presets.build_mapping(detected, norm_headers)
                source = "preset" if detected != presets.GENERIC else "heuristic"
        mapping.tz_offset_minutes = tz_offset_minutes

        duplicate_file = (
            await self.db.execute(
                select(ImportBatch.confirmed_at).where(
                    ImportBatch.user_id == user_id,
                    ImportBatch.status == "confirmed",
                    ImportBatch.file_sha256 == file_sha,
                ).order_by(ImportBatch.confirmed_at.desc()).limit(1)
            )
        ).first()
        if duplicate_file:
            when = duplicate_file[0]
            warnings.append(
                f"Ya importaste este archivo el {when.strftime('%d/%m/%Y')}." if when
                else "Ya importaste este archivo."
            )

        raw = {"kind": table.kind, "rows": table.rows}
        if len(json.dumps(raw, ensure_ascii=False)) > RAW_TABLE_MAX_BYTES:
            raise HTTPException(status_code=413, detail="El archivo es demasiado grande para previsualizar. Dividilo por fechas.")

        await self._cleanup_previews(user_id)
        batch = ImportBatch(
            user_id=user_id, status="preview", created_at=_now(), preset=chosen, filename=safe_filename(filename),
            file_sha256=file_sha, header_signature=signature, header_row=header_row,
            mapping=mapping.model_dump(mode="json"), account_id=account.id if account else None,
            raw_table=raw, row_count=max(len(table.rows) - header_row - 1, 0),
            expires_at=_now() + timedelta(hours=settings.FINANCE_IMPORT_PREVIEW_TTL_HOURS),
        )
        self.db.add(batch)
        await self.db.flush()
        analysis = await self._analyze(user_id, batch, mapping, account)
        await self.db.commit()
        return self._build_preview(batch, mapping, source, detected, analysis, warnings)

    async def _remembered(self, user_id: str, signature: str) -> Optional[ImportBatch]:
        return (
            await self.db.execute(
                select(ImportBatch)
                .where(
                    ImportBatch.user_id == user_id,
                    ImportBatch.status == "confirmed",
                    ImportBatch.header_signature == signature,
                )
                .order_by(ImportBatch.confirmed_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()

    def _build_preview(
        self, batch: ImportBatch, mapping: ImportMapping, source: str, detected: str,
        analysis: Analysis, warnings: list[str],
    ) -> ImportPreview:
        rows = (batch.raw_table or {}).get("rows", [])
        totals: dict[str, CurrencyTotal] = {}
        for r in analysis.rows:
            if r.status != "ok":
                continue
            t = totals.setdefault(
                r.currency, CurrencyTotal(currency=r.currency, income=Decimal(0), expense=Decimal(0), count=0)
            )
            t.count += 1
            if r.type == "income":
                t.income += r.amount
            else:
                t.expense += r.amount
        return ImportPreview(
            batch_id=batch.id,
            preset=batch.preset,
            detected_preset=detected,
            mapping=mapping,
            mapping_source=source,
            mapping_complete=mapping.is_complete(),
            headers=rows[batch.header_row] if rows else [],
            header_row=batch.header_row,
            sample_rows=rows[batch.header_row + 1 : batch.header_row + 6],
            rows=analysis.rows,
            counts=analysis.counts,
            totals_by_currency=sorted(totals.values(), key=lambda t: t.currency),
            warnings=[*warnings, *analysis.warnings],
            expires_at=batch.expires_at,
            filename=batch.filename,
            account_id=batch.account_id,
        )

    # ── Remap ───────────────────────────────────────────────────────────────

    async def remap(self, user_id: str, batch_id: str, upd: MappingUpdate) -> ImportPreview:
        batch = await self._get_preview(user_id, batch_id)
        raw = batch.raw_table or {}
        rows = raw.get("rows", [])
        mapping = ImportMapping(**batch.mapping)
        source, warnings = "user", []
        header_row = batch.header_row
        if upd.header_row is not None:
            if upd.header_row >= len(rows):
                raise HTTPException(status_code=422, detail="La fila de encabezado no existe en el archivo.")
            header_row = upd.header_row
        headers = rows[header_row]
        norm_headers = [ip.normalize_header(h) for h in headers]
        detected = presets.detect_preset(norm_headers)
        account_id = batch.account_id
        if upd.account_id is not None:
            account_id = (await self._own_account(user_id, upd.account_id)).id if upd.account_id else None

        if upd.preset:
            if upd.preset not in presets.PRESET_KEYS:
                raise HTTPException(status_code=422, detail="Origen de importación desconocido.")
            built = presets.build_mapping(upd.preset, norm_headers)
            if built is None:
                raise HTTPException(
                    status_code=422,
                    detail="El archivo no tiene las columnas de ese origen. Elegí otro origen o 'Otro banco o billetera'.",
                )
            mapping, source = built, "preset"
            batch.preset = upd.preset
        if upd.mapping is not None:
            mapping, source = upd.mapping, "user"
            width = len(headers)
            cols = [mapping.date, mapping.time, mapping.amount, mapping.fallback_amount, mapping.debit,
                    mapping.credit, mapping.type_column, mapping.currency, mapping.reference, *mapping.description]
            for f in (mapping.include_when, mapping.skip_when):
                if f is not None:
                    cols.append(f.column)
            if any(c is not None and c >= width for c in cols):
                raise HTTPException(status_code=422, detail="Elegiste una columna que no existe en el archivo.")
        if upd.tz_offset_minutes is not None:
            mapping.tz_offset_minutes = upd.tz_offset_minutes
        batch.header_row = header_row
        batch.header_signature = ip.header_signature(headers)
        batch.mapping = mapping.model_dump(mode="json")
        batch.account_id = account_id
        batch.row_count = max(len(rows) - header_row - 1, 0)
        account = await self._own_account(user_id, account_id)
        analysis = await self._analyze(user_id, batch, mapping, account)
        await self.db.commit()
        return self._build_preview(batch, mapping, source, detected, analysis, warnings)

    # ── Confirmar ───────────────────────────────────────────────────────────

    async def confirm(self, user_id: str, batch_id: str, req: ConfirmRequest) -> ImportBatchOut:
        batch = await self._get_preview(user_id, batch_id)
        mapping = ImportMapping(**batch.mapping)
        account = await self._own_account(user_id, batch.account_id)
        analysis = await self._analyze(user_id, batch, mapping, account)  # re-chequea huellas
        by_index = {r.index: r for r in analysis.rows}

        # Categorias elegidas: todas del usuario (una consulta).
        wanted = {c.category_id for c in req.rows if c.include and c.category_id}
        if wanted:
            owned = set(
                (await self.db.execute(
                    select(Category.id).where(Category.user_id == user_id, Category.id.in_(wanted))
                )).scalars().all()
            )
            if wanted - owned:
                raise HTTPException(status_code=404, detail="Categoría no encontrada")

        chosen: list[tuple[ParsedRow, Optional[str], str, str]] = []
        seen: set[int] = set()
        for c in req.rows:
            if not c.include:
                continue
            row = by_index.get(c.index)
            if row is None or c.index in seen:
                raise HTTPException(status_code=422, detail=f"La fila {c.index} no existe o está repetida.")
            seen.add(c.index)
            if row.status not in ("ok", "possible_duplicate"):
                raise HTTPException(
                    status_code=422,
                    detail=f"La fila {row.source_line} no se puede importar ({'ya importada' if row.status == 'duplicate' else 'tiene errores'}).",
                )
            category = row.suggested_category_id if c.category_id is None else (c.category_id or None)
            chosen.append((row, category, c.type or row.type, ip.sanitize_text(c.description) if c.description else row.description))

        # Transicion atomica preview -> confirmed: dos confirmaciones a la vez no duplican.
        now = _now().replace(microsecond=0)
        claimed = await self.db.execute(
            update(ImportBatch)
            .where(ImportBatch.id == batch.id, ImportBatch.status == "preview")
            .values(status="confirmed", confirmed_at=now)
        )
        if claimed.rowcount != 1:
            await self.db.rollback()
            raise HTTPException(status_code=409, detail="Esta importación ya se confirmó.")

        bank = (account.bank_name or account.name) if account else presets.BANK_LABEL_BY_PRESET.get(batch.preset, "")
        account_type = account.account_type if account else AccountType.CHECKING.value
        last4 = account.last4 if account else ""
        payment = presets.PAYMENT_BY_PRESET.get(batch.preset, PaymentMethod.OTHER.value)
        assert payment in PaymentMethod._value2member_map_ and account_type in AccountType._value2member_map_

        try:
            for i in range(0, len(chosen), INSERT_CHUNK):
                txs = []
                for row, category_id, tx_type, desc in chosen[i : i + INSERT_CHUNK]:
                    txs.append(Transaction(
                        user_id=user_id,
                        amount=row.amount,
                        currency=row.currency,
                        type=tx_type,
                        transaction_date=row.date,
                        transaction_time=row.time,
                        bank_entity_name=(bank or "")[:100],
                        account_type=account_type,
                        account_last4=(last4 or "")[:4],
                        payment_method=payment,
                        product_name=desc[:MAX_PRODUCT_NAME],
                        notes=("Descripción completa: " + desc) if len(desc) > MAX_PRODUCT_NAME else None,
                        merchant_name="",
                        merchant_category=row.merchant_category,
                        category_id=category_id,
                        is_recurring=False,
                        recurring_parent_id=None,
                        import_batch_id=batch.id,
                        import_row_hash=row.row_hash,
                        created_at=now,
                        updated_at=now,
                    ))
                self.db.add_all(txs)
            counts = analysis.counts
            await self.db.execute(
                update(ImportBatch).where(ImportBatch.id == batch.id).values(
                    raw_table=sa_null(),
                    imported_count=len(chosen),
                    skipped_count=counts.skipped + (counts.ok + counts.possible_duplicate - len(chosen)),
                    duplicate_count=counts.duplicate,
                    error_count=counts.error,
                    row_count=len(analysis.rows),
                    mapping=mapping.model_dump(mode="json"),
                )
            )
            await self.db.commit()
        except Exception:
            await self.db.rollback()
            raise
        await self.db.refresh(batch)
        return await self._out(batch)

    # ── Historial, detalle, deshacer ────────────────────────────────────────

    async def _edited_counts(self, batches: list[ImportBatch]) -> dict[str, int]:
        confirmed = {b.id: _aware(b.confirmed_at) for b in batches if b.status == "confirmed" and b.confirmed_at}
        if not confirmed:
            return {}
        rows = (
            await self.db.execute(
                select(Transaction.import_batch_id, Transaction.updated_at).where(
                    Transaction.import_batch_id.in_(list(confirmed)),
                    Transaction.is_deleted == False,  # noqa: E712
                    Transaction.user_id == batches[0].user_id,
                )
            )
        ).all()
        out: dict[str, int] = {}
        for bid, updated in rows:
            if updated is not None and _aware(updated) > confirmed[bid]:
                out[bid] = out.get(bid, 0) + 1
        return out

    async def _out(self, batch: ImportBatch, edited: Optional[dict[str, int]] = None) -> ImportBatchOut:
        if edited is None:
            edited = await self._edited_counts([batch])
        out = ImportBatchOut.model_validate(batch)
        out.edited_count = edited.get(batch.id, 0)
        return out

    async def list_batches(self, user_id: str, limit: int) -> list[ImportBatchOut]:
        batches = (
            await self.db.execute(
                select(ImportBatch)
                .where(ImportBatch.user_id == user_id, ImportBatch.status.in_(("confirmed", "undone")))
                .order_by(ImportBatch.created_at.desc(), ImportBatch.id)
                .limit(limit)
            )
        ).scalars().all()
        edited = await self._edited_counts(list(batches))
        return [await self._out(b, edited) for b in batches]

    async def get(self, user_id: str, batch_id: str) -> ImportBatchOut:
        return await self._out(await self._get(user_id, batch_id))

    async def discard_or_undo(self, user_id: str, batch_id: str) -> Optional[ImportBatchOut]:
        """preview -> se descarta (None); confirmed -> se deshace; undone -> 409."""
        batch = await self._get(user_id, batch_id)
        if batch.status == "preview":
            await self.db.delete(batch)
            await self.db.commit()
            return None
        if batch.status == "undone":
            raise HTTPException(status_code=409, detail="Esta importación ya se deshizo.")
        edited = await self._edited_counts([batch])
        now = _now()
        await self.db.execute(
            update(Transaction)
            .where(
                Transaction.import_batch_id == batch.id,
                Transaction.user_id == user_id,
                Transaction.is_deleted == False,  # noqa: E712
            )
            .values(is_deleted=True, deleted_at=now)
        )
        batch.status, batch.undone_at = "undone", now
        await self.db.commit()
        await self.db.refresh(batch)
        return await self._out(batch, edited)


class _Skip(Exception):
    """Fila que no es un movimiento (informativa o monto cero)."""
