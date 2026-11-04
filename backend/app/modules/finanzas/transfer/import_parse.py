"""Lectura segura y parseo de archivos a importar (CSV/XLSX).

El archivo es entrada NO confiable: el tamano se corta antes de parsear, el
tipo se decide por contenido (no por extension), los .xlsx se inspeccionan
como zip antes de abrirlos (zip bombs, rutas, macros), openpyxl corre con
defusedxml (sin entidades XML) y nunca se evalua una formula: solo se leen
los valores guardados.
"""

import csv
import hashlib
import io
import re
import unicodedata
import zipfile
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal
from typing import Optional

from app.config import settings

MAX_CELL_CHARS = 500
HEADER_SCAN_ROWS = 30
XLSX_MAX_ENTRIES = 200
XLSX_MAX_UNCOMPRESSED = 25 * 1024 * 1024
XLSX_MAX_RATIO = 100
XLSX_RATIO_MIN_SIZE = 1024 * 1024
MIN_DATE = date(2000, 1, 1)
MAX_AMOUNT = Decimal("9999999999.99")
FORMULA_NO_VALUE = "#FORMULA_SIN_VALOR"
UNSUPPORTED = "Formato no soportado: subí un .csv o .xlsx."
OLE_SIGNATURE = b"\xd0\xcf\x11\xe0"


class ImportFileError(Exception):
    """Error del archivo subido, con el status HTTP que corresponde."""

    def __init__(self, status_code: int, detail: str):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


@dataclass
class RawTable:
    kind: str  # "csv" | "xlsx"
    rows: list[list[str]]


# ── Texto ───────────────────────────────────────────────────────────────────

_CONTROL = re.compile(r"[\x00-\x1f\x7f]")


def strip_accents(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c))


def normalize_header(text: str) -> str:
    t = strip_accents(str(text)).lower().replace("_", " ").replace("-", " ")
    return re.sub(r"\s+", " ", t).strip()


def sanitize_text(text: str) -> str:
    return re.sub(r"\s+", " ", _CONTROL.sub(" ", str(text)).replace("\x00", "")).strip()


def header_signature(headers: list[str]) -> str:
    joined = "|".join(normalize_header(h) for h in headers if str(h).strip())
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()


# ── Recepcion y tipo ────────────────────────────────────────────────────────


async def read_upload(upload, max_bytes: Optional[int] = None) -> bytes:
    """Lee el UploadFile por chunks y corta apenas se pasa del tope (no se
    confia solo en Content-Length)."""
    limit = settings.FINANCE_IMPORT_MAX_BYTES if max_bytes is None else max_bytes
    buf = bytearray()
    while True:
        chunk = await upload.read(64 * 1024)
        if not chunk:
            break
        buf.extend(chunk)
        if len(buf) > limit:
            raise ImportFileError(
                413, f"El archivo pesa más de {limit // (1024 * 1024)} MB. Dividilo por fechas."
            )
    if not buf:
        raise ImportFileError(422, "El archivo está vacío.")
    return bytes(buf)


def detect_kind(data: bytes) -> str:
    if data.startswith(b"PK\x03\x04"):
        return "xlsx"
    if data.startswith(OLE_SIGNATURE):
        raise ImportFileError(
            415, "Es un .xls viejo: abrilo en Excel y guardalo como .xlsx o .csv."
        )
    if data.startswith(b"%PDF") or b"\x00" in data[:4096]:
        raise ImportFileError(415, UNSUPPORTED)
    return "csv"


def load_table(data: bytes) -> RawTable:
    kind = detect_kind(data)
    rows = _load_csv(data) if kind == "csv" else _load_xlsx(data)
    return RawTable(kind=kind, rows=_finish_rows(rows))


def _finish_rows(rows: list[list[str]]) -> list[list[str]]:
    max_rows = settings.FINANCE_IMPORT_MAX_ROWS
    max_cols = settings.FINANCE_IMPORT_MAX_COLUMNS
    cleaned = []
    for r in rows:
        cells = [c.strip()[:MAX_CELL_CHARS] for c in r]
        if any(cells):
            cleaned.append(cells)
    if not cleaned:
        raise ImportFileError(422, "El archivo no tiene filas con datos.")
    width = max(len(r) for r in cleaned)
    if width > max_cols:
        raise ImportFileError(422, f"El archivo tiene más de {max_cols} columnas.")
    if len(cleaned) - 1 > max_rows:
        raise ImportFileError(
            422, f"El archivo tiene más de {max_rows:,} movimientos: dividilo por fechas.".replace(",", ".")
        )
    return [r + [""] * (width - len(r)) for r in cleaned]


