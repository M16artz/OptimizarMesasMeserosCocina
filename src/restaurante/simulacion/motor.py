"""Motor de eventos discretos del restaurante.

Coordina las llegadas, las colas y los servicios mediante una agenda cronológica.

Convención provisional: lambda_llegada = grupos/hora; mu_servicio = pedidos
atendidos por mesero/hora. Todas las marcas de tiempo son minutos.
"""

from dataclasses import dataclass
import heapq
import itertools
import math
from random import Random

from restaurante.dominio.entidades import Cliente
from restaurante.dominio.parametros import ParametrosSistema
from restaurante.dominio.reglas import evaluar_transicion_estado
from .procesos import ConfiguracionSimulacion, RegistroAtencion, duracion_actividad
from .recursos import GestorRecursos


@dataclass
class ResultadoSimulacion:
    """Datos sin agregar para el análisis posterior de Miguel."""

    registros: list[dict]
    utilizacion: dict[str, float]
    area_ocupada_minutos: dict[str, float]
    area_colas_minutos: dict[str, float]
    horizonte_observado_minutos: float
    eventos: list[dict]

    @property
    def grupos_atendidos(self) -> int:
        return len(self.registros)

    @property
    def personas_atendidas(self) -> int:
        return sum(r["tamano_grupo"] for r in self.registros)


