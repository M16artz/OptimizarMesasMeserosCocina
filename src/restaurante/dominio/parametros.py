class ParametrosSistema:
    def __init__(self, lambda_llegada: float, mu_servicio: float, mesas: int, meseros: int, cocineros: int):
        # Tasa de llegada de clientes (lambda)
        self.lambda_llegada = lambda_llegada
        # Tasa de servicio individual (mu)
        self.mu_servicio = mu_servicio
        # Variables de decisión (capacidad de recursos)
        self.mesas = mesas
        self.meseros = meseros
        self.cocineros = cocineros

    def calcular_utilizacion(self, servidores: int) -> float:
        """Calcula la utilización del sistema o estación: rho = lambda / (c * mu)"""
        if servidores * self.mu_servicio == 0:
            return 0.0
        return self.lambda_llegada / (servidores * self.mu_servicio)