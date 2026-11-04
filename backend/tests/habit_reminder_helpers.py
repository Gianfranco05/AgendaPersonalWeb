"""Ayudas compartidas por los tests de avisos de habitos."""

import itertools
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from app.modules.auth.models import User
from app.modules.habitos_recordatorios.models import HabitReminderSettings
from app.modules.metas.models import Goal, HabitRecord
from app.modules.push.models import PushToken

TODAY = date(2026, 10, 25)

# created_at tiene resolucion de segundos en SQLite: sin esto el orden de dos
# habitos creados en el mismo test seria el del id (aleatorio).
_created = itertools.count()


def utc(day: int, hour: int, minute: int = 0, month: int = 10, year: int = 2026) -> datetime:
    return datetime(year, month, day, hour, minute, tzinfo=timezone.utc)


async def add_user(db, user_id: str, email: Optional[str] = None) -> User:
    user = User(
        id=user_id,
        email=email or f"{user_id}@test.com",
        password_hash="x",
        full_name=user_id,
        is_active=True,
        is_verified=True,
    )
    db.add(user)
    await db.commit()
    return user


async def add_token(db, user_id: str, token: Optional[str] = None) -> None:
    db.add(PushToken(user_id=user_id, token=token or f"ExponentPushToken[{user_id}]"))
    await db.commit()


async def add_goal(db, user_id: str, title: str = "Tomar agua", **overrides) -> Goal:
    values = dict(user_id=user_id, title=title, goal_type="binary", icon="fa-bullseye")
    values.setdefault(
        "created_at", datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(seconds=next(_created))
    )
    values.update(overrides)
    goal = Goal(**values)
    db.add(goal)
    await db.commit()
    return goal


async def add_record(db, user_id: str, goal_id: str, day: date, value: float = 1) -> None:
    db.add(HabitRecord(user_id=user_id, goal_id=goal_id, record_date=day, value=value))
    await db.commit()


async def set_config(db, user_id: str, **values) -> HabitReminderSettings:
    row = HabitReminderSettings(user_id=user_id, **values)
    db.add(row)
    await db.commit()
    return row
