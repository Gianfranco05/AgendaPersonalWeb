"""Reglas de calendario de los movimientos recurrentes: funciones puras, sin
base de datos ni reloj.

La ocurrencia k se calcula SIEMPRE desde el ancla (la primera fecha de la
regla), nunca desde la anterior. Asi el ajuste de fin de mes no se arrastra: un
"dia 31" da 31/01, 28/02 (o 29), 31/03, 30/04... y no 31/01, 28/02, 28/03.
"""

import calendar
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Iterator, Optional

#: Argentina: el mercado de la app. Se usa cuando el cliente no mando el offset.
DEFAULT_TZ_OFFSET_MINUTES = -180

DAILY, WEEKLY, MONTHLY, YEARLY = "daily", "weekly", "monthly", "yearly"
FREQUENCIES = (DAILY, WEEKLY, MONTHLY, YEARLY)
#: Maximo de "cada N" por frecuencia (minimo 1).
MAX_INTERVAL = {DAILY: 365, WEEKLY: 52, MONTHLY: 12, YEARLY: 10}

WEEKDAYS_PLURAL = (
    "lunes",
    "martes",
    "miércoles",
    "jueves",
    "viernes",
    "sábados",
    "domingos",
)


@dataclass(frozen=True)
class Rule:
    frequency: str
    interval_count: int = 1
    weekday: Optional[int] = None
    day_of_month: Optional[int] = None
    month_of_year: Optional[int] = None


# ── Huso horario ────────────────────────────────────────────────────────────


def effective_offset(offset: Optional[int]) -> int:
    return offset if offset is not None else DEFAULT_TZ_OFFSET_MINUTES


def local_now(now_utc: datetime, offset: Optional[int]) -> datetime:
    return now_utc + timedelta(minutes=effective_offset(offset))


def local_today(now_utc: datetime, offset: Optional[int]) -> date:
    return local_now(now_utc, offset).date()


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


# ── Validacion de la regla ──────────────────────────────────────────────────


def validate_rule(rule: Rule) -> None:
    """Campos obligatorios segun la frecuencia y rangos. Levanta `ValueError`
    con mensaje en espanol."""
    if rule.frequency not in FREQUENCIES:
        raise ValueError("La frecuencia debe ser diaria, semanal, mensual o anual")
    limit = MAX_INTERVAL[rule.frequency]
    if not (1 <= rule.interval_count <= limit):
        unit = {DAILY: "días", WEEKLY: "semanas", MONTHLY: "meses", YEARLY: "años"}[rule.frequency]
        raise ValueError(f"El intervalo tiene que estar entre 1 y {limit} {unit}")
    if rule.frequency == WEEKLY:
        if rule.weekday is None or not (0 <= rule.weekday <= 6):
            raise ValueError("Elegí el día de la semana (0 = lunes ... 6 = domingo)")
    if rule.frequency in (MONTHLY, YEARLY):
        if rule.day_of_month is None or not (1 <= rule.day_of_month <= 31):
            raise ValueError("Elegí el día del mes (entre 1 y 31)")
    if rule.frequency == YEARLY:
        if rule.month_of_year is None or not (1 <= rule.month_of_year <= 12):
            raise ValueError("Elegí el mes (entre 1 y 12)")
        # 29/02 vale (cae el 28 en anos no bisiestos); 30/02 o 31/04 no existen nunca.
        if rule.day_of_month > calendar.monthrange(2000, rule.month_of_year)[1]:
            raise ValueError("Ese día no existe en el mes elegido")


def normalize_rule(rule: Rule) -> Rule:
    """Deja en None los campos que no corresponden a la frecuencia."""
    return Rule(
        frequency=rule.frequency,
        interval_count=rule.interval_count,
        weekday=rule.weekday if rule.frequency == WEEKLY else None,
        day_of_month=rule.day_of_month if rule.frequency in (MONTHLY, YEARLY) else None,
        month_of_year=rule.month_of_year if rule.frequency == YEARLY else None,
    )


# ── Calendario ──────────────────────────────────────────────────────────────


def _last_day(year: int, month: int) -> int:
    return calendar.monthrange(year, month)[1]


def _clamped(year: int, month: int, day: int) -> date:
    return date(year, month, min(day, _last_day(year, month)))


def compute_anchor(rule: Rule, start_date: date, from_date: Optional[date] = None) -> date:
    """Primera fecha que cumple la regla en o despues de `max(start_date, from_date)`."""
    floor = max(start_date, from_date) if from_date is not None else start_date
    if rule.frequency == DAILY:
        return floor
    if rule.frequency == WEEKLY:
        return floor + timedelta(days=(rule.weekday - floor.weekday()) % 7)
    if rule.frequency == MONTHLY:
        year, month = floor.year, floor.month
        for _ in range(2):
            candidate = _clamped(year, month, rule.day_of_month)
            if candidate >= floor:
                return candidate
            year, month = (year + 1, 1) if month == 12 else (year, month + 1)
        return candidate  # pragma: no cover - el segundo mes siempre alcanza
    # yearly
    for year in (floor.year, floor.year + 1):
        candidate = _clamped(year, rule.month_of_year, rule.day_of_month)
        if candidate >= floor:
            return candidate
    raise AssertionError("unreachable")  # pragma: no cover


