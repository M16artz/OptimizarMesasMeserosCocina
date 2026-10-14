"""Vista de optimización: selección de configuración bajo restricciones y pesos."""

from __future__ import annotations

import streamlit as st

from .. import servicios

_RECURSOS = ("mesas", "meseros", "cocineros")


def _mostrar_resultado(resultado: dict) -> None:
    if not resultado.get("factible"):
        st.warning(resultado.get("mensaje", "Ninguna configuración es factible."))
        st.caption(
            f"Configuraciones evaluadas: {resultado.get('configuraciones_evaluadas', 0)} · "
            f"factibles: {resultado.get('configuraciones_factibles', 0)}"
        )
        return

    st.success(resultado.get("mensaje", "Configuración seleccionada."))
    configuracion = resultado.get("configuracion") or {}
    columnas = st.columns(4)
    columnas[0].metric("Mesas", configuracion.get("mesas", "-"))
    columnas[1].metric("Meseros", configuracion.get("meseros", "-"))
    columnas[2].metric("Cocineros", configuracion.get("cocineros", "-"))
    costo = resultado.get("costo_recursos")
    columnas[3].metric("Costo de recursos", f"{costo:,.2f}" if isinstance(costo, (int, float)) else "-")
    st.caption(
        f"Configuraciones evaluadas: {resultado.get('configuraciones_evaluadas', 0)} · "
        f"factibles: {resultado.get('configuraciones_factibles', 0)}"
    )
    st.markdown("**Métricas de la configuración seleccionada**")
    st.json(resultado.get("metricas", {}))


def _frontera(tabla, pesos: dict) -> None:
    st.divider()
    st.markdown("**Frontera de compromiso: costo de recursos vs espera total**")
    df = tabla.copy()
    df["costo_recursos"] = 0.0
    for recurso in _RECURSOS:
        if recurso in df.columns:
            df["costo_recursos"] = df["costo_recursos"] + df[recurso] * pesos[recurso]
    try:
        frontera = servicios.frontera(df, ["costo_recursos", "espera_total_media_min"])
    except Exception as e:  # noqa: BLE001
        st.info(f"No se pudo calcular la frontera: {e}")
        return
    st.dataframe(frontera, use_container_width=True)
    st.scatter_chart(frontera, x="costo_recursos", y="espera_total_media_min")


def render() -> None:
    st.subheader("Optimización")
    tabla = st.session_state.get("tabla_escenarios")
    if tabla is None:
        st.info("Genera primero la tabla de escenarios en la pestaña «Escenarios».")
        return

    st.caption("Los pesos son hipótesis de trabajo, no costos financieros reales.")
    col_mesas, col_meseros, col_cocineros = st.columns(3)
    pesos = {
        "mesas": col_mesas.number_input("Peso mesas", min_value=0.0, max_value=100.0, key="peso_mesas", step=0.1),
        "meseros": col_meseros.number_input("Peso meseros", min_value=0.0, max_value=100.0, key="peso_meseros", step=0.1),
        "cocineros": col_cocineros.number_input("Peso cocineros", min_value=0.0, max_value=100.0, key="peso_cocineros", step=0.1),
    }
    espera_max = st.number_input(
        "Espera total media máxima (min)", min_value=0.0, max_value=100000.0, key="restriccion_espera_max", step=1.0
    )
    restricciones: dict[str, float] = {"espera_total_media_min": espera_max}
    if st.checkbox(
        "Restringir también la longitud media de cola de mesas",
        value=False,
        key="usar_restriccion_cola",
    ):
        cola_max = st.number_input(
            "Cola media de mesas máxima (grupos)",
            min_value=0.0,
            max_value=10000.0,
            key="restriccion_cola_mesas_max",
            step=0.5,
        )
        restricciones["longitud_media_cola_mesas"] = cola_max

    if st.button("Seleccionar configuración", type="primary"):
        try:
            resultado = servicios.optimizar(tabla, restricciones, pesos)
            st.session_state["resultado_optimizacion"] = resultado
        except Exception as e:  # noqa: BLE001
            st.error(f"No se pudo optimizar: {e}")

    resultado = st.session_state.get("resultado_optimizacion")
    if resultado:
        _mostrar_resultado(resultado)

    _frontera(tabla, pesos)
