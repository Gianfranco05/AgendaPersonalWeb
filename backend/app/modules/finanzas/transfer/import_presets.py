"""Presets de origen (Mercado Pago) y heuristica para archivos genericos.

NOTA de verificacion: los identificadores de columna de los reportes de
Mercado Pago salen de su documentacion publica (reportes "Dinero disponible" y
"Dinero en cuenta", verificada en 2026). No tuvimos un archivo real: los alias
en espanol/portugues son razonables pero no confirmados, por eso el matcheo es
tolerante y el importador generico con mapeo editable es el respaldo. Hay que
validar con un archivo real y ajustar los alias (tarea 9.4 del change).
"""

from dataclasses import dataclass
from typing import Optional

from app.modules.finanzas.transfer.schemas import ColumnFilter, ImportMapping

GENERIC = "generic"
MP_RELEASE = "mercadopago_release"
MP_ACCOUNT = "mercadopago_account_money"

PAYMENT_BY_PRESET = {MP_RELEASE: "transfer", MP_ACCOUNT: "transfer", GENERIC: "other"}
BANK_LABEL_BY_PRESET = {MP_RELEASE: "Mercado Pago", MP_ACCOUNT: "Mercado Pago", GENERIC: ""}

# Alias ya normalizados (minusculas, sin tildes, "_" y "-" como espacio).
_MP_RELEASE_FIELDS: dict[str, tuple[str, ...]] = {
    "date": ("date", "date short", "fecha", "fecha de liberacion", "data"),
    "record_type": ("record type", "tipo de registro", "tipo de registo"),
    "description": ("description", "descripcion", "descricao"),
    "net_credit": ("net credit amount", "monto neto acreditado", "credito neto", "valor liquido credito"),
    "net_debit": ("net debit amount", "monto neto debitado", "debito neto", "valor liquido debito"),
    "currency": ("currency", "moneda", "moeda"),
    "source_id": ("source id", "id de origen", "id de la operacion", "id origem"),
    "external_reference": ("external reference", "referencia externa", "referencia externa de la operacion"),
}
_MP_RELEASE_REQUIRED = ("date", "record_type", "net_credit", "net_debit")

_MP_ACCOUNT_FIELDS: dict[str, tuple[str, ...]] = {
    "date": ("transaction date", "fecha de la transaccion", "fecha de transaccion", "data da transacao"),
    "transaction_type": ("transaction type", "tipo de transaccion", "tipo de operacion", "tipo de transacao"),
    "settlement_net": (
        "settlement net amount", "monto neto de liquidacion", "monto neto", "valor liquido da liquidacao",
    ),
    "transaction_amount": ("transaction amount", "monto de la transaccion", "valor da transacao"),
    "description": ("description", "descripcion", "descricao"),
    "currency": (
        "settlement currency", "moneda de liquidacion", "transaction currency", "moneda de la transaccion",
    ),
    "source_id": ("source id", "id de origen", "id origem"),
}
_MP_ACCOUNT_REQUIRED = ("date", "transaction_type")

_GENERIC_FIELDS: dict[str, tuple[str, ...]] = {
    "date": (
        "fecha", "fecha operacion", "fecha de operacion", "fecha valor", "fecha movimiento",
        "fecha de movimiento", "fecha contable", "fecha de la operacion", "date", "data",
    ),
    "time": ("hora", "time"),
    "description": (
        "descripcion", "concepto", "detalle", "movimiento", "referencia", "description", "leyenda",
        "descripcion del movimiento", "detalle del movimiento",
    ),
    "amount": ("importe", "monto", "valor", "amount", "importe en pesos", "importe pesos"),
    "debit": ("debito", "debitos", "debe", "egreso", "egresos", "retiro", "retiros", "gasto"),
    "credit": ("credito", "creditos", "haber", "ingreso", "ingresos", "deposito", "depositos"),
    "currency": ("moneda", "divisa", "currency"),
    "reference": (
        "comprobante", "nro operacion", "numero de operacion", "nro comprobante", "id operacion",
        "codigo", "nro de operacion",
    ),
    "balance": ("saldo", "balance", "saldo parcial"),
}

# Traducciones de codigos del origen (claves en minuscula, "_" como espacio).
_TABLES: dict[str, dict[str, str]] = {
    "mp_release": {
        "payment": "Cobro",
        "refund": "Devolución",
        "payout": "Retiro",
        "chargeback": "Contracargo",
        "shipping": "Envío",
        "asset management gain": "Rendimiento",
        "dispute": "Disputa",
    },
    "mp_account": {
        "settlement": "Cobro",
        "refund": "Devolución",
        "chargeback": "Contracargo",
        "dispute": "Disputa",
        "withdrawal": "Retiro",
        "withdrawal cancel": "Retiro cancelado",
        "payout": "Retiro",
        "cashback": "Cashback",
    },
}

_MP_ACCOUNT_TYPES = {
    "expense": ["withdrawal", "payout", "refund", "chargeback", "dispute"],
    "income": ["settlement", "withdrawal cancel", "cashback"],
}

_ALL_ALIASES: frozenset[str] = frozenset(
    a
    for group in (_MP_RELEASE_FIELDS, _MP_ACCOUNT_FIELDS, _GENERIC_FIELDS)
    for aliases in group.values()
    for a in aliases
)


