"""Reglas puras de los avisos de habitos: horas, husos y mensajes.

Sin acceso a la base: se prueban con datos en memoria y las usan por igual el
scheduler, el endpoint `/today` y los formularios de habitos.
"""

import re
from datetime import datetime, timedelta, timezone
from typing import Optional, Sequence

#: Argentina: el mercado de la app. Se usa cuando el cliente no mando el offset.
DEFAULT_TZ_OFFSET_MINUTES = -180
DEFAULT_HOUR = 20
DEFAULT_MINUTE = 0
DEFAULT_DAILY_CAP = 3
#: Dias seguidos (hasta ayer) desde los que una racha se destaca en el texto.
STREAK_MIN_DAYS = 3
#: Cuanto despues de la hora sigue valido el aviso (recuperacion tras una caida).
WINDOW_MINUTES = 60
MINUTES_PER_DAY = 1440
#: Historia que se mira para contar la racha.
STREAK_LOOKBACK_DAYS = 365
NAME_MAX_CHARS = 40
LIST_MAX_NAMES = 4
FALLBACK_EMOJI = "✅"

HHMM_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")
HHMM_ERROR = "La hora debe tener el formato HH:MM (de 00:00 a 23:59)"


def parse_hhmm(value: str) -> tuple[int, int]:
    if not isinstance(value, str) or not HHMM_RE.match(value):
        raise ValueError(HHMM_ERROR)
    hour, minute = value.split(":")
    return int(hour), int(minute)


def format_hhmm(hour: int, minute: int) -> str:
    return f"{hour:02d}:{minute:02d}"


def slot_minutes(hour: int, minute: int) -> int:
    return hour * 60 + minute


def format_slot(minutes: int) -> str:
    return format_hhmm(minutes // 60, minutes % 60)


def effective_offset(offset: Optional[int]) -> int:
    return DEFAULT_TZ_OFFSET_MINUTES if offset is None else offset


def local_now(now_utc: datetime, offset: Optional[int]) -> datetime:
    """Hora local (sin zona) del usuario: `offset` son minutos al este de UTC."""
    if now_utc.tzinfo is not None:
        now_utc = now_utc.astimezone(timezone.utc)
    return now_utc.replace(tzinfo=None) + timedelta(minutes=effective_offset(offset))


def minutes_of_day(local: datetime) -> int:
    return local.hour * 60 + local.minute


def window_contains(slot: int, local_minutes: int) -> bool:
    """El aviso de las `slot` esta en ventana desde esa hora y hasta 60 minutos
    despues, sin pasar de la medianoche local (el dia siguiente es otro dia)."""
    return slot <= local_minutes < min(slot + WINDOW_MINUTES, MINUTES_PER_DAY)


def slot_state(slot: int, local_minutes: int) -> str:
    if local_minutes < slot:
        return "upcoming"
    if window_contains(slot, local_minutes):
        return "due"
    return "missed"


# ── Mensajes ────────────────────────────────────────────────────────────────


def truncate_name(name: str) -> str:
    name = " ".join((name or "").split())
    if len(name) <= NAME_MAX_CHARS:
        return name
    return name[: NAME_MAX_CHARS - 1].rstrip() + "…"


def habit_emoji(icon: Optional[str]) -> str:
    """El icono del habito si es un emoji; los nombres de la web (`fa-bullseye`)
    son ASCII y no se pueden mostrar en una notificacion."""
    icon = (icon or "").strip()
    if icon and any(ord(ch) > 127 for ch in icon):
        return icon
    return FALLBACK_EMOJI


def join_names(names: Sequence[str]) -> str:
    if len(names) > LIST_MAX_NAMES:
        shown = ", ".join(names[:LIST_MAX_NAMES])
        return f"{shown} y {len(names) - LIST_MAX_NAMES} más"
    if len(names) <= 1:
        return "".join(names)
    return f"{', '.join(names[:-1])} y {names[-1]}"


def build_message(
    habits: Sequence[tuple[str, Optional[str], str]],
    streaks: dict[str, int],
    streak_alerts: bool,
    hide_content: bool = False,
) -> tuple[str, str]:
    """(titulo, cuerpo) de la push. `habits` son (id, titulo, icono) en orden.

    La racha en riesgo NO genera otra push: solo cambia el texto. `hide_content`
    es el punto de extension para ocultar los nombres en la pantalla de bloqueo.
    """
    count = len(habits)
    if hide_content:
        return "Can_cen", "Te faltan hábitos por marcar hoy"

    best_id: Optional[str] = None
    best_days = 0
    if streak_alerts:
        for goal_id, _, _ in habits:
            days = streaks.get(goal_id, 0)
            if days >= STREAK_MIN_DAYS and days > best_days:
                best_id, best_days = goal_id, days

    if count == 1:
        goal_id, title, icon = habits[0]
        name = truncate_name(title)
        heading = f"{habit_emoji(icon)} Can_cen"
        if best_id is not None:
            return heading, f"🔥 Llevás {best_days} días seguidos con «{name}». ¡No la cortes hoy!"
        return heading, f"Todavía no marcaste «{name}» hoy."

    names = [truncate_name(title) for _, title, _ in habits]
    body = join_names(names)
    if best_id is not None:
        best_name = next(truncate_name(t) for gid, t, _ in habits if gid == best_id)
        body += f" · 🔥 «{best_name}» lleva {best_days} días seguidos"
    return f"✅ Te faltan {count} hábitos hoy", body
