"""Seleccion exhaustiva de configuraciones del restaurante."""

from __future__ import annotations

from collections.abc import Mapping
from math import isfinite
from typing import Any

import pandas as pd


RECURSOS = ("mesas", "meseros", "cocineros")


def _normalizar_restriccion(nombre: str, valor: Any) -> tuple[str, str, float]:
    """Convierte varias notaciones de restriccion a (metrica, operador, limite)."""

    if isinstance(valor, Mapping):
        operadores = [(op, valor[op]) for op in ("max", "min") if op in valor]
        if len(operadores) != 1:
            raise ValueError(f"la restriccion '{nombre}' requiere un unico max o min")
        operador, limite = operadores[0]
        metrica = nombre
    elif nombre.startswith("max_"):
        metrica, operador, limite = nombre[4:], "max", valor
    elif nombre.startswith("min_"):
        metrica, operador, limite = nombre[4:], "min", valor
    else:
        # Por convencion, un limite simple es un maximo (p. ej. espera <= 10).
        metrica, operador, limite = nombre, "max", valor
    try:
        limite_normalizado = float(limite)
    except (TypeError, ValueError) as exc:
        raise TypeError(f"el limite de '{nombre}' debe ser numerico") from exc
    if not isfinite(limite_normalizado):
        raise ValueError(f"el limite de '{nombre}' debe ser finito")
    return metrica, operador, limite_normalizado


def _tabla_por_configuracion(tabla: pd.DataFrame) -> pd.DataFrame:
    claves = [c for c in ("configuracion_id", *RECURSOS) if c in tabla.columns]
    if not all(recurso in claves for recurso in RECURSOS):
        raise ValueError(f"la tabla debe contener las columnas {RECURSOS}")
    for recurso in RECURSOS:
        valores = pd.to_numeric(tabla[recurso], errors="coerce")
        if valores.isna().any() or (~valores.map(isfinite)).any():
            raise ValueError(f"la columna {recurso} debe contener numeros finitos")
        if (valores <= 0).any() or (valores % 1 != 0).any():
            raise ValueError(f"la columna {recurso} debe contener enteros positivos")
        tabla = tabla.assign(**{recurso: valores.astype(int)})

    # Si existen replicas, las restricciones se aplican a sus medias.
    if "replica" in tabla.columns or tabla.duplicated(claves).any():
        numericas = [
            c
            for c in tabla.select_dtypes(include="number").columns
            if c not in set(claves) | {"replica", "semilla"}
        ]
        return tabla.groupby(claves, as_index=False, dropna=False)[numericas].mean()
    return tabla.copy()


