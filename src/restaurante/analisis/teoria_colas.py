"""Resultados analiticos para una cola :math:`M/M/s`.

Las tasas de llegada y servicio deben estar expresadas en la misma unidad de
tiempo.  Las funciones de este modulo describen una estacion aislada; no
pretenden representar por si solas toda la red del restaurante.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from math import exp, isfinite, lgamma, log


@dataclass(frozen=True, slots=True)
class IndicadoresMMS:
    """Indicadores de estado estable de una cola M/M/s."""

    tasa_llegada: float
    tasa_servicio: float
    servidores: int
    utilizacion: float
    probabilidad_sistema_vacio: float
    probabilidad_espera: float
    longitud_media_cola: float
    longitud_media_sistema: float
    tiempo_medio_cola: float
    tiempo_medio_sistema: float

    def como_dict(self) -> dict[str, float | int]:
        """Devuelve una representacion apropiada para tablas o JSON."""

        return asdict(self)


def _validar_parametros(
    tasa_llegada: float, tasa_servicio: float, servidores: int
) -> tuple[float, float, int]:
    if isinstance(servidores, bool) or not isinstance(servidores, int):
        raise TypeError("servidores debe ser un numero entero")
    if servidores <= 0:
        raise ValueError("servidores debe ser mayor que cero")

    try:
        llegada = float(tasa_llegada)
        servicio = float(tasa_servicio)
    except (TypeError, ValueError) as exc:
        raise TypeError("las tasas deben ser numeros reales") from exc

    if not isfinite(llegada) or llegada < 0:
        raise ValueError("tasa_llegada debe ser finita y no negativa")
    if not isfinite(servicio) or servicio <= 0:
        raise ValueError("tasa_servicio debe ser finita y mayor que cero")
    if llegada >= servidores * servicio:
        raise ValueError(
            "la cola M/M/s no es estable: se requiere "
            "tasa_llegada < servidores * tasa_servicio"
        )
    return llegada, servicio, servidores


def calcular_indicadores_mms(
    tasa_llegada: float, tasa_servicio: float, servidores: int
) -> IndicadoresMMS:
    """Calcula los indicadores clasicos de una cola M/M/s estable.

    ``tasa_servicio`` es la tasa de *cada* servidor. Para una tasa de llegada
    cero se devuelve el sistema vacio, sin divisiones indeterminadas.
    """

    llegada, servicio, servidores = _validar_parametros(
        tasa_llegada, tasa_servicio, servidores
    )
    if llegada == 0:
        return IndicadoresMMS(
            tasa_llegada=llegada,
            tasa_servicio=servicio,
            servidores=servidores,
            utilizacion=0.0,
            probabilidad_sistema_vacio=1.0,
            probabilidad_espera=0.0,
            longitud_media_cola=0.0,
            longitud_media_sistema=0.0,
            tiempo_medio_cola=0.0,
            tiempo_medio_sistema=1.0 / servicio,
        )

    carga = llegada / servicio
    utilizacion = carga / servidores

    # Erlang B se evalua mediante una recurrencia acotada. A partir de ella se
    # obtiene Erlang C sin potencias ni factoriales que desborden para cargas o
    # cantidades de servidores grandes.
    erlang_b = 1.0
    for n in range(1, servidores + 1):
        erlang_b = carga * erlang_b / (n + carga * erlang_b)
    probabilidad_espera = erlang_b / (
        1.0 - utilizacion + utilizacion * erlang_b
    )

    # P0 no interviene en las demas medidas, pero se calcula en escala
    # logaritmica para mantenerla representable tanto como sea posible.
    log_carga = log(carga)
    log_terminos = [
        n * log_carga - lgamma(n + 1) for n in range(servidores)
    ]
    log_terminos.append(
        servidores * log_carga
        - lgamma(servidores + 1)
        - log(1.0 - utilizacion)
    )
    maximo = max(log_terminos)
    log_normalizador = maximo + log(
        sum(exp(termino - maximo) for termino in log_terminos)
    )
    probabilidad_vacio = exp(-log_normalizador)

    longitud_cola = (
        probabilidad_espera * utilizacion / (1.0 - utilizacion)
    )
    tiempo_cola = longitud_cola / llegada
    tiempo_sistema = tiempo_cola + 1.0 / servicio
    longitud_sistema = llegada * tiempo_sistema

    return IndicadoresMMS(
        tasa_llegada=llegada,
        tasa_servicio=servicio,
        servidores=servidores,
        utilizacion=utilizacion,
        probabilidad_sistema_vacio=probabilidad_vacio,
        probabilidad_espera=probabilidad_espera,
        longitud_media_cola=longitud_cola,
        longitud_media_sistema=longitud_sistema,
        tiempo_medio_cola=tiempo_cola,
        tiempo_medio_sistema=tiempo_sistema,
    )


def erlang_c(tasa_llegada: float, tasa_servicio: float, servidores: int) -> float:
    """Devuelve la probabilidad de que una llegada tenga que esperar."""

    return calcular_indicadores_mms(
        tasa_llegada, tasa_servicio, servidores
    ).probabilidad_espera


def calcular_mms(
    tasa_llegada: float, tasa_servicio: float, servidores: int
) -> dict[str, float | int]:
    """Atajo compatible con consumidores que prefieren un diccionario."""

    return calcular_indicadores_mms(
        tasa_llegada, tasa_servicio, servidores
    ).como_dict()
