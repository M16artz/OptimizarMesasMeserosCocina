from .entidades import RegistroGrupo

def validar_registro_grupo(registro: RegistroGrupo) -> bool:
    """Verifica que los hitos temporales de un grupo cumplan con el orden lógico del servicio
    y sean valores no negativos.
    """
    hitos = [
        registro.llegada_min,
        registro.mesa_inicio_min,
        registro.pedido_inicio_min,
        registro.pedido_fin_min,
        registro.cocina_inicio_min,
        registro.cocina_fin_min,
        registro.consumo_fin_min,
        registro.pago_inicio_min,
        registro.salida_min
    ]
    
    # Ningún hito temporal puede ser negativo
    if any(hito < 0 for hito in hitos):
        return False
        
    # Validar el orden cronológico del ciclo de atención del restaurante:
    # 1. Llegada -> Asignación de mesa -> Inicio pedido -> Fin pedido
    if not (registro.llegada_min <= registro.mesa_inicio_min <= registro.pedido_inicio_min <= registro.pedido_fin_min):
        return False
        
    # 2. Fin pedido -> Inicio cocina -> Fin cocina -> Fin consumo
    if not (registro.pedido_fin_min <= registro.cocina_inicio_min <= registro.cocina_fin_min <= registro.consumo_fin_min):
        return False
        
    # 3. Fin consumo -> Inicio pago -> Salida
    if not (registro.consumo_fin_min <= registro.pago_inicio_min <= registro.salida_min):
        return False
        
    return True