def seleccionar_configuracion(
    tabla_experimentos: pd.DataFrame,
    restricciones: Mapping[str, Any] | None,
    pesos: Mapping[str, float] | None,
) -> dict[str, Any]:
    """Selecciona la configuracion factible de menor costo ponderado.

    Las restricciones admiten tres formas: ``{"espera": 10}`` (maximo por
    defecto), ``{"max_espera": 10}`` o ``{"espera": {"max": 10}}``.
    Para minimos se usa ``min_`` o ``{"min": valor}``. Si hay empate de costo,
    se prefieren menor espera total y luego menos recursos.
    """

    if not isinstance(tabla_experimentos, pd.DataFrame):
        tabla_experimentos = pd.DataFrame(tabla_experimentos)
    if tabla_experimentos.empty:
        raise ValueError("tabla_experimentos no puede estar vacia")

    tabla = _tabla_por_configuracion(tabla_experimentos)
    pesos = dict(pesos or {recurso: 1.0 for recurso in RECURSOS})
    desconocidos = set(pesos) - set(RECURSOS)
    if desconocidos:
        raise ValueError(f"pesos desconocidos: {sorted(desconocidos)}")
    pesos_completos: dict[str, float] = {}
    for recurso in RECURSOS:
        try:
            peso = float(pesos.get(recurso, 0.0))
        except (TypeError, ValueError) as exc:
            raise TypeError(f"el peso de {recurso} debe ser numerico") from exc
        if not isfinite(peso) or peso < 0:
            raise ValueError(f"el peso de {recurso} debe ser finito y no negativo")
        pesos_completos[recurso] = peso

    mascara = pd.Series(True, index=tabla.index)
    restricciones_normalizadas = []
    for nombre, limite in (restricciones or {}).items():
        metrica, operador, umbral = _normalizar_restriccion(nombre, limite)
        if metrica not in tabla.columns:
            raise ValueError(f"la metrica de restriccion '{metrica}' no existe")
        if not pd.api.types.is_numeric_dtype(tabla[metrica]):
            raise TypeError(f"la metrica de restriccion '{metrica}' debe ser numerica")
        if tabla[metrica].isna().any() or (~tabla[metrica].map(isfinite)).any():
            raise ValueError(
                f"la metrica de restriccion '{metrica}' debe contener valores finitos"
            )
        mascara &= tabla[metrica].le(umbral) if operador == "max" else tabla[metrica].ge(umbral)
        restricciones_normalizadas.append(
            {"metrica": metrica, "operador": operador, "limite": umbral}
        )

    tabla = tabla.assign(
        costo_recursos=sum(tabla[r] * pesos_completos[r] for r in RECURSOS),
        factible=mascara,
    )
    factibles = tabla.loc[tabla["factible"]].copy()
    if factibles.empty:
        return {
            "factible": False,
            "configuracion": None,
            "costo_recursos": None,
            "metricas": {},
            "configuraciones_evaluadas": int(len(tabla)),
            "configuraciones_factibles": 0,
            "restricciones": restricciones_normalizadas,
            "mensaje": "ninguna configuracion satisface todas las restricciones",
        }

    orden = ["costo_recursos"]
    if "espera_total_media_min" in factibles.columns:
        orden.append("espera_total_media_min")
    orden.extend(RECURSOS)
    mejor = factibles.sort_values(orden, kind="stable").iloc[0]
    configuracion = {recurso: int(mejor[recurso]) for recurso in RECURSOS}
    omitidas = set(RECURSOS) | {"factible", "costo_recursos"}
    metricas = {
        columna: (valor.item() if hasattr(valor, "item") else valor)
        for columna, valor in mejor.items()
        if columna not in omitidas
    }
    return {
        "factible": True,
        "configuracion": configuracion,
        **configuracion,
        "costo_recursos": float(mejor["costo_recursos"]),
        "metricas": metricas,
        "configuraciones_evaluadas": int(len(tabla)),
        "configuraciones_factibles": int(len(factibles)),
        "restricciones": restricciones_normalizadas,
        "mensaje": "configuracion factible de menor costo ponderado",
    }


def frontera_pareto(
    tabla_experimentos: pd.DataFrame,
    objetivos_minimizar: list[str],
) -> pd.DataFrame:
    """Devuelve alternativas no dominadas para los objetivos indicados."""

    if tabla_experimentos.empty:
        raise ValueError("tabla_experimentos no puede estar vacia")
    faltantes = set(objetivos_minimizar) - set(tabla_experimentos.columns)
    if faltantes:
        raise ValueError(f"objetivos inexistentes: {sorted(faltantes)}")
    if not objetivos_minimizar:
        raise ValueError("se requiere al menos un objetivo")

    for objetivo in objetivos_minimizar:
        if not pd.api.types.is_numeric_dtype(tabla_experimentos[objetivo]):
            raise TypeError(f"el objetivo '{objetivo}' debe ser numerico")

    tabla = _tabla_por_configuracion(tabla_experimentos)
    for objetivo in objetivos_minimizar:
        if tabla[objetivo].isna().any() or (~tabla[objetivo].map(isfinite)).any():
            raise ValueError(f"el objetivo '{objetivo}' debe contener valores finitos")

    valores = tabla[objetivos_minimizar]
    no_dominada = []
    for indice, candidata in valores.iterrows():
        domina = valores.le(candidata).all(axis=1) & valores.lt(candidata).any(axis=1)
        domina.loc[indice] = False
        no_dominada.append(not bool(domina.any()))
    return tabla.loc[no_dominada].copy().reset_index(drop=True)