# ── CSV ─────────────────────────────────────────────────────────────────────


def _decode(data: bytes) -> str:
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError:
        return data.decode("cp1252", errors="replace")


def _pick_delimiter(sample_lines: list[str]) -> str:
    best, best_score = ",", -1
    for delim in (";", ",", "\t", "|"):
        widths = [len(r) for r in csv.reader(sample_lines, delimiter=delim) if r]
        if not widths:
            continue
        modal = max(set(widths), key=lambda w: (widths.count(w) if w > 1 else 0, w))
        score = (widths.count(modal) * 100 + modal) if modal > 1 else 0
        if score > best_score:
            best, best_score = delim, score
    return best


def _load_csv(data: bytes) -> list[list[str]]:
    text = _decode(data).replace("\x00", "").replace("\r\n", "\n").replace("\r", "\n")
    lines = [ln for ln in text.split("\n") if ln.strip()]
    delim = _pick_delimiter(lines[:40])
    try:
        return [list(r) for r in csv.reader(io.StringIO(text), delimiter=delim)]
    except csv.Error:
        raise ImportFileError(422, "No pudimos leer el CSV: revisá que esté bien formado.")


# ── XLSX ────────────────────────────────────────────────────────────────────


def _inspect_zip(data: bytes) -> None:
    try:
        z = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile:
        raise ImportFileError(415, UNSUPPORTED)
    with z:
        infos = z.infolist()
        if len(infos) > XLSX_MAX_ENTRIES:
            raise ImportFileError(422, "El .xlsx tiene demasiados componentes internos.")
        declared = sum(i.file_size for i in infos)
        if declared > XLSX_MAX_UNCOMPRESSED:
            raise ImportFileError(422, "El .xlsx descomprimido es demasiado grande.")
        for info in infos:
            name = info.filename
            if name.startswith(("/", "\\")) or ".." in name.replace("\\", "/").split("/"):
                raise ImportFileError(422, "El .xlsx tiene rutas internas no válidas.")
            if name.lower().endswith("vbaproject.bin"):
                raise ImportFileError(422, "El archivo tiene macros: guardalo como .xlsx sin macros.")
            if info.file_size > XLSX_RATIO_MIN_SIZE and info.file_size / max(info.compress_size, 1) > XLSX_MAX_RATIO:
                raise ImportFileError(422, "El .xlsx tiene un componente sospechosamente comprimido.")
        # El tamano declarado en el zip puede mentir: se cuenta lo que realmente se descomprime.
        total = 0
        for info in infos:
            with z.open(info) as f:
                while True:
                    chunk = f.read(1024 * 1024)
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > XLSX_MAX_UNCOMPRESSED:
                        raise ImportFileError(422, "El .xlsx descomprimido es demasiado grande.")


def _cell_text(v) -> str:
    if v is None:
        return ""
    if isinstance(v, datetime):
        if v.time() == time(0, 0) and v.tzinfo is None:
            return v.date().isoformat()
        return v.replace(tzinfo=None).isoformat()
    if isinstance(v, date):
        return v.isoformat()
    if isinstance(v, time):
        return v.strftime("%H:%M:%S")
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float, Decimal)):
        d = Decimal(str(v))
        text = format(d, "f")
        if "." in text:
            text = text.rstrip("0").rstrip(".")
        return text
    return str(v)


def _load_xlsx(data: bytes) -> list[list[str]]:
    _inspect_zip(data)
    from openpyxl import load_workbook

    max_rows = settings.FINANCE_IMPORT_MAX_ROWS + HEADER_SCAN_ROWS + 5
    try:
        values_wb = load_workbook(io.BytesIO(data), read_only=True, data_only=True)
        formulas_wb = load_workbook(io.BytesIO(data), read_only=True, data_only=False)
        try:
            sheet = next(
                (ws for ws in values_wb.worksheets if getattr(ws, "sheet_state", "visible") == "visible"),
                None,
            )
            if sheet is None:
                raise ImportFileError(422, "El .xlsx no tiene hojas visibles.")
            formula_sheet = formulas_wb[sheet.title]
            rows: list[list[str]] = []
            for vals, fvals in zip(
                sheet.iter_rows(values_only=True), formula_sheet.iter_rows(values_only=True)
            ):
                row = []
                for v, f in zip(vals, fvals):
                    if v is None and isinstance(f, str) and f.startswith("="):
                        row.append(FORMULA_NO_VALUE)
                    else:
                        row.append(_cell_text(v))
                rows.append(row)
                if len(rows) > max_rows:
                    break
            return rows
        finally:
            values_wb.close()
            formulas_wb.close()
    except ImportFileError:
        raise
    except Exception:
        raise ImportFileError(
            422, "No pudimos leer el .xlsx: puede estar dañado o no ser un Excel válido."
        )


