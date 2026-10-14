"""Pruebas de la capa de aplicación (servicios) contra el backend real."""

from __future__ import annotations

import pandas as pd
import pytest

from restaurante.dominio.parametros import ParametrosSistema
from restaurante.interfaz import servicios


def _configuracion(**cambios):
    base = dict(servicios.CONFIGURACION_POR_DEFECTO)
    base.update(cambios)
    return base


def test_completar_con_defecto_rellena_faltantes():
    completa = servicios.completar_con_defecto({"mesas": 9})
    assert completa["mesas"] == 9
    assert completa["distribucion"] == servicios.CONFIGURACION_POR_DEFECTO["distribucion"]
    assert set(completa) == set(servicios.CONFIGURACION_POR_DEFECTO)


def test_parametros_convierten_tiempo_de_pedido_a_mu_servicio():
    parametros = servicios.parametros_desde_dict(_configuracion(tiempo_pedido_media_min=2.0))
    assert isinstance(parametros, ParametrosSistema)
    assert parametros.mu_servicio == pytest.approx(30.0)
    assert parametros.mesas == servicios.CONFIGURACION_POR_DEFECTO["mesas"]


def test_mu_servicio_explicito_tiene_prioridad():
    parametros = servicios.parametros_desde_dict(_configuracion(mu_servicio=12.0))
    assert parametros.mu_servicio == pytest.approx(12.0)


@pytest.mark.parametrize("campo", ["mesas", "meseros", "cocineros"])
def test_cantidades_de_recursos_deben_ser_enteros_positivos(campo):
    with pytest.raises(ValueError):
        servicios.parametros_desde_dict(_configuracion(**{campo: 0}))


def test_distribucion_invalida_falla():
    with pytest.raises(ValueError):
        servicios.configuracion_simulacion_desde_dict(_configuracion(distribucion="normal"))


def test_dict_desde_config_es_inverso_de_config_desde_dict():
    original = _configuracion()
    parametros, configuracion_sim = servicios.config_desde_dict(original)
    reconstruido = servicios.dict_desde_config(parametros, configuracion_sim)
    for clave in ("mesas", "meseros", "cocineros", "tamano_grupo", "distribucion"):
        assert reconstruido[clave] == original[clave]
    assert reconstruido["tiempo_pedido_media_min"] == pytest.approx(original["tiempo_pedido_media_min"])


def test_ejecutar_una_devuelve_metricas_y_registros():
    parametros, configuracion_sim = servicios.config_desde_dict(
        _configuracion(distribucion="fija", duracion_llegadas_min=60)
    )
    ejecucion = servicios.ejecutar_una(parametros, configuracion_sim, semilla=1)
    assert "espera_total_media_min" in ejecucion.metricas
    assert "utilizacion_mesas" in ejecucion.metricas
    assert "longitud_media_cola_mesas" in ejecucion.metricas
    assert isinstance(ejecucion.registros, pd.DataFrame)
    assert len(ejecucion.registros) >= 1


def test_ejecutar_replicas_cuenta_las_replicas():
    parametros, configuracion_sim = servicios.config_desde_dict(_configuracion())
    tabla = servicios.ejecutar_replicas(parametros, configuracion_sim, replicas=4, semilla_base=1)
    assert len(tabla) == 4
    assert {"replica", "semilla", "espera_total_media_min"}.issubset(tabla.columns)


def test_comparar_escenarios_agrega_la_columna_escenario():
    escenarios = [
        {"nombre": "base", **_configuracion()},
        {"nombre": "mas_meseros", **_configuracion(meseros=4)},
    ]
    tabla = servicios.comparar_escenarios(escenarios, replicas=2, semilla_base=1)
    assert set(tabla["escenario"]) == {"base", "mas_meseros"}


def test_optimizar_devuelve_factibilidad():
    escenarios = [
        {"nombre": "base", **_configuracion(mesas=6, meseros=3, cocineros=3)},
        {"nombre": "grande", **_configuracion(mesas=10, meseros=5, cocineros=5)},
    ]
    tabla = servicios.comparar_escenarios(escenarios, replicas=2, semilla_base=1)
    resultado = servicios.optimizar(tabla, {"espera_total_media_min": 100.0}, {"mesas": 1.0})
    assert "factible" in resultado
    assert "configuraciones_evaluadas" in resultado


def test_frontera_pareto_no_vacia():
    escenarios = [
        {"nombre": "a", **_configuracion(mesas=6, meseros=3, cocineros=3)},
        {"nombre": "b", **_configuracion(mesas=8, meseros=4, cocineros=4)},
    ]
    tabla = servicios.comparar_escenarios(escenarios, replicas=2, semilla_base=1)
    frontera = servicios.frontera(tabla, ["espera_total_media_min", "utilizacion_mesas"])
    assert isinstance(frontera, pd.DataFrame)
    assert not frontera.empty


def test_optimizar_acepta_restriccion_de_longitud_de_cola():
    tabla = pd.DataFrame(
        [
            {
                "configuracion_id": 0,
                "mesas": 4,
                "meseros": 2,
                "cocineros": 1,
                "longitud_media_cola_mesas": 23.9,
                "espera_total_media_min": 143.7,
            },
            {
                "configuracion_id": 1,
                "mesas": 12,
                "meseros": 5,
                "cocineros": 3,
                "longitud_media_cola_mesas": 1.8,
                "espera_total_media_min": 7.4,
            },
        ]
    )
    resultado = servicios.optimizar(
        tabla,
        {"longitud_media_cola_mesas": 2.0},
        {"mesas": 1.0, "meseros": 1.0, "cocineros": 1.0},
    )
    assert resultado["factible"]
    assert resultado["mesas"] == 12
