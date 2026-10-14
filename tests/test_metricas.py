"""Pruebas de las métricas agregadas, incluidas las longitudes medias de cola."""

from __future__ import annotations

import pytest

from restaurante.analisis import calcular_metricas
from restaurante.dominio.parametros import ParametrosSistema
from restaurante.simulacion.motor import MotorSimulacion
from restaurante.simulacion.procesos import ConfiguracionSimulacion

_COLAS = (
    "longitud_media_cola_mesas",
    "longitud_media_cola_meseros",
    "longitud_media_cola_cocineros",
)


def _configuracion(**cambios) -> ConfiguracionSimulacion:
    base = dict(
        duracion_llegadas_minutos=100.0,
        preparacion_media_minutos=1.0,
        consumo_media_minutos=1.0,
        pago_medio_minutos=1.0,
        tamano_grupo=1,
        distribucion="fija",
    )
    base.update(cambios)
    return ConfiguracionSimulacion(**base)


def _parametros(mesas: int) -> ParametrosSistema:
    # mu_servicio = 60 pedidos/hora => media de pedido = 1 minuto.
    return ParametrosSistema(
        lambda_llegada=0, mu_servicio=60, mesas=mesas, meseros=5, cocineros=5
    )


def test_longitud_media_cola_determinista():
    """Con una sola mesa, el segundo grupo espera 4 min en un horizonte de 8."""

    parametros = _parametros(mesas=1)
    configuracion = _configuracion()
    resultado = MotorSimulacion(parametros, configuracion, semilla=1).ejecutar(
        tiempos_llegada=[0.0, 0.0]
    )
    metricas = calcular_metricas(resultado, (parametros, configuracion))

    assert resultado.area_colas_minutos["mesa"] == pytest.approx(4.0)
    assert resultado.horizonte_observado_minutos == pytest.approx(8.0)
    assert metricas["longitud_media_cola_mesas"] == pytest.approx(0.5)
    assert metricas["longitud_media_cola_meseros"] == pytest.approx(0.0)
    assert metricas["longitud_media_cola_cocineros"] == pytest.approx(0.0)


def test_sin_contencion_no_hay_colas_de_mesa():
    parametros = _parametros(mesas=5)
    configuracion = _configuracion()
    resultado = MotorSimulacion(parametros, configuracion, semilla=1).ejecutar(
        tiempos_llegada=[0.0, 0.0]
    )
    metricas = calcular_metricas(resultado, (parametros, configuracion))

    assert resultado.area_colas_minutos["mesa"] == pytest.approx(0.0)
    assert metricas["longitud_media_cola_mesas"] == pytest.approx(0.0)


def test_metricas_incluyen_las_colas_de_los_tres_recursos():
    parametros = _parametros(mesas=1)
    configuracion = _configuracion()
    resultado = MotorSimulacion(parametros, configuracion, semilla=3).ejecutar(
        tiempos_llegada=[0.0, 0.5, 1.0]
    )
    metricas = calcular_metricas(resultado, (parametros, configuracion))

    for clave in ("longitud_media_cola_mesas", "longitud_media_cola_meseros", "longitud_media_cola_cocineros"):
        assert clave in metricas
        assert metricas[clave] >= 0.0
    assert metricas["longitud_media_cola_mesas"] > 0.0


def test_longitud_cola_es_cero_si_falta_el_area():
    resultado = {
        "registros": [],
        "utilizacion": {"mesa": 0.0, "mesero": 0.0, "cocinero": 0.0},
        "horizonte_observado_minutos": 60.0,
        "grupos_llegados_horizonte": 0,
        "grupos_salidos_horizonte": 0,
        "grupos_pendientes_al_cierre": 0,
        "tiempo_ultima_salida_min": 0.0,
    }
    metricas = calcular_metricas(resultado)
    assert metricas["longitud_media_cola_mesas"] == pytest.approx(0.0)
    assert metricas["longitud_media_cola_meseros"] == pytest.approx(0.0)
    assert metricas["longitud_media_cola_cocineros"] == pytest.approx(0.0)