# ── Encabezado ──────────────────────────────────────────────────────────────


def find_header_row(rows: list[list[str]]) -> int:
    from app.modules.finanzas.transfer.import_presets import is_known_header

    best, best_score = 0, 1
    for i, row in enumerate(rows[:HEADER_SCAN_ROWS]):
        score = sum(1 for c in row if is_known_header(normalize_header(c)))
        if score > best_score:
            best, best_score = i, score
    return best


# ── Fechas ──────────────────────────────────────────────────────────────────

_ISO = re.compile(
    r"^(\d{4})-(\d{1,2})-(\d{1,2})(?:[T ]+(\d{1,2}):(\d{2})(?::(\d{2})(?:[.,]\d+)?)?\s*(Z|[+-]\d{2}(?::?\d{2})?)?)?$"
)
_SLASH = re.compile(
    r"^(\d{1,2})[/.\-](\d{1,2})[/.\-](\d{2}|\d{4})(?:[T ]+(\d{1,2}):(\d{2})(?::(\d{2}))?)?$"
)
_SERIAL = re.compile(r"^(\d{5})(?:\.\d+)?$")
_EXCEL_EPOCH = date(1899, 12, 30)


def _max_date(today: date) -> date:
    try:
        return today.replace(year=today.year + 1)
    except ValueError:  # 29/02
        return today.replace(year=today.year + 1, day=28)


def _check_range(d: date, today: date) -> date:
    if d < MIN_DATE or d > _max_date(today):
        raise ValueError("fecha fuera de rango")
    return d


def parse_datetime_cell(
    text: str, dayfirst: bool, tz_offset_minutes: int, today: date
) -> tuple[date, Optional[time]]:
    """Fecha (y hora, si viene) de una celda. Una fecha ISO con zona se pasa a
    la hora local del usuario."""
    s = str(text).strip()
    if not s:
        raise ValueError("fecha vacía")
    try:
        m = _ISO.match(s)
        if m:
            y, mo, d = int(m[1]), int(m[2]), int(m[3])
            day = date(y, mo, d)
            if m[4] is None:
                return _check_range(day, today), None
            hh, mi, ss = int(m[4]), int(m[5]), int(m[6] or 0)
            dt = datetime(y, mo, d, hh, mi, ss)
            if m[7]:
                zone = m[7]
                if zone == "Z":
                    offset = timedelta(0)
                else:
                    sign = -1 if zone[0] == "-" else 1
                    digits = zone[1:].replace(":", "")
                    offset = sign * timedelta(hours=int(digits[:2]), minutes=int(digits[2:4] or 0))
                dt = (dt - offset) + timedelta(minutes=tz_offset_minutes)
            return _check_range(dt.date(), today), dt.time()
        m = _SLASH.match(s)
        if m:
            a, b, y = int(m[1]), int(m[2]), int(m[3])
            if y < 100:
                y += 2000
            day = date(y, b, a) if dayfirst else date(y, a, b)
            t = time(int(m[4]), int(m[5]), int(m[6] or 0)) if m[4] else None
            return _check_range(day, today), t
        m = _SERIAL.match(s)
        if m and 20000 <= int(m[1]) <= 80000:
            value = float(s)
            day = _EXCEL_EPOCH + timedelta(days=int(value))
            frac = value - int(value)
            t = None
            if frac:
                secs = round(frac * 86400)
                t = (datetime.min + timedelta(seconds=secs)).time()
            return _check_range(day, today), t
    except OverflowError:
        raise ValueError("fecha inválida")
    except ValueError as e:
        if "fuera de rango" in str(e):
            raise
        raise ValueError("fecha inválida")
    raise ValueError("fecha inválida")


def parse_time_cell(text: str) -> Optional[time]:
    m = re.match(r"^(\d{1,2}):(\d{2})(?::(\d{2}))?", str(text).strip())
    if not m:
        return None
    try:
        return time(int(m[1]), int(m[2]), int(m[3] or 0))
    except ValueError:
        return None


