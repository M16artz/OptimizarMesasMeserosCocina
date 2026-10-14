"""Manejo del estado de sesión y valores por defecto de la interfaz."""

from __future__ import annotations

from typing import Any

import streamlit as st

from .servicios import CONFIGURACION_POR_DEFECTO

PESOS_POR_DEFECTO: dict[str, float] = {"mesas": 1.0, "meseros": 1.0, "cocineros": 1.0}


def inicializar_estado() -> None:
    """Inicializa las claves de ``st.session_state`` con valores por defecto."""
    st.session_state.setdefault("configuracion", dict(CONFIGURACION_POR_DEFECTO))
    # Pestaña de resultados
    st.session_state.setdefault("replicas", 5)
    st.session_state.setdefault("semilla_base", 1)
    # Pestaña de escenarios
    st.session_state.setdefault("replicas_escenarios", 3)
    st.session_state.setdefault("semilla_escenarios", 1)
    # Pestaña de optimización
    st.session_state.setdefault("peso_mesas", 1.0)
    st.session_state.setdefault("peso_meseros", 1.0)
    st.session_state.setdefault("peso_cocineros", 1.0)
    st.session_state.setdefault("restriccion_espera_max", 30.0)
    st.session_state.setdefault("pesos", dict(PESOS_POR_DEFECTO))


def configuracion_actual() -> dict[str, Any]:
    """Devuelve una copia de la configuración vigente."""
    return dict(st.session_state["configuracion"])


def establecer_configuracion(configuracion: dict[str, Any]) -> None:
    """Fija la configuración vigente."""
    st.session_state["configuracion"] = dict(configuracion)
