from dataclasses import dataclass
from .parametros import ConfiguracionRestaurante

@dataclass(frozen=True)
class RegistroGrupo:
    grupo_id: int
    llegada_min: float
    mesa_inicio_min: float
    pedido_inicio_min: float
    pedido_fin_min: float
    cocina_inicio_min: float
    cocina_fin_min: float
    consumo_fin_min: float
    pago_inicio_min: float
    salida_min: float

@dataclass(frozen=True)
class ResultadoSimulacion:
    configuracion: ConfiguracionRestaurante
    semilla: int
    registros: tuple[RegistroGrupo, ...]
    grupos_llegados_horizonte: int
    grupos_salidos_horizonte: int
    grupos_pendientes_al_cierre: int
    ocupacion_mesas_minutos_horizonte: float
    ocupacion_meseros_minutos_horizonte: float
    ocupacion_cocineros_minutos_horizonte: float
    tiempo_ultima_salida_min: float