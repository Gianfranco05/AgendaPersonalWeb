"""Helpers de los tests del buscador: siembran filas directo en la base."""
from datetime import date, datetime, timezone

from app.core.security import hash_password
from app.modules.anotaciones.models import Note, Tag
from app.modules.auth.models import User
from app.modules.eventos.models import Event
from app.modules.finanzas.models import Transaction
from app.modules.tareas.models import Task

OTHER_USER_ID = "b2c3d4e5-f6a7-8901-bcde-f12345678901"


async def make_other_user(db, email="otro@test.com", user_id=OTHER_USER_ID):
    user = User(
        id=user_id,
        email=email,
        password_hash=hash_password("test123"),
        full_name="Otro",
        is_active=True,
        is_verified=True,
    )
    db.add(user)
    await db.commit()
    return user


async def add(db, *rows):
    for row in rows:
        db.add(row)
    await db.commit()
    return rows[0] if len(rows) == 1 else rows


def note(user_id, title, content="", updated=None, archived=False, **kw):
    n = Note(user_id=user_id, title=title, content=content, is_archived=archived, **kw)
    if updated is not None:
        n.updated_at = updated
        n.created_at = updated
    return n


def task(user_id, title, description=None, area="General", **kw):
    return Task(user_id=user_id, title=title, description=description, area=area, **kw)


def event(user_id, title, description=None, location=None, start=None, **kw):
    return Event(
        user_id=user_id,
        title=title,
        description=description,
        location=location,
        start_datetime=start or datetime(2026, 10, 20, 10, 0, tzinfo=timezone.utc),
        **kw,
    )


def txn(user_id, product, merchant="", description=None, notes=None, day="2026-10-10", **kw):
    return Transaction(
        user_id=user_id,
        amount=kw.pop("amount", 100),
        type=kw.pop("type", "expense"),
        transaction_date=day,
        product_name=product,
        merchant_name=merchant,
        product_description=description,
        notes=notes,
        **kw,
    )


def utc(y, m, d, h=12):
    return datetime(y, m, d, h, 0, tzinfo=timezone.utc)


async def tag_note(db, note_obj, name, user_id):
    tag = Tag(user_id=user_id, name=name)
    db.add(tag)
    await db.flush()
    from app.modules.anotaciones.models import note_tags

    await db.execute(note_tags.insert().values(note_id=note_obj.id, tag_id=tag.id))
    await db.commit()
    return tag


def search_url(q, **params):
    from urllib.parse import urlencode

    return "/api/v1/search?" + urlencode({"q": q, **params})


def group(resp_json, type_):
    for g in resp_json["groups"]:
        if g["type"] == type_:
            return g
    return None


def titles(resp_json, type_):
    g = group(resp_json, type_)
    return [i["title"] for i in g["items"]] if g else []
