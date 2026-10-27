"""Reglas de calendario de los recurrentes: funciones puras, sin base ni reloj."""

from datetime import date

import pytest

from app.modules.recurrentes import rules
from app.modules.recurrentes.rules import Rule


def monthly(day, n=1):
    return Rule("monthly", n, day_of_month=day)


def take(rule, anchor, count):
    return [rules.occurrence(rule, anchor, k) for k in range(count)]


def test_dia_31_en_meses_cortos_y_vuelve_a_31():
    rule = monthly(31)
    anchor = rules.compute_anchor(rule, date(2027, 1, 31))
    assert anchor == date(2027, 1, 31)
    assert take(rule, anchor, 4) == [
        date(2027, 1, 31),
        date(2027, 2, 28),
        date(2027, 3, 31),
        date(2027, 4, 30),
    ]


def test_dia_31_en_febrero_bisiesto():
    rule = monthly(31)
    assert rules.occurrence(rule, date(2028, 1, 31), 1) == date(2028, 2, 29)


def test_dia_30_en_febrero_2028_cae_el_29():
    rule = monthly(30)
    anchor = date(2028, 1, 30)
    assert rules.occurrence(rule, anchor, 1) == date(2028, 2, 29)
    # y sin arrastre: marzo vuelve al 30
    assert rules.occurrence(rule, anchor, 2) == date(2028, 3, 30)


def test_ancla_con_dia_ajustado_no_se_arrastra():
    # El ancla cae el 28/02 por ser febrero, pero la regla sigue siendo "dia 31".
    rule = monthly(31)
    anchor = rules.compute_anchor(rule, date(2027, 2, 10))
    assert anchor == date(2027, 2, 28)
    assert take(rule, anchor, 3) == [date(2027, 2, 28), date(2027, 3, 31), date(2027, 4, 30)]


def test_bimestral_anclado_en_el_primer_match():
    rule = monthly(5, n=2)
    anchor = rules.compute_anchor(rule, date(2026, 10, 25))
    assert anchor == date(2026, 11, 5)
    assert take(rule, anchor, 3) == [date(2026, 11, 5), date(2027, 1, 5), date(2027, 3, 5)]


def test_mensual_ancla_en_el_mismo_mes_si_todavia_no_paso():
    assert rules.compute_anchor(monthly(5), date(2026, 11, 1)) == date(2026, 11, 5)
    assert rules.compute_anchor(monthly(5), date(2026, 11, 5)) == date(2026, 11, 5)
    assert rules.compute_anchor(monthly(5), date(2026, 11, 6)) == date(2026, 12, 5)
    # cruza de anio
    assert rules.compute_anchor(monthly(5), date(2026, 12, 20)) == date(2027, 1, 5)


def test_semanal_por_dia_de_la_semana():
    rule = Rule("weekly", 1, weekday=0)
    # 2026-10-28 es miercoles
    anchor = rules.compute_anchor(rule, date(2026, 10, 28))
    assert anchor == date(2026, 11, 2)
    assert take(rule, anchor, 3) == [date(2026, 11, 2), date(2026, 11, 9), date(2026, 11, 16)]


def test_cada_dos_semanas():
    rule = Rule("weekly", 2, weekday=4)
    anchor = rules.compute_anchor(rule, date(2026, 10, 28))
    assert anchor == date(2026, 10, 30)
    assert take(rule, anchor, 3) == [date(2026, 10, 30), date(2026, 11, 13), date(2026, 11, 27)]


def test_cada_15_dias():
    rule = Rule("daily", 15)
    anchor = rules.compute_anchor(rule, date(2026, 10, 28))
    assert take(rule, anchor, 3) == [date(2026, 10, 28), date(2026, 11, 12), date(2026, 11, 27)]


def test_anual_29_de_febrero():
    rule = Rule("yearly", 1, day_of_month=29, month_of_year=2)
    anchor = date(2028, 2, 29)
    assert take(rule, anchor, 5) == [
        date(2028, 2, 29),
        date(2029, 2, 28),
        date(2030, 2, 28),
        date(2031, 2, 28),
        date(2032, 2, 29),
    ]


def test_anual_ancla_en_el_anio_siguiente_si_ya_paso():
    rule = Rule("yearly", 1, day_of_month=15, month_of_year=3)
    assert rules.compute_anchor(rule, date(2026, 4, 1)) == date(2027, 3, 15)
    assert rules.compute_anchor(rule, date(2026, 3, 15)) == date(2026, 3, 15)


def test_next_after_y_first_on_or_after():
    rule = monthly(31)
    anchor = date(2027, 1, 31)
    assert rules.first_on_or_after(rule, anchor, date(2027, 2, 1)) == (1, date(2027, 2, 28))
    assert rules.first_on_or_after(rule, anchor, date(2027, 2, 28)) == (1, date(2027, 2, 28))
    assert rules.next_after(rule, anchor, date(2027, 2, 28)) == date(2027, 3, 31)
    # antes del ancla devuelve el ancla
    assert rules.first_on_or_after(rule, anchor, date(2020, 1, 1)) == (0, anchor)


