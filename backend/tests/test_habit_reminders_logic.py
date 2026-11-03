"""Avisos de habitos: reglas puras, habitos pendientes, rachas y mensajes."""

from datetime import date, timedelta

import pytest

from app.modules.habitos_recordatorios import rules, service
from habit_reminder_helpers import (
    TODAY,
    add_goal,
    add_record,
    add_user,
    utc,
)



GENERAL = rules.slot_minutes(20, 0)


# ── Horas y ventana (reglas puras) ──────────────────────────────────────────


def test_parse_hhmm_acepta_y_rechaza():
    assert rules.parse_hhmm("07:30") == (7, 30)
    assert rules.parse_hhmm("23:59") == (23, 59)
    for bad in ("24:00", "7:30", "12:60", "", "12-30"):
        with pytest.raises(ValueError):
            rules.parse_hhmm(bad)


def test_local_now_usa_el_offset_y_argentina_si_es_null():
    # 23:00 UTC con -180 son las 20:00 locales; con +60 ya es el dia siguiente a las 00:00.
    assert rules.local_now(utc(25, 23), -180).hour == 20
    assert rules.local_now(utc(25, 23), None).hour == 20
    plus = rules.local_now(utc(25, 23), 60)
    assert (plus.day, plus.hour) == (26, 0)


def test_ventana_de_60_minutos_sin_pasar_de_la_medianoche():
    slot = rules.slot_minutes(20, 0)
    assert not rules.window_contains(slot, 19 * 60 + 59)
    assert rules.window_contains(slot, 20 * 60)
    assert rules.window_contains(slot, 20 * 60 + 59)
    assert not rules.window_contains(slot, 21 * 60)
    # 23:30: la ventana termina a medianoche, no a las 00:30 del dia siguiente.
    late = rules.slot_minutes(23, 30)
    assert rules.window_contains(late, 23 * 60 + 59)
    assert not rules.window_contains(late, 10)


def test_estado_del_slot():
    slot = rules.slot_minutes(20, 0)
    assert rules.slot_state(slot, 18 * 60) == "upcoming"
    assert rules.slot_state(slot, 20 * 60 + 10) == "due"
    assert rules.slot_state(slot, 22 * 60) == "missed"


# ── Mensajes ────────────────────────────────────────────────────────────────


def habit(goal_id, title, icon="fa-bullseye"):
    return (goal_id, title, icon)


def test_un_solo_habito_texto_plano():
    title, body = rules.build_message([habit("a", "Tomar agua")], {}, True)
    assert title == "✅ Can_cen"
    assert body == "Todavía no marcaste «Tomar agua» hoy."


def test_el_emoji_del_icono_se_usa_si_no_es_ascii():
    title, _ = rules.build_message([habit("a", "Correr", "🏃")], {}, True)
    assert title == "🏃 Can_cen"
    title, _ = rules.build_message([habit("a", "Correr", "fa-bullseye")], {}, True)
    assert title == "✅ Can_cen"


def test_tres_habitos_se_agrupan_en_una_push():
    title, body = rules.build_message(
        [habit("a", "Agua"), habit("b", "Leer"), habit("c", "Correr")], {}, True
    )
    assert title == "✅ Te faltan 3 hábitos hoy"
    assert body == "Agua, Leer y Correr"


def test_dos_habitos_se_unen_con_y_y_seis_cortan_en_cuatro():
    _, body = rules.build_message([habit("a", "Agua"), habit("b", "Leer")], {}, True)
    assert body == "Agua y Leer"
    names = ["Agua", "Leer", "Correr", "Meditar", "Yoga", "Estirar"]
    _, body = rules.build_message([habit(str(i), n) for i, n in enumerate(names)], {}, True)
    assert body == "Agua, Leer, Correr, Meditar y 2 más"


def test_el_nombre_se_trunca_a_40_caracteres():
    long_title = "A" * 60
    _, body = rules.build_message([habit("a", long_title)], {}, True)
    inside = body.split("«")[1].split("»")[0]
    assert len(inside) == 40 and inside.endswith("…")


def test_racha_en_un_solo_habito():
    _, body = rules.build_message([habit("a", "Leer")], {"a": 12}, True)
    assert body == "🔥 Llevás 12 días seguidos con «Leer». ¡No la cortes hoy!"


def test_racha_corta_o_desactivada_queda_texto_plano():
    _, short = rules.build_message([habit("a", "Leer")], {"a": 2}, True)
    _, off = rules.build_message([habit("a", "Leer")], {"a": 12}, False)
    assert short == off == "Todavía no marcaste «Leer» hoy."


def test_racha_en_varios_destaca_la_mas_larga():
    _, body = rules.build_message(
        [habit("a", "Agua"), habit("b", "Leer"), habit("c", "Correr")],
        {"a": 3, "b": 9, "c": 1},
        True,
    )
    assert body == "Agua, Leer y Correr · 🔥 «Leer» lleva 9 días seguidos"


def test_ocultar_contenido_usa_texto_generico():
    title, body = rules.build_message([habit("a", "Terapia")], {"a": 40}, True, hide_content=True)
    assert "Terapia" not in title + body


# ── Habitos pendientes ──────────────────────────────────────────────────────


