"""Capa de aplicación del simulador.

Une el backend (dominio + simulación + análisis) con las interfaces (consola y
web) sin depender de Streamlit. Todas las funciones de este módulo son puras y
testeables con pytest.

El backend real trabaja con dos objetos: ``ParametrosSistema`` (tasas y
cantidades de recursos) y ``ConfiguracionSimulacion`` (tiempos y tamaño de
grupo). Aquí se ofrece un único diccionario de configuración, con los nombres
del acuerdo técnico, y se traduce a esos dos objetos.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd

from restaurante.analisis import (
    calcular_metricas,
    ejecutar_experimentos,
    frontera_pareto,
    resumir_experimentos,
    seleccionar_configuracion,
)
from restaurante.dominio.parametros import ParametrosSistema
from restaurante.simulacion.motor import MotorSimulacion
from restaurante.simulacion.procesos import ConfiguracionSimulacion

# Claves del diccionario de configuración que usa la interfaz.
CLAVES_CONFIGURACION = (
    "mesas",
    "meseros",
    "cocineros",
    "tasa_llegadas_grupos_hora",
    "tiempo_pedido_media_min",
    "tiempo_preparacion_media_min",
    "tiempo_consumo_media_min",
    "tiempo_pago_media_min",
    "duracion_llegadas_min",
    "tamano_grupo",
    "distribucion",
)

CONFIGURACION_POR_DEFECTO: dict[str, Any] = {
    "mesas": 4,
    "meseros": 2,
    "cocineros": 2,
    "tasa_llegadas_grupos_hora": 30.0,
    "tiempo_pedido_media_min": 2.0,
    "tiempo_preparacion_media_min": 8.0,
    "tiempo_consumo_media_min": 20.0,
    "tiempo_pago_media_min": 3.0,
    "duracion_llegadas_min": 240.0,
    "tamano_grupo": 2,
    "distribucion": "exponencial",
}

_DISTRIBUCIONES = ("exponencial", "fija")


def _obtener(datos: dict[str, Any], *nombres: str, predeterminado: Any = None) -> Any:
    """Devuelve el primer alias presente en ``datos``."""
    for nombre in nombres:
        if nombre in datos and datos[nombre] is not None:
            return datos[nombre]
    return predeterminado


def _entero_positivo(valor: Any, nombre: str) -> int:
    try:
        numero = float(valor)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"'{nombre}' debe ser un número entero positivo") from exc
    if numero <= 0 or numero != int(numero):
        raise ValueError(f"'{nombre}' debe ser un entero positivo (se recibió {valor!r})")
    return int(numero)


def _positivo(valor: Any, nombre: str) -> float:
    try:
        numero = float(valor)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"'{nombre}' debe ser un número positivo") from exc
    if numero <= 0:
        raise ValueError(f"'{nombre}' debe ser positivo (se recibió {valor!r})")
    return numero


def _no_negativo(valor: Any, nombre: str) -> float:
    try:
        numero = float(valor)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"'{nombre}' debe ser un número no negativo") from exc
    if numero < 0:
        raise ValueError(f"'{nombre}' no puede ser negativo (se recibió {valor!r})")
    return numero


def parametros_desde_dict(datos: dict[str, Any]) -> ParametrosSistema:
    """Construye ``ParametrosSistema`` a partir del diccionario de configuración."""
    tiempo_pedido = _positivo(
        _obtener(datos, "tiempo_pedido_media_min", "t_pedido_min"),
        "tiempo_pedido_media_min",
    )
    # El backend usa la tasa de toma de pedidos por mesero/hora.
    mu_servicio = _obtener(datos, "mu_servicio")
    mu_servicio = _positivo(mu_servicio, "mu_servicio") if mu_servicio else 60.0 / tiempo_pedido

    return ParametrosSistema(
        lambda_llegada=_no_negativo(
            _obtener(
                datos,
                "tasa_llegadas_grupos_hora",
                "lambda_hora",
                "lambda_llegada",
                predeterminado=0.0,
            ),
            "tasa_llegadas_grupos_hora",
        ),
        mu_servicio=mu_servicio,
        mesas=_entero_positivo(_obtener(datos, "mesas", "n_mesas"), "mesas"),
        meseros=_entero_positivo(_obtener(datos, "meseros", "n_meseros"), "meseros"),
        cocineros=_entero_positivo(_obtener(datos, "cocineros", "n_cocineros"), "cocineros"),
    )


def configuracion_simulacion_desde_dict(datos: dict[str, Any]) -> ConfiguracionSimulacion:
    """Construye ``ConfiguracionSimulacion`` a partir del diccionario."""
    distribucion = str(
        _obtener(datos, "distribucion", predeterminado="exponencial")
    ).lower()
    if distribucion not in _DISTRIBUCIONES:
        raise ValueError(
            f"'distribucion' debe ser una de {_DISTRIBUCIONES} (se recibió {distribucion!r})"
        )
    return ConfiguracionSimulacion(
        duracion_llegadas_minutos=_positivo(
            _obtener(datos, "duracion_llegadas_min", "duracion_llegadas_minutos", "horizonte_min"),
            "duracion_llegadas_min",
        ),
        preparacion_media_minutos=_positivo(
            _obtener(datos, "tiempo_preparacion_media_min", "preparacion_media_minutos", "t_preparacion_min"),
            "tiempo_preparacion_media_min",
        ),
        consumo_media_minutos=_positivo(
            _obtener(datos, "tiempo_consumo_media_min", "consumo_media_minutos", "t_consumo_min"),
            "tiempo_consumo_media_min",
        ),
        pago_medio_minutos=_positivo(
            _obtener(datos, "tiempo_pago_media_min", "pago_medio_minutos", "t_pago_min"),
            "tiempo_pago_media_min",
        ),
        tamano_grupo=_entero_positivo(
            _obtener(datos, "tamano_grupo", predeterminado=2), "tamano_grupo"
        ),
        distribucion=distribucion,
    )


def config_desde_dict(datos: dict[str, Any]) -> tuple[ParametrosSistema, ConfiguracionSimulacion]:
    """Traduce el diccionario de configuración a la pareja que usa el backend."""
    return parametros_desde_dict(datos), configuracion_simulacion_desde_dict(datos)


def completar_con_defecto(datos: dict[str, Any]) -> dict[str, Any]:
    """Completa una configuración parcial con los valores por defecto."""
    completa = dict(CONFIGURACION_POR_DEFECTO)
    for clave in CLAVES_CONFIGURACION:
        if clave in datos and datos[clave] is not None:
            completa[clave] = datos[clave]
    return completa


def dict_desde_config(
    parametros: ParametrosSistema, configuracion: ConfiguracionSimulacion
) -> dict[str, Any]:
    """Reconstruye el diccionario de configuración desde la pareja del backend."""
    return {
        "mesas": parametros.mesas,
        "meseros": parametros.meseros,
        "cocineros": parametros.cocineros,
        "tasa_llegadas_grupos_hora": parametros.lambda_llegada,
        "tiempo_pedido_media_min": 60.0 / parametros.mu_servicio,
        "tiempo_preparacion_media_min": configuracion.preparacion_media_minutos,
        "tiempo_consumo_media_min": configuracion.consumo_media_minutos,
        "tiempo_pago_media_min": configuracion.pago_medio_minutos,
        "duracion_llegadas_min": configuracion.duracion_llegadas_minutos,
        "tamano_grupo": configuracion.tamano_grupo,
        "distribucion": configuracion.distribucion,
    }


@dataclass
class ResultadoEjecucion:
    """Resultado de una única réplica más sus métricas y registros tabulares."""

    resultado: Any
    metricas: dict[str, Any]
    registros: pd.DataFrame


def ejecutar_una(
    parametros: ParametrosSistema,
    configuracion: ConfiguracionSimulacion,
    semilla: int = 42,
) -> ResultadoEjecucion:
    """Ejecuta una réplica y devuelve resultado, métricas y registros."""
    motor = MotorSimulacion(parametros, configuracion, semilla=semilla)
    resultado = motor.ejecutar()
    metricas = calcular_metricas(resultado, (parametros, configuracion))
    registros = pd.DataFrame(resultado.registros)
    return ResultadoEjecucion(resultado=resultado, metricas=metricas, registros=registros)


def ejecutar_replicas(
    parametros: ParametrosSistema,
    configuracion: ConfiguracionSimulacion,
    replicas: int = 5,
    semilla_base: int = 1,
) -> pd.DataFrame:
    """Ejecuta varias réplicas de una misma configuración."""
    return ejecutar_experimentos(
        [(parametros, configuracion)], replicas=replicas, semilla_base=semilla_base
    )


def resumir_replicas(tabla: pd.DataFrame) -> pd.DataFrame:
    """Resume la tabla de réplicas con media, desviación e intervalos."""
    return resumir_experimentos(tabla)


_METRICAS_CLAVE = {
    "espera_total_media_min": "Espera total media (min)",
    "permanencia_media_min": "Permanencia media (min)",
    "utilizacion_mesas": "Utilización de mesas",
    "utilizacion_meseros": "Utilización de meseros",
    "utilizacion_cocineros": "Utilización de cocineros",
    "longitud_media_cola_mesas": "Cola media de mesas (grupos)",
    "longitud_media_cola_meseros": "Cola media de meseros (grupos)",
    "longitud_media_cola_cocineros": "Cola media de cocineros (grupos)",
    "tasa_salida_horizonte_grupos_hora": "Capacidad de atención (grupos/hora)",
    "grupos_salidos_horizonte": "Grupos salidos en H",
    "grupos_pendientes_al_cierre": "Grupos pendientes en H",
}


def resumen_metricas(metricas: dict[str, Any]) -> list[tuple[str, Any]]:
    """Parejas (etiqueta, valor) listas para mostrar como indicadores."""
    filas: list[tuple[str, Any]] = []
    for clave, etiqueta in _METRICAS_CLAVE.items():
        if clave in metricas:
            filas.append((etiqueta, metricas[clave]))
    return filas


def comparar_escenarios(
    escenarios: list[dict[str, Any]],
    replicas: int = 3,
    semilla_base: int = 1,
) -> pd.DataFrame:
    """Ejecuta varios escenarios y devuelve la tabla comparativa con su nombre."""
    if not escenarios:
        raise ValueError("Se requiere al menos un escenario")

    configuraciones = [config_desde_dict(escenario) for escenario in escenarios]
    nombres = [
        str(escenario.get("nombre", f"escenario_{i}"))
        for i, escenario in enumerate(escenarios)
    ]
    tabla = ejecutar_experimentos(configuraciones, replicas=replicas, semilla_base=semilla_base)
    mapa = {i: nombre for i, nombre in enumerate(nombres)}
    tabla.insert(0, "escenario", tabla["configuracion_id"].map(mapa))
    return tabla


def resumir_escenarios(tabla: pd.DataFrame) -> pd.DataFrame:
    """Resumen por escenario (agrupa también por las cantidades de recursos)."""
    return resumir_experimentos(tabla)


def optimizar(
    tabla: pd.DataFrame,
    restricciones: dict[str, Any] | None = None,
    pesos: dict[str, float] | None = None,
) -> dict[str, Any]:
    """Selecciona la configuración factible de menor costo ponderado."""
    return seleccionar_configuracion(tabla, restricciones=restricciones or {}, pesos=pesos)


def frontera(tabla: pd.DataFrame, objetivos: list[str]) -> pd.DataFrame:
    """Devuelve las alternativas no dominadas (frontera de compromiso)."""
    return frontera_pareto(tabla, objetivos)
