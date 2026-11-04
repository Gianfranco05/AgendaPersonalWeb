"""validate_app_redirect: a donde puede volver el login con Google con los
tokens en la URL. Un redirect aceptado de mas es robo de cuenta."""

import pytest
from fastapi import HTTPException

from app.config import settings
from app.core.redirect_safety import validate_app_redirect

BASE = "https://cancen.example.com"


@pytest.fixture(autouse=True)
def _public_base(monkeypatch):
    monkeypatch.setattr(settings, "PUBLIC_BASE_URL", BASE)


@pytest.fixture
def production(monkeypatch):
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")


def _rejected(url: str) -> bool:
    try:
        validate_app_redirect(url)
    except HTTPException as exc:
        assert exc.status_code == 400
        return True
    return False


@pytest.mark.parametrize(
    "url",
    [
        f"{BASE}/google/callback",
        f"{BASE}/store",
        "cancen://google-callback",
        "cancen:///store",
    ],
)
def test_acepta_dominio_propio_y_scheme_de_la_app(url, production):
    assert not _rejected(url)


@pytest.mark.parametrize(
    "url",
    [
        # Mismo prefijo, otro host: era el agujero de la comparacion por prefijo.
        "https://cancen.example.com.atacante.com/google/callback",
        "https://cancen.example.comatacante.com/",
        "http://localhost.atacante.com/google/callback",
        "http://127.0.0.1.atacante.com/",
        # Credenciales en la URL: el host real es el que va despues del @.
        f"https://cancen.example.com@atacante.com/",
        "http://localhost\\@atacante.com/",
        # Otro scheme o puerto que el dominio publico.
        "http://cancen.example.com/google/callback",
        "https://cancen.example.com:8443/",
        "javascript:alert(1)",
        "https://atacante.com/",
        "",
    ],
)
def test_rechaza_hosts_que_solo_comparten_el_prefijo(url):
    assert _rejected(url)


def test_en_desarrollo_acepta_localhost_y_expo_go():
    assert not _rejected("http://localhost:5173/google/callback")
    assert not _rejected("http://127.0.0.1:5180/google/callback")
    assert not _rejected("exp://192.168.1.40:8081/--/google-callback")


@pytest.mark.parametrize(
    "url",
    [
        "http://localhost:5173/google/callback",
        "http://127.0.0.1:5180/",
        # Expo Go carga JS de cualquier host: en prod le daria los tokens a un
        # bundle ajeno.
        "exp://atacante.com:8081/--/google-callback",
    ],
)
def test_en_produccion_rechaza_localhost_y_expo_go(url, production):
    assert _rejected(url)


def test_puerto_invalido_no_rompe(production):
    assert _rejected("https://cancen.example.com:99999/")
