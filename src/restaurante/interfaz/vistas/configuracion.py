"""Vista de configuración: parámetros del modelo y persistencia en YAML."""

from __future__ import annotations

import streamlit as st

from ...infraestructura import archivos
from .. import estado, rutas
from ..servicios import CONFIGURACION_POR_DEFECTO, completar_con_defecto, config_desde_dict

_DISTRIBUCIONES = ("exponencial", "fija")


def _formulario() -> None:
    cfg = estado.configuracion_actual()
    indice_distribucion = _DISTRIBUCIONES.index(cfg["distribucion"]) if cfg["distribucion"] in _DISTRIBUCIONES else 0

    with st.form("formulario_configuracion"):
        st.caption("Tiempos en minutos · tasa en grupos/hora")
        mesas = st.number_input("Mesas", min_value=1, max_value=200, value=int(cfg["mesas"]))
        meseros = st.number_input("Meseros", min_value=1, max_value=200, value=int(cfg["meseros"]))
        cocineros = st.number_input("Cocineros", min_value=1, max_value=200, value=int(cfg["cocineros"]))
        tamano_grupo = st.number_input("Tamaño de grupo", min_value=1, max_value=50, value=int(cfg["tamano_grupo"]))
        tasa = st.number_input(
            "Tasa de llegadas (grupos/hora)", min_value=0.0, max_value=2000.0, value=float(cfg["tasa_llegadas_grupos_hora"]), step=1.0
        )
        t_pedido = st.number_input(
            "Tiempo de pedido (min)", min_value=0.1, max_value=240.0, value=float(cfg["tiempo_pedido_media_min"]), step=0.5
        )
        t_preparacion = st.number_input(
            "Tiempo de preparación (min)", min_value=0.1, max_value=480.0, value=float(cfg["tiempo_preparacion_media_min"]), step=0.5
        )
        t_consumo = st.number_input(
            "Tiempo de consumo (min)", min_value=0.1, max_value=960.0, value=float(cfg["tiempo_consumo_media_min"]), step=0.5
        )
        t_pago = st.number_input(
            "Tiempo de pago (min)", min_value=0.1, max_value=120.0, value=float(cfg["tiempo_pago_media_min"]), step=0.5
        )
        duracion = st.number_input(
            "Duración de llegadas H (min)", min_value=1.0, max_value=100000.0, value=float(cfg["duracion_llegadas_min"]), step=10.0
        )
        distribucion = st.selectbox("Distribución", _DISTRIBUCIONES, index=indice_distribucion)
        enviado = st.form_submit_button("Aplicar configuración", use_container_width=True)

    if enviado:
        nueva = {
            "mesas": int(mesas),
            "meseros": int(meseros),
            "cocineros": int(cocineros),
            "tamano_grupo": int(tamano_grupo),
            "tasa_llegadas_grupos_hora": float(tasa),
            "tiempo_pedido_media_min": float(t_pedido),
            "tiempo_preparacion_media_min": float(t_preparacion),
            "tiempo_consumo_media_min": float(t_consumo),
            "tiempo_pago_media_min": float(t_pago),
            "duracion_llegadas_min": float(duracion),
            "distribucion": distribucion,
        }
        try:
            config_desde_dict(nueva)  # valida con las reglas del backend
            estado.establecer_configuracion(nueva)
            st.success("Configuración aplicada.")
        except Exception as e:  # noqa: BLE001 - se muestra al usuario
            st.error(f"Configuración inválida: {e}")


def _persistencia() -> None:
    st.subheader("Archivo de configuración")
    ruta = st.text_input(
        "Ruta YAML",
        value=str(rutas.DIR_CONFIGS / "base.yaml"),
        key="ruta_config",
    )
    col_cargar, col_guardar = st.columns(2)
    if col_cargar.button("Cargar", use_container_width=True):
        try:
            datos = archivos.cargar_configuracion(ruta)
            nueva = completar_con_defecto(datos)
            config_desde_dict(nueva)
            estado.establecer_configuracion(nueva)
            st.success("Configuración cargada.")
            st.rerun()
        except Exception as e:  # noqa: BLE001
            st.error(f"No se pudo cargar: {e}")
    if col_guardar.button("Guardar", use_container_width=True):
        try:
            archivos.guardar_configuracion(ruta, estado.configuracion_actual())
            st.success("Configuración guardada.")
        except Exception as e:  # noqa: BLE001
            st.error(f"No se pudo guardar: {e}")
    if st.button("Restaurar valores por defecto", use_container_width=True):
        estado.establecer_configuracion(CONFIGURACION_POR_DEFECTO)
        st.rerun()


def _resumen() -> None:
    cfg = estado.configuracion_actual()
    st.caption(
        f"Activa: {cfg['mesas']} mesas · {cfg['meseros']} meseros · {cfg['cocineros']} cocineros · "
        f"λ={cfg['tasa_llegadas_grupos_hora']:.1f} g/h · H={cfg['duracion_llegadas_min']:.0f} min"
    )


def render_sidebar() -> None:
    """Dibuja la configuración y la persistencia en la barra lateral."""
    with st.sidebar:
        st.header("Configuración")
        _formulario()
        st.divider()
        _persistencia()
        st.divider()
        _resumen()
