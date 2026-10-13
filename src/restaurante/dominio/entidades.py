class Cliente:
    def __init__(self, id_cliente: int, tamaño_grupo: int, tiempo_llegada: float):
        self.id_cliente = id_cliente
        self.tamaño_grupo = tamaño_grupo
        self.tiempo_llegada = tiempo_llegada
        self.estado = "LLEGADA"
        self.tiempo_inicio_espera_mesa = 0.0
        self.tiempo_inicio_atencion = 0.0
        self.tiempo_salida = 0.0

class RecursoOperativo:
    def __init__(self, tipo: str, capacidad_total: int):
        self.tipo = tipo
        self.capacidad_total = capacidad_total
        self.disponibles = capacidad_total

    def ocupar(self, cantidad: int = 1) -> bool:
        if self.disponibles >= cantidad:
            self.disponibles -= cantidad
            return True
        return False

    def liberar(self, cantidad: int = 1):
        self.disponibles = min(self.capacidad_total, self.disponibles + cantidad)