def translate(table: str, value: str) -> str:
    """Traduce un codigo del origen; si no lo conoce lo deja tal cual (con
    `tax_*` agrupado como impuesto)."""
    key = value.strip().lower().replace("_", " ").replace("-", " ")
    if table == "mp_release" and key.startswith("tax"):
        return "Impuesto / retención"
    return _TABLES.get(table, {}).get(key, value.strip())


def is_known_header(norm: str) -> bool:
    return bool(norm) and norm in _ALL_ALIASES


def _find(headers: list[str], aliases: tuple[str, ...], used: set[int]) -> Optional[int]:
    for i, h in enumerate(headers):
        if i not in used and h in aliases:
            return i
    # Tolerancia: el alias largo contenido en el encabezado ("fecha operacion contable").
    for i, h in enumerate(headers):
        if i not in used and any(len(a) >= 8 and a in h for a in aliases):
            return i
    return None


def _match(headers: list[str], fields: dict[str, tuple[str, ...]]) -> dict[str, int]:
    found: dict[str, int] = {}
    used: set[int] = set()
    for field, aliases in fields.items():
        idx = _find(headers, aliases, used)
        if idx is not None:
            found[field] = idx
            used.add(idx)
    return found


@dataclass(frozen=True)
class PresetDef:
    key: str
    label: str
    description: str
    required_fields: tuple[str, ...]


PRESETS: list[PresetDef] = [
    PresetDef(
        MP_RELEASE,
        "Mercado Pago · Dinero disponible",
        "Reporte de dinero disponible (released money) de Mercado Pago, en .csv o .xlsx.",
        ("Fecha", "Tipo de registro", "Crédito neto", "Débito neto"),
    ),
    PresetDef(
        MP_ACCOUNT,
        "Mercado Pago · Dinero en cuenta",
        "Reporte de dinero en cuenta (account money) de Mercado Pago, en .csv o .xlsx.",
        ("Fecha de la transacción", "Tipo de transacción", "Monto neto"),
    ),
    PresetDef(
        GENERIC,
        "Otro banco o billetera (CSV/Excel)",
        "Cualquier archivo con fecha, descripción y monto (con signo o en débito/crédito). Elegís las columnas una vez y la app las recuerda.",
        ("Fecha", "Monto, o Débito y Crédito"),
    ),
]
PRESET_KEYS = {p.key for p in PRESETS}


def _mp_release_mapping(h: dict[str, int]) -> ImportMapping:
    desc = [h[k] for k in ("description", "external_reference") if k in h]
    return ImportMapping(
        date=h["date"],
        description=desc,
        amount_mode="debit_credit",
        debit=h.get("net_debit"),
        credit=h.get("net_credit"),
        currency=h.get("currency"),
        reference=h.get("source_id"),
        include_when=ColumnFilter(column=h["record_type"], values=["release"]),
        translations={str(h["description"]): "mp_release"} if "description" in h else {},
    )


def _mp_account_mapping(h: dict[str, int]) -> ImportMapping:
    desc = [h["transaction_type"]] + ([h["description"]] if "description" in h else [])
    return ImportMapping(
        date=h["date"],
        description=desc,
        amount_mode="signed",
        amount=h.get("settlement_net", h.get("transaction_amount")),
        fallback_amount=h.get("transaction_amount") if "settlement_net" in h else None,
        type_column=h["transaction_type"],
        type_values=_MP_ACCOUNT_TYPES,
        currency=h.get("currency"),
        reference=h.get("source_id"),
        translations={str(h["transaction_type"]): "mp_account"},
    )


def generic_mapping(headers: list[str]) -> ImportMapping:
    h = _match(headers, _GENERIC_FIELDS)
    desc = [h["description"]] if "description" in h else []
    mode = "signed"
    if "amount" not in h and ("debit" in h or "credit" in h):
        mode = "debit_credit"
    return ImportMapping(
        date=h.get("date"),
        time=h.get("time"),
        description=desc,
        amount_mode=mode,
        amount=h.get("amount"),
        debit=h.get("debit"),
        credit=h.get("credit"),
        currency=h.get("currency"),
        reference=h.get("reference"),
    )


def build_mapping(preset: str, headers: list[str]) -> Optional[ImportMapping]:
    """Mapeo del preset para estos encabezados normalizados, o None si no matchea."""
    if preset == MP_RELEASE:
        h = _match(headers, _MP_RELEASE_FIELDS)
        return _mp_release_mapping(h) if all(k in h for k in _MP_RELEASE_REQUIRED) else None
    if preset == MP_ACCOUNT:
        h = _match(headers, _MP_ACCOUNT_FIELDS)
        ok = all(k in h for k in _MP_ACCOUNT_REQUIRED) and (
            "settlement_net" in h or "transaction_amount" in h
        )
        return _mp_account_mapping(h) if ok else None
    if preset == GENERIC:
        return generic_mapping(headers)
    return None


def detect_preset(headers: list[str]) -> str:
    """Primer preset de Mercado Pago cuyas columnas requeridas estan todas; si
    ninguno, `generic`."""
    for key in (MP_RELEASE, MP_ACCOUNT):
        if build_mapping(key, headers) is not None:
            return key
    return GENERIC
