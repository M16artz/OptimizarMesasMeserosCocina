"""Pruebas de integración: dominio + los tres módulos de simulación.

Copiar las funciones a tests/test_simulacion.py o guardar como
`tests/test_simulacion_yandry.py` sin reemplazar las pruebas existentes.
Ejecutar: python -m pytest tests/test_simulacion_yandry.py -v
"""

from statistics import mean

import pytest

from restaurante.dominio.parametros import ParametrosSistema
from restaurante.simulacion.motor import MotorSimulacion
from restaurante.simulacion.procesos import ConfiguracionSimulacion


def crear_motor(mesas=1, distribucion="fija", tasa_llegada=6, semilla=42):
    parametros = ParametrosSistema(
        lambda_llegada=tasa_llegada,
        mu_servicio=30,  # Pedido: 2 minutos (60 / 30)
        mesas=mesas,
        meseros=1,
        cocineros=1,
    )
    configuracion = ConfiguracionSimulacion(
        duracion_llegadas_minutos=30,
        preparacion_media_minutos=3,
        consumo_media_minutos=4,
        pago_medio_minutos=1,
        tamano_grupo=2,
        distribucion=distribucion,
    )
    return MotorSimulacion(parametros, configuracion, semilla=semilla)


def test_un_grupo_completa_todas_las_etapas():
    resultado = crear_motor().ejecutar(tiempos_llegada=[0])
    grupo = resultado.registros[0]
    assert resultado.grupos_atendidos == 1
    assert resultado.personas_atendidas == 2
    assert grupo["estado_final"] == "FINALIZADO"
    assert grupo["espera_mesa"] == 0
    assert grupo["salida"] == pytest.approx(10)  # 2 + 3 + 4 + 1


def test_una_mesa_produce_cola_fifo():
    resultado = crear_motor(mesas=1).ejecutar(tiempos_llegada=[0, 1, 2])
    assert [grupo["mesa_asignada"] for grupo in resultado.registros] == [0, 10, 20]
    assert [grupo["espera_mesa"] for grupo in resultado.registros] == [0, 9, 18]
    assert all(g["estado_final"] == "FINALIZADO" for g in resultado.registros)


def test_dos_mesas_reducen_espera_en_este_ejemplo():
    llegadas = [0, 1, 2]
    uno = crear_motor(mesas=1).ejecutar(tiempos_llegada=llegadas)
    dos = crear_motor(mesas=2).ejecutar(tiempos_llegada=llegadas)
    espera_uno = mean(g["espera_mesa"] for g in uno.registros)
    espera_dos = mean(g["espera_mesa"] for g in dos.registros)
    assert espera_dos < espera_uno
    assert all(0 <= u <= 1 for u in dos.utilizacion.values())


def test_misma_semilla_produce_mismos_resultados():
    a = crear_motor(mesas=3, distribucion="exponencial", semilla=19).ejecutar()
    b = crear_motor(mesas=3, distribucion="exponencial", semilla=19).ejecutar()
    assert a == b


def test_cero_llegadas_no_genera_clientes():
    resultado = crear_motor(tasa_llegada=0).ejecutar()
    assert resultado.grupos_atendidos == 0
    assert resultado.eventos == []
