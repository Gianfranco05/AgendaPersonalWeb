"""Inflacion acumulada y rendimiento real: calculos puros (sin base ni HTTP).

La serie es `{primer dia del mes: variacion mensual %}` del IPC nacional.
Todo se hace en `Decimal` con precision 28. Un periodo `[inicio, fin)` toma
cada mes que se superpone y lo prorratea con interes compuesto: se supone una
inflacion diaria uniforme dentro del mes, `f = (1 + pi/100) ^ (dias / dias_del_mes)`.
Los meses sin dato publicado (el actual siempre, y el anterior hasta que el
INDEC publica, a mediados de mes) se estiman con el ultimo dato disponible y
el resultado queda marcado como estimado.
"""

import calendar
from dataclasses import dataclass, field
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from typing import Mapping, Optional

ZERO = Decimal("0")
ONE = Decimal("1")
HUNDRED = Decimal("100")
CENT = Decimal("0.01")

#: Motivos por los que no hay rendimiento real (los muestran los clientes).
REASON_CURRENCY = "currency"
REASON_NO_START_DATE = "no_start_date"
REASON_TOO_SHORT = "too_short"
REASON_NO_INFLATION = "no_inflation_data"
REASON_NO_INVESTED = "no_invested_amount"


def _round2(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def month_key(period: date) -> str:
    return f"{period.year:04d}-{period.month:02d}"


def _next_month(period: date) -> date:
    return date(period.year + 1, 1, 1) if period.month == 12 else date(period.year, period.month + 1, 1)


def _days_in_month(period: date) -> int:
    return calendar.monthrange(period.year, period.month)[1]


@dataclass(frozen=True)
class InflationFactor:
    factor: Decimal
    estimated: bool
    estimated_months: tuple[str, ...] = ()

    @property
    def inflation_pct(self) -> Decimal:
        return (self.factor - ONE) * HUNDRED


def accumulated_factor(
    series: Mapping[date, Decimal], start: date, end: date
) -> Optional[InflationFactor]:
    """Factor de inflacion acumulada de `[start, end)`, o None si la serie no
    cubre el inicio (o esta vacia). `end <= start` da factor 1."""
    if not series:
        return None
    first_period = min(series)
    last_period = max(series)
    if start < first_period:
        return None
    factor = ONE
    estimated: list[str] = []
    cursor = start.replace(day=1)
    while cursor < end:
        nxt = _next_month(cursor)
        covered = (min(end, nxt) - max(start, cursor)).days
        if covered > 0:
            published = series.get(cursor)
            if published is None:
                # Mes sin publicar: se estima con el ultimo dato disponible.
                published = series[last_period]
                estimated.append(month_key(cursor))
            growth = ONE + Decimal(published) / HUNDRED
            if covered == _days_in_month(cursor):
                factor *= growth
            else:
                factor *= growth ** (Decimal(covered) / Decimal(_days_in_month(cursor)))
        cursor = nxt
    return InflationFactor(factor, bool(estimated), tuple(estimated))


@dataclass(frozen=True)
class Projection:
    nominal_pct: Decimal
    inflation_pct: Decimal
    real_pct: Decimal
    estimated: bool


@dataclass(frozen=True)
class RealReturn:
    nominal_pct: Decimal
    inflation_pct: Decimal
    real_pct: Decimal
    estimated: bool
    estimated_months: tuple[str, ...]
    period_start: date
    period_end: date
    projected_at_maturity: Optional[Projection] = None
    #: Para el agregado de cartera (no se serializan): monto y factor.
    invested: Decimal = field(default=ZERO, repr=False)
    value: Decimal = field(default=ZERO, repr=False)
    factor: Decimal = field(default=ONE, repr=False)


def _real_pct(nominal_ratio: Decimal, factor: Decimal) -> Decimal:
    return (nominal_ratio / factor - ONE) * HUNDRED


def compute_real_return(
    *,
    invested: Decimal,
    value: Decimal,
    start: date,
    end: date,
    series: Mapping[date, Decimal],
) -> tuple[Optional[RealReturn], Optional[str]]:
    """Rendimiento real de un activo en pesos entre `start` y `end`.
    Devuelve `(resultado, None)` o `(None, motivo)`."""
    if invested <= 0:
        return None, REASON_NO_INVESTED
    if (end - start).days < 1:
        return None, REASON_TOO_SHORT
    acc = accumulated_factor(series, start, end)
    if acc is None:
        return None, REASON_NO_INFLATION
    ratio = value / invested
    return (
        RealReturn(
            nominal_pct=_round2((ratio - ONE) * HUNDRED),
            inflation_pct=_round2(acc.inflation_pct),
            real_pct=_round2(_real_pct(ratio, acc.factor)),
            estimated=acc.estimated,
            estimated_months=acc.estimated_months,
            period_start=start,
            period_end=end,
            invested=invested,
            value=value,
            factor=acc.factor,
        ),
        None,
    )


def project_fixed_term(
    *,
    invested: Decimal,
    interest_total: Decimal,
    start: date,
    maturity: date,
    series: Mapping[date, Decimal],
) -> Optional[Projection]:
    """Real proyectado al vencimiento de un plazo fijo: el interes total sobre
    la inflacion de todo el plazo. Los meses futuros se estiman, asi que casi
    siempre sale `estimated`."""
    if invested <= 0 or (maturity - start).days < 1:
        return None
    acc = accumulated_factor(series, start, maturity)
    if acc is None:
        return None
    ratio = (invested + interest_total) / invested
    return Projection(
        nominal_pct=_round2((ratio - ONE) * HUNDRED),
        inflation_pct=_round2(acc.inflation_pct),
        real_pct=_round2(_real_pct(ratio, acc.factor)),
        estimated=acc.estimated,
    )


@dataclass(frozen=True)
class PortfolioReal:
    nominal_pct: Decimal
    inflation_pct: Decimal
    real_pct: Decimal
    estimated: bool
    included_count: int
    excluded_count: int


def portfolio_real_return(
    results: list[Optional[RealReturn]],
) -> Optional[PortfolioReal]:
    """Agregado de los activos en pesos con rendimiento calculable, ponderado
    por monto. `None` entre los resultados = activo excluido."""
    included = [r for r in results if r is not None]
    excluded = len(results) - len(included)
    if not included:
        return None
    total_invested = sum((r.invested for r in included), ZERO)
    total_value = sum((r.value for r in included), ZERO)
    inflated = sum((r.invested * r.factor for r in included), ZERO)
    if total_invested <= 0 or inflated <= 0:
        return None
    return PortfolioReal(
        nominal_pct=_round2((total_value / total_invested - ONE) * HUNDRED),
        inflation_pct=_round2((inflated / total_invested - ONE) * HUNDRED),
        real_pct=_round2((total_value / inflated - ONE) * HUNDRED),
        estimated=any(r.estimated for r in included),
        included_count=len(included),
        excluded_count=excluded,
    )