def test_first_on_or_after_con_saltos_grandes_es_exacto():
    # Diario cada 7 dias durante anios: se compara contra recorrer uno por uno.
    rule = Rule("daily", 7)
    anchor = date(2024, 1, 1)
    for target in (date(2026, 10, 26), date(2027, 1, 1), date(2030, 6, 30)):
        _, found = rules.first_on_or_after(rule, anchor, target)
        assert found >= target
        assert (found - anchor).days % 7 == 0
        assert (found - target).days < 7


@pytest.mark.parametrize("n,day", [(1, 31), (2, 30), (3, 29), (12, 31)])
def test_first_on_or_after_mensual_coincide_con_busqueda_lineal(n, day):
    rule = monthly(day, n)
    anchor = rules.compute_anchor(rule, date(2025, 1, 1))
    ocurrencias = take(rule, anchor, 200)
    for target in [date(2025, 1, 1), date(2026, 2, 28), date(2028, 2, 29), date(2031, 12, 31)]:
        expected = next(d for d in ocurrencias if d >= target)
        assert rules.first_on_or_after(rule, anchor, target)[1] == expected


def test_end_date_inclusive_y_cursor_null():
    rule = monthly(5)
    anchor = date(2026, 11, 5)
    assert rules.occurrences_between(rule, anchor, date(2026, 11, 1), date(2027, 6, 1), date(2027, 1, 5)) == [
        date(2026, 11, 5),
        date(2026, 12, 5),
        date(2027, 1, 5),
    ]
    assert rules.next_cursor(rule, anchor, date(2026, 12, 5), date(2027, 1, 5)) == date(2027, 1, 5)
    assert rules.next_cursor(rule, anchor, date(2027, 1, 5), date(2027, 1, 5)) is None
    assert rules.cursor_from(rule, anchor, date(2027, 1, 6), date(2027, 1, 5)) is None


def test_occurrences_between_respeta_limite():
    rule = Rule("daily", 1)
    result = rules.occurrences_between(rule, date(2026, 1, 1), date(2026, 1, 1), date(2026, 12, 31), limit=5)
    assert len(result) == 5


@pytest.mark.parametrize(
    "rule,label",
    [
        (monthly(5), "Todos los meses el día 5"),
        (monthly(10, 2), "Cada 2 meses el día 10"),
        (monthly(31), "Todos los meses el día 31 (o el último día del mes)"),
        (Rule("weekly", 1, weekday=0), "Todas las semanas los lunes"),
        (Rule("weekly", 2, weekday=4), "Cada 2 semanas los viernes"),
        (Rule("daily", 15), "Cada 15 días"),
        (Rule("daily", 1), "Todos los días"),
        (Rule("yearly", 1, day_of_month=15, month_of_year=3), "Todos los años el 15/03"),
        (Rule("yearly", 2, day_of_month=15, month_of_year=3), "Cada 2 años el 15/03"),
    ],
)
def test_rule_label(rule, label):
    assert rules.rule_label(rule) == label


@pytest.mark.parametrize(
    "rule",
    [
        Rule("hourly"),
        Rule("daily", 0),
        Rule("daily", 366),
        Rule("weekly", 1),
        Rule("weekly", 53, weekday=1),
        Rule("weekly", 1, weekday=7),
        Rule("monthly", 1),
        Rule("monthly", 13, day_of_month=5),
        Rule("monthly", 1, day_of_month=32),
        Rule("yearly", 1, day_of_month=5),
        Rule("yearly", 11, day_of_month=5, month_of_year=1),
        Rule("yearly", 1, day_of_month=31, month_of_year=4),
        Rule("yearly", 1, day_of_month=30, month_of_year=2),
    ],
)
def test_validate_rule_rechaza_reglas_incompletas_o_fuera_de_rango(rule):
    with pytest.raises(ValueError):
        rules.validate_rule(rule)


def test_validate_acepta_29_de_febrero_anual():
    rules.validate_rule(Rule("yearly", 1, day_of_month=29, month_of_year=2))


def test_normalize_deja_en_null_lo_que_no_corresponde():
    rule = rules.normalize_rule(Rule("weekly", 1, weekday=2, day_of_month=5, month_of_year=3))
    assert rule == Rule("weekly", 1, weekday=2)
    rule = rules.normalize_rule(Rule("monthly", 1, weekday=2, day_of_month=5, month_of_year=3))
    assert rule == Rule("monthly", 1, day_of_month=5)


def test_hora_local_con_offsets():
    from datetime import datetime, timezone

    now = datetime(2026, 11, 6, 1, 30, tzinfo=timezone.utc)
    assert rules.local_today(now, -180) == date(2026, 11, 5)
    assert rules.local_today(now, None) == date(2026, 11, 5)  # fallback -180
    assert rules.local_today(now, 600) == date(2026, 11, 6)
    assert rules.local_now(now, -180).hour == 22
