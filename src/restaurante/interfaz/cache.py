"""Envolturas con caché para no repetir simulaciones costosas.

``st.cache_data`` serializa las entradas y salidas, por lo que se usan
diccionarios (configuración) y tipos básicos como claves.
"""

from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from . import servicios


@st.cache_data(show_spinner=False)
def ejecucion_unica(configuracion: dict[str, Any], semilla: int):
    """Ejecuta una réplica cacheando por configuración y semilla."""
    parametros, configuracion_sim = servicios.config_desde_dict(configuracion)
    return servicios.ejecutar_una(parametros, configuracion_sim, semilla)


@st.cache_data(show_spinner=False)
def replicas(configuracion: dict[str, Any], num_replicas: int, semilla_base: int) -> pd.DataFrame:
    """Ejecuta varias réplicas cacheando por configuración, réplicas y semilla."""
    parametros, configuracion_sim = servicios.config_desde_dict(configuracion)
    return servicios.ejecutar_replicas(parametros, configuracion_sim, num_replicas, semilla_base)


@st.cache_data(show_spinner=False)
def comparar(escenarios: tuple[dict[str, Any], ...], num_replicas: int, semilla_base: int) -> pd.DataFrame:
    """Compara escenarios cacheando por su contenido."""
    return servicios.comparar_escenarios(list(escenarios), num_replicas, semilla_base)