async def pending(db, user_id):
    return [h.title for h in await service.pending_habits(db, user_id, TODAY, GENERAL)]


@pytest.mark.asyncio
async def test_binario_sin_registro_esta_pendiente_y_marcado_no(db_session, test_user):
    goal = await add_goal(db_session, test_user.id, "Agua")
    assert await pending(db_session, test_user.id) == ["Agua"]
    await add_record(db_session, test_user.id, goal.id, TODAY)
    assert await pending(db_session, test_user.id) == []


@pytest.mark.asyncio
async def test_metrico_cero_pendiente_y_con_valor_parcial_ya_cuenta(db_session, test_user):
    goal = await add_goal(db_session, test_user.id, "Agua", goal_type="metric", target_value=2)
    await add_record(db_session, test_user.id, goal.id, TODAY, 0)
    assert await pending(db_session, test_user.id) == ["Agua"]
    await add_record(db_session, test_user.id, goal.id, TODAY, 0.5)
    assert await pending(db_session, test_user.id) == []


@pytest.mark.asyncio
async def test_is_completed_historico_no_cuenta_como_hecho_hoy(db_session, test_user):
    goal = await add_goal(db_session, test_user.id, "Leer", is_completed=True, current_value=40)
    await add_record(db_session, test_user.id, goal.id, TODAY - timedelta(days=1))
    assert await pending(db_session, test_user.id) == ["Leer"]


@pytest.mark.asyncio
async def test_rango_de_fechas_y_exclusion(db_session, test_user):
    await add_goal(db_session, test_user.id, "Futuro", start_date=TODAY + timedelta(days=1))
    await add_goal(db_session, test_user.id, "Vencido", end_date=TODAY - timedelta(days=1))
    await add_goal(db_session, test_user.id, "Excluido", reminder_enabled=False)
    await add_goal(db_session, test_user.id, "Hoy justo", start_date=TODAY, end_date=TODAY)
    assert await pending(db_session, test_user.id) == ["Hoy justo"]


@pytest.mark.asyncio
async def test_progress_y_savings_nunca_son_habitos(db_session, test_user):
    await add_goal(db_session, test_user.id, "Ahorro", goal_type="savings", target_value=100)
    await add_goal(db_session, test_user.id, "Avance", goal_type="progress", target_value=10)
    assert await pending(db_session, test_user.id) == []


@pytest.mark.asyncio
async def test_hora_propia_o_general_en_cada_habito(db_session, test_user):
    await add_goal(db_session, test_user.id, "General")
    await add_goal(db_session, test_user.id, "Propia", reminder_hour=22, reminder_minute=30)
    slots = {h.title: h.slot_label for h in await service.pending_habits(
        db_session, test_user.id, TODAY, GENERAL)}
    assert slots == {"General": "20:00", "Propia": "22:30"}


@pytest.mark.asyncio
async def test_los_registros_de_otro_usuario_no_marcan_mi_habito(db_session, test_user):
    other = await add_user(db_session, "otro-usuario")
    mine = await add_goal(db_session, test_user.id, "Agua")
    # Registro de B apuntando al goal de A: no debe contar.
    await add_record(db_session, other.id, mine.id, TODAY)
    assert await pending(db_session, test_user.id) == ["Agua"]
    assert await pending(db_session, other.id) == []


# ── Rachas ──────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_racha_cuenta_dias_seguidos_hasta_ayer(db_session, test_user):
    goal = await add_goal(db_session, test_user.id, "Leer")
    for back in range(1, 13):
        await add_record(db_session, test_user.id, goal.id, TODAY - timedelta(days=back))
    streaks = await service.streaks_until_yesterday(db_session, test_user.id, [goal.id], TODAY)
    assert streaks == {goal.id: 12}


@pytest.mark.asyncio
async def test_racha_se_corta_con_un_hueco_y_ayer_vacio_es_cero(db_session, test_user):
    gap = await add_goal(db_session, test_user.id, "Hueco")
    for back in (1, 2, 4, 5):  # falta el dia 3
        await add_record(db_session, test_user.id, gap.id, TODAY - timedelta(days=back))
    stale = await add_goal(db_session, test_user.id, "Vieja")
    await add_record(db_session, test_user.id, stale.id, TODAY - timedelta(days=2))
    streaks = await service.streaks_until_yesterday(
        db_session, test_user.id, [gap.id, stale.id], TODAY
    )
    assert streaks == {gap.id: 2, stale.id: 0}


@pytest.mark.asyncio
async def test_racha_ignora_registros_en_cero_y_de_otro_usuario(db_session, test_user):
    other = await add_user(db_session, "otro-usuario")
    goal = await add_goal(db_session, test_user.id, "Agua", goal_type="metric")
    await add_record(db_session, test_user.id, goal.id, TODAY - timedelta(days=1), 0)
    await add_record(db_session, other.id, goal.id, TODAY - timedelta(days=1), 1)
    streaks = await service.streaks_until_yesterday(db_session, test_user.id, [goal.id], TODAY)
    assert streaks == {goal.id: 0}
    assert await service.streaks_until_yesterday(db_session, test_user.id, [], TODAY) == {}
