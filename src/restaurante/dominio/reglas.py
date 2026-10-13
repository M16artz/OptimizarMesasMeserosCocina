def evaluar_transicion_estado(cliente, estacion_actual: str) -> str:
    """
    Define el cambio de estado del cliente conforme avanza en la red de colas.
    Etapas: llegada -> mesa -> pedido -> cocina -> pago -> salida
    """
    flujo = {
        "LLEGADA": "ESPERANDO_MESA",
        "ESPERANDO_MESA": "TOMANDO_PEDIDO",
        "TOMANDO_PEDIDO": "EN_COCINA",
        "EN_COCINA": "EN_CONSUMO",
        "EN_CONSUMO": "PAGANDO",
        "PAGANDO": "FINALIZADO"
    }
    return flujo.get(estacion_actual, "FINALIZADO")