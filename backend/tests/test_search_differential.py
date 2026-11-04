"""El SQL del buscador tiene que coincidir con un oraculo en Python (fold_text) para
cualquier mezcla de mayusculas, tildes, enie, comodines y barras. Sirve de red de
seguridad para optimizaciones del SQL (p. ej. el prefiltro barato)."""
import random

import pytest

from app.modules.buscador.normalize import fold_text
from tests.search_helpers import add, note, search_url

pytestmark = pytest.mark.asyncio

ALPHABET = "aAáÁeEéÉiIíÍoOóÓuUúÚüÜnNñÑcCçÇxXk0 _%" + chr(92)


def _rand_text(rng, lo=4, hi=22):
    return "".join(rng.choice(ALPHABET) for _ in range(rng.randint(lo, hi))).strip() or "zz"


def _mangle(rng, s):
    """Variante del mismo texto con otra capitalizacion/tildes (sigue plegando igual)."""
    swaps = {"a": "áÁA", "e": "éÉE", "i": "íÍI", "o": "óÓO", "u": "úÚüÜU", "n": "ñÑN"}
    out = []
    for ch in s:
        base = fold_text(ch)
        out.append(rng.choice(swaps[base] + base) if base in swaps and rng.random() < 0.7 else ch)
    return "".join(out)


async def test_sql_matches_the_python_oracle_for_random_texts(
    api_auth_client, db_session, test_user, monkeypatch
):
    from app.config import settings

    monkeypatch.setattr(settings, "RATE_LIMIT_ENABLED", False)
    rng = random.Random(20261103)
    titles = [_rand_text(rng) for _ in range(120)]
    contents = [_rand_text(rng, 10, 60) for _ in range(120)]
    await add(db_session, *[note(test_user.id, t, c) for t, c in zip(titles, contents)])

    checked = 0
    for _ in range(150):
        i = rng.randrange(len(titles))
        source = rng.choice([titles[i], contents[i]])
        if len(source) < 3:
            continue
        start = rng.randrange(0, len(source) - 2)
        token = _mangle(rng, source[start : start + rng.randint(2, 6)]).strip()
        if len(token) < 2 or " " in token:
            continue
        expected = {
            (t, c)
            for t, c in zip(titles, contents)
            if fold_text(token) in fold_text(t) or fold_text(token) in fold_text(c)
        }
        resp = await api_auth_client.get(search_url(token, types="notes", limit="20"))
        assert resp.status_code == 200, (token, resp.text)
        groups = resp.json()["groups"]
        got = {(i["title"], None) for i in groups[0]["items"]} if groups else set()
        got_titles = {t for t, _ in got}
        expected_titles = {t for t, _ in expected}
        if len(expected_titles) <= 20 and len(expected) <= 20:
            assert got_titles == expected_titles, (token, got_titles ^ expected_titles)
        else:
            assert got_titles <= expected_titles, token
            assert groups[0]["has_more"] is True
        checked += 1
    assert checked > 80
