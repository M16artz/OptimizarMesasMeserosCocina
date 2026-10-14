from dataclasses import dataclass

@dataclass(frozen=True)
class ConfiguracionRestaurante:
    mesas: int
    meseros: int
    cocineros: int
    tasa_llegadas_grupos_hora: float
    tiempo_pedido_media_min: float
    tiempo_preparacion_media_min: float
    tiempo_consumo_media_min: float
    tiempo_pago_media_min: float
    duracion_llegadas_min: float

    def validar(self) -> None:
        """Valida que los parámetros cumplan con las restricciones del modelo."""
        if not isinstance(self.mesas, int) or self.mesas <= 0:
            raise ValueError("El número de mesas debe ser un entero positivo.")
        if not isinstance(self.meseros, int) or self.meseros <= 0:
            raise ValueError("El número de meseros debe ser un entero positivo.")
        if not isinstance(self.cocineros, int) or self.cocineros <= 0:
            raise ValueError("El número de cocineros debe ser un entero positivo.")
        if self.tasa_llegadas_grupos_hora <= 0:
            raise ValueError("La tasa de llegadas debe ser un valor positivo.")
        if (
            self.tiempo_pedido_media_min <= 0 or
            self.tiempo_preparacion_media_min <= 0 or
            self.tiempo_consumo_media_min <= 0 or
            self.tiempo_pago_media_min <= 0 or
            self.duracion_llegadas_min <= 0
        ):
            raise ValueError("Todos los tiempos y la duración de llegadas deben ser positivos.")