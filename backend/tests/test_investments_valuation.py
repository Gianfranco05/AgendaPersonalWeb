"""Calculos puros de inversiones: plazo fijo, valor efectivo y conversion."""

from datetime import date, datetime, timezone
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.modules.inversiones import valuation
from app.modules.inversiones.valuation import (
    PRICE_PROVIDERS,
    Rates,
    compute_totals,
    convert_to_ars,
    fixed_term_info,
    format_money_es_ar,
    round2,
    to_decimal,
    valuate,
)

D = Decimal


def make_inv(**overrides):
    base = dict(
        asset_type="stock",
        currency="ARS",
        quantity=None,
        invested_amount=D("1000"),
        current_value=None,
        interest_rate_tna=None,
        start_date=None,
        maturity_date=None,
        price_source="manual",
        last_price=None,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


# ── Redondeo y conversion segura ────────────────────────────────────────────


def test_round2_es_half_up_y_no_bancario():
    assert round2(D("2.675")) == D("2.68")  # round() de Python daria 2.67
    assert round2(D("0.005")) == D("0.01")
    assert round2(D("1.004")) == D("1.00")


def test_to_decimal_va_por_str_para_no_arrastrar_el_float():
    assert to_decimal(0.1) == D("0.1")
    assert to_decimal(None) is None
    assert to_decimal(D("5")) == D("5")


# ── Plazo fijo ──────────────────────────────────────────────────────────────


def test_plazo_fijo_interes_monto_al_vencimiento_y_tea():
    info = fixed_term_info(
        D("1000000"), D("30"), date(2026, 10, 1), date(2026, 10, 31), date(2026, 10, 1)
    )
    assert info.term_days == 30
    assert info.interest_total == D("24657.53")
    assert info.amount_at_maturity == D("1024657.53")
    assert info.tea_pct == D("34.50")


def test_plazo_fijo_devengado_a_12_dias():
    info = fixed_term_info(
        D("1000000"), D("30"), date(2026, 10, 1), date(2026, 10, 31), date(2026, 10, 13)
    )
    assert info.accrued_interest == D("9863.01")


def test_devengado_es_cero_antes_del_inicio():
    info = fixed_term_info(
        D("1000000"), D("30"), date(2026, 10, 1), date(2026, 10, 31), date(2026, 9, 1)
    )
    assert info.accrued_interest == D("0.00")


def test_devengado_se_frena_en_el_vencimiento():
    info = fixed_term_info(
        D("1000000"), D("30"), date(2026, 10, 1), date(2026, 10, 31), date(2027, 3, 1)
    )
    assert info.accrued_interest == info.interest_total == D("24657.53")


def test_plazo_fijo_con_tna_cero_no_rinde():
    info = fixed_term_info(D("5000"), D("0"), date(2026, 1, 1), date(2026, 2, 1), date(2026, 1, 15))
    assert info.interest_total == D("0.00")
    assert info.amount_at_maturity == D("5000.00")
    assert info.tea_pct == D("0.00")


# ── Valor efectivo ──────────────────────────────────────────────────────────


def test_valor_manual_gana_sobre_lo_invertido():
    v = valuate(make_inv(invested_amount=D("150000"), current_value=D("172500")), date(2026, 10, 15))
    assert v.effective_value == D("172500.00")
    assert v.value_source == "manual"
    assert v.gain == D("22500.00")
    assert v.gain_pct == D("15.00")


def test_perdida_es_negativa():
    v = valuate(make_inv(invested_amount=D("1000"), current_value=D("800")), date(2026, 10, 15))
    assert v.gain == D("-200.00")
    assert v.gain_pct == D("-20.00")


def test_sin_valor_actual_vale_lo_invertido():
    v = valuate(make_inv(asset_type="real_estate", invested_amount=D("50000")), date(2026, 10, 15))
    assert v.effective_value == D("50000.00")
    assert v.gain == D("0.00")
    assert v.value_source == "invested"


def test_plazo_fijo_sin_valor_manual_usa_el_devengado():
    inv = make_inv(
        asset_type="fixed_term",
        invested_amount=D("1000000"),
        interest_rate_tna=D("30"),
        start_date=date(2026, 10, 1),
        maturity_date=date(2026, 10, 31),
    )
    v = valuate(inv, date(2026, 10, 13))
    assert v.effective_value == D("1009863.01")
    assert v.value_source == "fixed_term_accrued"
    assert v.fixed_term.amount_at_maturity == D("1024657.53")
    assert v.days_to_maturity == 18
    assert v.is_matured is False


def test_plazo_fijo_con_valor_manual_pisa_al_devengado():
    inv = make_inv(
        asset_type="fixed_term",
        invested_amount=D("1000000"),
        current_value=D("1005000"),
        interest_rate_tna=D("30"),
        start_date=date(2026, 10, 1),
        maturity_date=date(2026, 10, 31),
    )
    v = valuate(inv, date(2026, 10, 13))
    assert v.effective_value == D("1005000.00")
    assert v.value_source == "manual"


def test_cotizacion_automatica_gana_sobre_todo():
    inv = make_inv(
        price_source="coingecko",
        quantity=D("2"),
        last_price=D("100"),
        current_value=D("999"),
    )
    v = valuate(inv, date(2026, 10, 15))
    assert v.effective_value == D("200.00")
    assert v.value_source == "quote"


def test_fuente_automatica_sin_precio_cae_al_valor_manual():
    inv = make_inv(price_source="coingecko", quantity=D("2"), last_price=None, current_value=D("300"))
    assert valuate(inv, date(2026, 10, 15)).value_source == "manual"


def test_ganancia_porcentual_es_null_si_no_hay_nada_invertido():
    v = valuate(make_inv(invested_amount=D("0"), current_value=D("100")), date(2026, 10, 15))
    assert v.gain == D("100.00")
    assert v.gain_pct is None


def test_dias_al_vencimiento_hoy_futuro_y_vencido():
    hoy = date(2026, 10, 15)
    assert valuate(make_inv(maturity_date=date(2026, 10, 20)), hoy).days_to_maturity == 5
    v_hoy = valuate(make_inv(maturity_date=hoy), hoy)
    assert v_hoy.days_to_maturity == 0 and v_hoy.is_matured is False
    v_vencido = valuate(make_inv(maturity_date=date(2026, 10, 14)), hoy)
    assert v_vencido.days_to_maturity == -1 and v_vencido.is_matured is True
    assert valuate(make_inv(), hoy).days_to_maturity is None


def test_valuate_acepta_floats_de_sqlite():
    v = valuate(make_inv(invested_amount=1000.1, current_value=1100.2), date(2026, 10, 15))
    assert v.effective_value == D("1100.20")
    assert v.gain == D("100.10")


# ── Conversion de moneda y totales ──────────────────────────────────────────

RATES = Rates(usd_ars=D("1450.50"))


def test_totales_ars_y_usd_con_cotizacion():
    t = compute_totals({"ARS": D("500000"), "USD": D("2000")}, RATES)
    assert t.total_ars == D("3401000.00")
    assert t.total_usd == D("2344.71")
    assert t.missing_rates == []


def test_sin_cotizacion_los_totales_son_null_y_se_informa_el_par():
    t = compute_totals({"ARS": D("500000"), "USD": D("2000")}, Rates())
    assert t.total_ars is None and t.total_usd is None
    assert t.missing_rates == ["USD"]


def test_solo_ars_sin_cotizacion_calcula_ars_pero_no_usd():
    t = compute_totals({"ARS": D("500000")}, Rates())
    assert t.total_ars == D("500000.00")
    assert t.total_usd is None
    assert t.missing_rates == ["USD"]


def test_solo_usd_sin_cotizacion_calcula_usd_pero_no_ars():
    t = compute_totals({"USD": D("2000")}, Rates())
    assert t.total_usd == D("2000.00")
    assert t.total_ars is None
    assert t.missing_rates == ["USD"]


def test_eur_sin_cotizacion_de_euro_deja_ambos_totales_en_null():
    t = compute_totals({"ARS": D("1000"), "EUR": D("10")}, RATES)
    assert t.total_ars is None and t.total_usd is None
    assert t.missing_rates == ["EUR"]


def test_eur_con_cotizacion():
    t = compute_totals({"EUR": D("100")}, Rates(usd_ars=D("1000"), eur_ars=D("1100")))
    assert t.total_ars == D("110000.00")
    assert t.total_usd == D("110.00")


def test_usdt_vale_uno_a_uno_con_usd():
    t = compute_totals({"USD": D("100"), "USDT": D("50")}, RATES)
    assert t.total_usd == D("150.00")
    assert t.total_ars == D("217575.00")


def test_sin_activos_los_totales_son_cero():
    t = compute_totals({}, Rates())
    assert t.total_ars == D("0.00") and t.total_usd == D("0.00")
    assert t.missing_rates == []


def test_se_redondea_una_sola_vez_al_final():
    # Dos subtotales de 0.005 USD: redondeados antes darian 0.02; juntos, 0.01.
    t = compute_totals({"USD": D("0.005"), "USDT": D("0.004")}, RATES)
    assert t.total_usd == D("0.01")


def test_convert_to_ars():
    assert convert_to_ars(D("10"), "ARS", Rates()) == D("10")
    assert convert_to_ars(D("10"), "USDT", RATES) == D("14505.00")
    assert convert_to_ars(D("10"), "USD", Rates()) is None
    assert convert_to_ars(D("10"), "EUR", RATES) is None


# ── Formato y punto de extension ────────────────────────────────────────────


def test_formato_es_ar():
    assert format_money_es_ar(D("1024657.53")) == "$ 1.024.657,53 ARS"
    assert format_money_es_ar(D("1500.5"), "USD") == "US$ 1.500,50 USD"
    assert format_money_es_ar(D("0")) == "$ 0,00 ARS"


def test_no_hay_proveedores_de_precios_en_esta_etapa():
    assert PRICE_PROVIDERS == {}


@pytest.mark.asyncio
async def test_refresh_quotes_es_un_noop():
    assert await valuation.refresh_quotes(None, "user-1") == 0


def test_price_quote_tiene_la_forma_esperada():
    q = valuation.PriceQuote(D("1"), "USD", datetime.now(timezone.utc))
    assert q.price == D("1")
