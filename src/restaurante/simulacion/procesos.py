"""Configuración, duraciones y registros de los procesos del restaurante.

No administra recursos ni avanza el reloj.
"""

from dataclasses import asdict, dataclass
from random import Random


@dataclass(frozen=True)
class ConfiguracionSimulacion:
    """Valores medios de las actividades, expresados en minutos."""

    duracion_llegadas_minutos: float = 480.0
    preparacion_media_minutos: float = 12.0
    consumo_media_minutos: float = 25.0
    pago_medio_minutos: float = 3.0
    tamano_grupo: int = 2
    distribucion: str = "exponencial"  # También se admite "fija" para pruebas.

    def validar(self) -> None:
        if self.duracion_llegadas_minutos <= 0:
            raise ValueError("La duración de llegadas debe ser positiva")
        for media in (
            self.preparacion_media_minutos,
            self.consumo_media_minutos,
            self.pago_medio_minutos,
        ):
            if media <= 0:
                raise ValueError("Los tiempos medios deben ser positivos")
        if self.tamano_grupo < 1:
            raise ValueError("El tamaño del grupo debe ser al menos 1")
        if self.distribucion not in ("fija", "exponencial"):
            raise ValueError("La distribución debe ser 'fija' o 'exponencial'")


def duracion_actividad(
    actividad: str,
    mu_servicio: float,
    configuracion: ConfiguracionSimulacion,
    azar: Random,
) -> float:
    """Genera una duración en minutos para pedido, cocina, consumo o pago.

    Se acuerda provisionalmente que mu_servicio es la tasa de toma de pedidos
    por mesero y por hora. Por tanto, su media en minutos es 60 / mu_servicio.
    """
    if mu_servicio <= 0:
        raise ValueError("mu_servicio debe ser positivo")
    configuracion.validar()

    medias = {
        "pedido": 60.0 / mu_servicio,
        "cocina": configuracion.preparacion_media_minutos,
        "consumo": configuracion.consumo_media_minutos,
        "pago": configuracion.pago_medio_minutos,
    }
    if actividad not in medias:
        raise ValueError(f"Actividad desconocida: {actividad}")

    media = medias[actividad]
    if configuracion.distribucion == "fija":
        return media
    return azar.expovariate(1.0 / media)


@dataclass
class RegistroAtencion:
    """Instantes de atención de un grupo; todos los tiempos están en minutos."""

    id_cliente: int
    tamano_grupo: int
    llegada: float
    mesa_asignada: float | None = None
    inicio_pedido: float | None = None
    fin_pedido: float | None = None
    inicio_cocina: float | None = None
    fin_cocina: float | None = None
    fin_consumo: float | None = None
    inicio_pago: float | None = None
    salida: float | None = None
    estado_final: str = "LLEGADA"

    def como_diccionario(self) -> dict:
        """Devuelve marcas de tiempo y, si terminó, los tiempos de espera."""
        datos = asdict(self)
        if self.salida is not None:
            if any(
                instante is None
                for instante in (
                    self.mesa_asignada,
                    self.inicio_pedido,
                    self.fin_pedido,
                    self.inicio_cocina,
                    self.fin_consumo,
                    self.inicio_pago,
                )
            ):
                raise ValueError("Faltan marcas de tiempo de un grupo finalizado")
            datos.update(
                espera_mesa=self.mesa_asignada - self.llegada,
                espera_mesero_pedido=self.inicio_pedido - self.mesa_asignada,
                espera_cocinero=self.inicio_cocina - self.fin_pedido,
                espera_mesero_pago=self.inicio_pago - self.fin_consumo,
                permanencia_total=self.salida - self.llegada,
            )
        return datos
