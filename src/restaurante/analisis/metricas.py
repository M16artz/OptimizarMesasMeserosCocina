"""Calculo y validacion de indicadores de una simulacion del restaurante."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from numbers import Integral
from math import isfinite
from statistics import fmean
from typing import Any


def _obtener(objeto: Any, nombre: str, predeterminado: Any = None) -> Any:
    if isinstance(objeto, Mapping):
        return objeto.get(nombre, predeterminado)
    return getattr(objeto, nombre, predeterminado)


def _numero(objeto: Any, nombre: str) -> float:
    valor = _obtener(objeto, nombre)
    if valor is None:
        raise ValueError(f"falta el campo requerido '{nombre}'")
    if isinstance(valor, bool):
        raise TypeError(f"'{nombre}' debe ser numerico")
    try:
        numero = float(valor)
    except (TypeError, ValueError) as exc:
        raise TypeError(f"'{nombre}' debe ser numerico") from exc
    if not isfinite(numero):
        raise ValueError(f"'{nombre}' debe ser finito")
    return numero


_CAMPOS_TIEMPO = {
    "llegada_min": ("llegada_min", "llegada"),
    "mesa_inicio_min": ("mesa_inicio_min", "mesa_asignada"),
    "pedido_inicio_min": ("pedido_inicio_min", "inicio_pedido"),
    "pedido_fin_min": ("pedido_fin_min", "fin_pedido"),
    "cocina_inicio_min": ("cocina_inicio_min", "inicio_cocina"),
    "cocina_fin_min": ("cocina_fin_min", "fin_cocina"),
    "consumo_fin_min": ("consumo_fin_min", "fin_consumo"),
    "pago_inicio_min": ("pago_inicio_min", "inicio_pago"),
    "salida_min": ("salida_min", "salida"),
}


def _obtener_alias(objeto: Any, nombres: Sequence[str], predeterminado: Any = None) -> Any:
    for nombre in nombres:
        valor = _obtener(objeto, nombre)
        if valor is not None:
            return valor
    return predeterminado


def _numero_alias(objeto: Any, nombre_canonico: str) -> float:
    nombres = _CAMPOS_TIEMPO[nombre_canonico]
    valor = _obtener_alias(objeto, nombres)
    if valor is None:
        raise ValueError(
            f"falta el campo requerido '{nombre_canonico}' "
            f"(tambien se admite '{nombres[-1]}')"
        )
    return _numero({nombre_canonico: valor}, nombre_canonico)


def _fuentes_configuracion(configuracion: Any) -> list[Any]:
    """Descompone configuraciones unificadas, anidadas o en una pareja."""

    if configuracion is None:
        return []
    if isinstance(configuracion, (tuple, list)) and len(configuracion) == 2:
        return [configuracion[0], configuracion[1]]
    fuentes = [configuracion]
    for nombre in ("parametros", "configuracion", "configuracion_simulacion"):
        anidada = _obtener(configuracion, nombre)
        if anidada is not None and anidada is not configuracion:
            fuentes.append(anidada)
    return fuentes


def _buscar_configuracion(fuentes: Sequence[Any], *nombres: str) -> Any:
    for fuente in fuentes:
        valor = _obtener_alias(fuente, nombres)
        if valor is not None:
            return valor
    return None


def esperas_registro(registro: Any) -> dict[str, float]:
    """Calcula las esperas de un grupo y verifica el orden de sus hitos."""

    nombres = (
        "llegada_min",
        "mesa_inicio_min",
        "pedido_inicio_min",
        "pedido_fin_min",
        "cocina_inicio_min",
        "cocina_fin_min",
        "consumo_fin_min",
        "pago_inicio_min",
        "salida_min",
    )
    tiempos = {nombre: _numero_alias(registro, nombre) for nombre in nombres}
    secuencia = [tiempos[nombre] for nombre in nombres]
    if any(actual > siguiente for actual, siguiente in zip(secuencia, secuencia[1:])):
        grupo_id = _obtener(registro, "grupo_id", "desconocido")
        raise ValueError(f"los hitos del grupo {grupo_id} no estan ordenados")

    espera_mesa = tiempos["mesa_inicio_min"] - tiempos["llegada_min"]
    espera_pedido = tiempos["pedido_inicio_min"] - tiempos["mesa_inicio_min"]
    espera_cocina = tiempos["cocina_inicio_min"] - tiempos["pedido_fin_min"]
    espera_pago = tiempos["pago_inicio_min"] - tiempos["consumo_fin_min"]
    espera_total = espera_mesa + espera_pedido + espera_cocina + espera_pago
    return {
        "espera_mesa_min": espera_mesa,
        "espera_mesero_pedido_min": espera_pedido,
        "espera_cocina_min": espera_cocina,
        "espera_mesero_pago_min": espera_pago,
        "espera_total_min": espera_total,
        "permanencia_total_min": tiempos["salida_min"] - tiempos["llegada_min"],
    }


def _media(filas: list[dict[str, float]], campo: str) -> float:
    return fmean(fila[campo] for fila in filas) if filas else 0.0


def _conteo(resultado: Any, nombre: str, predeterminado: int) -> int:
    valor = _obtener(resultado, nombre, predeterminado)
    if isinstance(valor, bool) or not isinstance(valor, Integral):
        raise TypeError(f"'{nombre}' debe ser un entero")
    return int(valor)


def _validar_utilizacion(valor: Any, recurso: str) -> float:
    try:
        utilizacion = float(valor)
    except (TypeError, ValueError) as exc:
        raise TypeError(f"la utilizacion de {recurso} debe ser numerica") from exc
    if not isfinite(utilizacion):
        raise ValueError(f"la utilizacion de {recurso} debe ser finita")
    tolerancia = 1e-9
    if utilizacion < -tolerancia or utilizacion > 1.0 + tolerancia:
        raise ValueError(f"la utilizacion de {recurso} queda fuera de [0, 1]")
    return min(1.0, max(0.0, utilizacion))


def _utilizacion(
    resultado: Any, recurso: str, cantidad: int | None, horizonte: float
) -> float:
    utilizaciones = _obtener(resultado, "utilizacion")
    singular = {"mesas": "mesa", "meseros": "mesero", "cocineros": "cocinero"}[recurso]
    if isinstance(utilizaciones, Mapping) and singular in utilizaciones:
        return _validar_utilizacion(utilizaciones[singular], recurso)

    if cantidad is None:
        raise ValueError(
            f"no se puede calcular la utilizacion de {recurso}: falta su cantidad"
        )
    ocupacion = _numero(resultado, f"ocupacion_{recurso}_minutos_horizonte")
    if ocupacion < 0:
        raise ValueError(f"la ocupacion de {recurso} no puede ser negativa")
    return _validar_utilizacion(ocupacion / (cantidad * horizonte), recurso)


def _longitud_media_cola(resultado: Any, recurso: str, horizonte_observado: float) -> float:
    """Longitud media de cola (numero medio de grupos en espera).

    Se obtiene integrando la longitud de la cola en el tiempo: el motor acumula
    ``area_colas_minutos``; dividirla por el horizonte observado (que cubre
    llegadas y fase de vaciado) da el numero medio de grupos en espera del
    recurso, segun la Ley de Little. Si el resultado no incluye esa area, se
    reporta ``0.0`` para no romper el contrato de metricas.
    """

    singular = {"mesas": "mesa", "meseros": "mesero", "cocineros": "cocinero"}[recurso]
    areas = _obtener(resultado, "area_colas_minutos")
    if not isinstance(areas, Mapping) or singular not in areas:
        return 0.0
    try:
        area = float(areas[singular])
    except (TypeError, ValueError) as exc:
        raise TypeError(f"el area de cola de {recurso} debe ser numerica") from exc
    if not isfinite(area):
        raise ValueError(f"el area de cola de {recurso} debe ser finita")
    if area < 0:
        raise ValueError(f"el area de cola de {recurso} no puede ser negativa")
    return area / horizonte_observado


def calcular_metricas(
    resultado: Any, configuracion: Any | None = None
) -> dict[str, float | int]:
    """Obtiene indicadores comparables a partir de ``ResultadoSimulacion``.

    Se acepta tanto una instancia con atributos como un diccionario equivalente,
    lo que facilita usar el analisis con dataclasses y con datos serializados.
    Las medias de espera incluyen todos los grupos admitidos y finalizados tras
    la fase de vaciado.
    """

    configuracion_resultado = _obtener(resultado, "configuracion")
    if configuracion is None:
        configuracion = configuracion_resultado
    fuentes = _fuentes_configuracion(configuracion)
    if configuracion_resultado is not None and configuracion_resultado is not configuracion:
        fuentes.extend(_fuentes_configuracion(configuracion_resultado))

    cantidades: dict[str, int | None] = {}
    for recurso in ("mesas", "meseros", "cocineros"):
        valor = _buscar_configuracion(fuentes, recurso)
        if valor is None:
            cantidades[recurso] = None
            continue
        if isinstance(valor, bool) or not isinstance(valor, Integral) or valor <= 0:
            raise ValueError(f"configuracion.{recurso} debe ser un entero positivo")
        cantidades[recurso] = int(valor)

    horizonte_valor = _buscar_configuracion(
        fuentes, "duracion_llegadas_min", "duracion_llegadas_minutos"
    )
    if horizonte_valor is None:
        horizonte_valor = _obtener(resultado, "horizonte_observado_minutos")
    if horizonte_valor is None:
        raise ValueError("falta la duracion del horizonte de observacion")
    try:
        horizonte = float(horizonte_valor)
    except (TypeError, ValueError) as exc:
        raise TypeError("la duracion del horizonte debe ser numerica") from exc
    if not isfinite(horizonte):
        raise ValueError("la duracion del horizonte debe ser finita")
    if horizonte <= 0:
        raise ValueError("la duracion del horizonte debe ser mayor que cero")

    registros_obj = _obtener(resultado, "registros", ())
    if registros_obj is None:
        registros_obj = ()
    registros = list(registros_obj)
    esperas = [esperas_registro(registro) for registro in registros]

    llegados = _conteo(resultado, "grupos_llegados_horizonte", len(registros))
    salidos_horizonte = _conteo(
        resultado,
        "grupos_salidos_horizonte",
        sum(_numero_alias(r, "salida_min") <= horizonte for r in registros),
    )
    pendientes = _conteo(
        resultado, "grupos_pendientes_al_cierre", llegados - salidos_horizonte
    )
    if min(llegados, salidos_horizonte, pendientes) < 0:
        raise ValueError("los conteos de grupos no pueden ser negativos")
    if salidos_horizonte > llegados or pendientes != llegados - salidos_horizonte:
        raise ValueError("los conteos de grupos son inconsistentes")

    ultima_salida = _obtener(resultado, "tiempo_ultima_salida_min")
    if ultima_salida is None:
        ultima_salida = max(
            (_numero_alias(r, "salida_min") for r in registros), default=0.0
        )
    try:
        ultima_salida = float(ultima_salida)
    except (TypeError, ValueError) as exc:
        raise TypeError("tiempo_ultima_salida_min debe ser numerico") from exc
    if not isfinite(ultima_salida) or ultima_salida < 0:
        raise ValueError("tiempo_ultima_salida_min debe ser finito y no negativo")

    horizonte_observado_valor = _obtener(resultado, "horizonte_observado_minutos")
    if horizonte_observado_valor is None:
        horizonte_observado = max(horizonte, ultima_salida)
    else:
        try:
            horizonte_observado = float(horizonte_observado_valor)
        except (TypeError, ValueError) as exc:
            raise TypeError("el horizonte observado debe ser numerico") from exc
        if not isfinite(horizonte_observado) or horizonte_observado <= 0:
            raise ValueError("el horizonte observado debe ser finito y positivo")

    return {
        "grupos_llegados_horizonte": llegados,
        "grupos_salidos_horizonte": salidos_horizonte,
        "grupos_pendientes_al_cierre": pendientes,
        "espera_mesa_media_min": _media(esperas, "espera_mesa_min"),
        "espera_mesero_pedido_media_min": _media(
            esperas, "espera_mesero_pedido_min"
        ),
        "espera_cocina_media_min": _media(esperas, "espera_cocina_min"),
        "espera_mesero_pago_media_min": _media(
            esperas, "espera_mesero_pago_min"
        ),
        "espera_total_media_min": _media(esperas, "espera_total_min"),
        "permanencia_media_min": _media(esperas, "permanencia_total_min"),
        "utilizacion_mesas": _utilizacion(
            resultado, "mesas", cantidades["mesas"], horizonte
        ),
        "utilizacion_meseros": _utilizacion(
            resultado, "meseros", cantidades["meseros"], horizonte
        ),
        "utilizacion_cocineros": _utilizacion(
            resultado, "cocineros", cantidades["cocineros"], horizonte
        ),
        "longitud_media_cola_mesas": _longitud_media_cola(
            resultado, "mesas", horizonte_observado
        ),
        "longitud_media_cola_meseros": _longitud_media_cola(
            resultado, "meseros", horizonte_observado
        ),
        "longitud_media_cola_cocineros": _longitud_media_cola(
            resultado, "cocineros", horizonte_observado
        ),
        "tasa_salida_horizonte_grupos_hora": salidos_horizonte * 60.0 / horizonte,
        "tiempo_ultima_salida_min": ultima_salida,
    }
