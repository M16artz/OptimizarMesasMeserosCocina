"""Prueba de humo de la aplicación Streamlit con ``AppTest``."""

from __future__ import annotations

from pathlib import Path

from streamlit.testing.v1 import AppTest

RAIZ = Path(__file__).resolve().parents[1]


def _nueva_app() -> AppTest:
    at = AppTest.from_file(str(RAIZ / "app.py"), default_timeout=120)
    at.run()
    return at


def test_app_arranca_sin_excepciones():
    at = _nueva_app()
    assert not at.exception


def test_ejecutar_simulacion_genera_metricas():
    at = _nueva_app()
    boton = next(b for b in at.button if b.label == "Ejecutar simulación")
    boton.click().run()
    assert not at.exception
    assert len(at.metric) > 0