def detect_dayfirst(values: list[str]) -> tuple[bool, bool]:
    """(dia primero?, ambigua?). Sin pistas queda dd/mm (es-AR) y avisa."""
    day_evidence = month_evidence = slash_seen = False
    for v in values:
        m = _SLASH.match(str(v).strip())
        if not m:
            continue
        slash_seen = True
        if int(m[1]) > 12:
            day_evidence = True
        if int(m[2]) > 12:
            month_evidence = True
    if not slash_seen:
        return True, False
    if day_evidence and not month_evidence:
        return True, False
    if month_evidence and not day_evidence:
        return False, False
    return True, True


# ── Numeros ─────────────────────────────────────────────────────────────────

_CURRENCY_WORDS = re.compile(r"u\$s|us\$|u\$d|ars|usd|eur|brl|uyu|clp|\$|€", re.IGNORECASE)
_DIGITS = re.compile(r"^[\d.,]+$")
_DOT_THOUSANDS = re.compile(r"^\d{1,3}(\.\d{3})+$")


def _strip_amount(text: str) -> str:
    return _CURRENCY_WORDS.sub("", str(text)).replace(" ", "").replace(" ", "").strip()


def infer_dot_mode(values: list[str]) -> str:
    """Un punto con 3 digitos atras ("1.234"): miles (default es-AR) salvo que
    la columna tenga algun valor con punto y 1-2 decimales ("12.50") o 4+."""
    for v in values:
        s = _strip_amount(v).lstrip("-(").rstrip(")-")
        if re.match(r"^\d+\.\d{1,2}$", s) or re.match(r"^\d+\.\d{4,}$", s):
            return "decimal"
    return "thousands"


def parse_amount(text: str, decimal_separator: str = "auto", dot_mode: str = "thousands") -> Decimal:
    raw = _strip_amount(text)
    if not raw:
        raise ValueError("monto vacío")
    negative = False
    if raw.startswith("(") and raw.endswith(")"):
        negative, raw = True, raw[1:-1]
    if raw.startswith("-"):
        negative, raw = True, raw[1:]
    elif raw.endswith("-"):
        negative, raw = True, raw[:-1]
    if raw.startswith("+"):
        raw = raw[1:]
    if not raw or not _DIGITS.match(raw) or not any(c.isdigit() for c in raw):
        raise ValueError("monto inválido")

    if decimal_separator == ",":
        normalized = raw.replace(".", "").replace(",", ".")
    elif decimal_separator == ".":
        normalized = raw.replace(",", "")
    else:
        has_dot, has_comma = "." in raw, "," in raw
        if has_dot and has_comma:
            if raw.rfind(".") > raw.rfind(","):
                normalized = raw.replace(",", "")
            else:
                normalized = raw.replace(".", "").replace(",", ".")
        elif has_comma:
            normalized = raw.replace(",", "") if raw.count(",") > 1 else raw.replace(",", ".")
        elif has_dot:
            if raw.count(".") > 1:
                normalized = raw.replace(".", "")
            elif dot_mode == "thousands" and _DOT_THOUSANDS.match(raw):
                normalized = raw.replace(".", "")
            else:
                normalized = raw
        else:
            normalized = raw
    if normalized.count(".") > 1:
        raise ValueError("monto inválido")
    try:
        value = Decimal(normalized).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except Exception:
        raise ValueError("monto inválido")
    if value > MAX_AMOUNT:
        raise ValueError("monto fuera de rango (máximo 9.999.999.999,99)")
    return -value if negative else value


_CURRENCIES = {
    "$": "ARS", "ARS": "ARS", "PESOS": "ARS", "PESO": "ARS", "$ARS": "ARS",
    "U$S": "USD", "US$": "USD", "U$D": "USD", "USD": "USD", "DOLARES": "USD", "DOLAR": "USD",
    "EUR": "EUR", "€": "EUR", "EUROS": "EUR", "BRL": "BRL", "UYU": "UYU", "CLP": "CLP",
}


def normalize_currency(raw: str) -> Optional[str]:
    key = strip_accents(str(raw)).strip().upper()
    if not key:
        return None
    code = _CURRENCIES.get(key)
    if code is None:
        raise ValueError(f"moneda no soportada: {sanitize_text(raw)[:10]}")
    return code