def occurrence(rule: Rule, anchor: date, k: int) -> date:
    """Ocurrencia numero `k` (0 = el ancla), calculada desde el ancla."""
    n = rule.interval_count
    if rule.frequency == DAILY:
        return anchor + timedelta(days=n * k)
    if rule.frequency == WEEKLY:
        return anchor + timedelta(days=7 * n * k)
    if rule.frequency == MONTHLY:
        index = anchor.year * 12 + (anchor.month - 1) + n * k
        return _clamped(index // 12, index % 12 + 1, rule.day_of_month)
    return _clamped(anchor.year + n * k, rule.month_of_year, rule.day_of_month)


def _estimate_k(rule: Rule, anchor: date, target: date) -> int:
    """Un k que seguro no se pasa de la primera ocurrencia >= target."""
    if target <= anchor:
        return 0
    n = rule.interval_count
    if rule.frequency == DAILY:
        return (target - anchor).days // n
    if rule.frequency == WEEKLY:
        return (target - anchor).days // (7 * n)
    if rule.frequency == MONTHLY:
        months = (target.year - anchor.year) * 12 + target.month - anchor.month
        return max(0, months // n - 1)
    return max(0, (target.year - anchor.year) // n - 1)


def first_on_or_after(rule: Rule, anchor: date, d: date) -> tuple[int, date]:
    """(k, fecha) de la primera ocurrencia >= `d`."""
    k = _estimate_k(rule, anchor, d)
    while True:
        value = occurrence(rule, anchor, k)
        if value >= d:
            return k, value
        k += 1


def next_after(rule: Rule, anchor: date, d: date) -> date:
    """Primera ocurrencia estrictamente posterior a `d`."""
    return first_on_or_after(rule, anchor, d + timedelta(days=1))[1]


def iter_from(
    rule: Rule, anchor: date, start: date, end_date: Optional[date] = None
) -> Iterator[date]:
    """Ocurrencias desde la primera >= `start`, sin pasar de `end_date`."""
    k, value = first_on_or_after(rule, anchor, start)
    while end_date is None or value <= end_date:
        yield value
        k += 1
        try:
            value = occurrence(rule, anchor, k)
        except (ValueError, OverflowError):  # se paso de date.max
            return


def occurrences_between(
    rule: Rule,
    anchor: date,
    start: date,
    end: date,
    end_date: Optional[date] = None,
    limit: Optional[int] = None,
) -> list[date]:
    """Ocurrencias en [start, end] (inclusive), respetando `end_date`."""
    cap = min(end, end_date) if end_date is not None else end
    result: list[date] = []
    for value in iter_from(rule, anchor, start, cap):
        result.append(value)
        if limit is not None and len(result) >= limit:
            break
    return result


def next_cursor(rule: Rule, anchor: date, after: date, end_date: Optional[date]) -> Optional[date]:
    """Siguiente ocurrencia posterior a `after`, o None si pasa de `end_date`."""
    value = next_after(rule, anchor, after)
    if end_date is not None and value > end_date:
        return None
    return value


def cursor_from(rule: Rule, anchor: date, floor: date, end_date: Optional[date]) -> Optional[date]:
    """Primera ocurrencia >= `floor`, o None si pasa de `end_date`."""
    value = first_on_or_after(rule, anchor, floor)[1]
    if end_date is not None and value > end_date:
        return None
    return value


# ── Etiqueta en espanol ─────────────────────────────────────────────────────


def rule_label(rule: Rule) -> str:
    n = rule.interval_count
    if rule.frequency == DAILY:
        return "Todos los días" if n == 1 else f"Cada {n} días"
    if rule.frequency == WEEKLY:
        day = WEEKDAYS_PLURAL[rule.weekday]
        return f"Todas las semanas los {day}" if n == 1 else f"Cada {n} semanas los {day}"
    suffix = " (o el último día del mes)" if (rule.day_of_month or 0) > 28 else ""
    if rule.frequency == MONTHLY:
        base = "Todos los meses" if n == 1 else f"Cada {n} meses"
        return f"{base} el día {rule.day_of_month}{suffix}"
    base = "Todos los años" if n == 1 else f"Cada {n} años"
    return f"{base} el {rule.day_of_month:02d}/{rule.month_of_year:02d}{suffix}"
