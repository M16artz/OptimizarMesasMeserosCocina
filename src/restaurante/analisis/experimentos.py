"""Ejecucion reproducible y resumen estadistico de experimentos."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping, Sequence
from math import isfinite
from typing import Any

import pandas as pd

from .metricas import calcular_metricas


def _obtener(objeto: Any, nombre: str, predeterminado: Any = None) -> Any:
    if isinstance(objeto, Mapping):
        return objeto.get(nombre, predeterminado)
    return getattr(objeto, nombre, predeterminado)


def _motor_predeterminado(configuracion: Any, semilla: int) -> Any:
    # Importacion diferida: analisis puede importarse aun si el motor esta en
    # desarrollo, y las pruebas pueden inyectar un simulador determinista.
    from restaurante.simulacion.motor import MotorSimulacion

    if isinstance(configuracion, (tuple, list)) and len(configuracion) == 2:
        parametros, configuracion_simulacion = configuracion
        return MotorSimulacion(
            parametros, configuracion_simulacion, semilla=semilla
        )

    parametros = _obtener(configuracion, "parametros")
    configuracion_simulacion = _obtener(
        configuracion,
        "configuracion_simulacion",
        _obtener(configuracion, "configuracion"),
    )
    if parametros is not None:
        return MotorSimulacion(
            parametros, configuracion_simulacion, semilla=semilla
        )
    return MotorSimulacion(configuracion, semilla=semilla)


def _obtener_recurso(configuracion: Any, nombre: str) -> Any:
    valor = _obtener(configuracion, nombre)
    if valor is not None:
        return valor
    if isinstance(configuracion, (tuple, list)) and len(configuracion) == 2:
        valor = _obtener(configuracion[0], nombre)
        if valor is not None:
            return valor
    parametros = _obtener(configuracion, "parametros")
    return _obtener(parametros, nombre) if parametros is not None else None


def _ejecutar_motor(motor_o_resultado: Any) -> Any:
    ejecutar = getattr(motor_o_resultado, "ejecutar", None)
    return ejecutar() if callable(ejecutar) else motor_o_resultado


def ejecutar_experimentos(
    configuraciones: Iterable[Any],
    replicas: int,
    semilla_base: int,
    simulador_factory: Callable[[Any, int], Any] | None = None,
) -> pd.DataFrame:
    """Ejecuta todas las configuraciones usando semillas comunes por replica.

    El uso de la misma semilla para la replica ``r`` de cada configuracion
    reduce ruido al comparar alternativas (numeros aleatorios comunes).
    ``simulador_factory`` puede devolver un motor con ``ejecutar()`` o el
    resultado directamente.
    """

    if isinstance(replicas, bool) or not isinstance(replicas, int) or replicas <= 0:
        raise ValueError("replicas debe ser un entero positivo")
    if isinstance(semilla_base, bool) or not isinstance(semilla_base, int):
        raise TypeError("semilla_base debe ser un entero")
    configuraciones = list(configuraciones)
    if not configuraciones:
        raise ValueError("se requiere al menos una configuracion")

    fabrica = simulador_factory or _motor_predeterminado
    filas: list[dict[str, Any]] = []
    for indice_configuracion, configuracion in enumerate(configuraciones):
        for replica in range(replicas):
            semilla = semilla_base + replica
            resultado = _ejecutar_motor(fabrica(configuracion, semilla))
            fila: dict[str, Any] = {
                "configuracion_id": indice_configuracion,
                "replica": replica + 1,
                "semilla": semilla,
            }
            for nombre in ("mesas", "meseros", "cocineros"):
                valor = _obtener_recurso(configuracion, nombre)
                if valor is not None:
                    fila[nombre] = valor
            fila.update(calcular_metricas(resultado, configuracion))
            filas.append(fila)
    return pd.DataFrame(filas)


def resumir_experimentos(
    tabla_experimentos: pd.DataFrame,
    metricas: Sequence[str] | None = None,
    nivel_confianza: float = 0.95,
) -> pd.DataFrame:
    """Resume replicas por configuracion con media, desviacion e IC de Student."""

    if tabla_experimentos.empty:
        raise ValueError("tabla_experimentos no puede estar vacia")
    if isinstance(nivel_confianza, bool):
        raise TypeError("nivel_confianza debe ser numerico")
    try:
        nivel_confianza = float(nivel_confianza)
    except (TypeError, ValueError) as exc:
        raise TypeError("nivel_confianza debe ser numerico") from exc
    if not isfinite(nivel_confianza) or not 0 < nivel_confianza < 1:
        raise ValueError("nivel_confianza debe estar entre 0 y 1")

    identificadores = [
        c
        for c in ("configuracion_id", "mesas", "meseros", "cocineros")
        if c in tabla_experimentos.columns
    ]
    if not identificadores:
        raise ValueError("la tabla no contiene columnas de configuracion")

    excluidas = set(identificadores) | {"replica", "semilla"}
    if metricas is None:
        metricas = [
            c
            for c in tabla_experimentos.select_dtypes(include="number").columns
            if c not in excluidas
        ]
    else:
        metricas = list(metricas)
        faltantes = set(metricas) - set(tabla_experimentos.columns)
        if faltantes:
            raise ValueError(f"metricas inexistentes: {sorted(faltantes)}")
    if not metricas:
        raise ValueError("se requiere al menos una metrica numerica")
    no_numericas = [
        metrica
        for metrica in metricas
        if not pd.api.types.is_numeric_dtype(tabla_experimentos[metrica])
    ]
    if no_numericas:
        raise TypeError(f"metricas no numericas: {sorted(no_numericas)}")

    agrupada = tabla_experimentos.groupby(identificadores, dropna=False)[list(metricas)]
    medias = agrupada.mean().add_suffix("_media")
    desviaciones = agrupada.std(ddof=1).fillna(0.0).add_suffix("_desviacion")
    cantidades = agrupada.size().rename("replicas")

    # scipy ya forma parte de las dependencias del proyecto.
    from scipy.stats import t

    resumen = pd.concat([medias, desviaciones, cantidades], axis=1).reset_index()
    for metrica in metricas:
        error = resumen[f"{metrica}_desviacion"] / resumen["replicas"].pow(0.5)
        critico = resumen["replicas"].map(
            lambda n: float(t.ppf((1 + nivel_confianza) / 2, n - 1)) if n > 1 else 0.0
        )
        margen = critico * error
        resumen[f"{metrica}_ic_inferior"] = resumen[f"{metrica}_media"] - margen
        resumen[f"{metrica}_ic_superior"] = resumen[f"{metrica}_media"] + margen
    return resumen