class MotorSimulacion:
    """Ejecuta el restaurante hasta atender los grupos que llegaron en la jornada."""

    def __init__(
        self,
        parametros: ParametrosSistema,
        configuracion: ConfiguracionSimulacion | None = None,
        semilla: int = 42,
    ):
        if not math.isfinite(parametros.lambda_llegada) or parametros.lambda_llegada < 0:
            raise ValueError("lambda_llegada debe ser finita y no negativa")
        if not math.isfinite(parametros.mu_servicio) or parametros.mu_servicio <= 0:
            raise ValueError("mu_servicio debe ser finita y positiva")
        self.parametros = parametros
        self.configuracion = configuracion or ConfiguracionSimulacion()
        self.configuracion.validar()
        self.semilla = semilla
        # La validación de cantidades de recursos se hace en GestorRecursos.

    def _agendar(self, tiempo: float, evento: str, id_cliente: int | None = None):
        """Programa un evento futuro manteniendo el orden de los empates."""
        if not math.isfinite(tiempo) or tiempo < self.reloj:
            raise ValueError("El instante del evento debe ser válido y no anterior al reloj")
        heapq.heappush(self.agenda, (tiempo, next(self.orden), evento, id_cliente))

    def _cambiar_estado(self, id_cliente: int):
        cliente = self.clientes[id_cliente]
        cliente.estado = evaluar_transicion_estado(cliente, cliente.estado)
        self.registros[id_cliente].estado_final = cliente.estado

    def _solicitar(self, recurso: str, id_cliente: int, actividad: str):
        """Inicia la actividad si hay capacidad; de lo contrario queda en FIFO."""
        if self.gestor.solicitar(recurso, id_cliente, actividad, self.reloj):
            self._iniciar(actividad, id_cliente)

    def _liberar(self, recurso: str):
        """Entrega el recurso liberado al primero en espera, si existe."""
        siguiente = self.gestor.liberar(recurso)
        if siguiente is not None:
            self._iniciar(siguiente.actividad, siguiente.id_cliente)

    def _iniciar(self, actividad: str, id_cliente: int):
        """Inicia la etapa y, si corresponde, programa su finalización."""
        registro = self.registros[id_cliente]
        if actividad == "mesa":
            registro.mesa_asignada = self.reloj
            self._cambiar_estado(id_cliente)  # ESPERANDO_MESA -> TOMANDO_PEDIDO
            self._solicitar("mesero", id_cliente, "pedido")
        elif actividad == "pedido":
            registro.inicio_pedido = self.reloj
            self.clientes[id_cliente].tiempo_inicio_atencion = self.reloj
            self._programar_fin("pedido", id_cliente)
        elif actividad == "cocina":
            registro.inicio_cocina = self.reloj
            self._programar_fin("cocina", id_cliente)
        elif actividad == "pago":
            registro.inicio_pago = self.reloj
            self._programar_fin("pago", id_cliente)
        else:
            raise ValueError(f"Actividad desconocida: {actividad}")

    def _programar_fin(self, actividad: str, id_cliente: int):
        duracion = duracion_actividad(
            actividad, self.parametros.mu_servicio, self.configuracion, self.azar
        )
        self._agendar(self.reloj + duracion, f"fin_{actividad}", id_cliente)

    def _llegada(self):
        id_cliente = len(self.clientes) + 1
        cliente = Cliente(id_cliente, self.configuracion.tamano_grupo, self.reloj)
        cliente.tiempo_inicio_espera_mesa = self.reloj
        self.clientes[id_cliente] = cliente
        self.registros[id_cliente] = RegistroAtencion(
            id_cliente, cliente.tamaño_grupo, self.reloj
        )
        self._cambiar_estado(id_cliente)  # LLEGADA -> ESPERANDO_MESA
        self._solicitar("mesa", id_cliente, "mesa")

    def _fin_pedido(self, id_cliente: int):
        self.registros[id_cliente].fin_pedido = self.reloj
        self._cambiar_estado(id_cliente)  # TOMANDO_PEDIDO -> EN_COCINA
        self._liberar("mesero")
        self._solicitar("cocinero", id_cliente, "cocina")

    def _fin_cocina(self, id_cliente: int):
        self.registros[id_cliente].fin_cocina = self.reloj
        self._cambiar_estado(id_cliente)  # EN_COCINA -> EN_CONSUMO
        self._liberar("cocinero")
        self._programar_fin("consumo", id_cliente)

    def _fin_consumo(self, id_cliente: int):
        self.registros[id_cliente].fin_consumo = self.reloj
        self._cambiar_estado(id_cliente)  # EN_CONSUMO -> PAGANDO
        self._solicitar("mesero", id_cliente, "pago")

    def _fin_pago(self, id_cliente: int):
        self.registros[id_cliente].salida = self.reloj
        self.clientes[id_cliente].tiempo_salida = self.reloj
        self._cambiar_estado(id_cliente)  # PAGANDO -> FINALIZADO
        self._liberar("mesero")
        self._liberar("mesa")  # La mesa no se libera hasta la salida.

    def _acumular_ocupacion_y_colas(self, minutos: float):
        for nombre in ("mesa", "mesero", "cocinero"):
            recurso = self.gestor.recursos[nombre]
            ocupados = recurso.capacidad_total - recurso.disponibles
            self.area_ocupada[nombre] += ocupados * minutos
            self.area_colas[nombre] += self.gestor.esperando(nombre) * minutos

    def ejecutar(self, tiempos_llegada: list[float] | None = None) -> ResultadoSimulacion:
        """Ejecuta una jornada; acepta llegadas fijas para pruebas.

        Los arribos cesan en el horizonte configurado, pero los grupos ya
        presentes continúan hasta terminar su atención.
        """
        self.azar = Random(self.semilla)
        self.gestor = GestorRecursos(self.parametros)
        self.reloj = 0.0
        self.agenda = []
        self.orden = itertools.count()
        self.clientes = {}
        self.registros = {}
        self.eventos = []
        self.area_ocupada = {r: 0.0 for r in ("mesa", "mesero", "cocinero")}
        self.area_colas = {r: 0.0 for r in ("mesa", "mesero", "cocinero")}

        if tiempos_llegada is not None:
            for t in tiempos_llegada:
                if not math.isfinite(t) or not 0 <= t <= self.configuracion.duracion_llegadas_minutos:
                    raise ValueError("Llegada fuera de la jornada o no finita")
                self._agendar(float(t), "llegada")
        elif self.parametros.lambda_llegada > 0:
            tasa_por_minuto = self.parametros.lambda_llegada / 60.0
            instante = self.azar.expovariate(tasa_por_minuto)
            while instante <= self.configuracion.duracion_llegadas_minutos:
                self._agendar(instante, "llegada")
                instante += self.azar.expovariate(tasa_por_minuto)

        acciones = {
            "fin_pedido": self._fin_pedido,
            "fin_cocina": self._fin_cocina,
            "fin_consumo": self._fin_consumo,
            "fin_pago": self._fin_pago,
        }
        while self.agenda:
            instante, _, evento, id_cliente = heapq.heappop(self.agenda)
            self._acumular_ocupacion_y_colas(instante - self.reloj)
            self.reloj = instante
            if evento == "llegada":
                self._llegada()
            else:
                acciones[evento](id_cliente)
            self.eventos.append({"tiempo": self.reloj, "evento": evento, "id_cliente": id_cliente})

        if any(self.gestor.esperando(r) for r in self.area_colas):
            raise RuntimeError("La simulación terminó con solicitudes pendientes")
        if any(self.gestor.recursos[r].disponibles != self.gestor.recursos[r].capacidad_total
               for r in self.area_ocupada):
            raise RuntimeError("La simulación terminó con recursos ocupados")

        utilizacion = {
            r: (self.area_ocupada[r] / (self.gestor.recursos[r].capacidad_total * self.reloj)
                if self.reloj > 0 else 0.0)
            for r in self.area_ocupada
        }
        return ResultadoSimulacion(
            registros=[r.como_diccionario() for r in self.registros.values()],
            utilizacion=utilizacion,
            area_ocupada_minutos=self.area_ocupada.copy(),
            area_colas_minutos=self.area_colas.copy(),
            horizonte_observado_minutos=self.reloj,
            eventos=self.eventos.copy(),
        )
