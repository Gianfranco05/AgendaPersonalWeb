from datetime import date, datetime, time
from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator

Currency = Literal["ARS", "USD", "EUR", "BRL", "UYU", "CLP"]
RowStatus = Literal["ok", "error", "skipped", "duplicate", "possible_duplicate"]
MappingSource = Literal["preset", "remembered", "heuristic", "user"]
ColIndex = Optional[int]


class ColumnFilter(BaseModel):
    column: int = Field(ge=0, le=200)
    values: list[str] = Field(default_factory=list, max_length=50)


class ImportMapping(BaseModel):
    """Que columna es que. Las columnas van por indice (posicion en el archivo):
    la firma de encabezados del lote asegura que el mapeo recordado aplica a
    archivos con las mismas columnas en el mismo orden."""

    date: ColIndex = Field(None, ge=0, le=200)
    time: ColIndex = Field(None, ge=0, le=200)
    description: list[int] = Field(default_factory=list, max_length=6)
    amount_mode: Literal["signed", "debit_credit", "amount_and_type"] = "signed"
    amount: ColIndex = Field(None, ge=0, le=200)
    #: Columna de respaldo si `amount` viene vacio (su signo sale de `type_column`).
    fallback_amount: ColIndex = Field(None, ge=0, le=200)
    debit: ColIndex = Field(None, ge=0, le=200)
    credit: ColIndex = Field(None, ge=0, le=200)
    type_column: ColIndex = Field(None, ge=0, le=200)
    #: {"income": [...], "expense": [...]} con valores normalizados (sin tildes, minuscula).
    type_values: dict[str, list[str]] = Field(default_factory=dict)
    currency: ColIndex = Field(None, ge=0, le=200)
    default_currency: Currency = "ARS"
    reference: ColIndex = Field(None, ge=0, le=200)
    include_when: Optional[ColumnFilter] = None
    skip_when: Optional[ColumnFilter] = None
    #: {"<columna>": "<tabla>"}: traduce codigos del origen (p. ej. Mercado Pago).
    translations: dict[str, str] = Field(default_factory=dict)
    date_format: Literal["auto", "dd/mm/yyyy", "mm/dd/yyyy", "yyyy-mm-dd", "iso_datetime"] = "auto"
    decimal_separator: Literal["auto", ",", "."] = "auto"
    invert_sign: bool = False
    tz_offset_minutes: int = Field(0, ge=-840, le=840)

    @field_validator("description")
    @classmethod
    def _desc_idx(cls, v):
        if any(i < 0 or i > 200 for i in v):
            raise ValueError("Columna fuera de rango")
        return v

    def is_complete(self) -> bool:
        if self.date is None:
            return False
        if self.amount_mode == "debit_credit":
            return self.debit is not None or self.credit is not None
        if self.amount_mode == "amount_and_type":
            return self.amount is not None and self.type_column is not None
        return self.amount is not None or self.fallback_amount is not None


class DuplicateOf(BaseModel):
    id: str
    date: date
    description: str


class ParsedRow(BaseModel):
    index: int
    source_line: int
    date: Optional[date] = None
    time: Optional[time] = None
    description: str = ""
    amount: Optional[Decimal] = None
    type: Optional[Literal["income", "expense"]] = None
    currency: Optional[str] = None
    reference: str = ""
    status: RowStatus
    errors: list[str] = Field(default_factory=list)
    row_hash: Optional[str] = None
    duplicate_of: Optional[DuplicateOf] = None
    suggested_category_id: Optional[str] = None
    suggestion_source: Literal["history", "rule", "none"] = "none"
    merchant_category: str = "other"


class ImportCounts(BaseModel):
    ok: int = 0
    error: int = 0
    duplicate: int = 0
    possible_duplicate: int = 0
    skipped: int = 0


class CurrencyTotal(BaseModel):
    currency: str
    income: Decimal
    expense: Decimal
    count: int


class ImportPreview(BaseModel):
    batch_id: str
    preset: str
    detected_preset: str
    mapping: ImportMapping
    mapping_source: MappingSource
    mapping_complete: bool
    headers: list[str]
    header_row: int
    sample_rows: list[list[str]]
    rows: list[ParsedRow]
    counts: ImportCounts
    totals_by_currency: list[CurrencyTotal]
    warnings: list[str]
    expires_at: Optional[datetime] = None
    filename: str = ""
    account_id: Optional[str] = None


class MappingUpdate(BaseModel):
    preset: Optional[str] = Field(None, max_length=40)
    header_row: Optional[int] = Field(None, ge=0, le=200)
    mapping: Optional[ImportMapping] = None
    account_id: Optional[str] = Field(None, max_length=36)
    tz_offset_minutes: Optional[int] = Field(None, ge=-840, le=840)


class ConfirmRow(BaseModel):
    index: int = Field(ge=0)
    include: bool = True
    category_id: Optional[str] = Field(None, max_length=36)
    type: Optional[Literal["income", "expense"]] = None
    description: Optional[str] = Field(None, min_length=1, max_length=255)


class ConfirmRequest(BaseModel):
    rows: list[ConfirmRow] = Field(max_length=5_000)


class ImportBatchOut(BaseModel):
    id: str
    status: str
    preset: str
    filename: str
    account_id: Optional[str] = None
    row_count: int
    imported_count: int
    skipped_count: int
    duplicate_count: int
    error_count: int
    #: Movimientos del lote que el usuario edito despues de importar (solo `confirmed`).
    edited_count: int = 0
    created_at: Optional[datetime] = None
    confirmed_at: Optional[datetime] = None
    undone_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ImportPresetOut(BaseModel):
    key: str
    label: str
    description: str
    required_fields: list[str]
