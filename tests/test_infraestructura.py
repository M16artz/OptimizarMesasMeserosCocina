"""Pruebas de lectura/escritura de archivos y generación de figuras."""

from __future__ import annotations

import csv
import json

import matplotlib

matplotlib.use("Agg")

import pytest

from restaurante.dominio.parametros import ParametrosSistema
from restaurante.infraestructura import archivos, graficos
from restaurante.simulacion.motor import MotorSimulacion
from restaurante.simulacion.procesos import ConfiguracionSimulacion


def _resultado(semilla: int = 5):
    parametros = ParametrosSistema(lambda_llegada=30, mu_servicio=30, mesas=4, meseros=2, cocineros=2)
    configuracion = ConfiguracionSimulacion(
        duracion_llegadas_minutos=60,
        preparacion_media_minutos=8,
        consumo_media_minutos=20,
        pago_medio_minutos=3,
        tamano_grupo=2,
        distribucion="fija",
    )
    return MotorSimulacion(parametros, configuracion, semilla=semilla).ejecutar()


def test_round_trip_configuracion(tmp_path):
    ruta = tmp_path / "config.yaml"
    configuracion = {"mesas": 5, "meseros": 3, "cocineros": 2, "distribucion": "fija"}
    archivos.guardar_configuracion(str(ruta), configuracion)
    assert archivos.cargar_configuracion(str(ruta)) == configuracion


def test_cargar_escenarios_devuelve_lista_completa(tmp_path):
    import yaml

    ruta = tmp_path / "escenarios.yaml"
    ruta.write_text(
        yaml.safe_dump([{"nombre": "a", "mesas": 4}, {"nombre": "b", "mesas": 6}]),
        encoding="utf-8",
    )
    escenarios = archivos.cargar_escenarios(str(ruta))
    assert [e["nombre"] for e in escenarios] == ["a", "b"]


def test_guardar_resultados_csv_genera_resumen_no_vacio(tmp_path):
    ruta = tmp_path / "registros.csv"
    archivos.guardar_resultados_csv(str(ruta), _resultado())
    resumen = ruta.with_name("registros_resumen.csv")
    assert resumen.exists()
    filas = list(csv.reader(resumen.open(encoding="utf-8")))
    assert filas[0] == ["campo", "valor"]
    assert len(filas) > 1  # no solo el encabezado
    campos = {fila[0] for fila in filas[1:]}
    assert "utilizacion_mesa" in campos


def test_guardar_resultados_csv_acepta_metricas(tmp_path):
    ruta = tmp_path / "registros.csv"
    metricas = {"espera_total_media_min": 1.5, "utilizacion_mesas": 0.8}
    archivos.guardar_resultados_csv(str(ruta), _resultado(), metricas=metricas)
    filas = dict(
        csv.reader(ruta.with_name("registros_resumen.csv").open(encoding="utf-8"))
    )
    assert filas["espera_total_media_min"] == "1.5"


def test_json_bytes_y_csv_bytes():
    resultado = _resultado()
    contenido_json = archivos.resultado_a_json_bytes(resultado)
    assert json.loads(contenido_json.decode("utf-8"))["registros"]
    contenido_csv = archivos.resultado_a_csv_bytes(resultado)
    assert b"id_cliente" in contenido_csv


def test_figura_utilizaciones_refleja_el_resultado():
    resultado = _resultado()
    figura = graficos.figura_utilizaciones(resultado)
    alturas = [parche.get_height() for parche in figura.axes[0].patches]
    esperadas = [resultado.utilizacion[clave] for clave in ("mesa", "mesero", "cocinero")]
    assert alturas == pytest.approx(esperadas)


def test_figura_longitudes_cola_refleja_el_resultado():
    resultado = _resultado()
    figura = graficos.figura_longitudes_cola(resultado)
    alturas = [parche.get_height() for parche in figura.axes[0].patches]
    esperadas = [
        resultado.area_colas_minutos[clave] / resultado.horizonte_observado_minutos
        for clave in ("mesa", "mesero", "cocinero")
    ]
    assert alturas == pytest.approx(esperadas)


def test_figuras_no_fallan_con_resultado_vacio():
    for fabrica in (
        graficos.figura_utilizaciones,
        graficos.figura_esperas_por_grupo,
        graficos.figura_permanencia_vs_llegada,
        graficos.figura_longitudes_cola,
    ):
        assert fabrica({"registros": []}) is not None
