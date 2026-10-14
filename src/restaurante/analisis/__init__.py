"""Herramientas de analisis, experimentacion y optimizacion.

Las exportaciones se cargan bajo demanda para que las formulas de colas y las
metricas basicas puedan usarse sin cargar Pandas innecesariamente.
"""

from __future__ import annotations

from importlib import import_module
from typing import Any

__all__ = [
    "IndicadoresMMS",
    "calcular_indicadores_mms",
    "calcular_metricas",
    "calcular_mms",
    "ejecutar_experimentos",
    "erlang_c",
    "esperas_registro",
    "frontera_pareto",
    "resumir_experimentos",
    "seleccionar_configuracion",
]

_MODULO_POR_NOMBRE = {
    "IndicadoresMMS": "teoria_colas",
    "calcular_indicadores_mms": "teoria_colas",
    "calcular_mms": "teoria_colas",
    "erlang_c": "teoria_colas",
    "calcular_metricas": "metricas",
    "esperas_registro": "metricas",
    "ejecutar_experimentos": "experimentos",
    "resumir_experimentos": "experimentos",
    "frontera_pareto": "optimizador",
    "seleccionar_configuracion": "optimizador",
}


def __getattr__(nombre: str) -> Any:
    try:
        modulo = import_module(f".{_MODULO_POR_NOMBRE[nombre]}", __name__)
    except KeyError as exc:
        raise AttributeError(f"module {__name__!r} has no attribute {nombre!r}") from exc
    valor = getattr(modulo, nombre)
    globals()[nombre] = valor
    return valor
