"""Gestión FIFO de mesas, meseros y cocineros para una simulación por eventos.
El motor decide cuándo solicitar/liberar; aquí no se avanza el reloj.
"""

from collections import deque
from dataclasses import dataclass

from restaurante.dominio.entidades import RecursoOperativo
from restaurante.dominio.parametros import ParametrosSistema


@dataclass(frozen=True)
class SolicitudRecurso:
    """Solicitud pendiente para atender a un grupo de clientes."""

    tipo: str
    id_cliente: int
    actividad: str
    tiempo_solicitud: float


class GestorRecursos:
    """Controla capacidades y colas FIFO independientes por tipo de recurso."""

    def __init__(self, parametros: ParametrosSistema):
        capacidades = {
            "mesa": parametros.mesas,
            "mesero": parametros.meseros,
            "cocinero": parametros.cocineros,
        }
        if any(cantidad <= 0 for cantidad in capacidades.values()):
            raise ValueError("Las cantidades de mesas, meseros y cocineros deben ser positivas")

        self.recursos = {
            tipo: RecursoOperativo(tipo, cantidad)
            for tipo, cantidad in capacidades.items()
        }
        self.colas = {tipo: deque() for tipo in capacidades}

    def solicitar(
        self, tipo: str, id_cliente: int, actividad: str, tiempo_actual: float
    ) -> bool:
        """Asigna inmediatamente si hay capacidad; si no, registra espera FIFO.

        Devuelve True si se asignó; False si quedó pendiente en la cola.
        """
        recurso = self.recursos[tipo]
        cola = self.colas[tipo]
        if not cola and recurso.ocupar():
            return True

        cola.append(SolicitudRecurso(tipo, id_cliente, actividad, tiempo_actual))
        return False

    def liberar(self, tipo: str) -> SolicitudRecurso | None:
        """Libera una unidad; si hay espera, la transfiere al primero de la cola.

        Si devuelve una solicitud, la unidad queda ocupada para ese grupo;
        el motor debe iniciar su actividad en el instante actual.
        Si devuelve None, la unidad queda disponible.
        """
        recurso = self.recursos[tipo]
        if recurso.disponibles == recurso.capacidad_total:
            raise ValueError(f"No hay ningún {tipo} ocupado que se pueda liberar")

        cola = self.colas[tipo]
        if cola:
            return cola.popleft()  # Cesión directa: sigue ocupado, sin liberación intermedia.

        recurso.liberar()
        return None

    def disponibles(self, tipo: str) -> int:
        return self.recursos[tipo].disponibles

    def esperando(self, tipo: str) -> int:
        return len(self.colas[tipo])
