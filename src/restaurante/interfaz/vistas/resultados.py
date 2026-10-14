"""Vista de ejecución y resultados de una configuración."""

from __future__ import annotations

import matplotlib.pyplot as plt
import streamlit as st

from ...infraestructura import archivos, graficos
from .. import cache, estado, servicios


def _mostrar_metricas(metricas: dict) -> None:
    filas = servicios.resumen_metricas(metricas)
    columnas = st.columns(4)
    for indice, (etiqueta, valor) in enumerate(filas):
        columna = columnas[indice % len(columnas)]
        if isinstance(valor, float):
            columna.metric(etiqueta, f"{valor:,.2f}")
        else:
            columna.metric(etiqueta, f"{valor:,}")


def _mostrar_figura(figura, titulo: str) -> None:
    st.markdown(f"**{titulo}**")
    st.pyplot(figura, use_container_width=True)
    plt.close(figura)


def _seccion_replicas(configuracion: dict, num_replicas: int, semilla: int) -> None:
    if st.button("Calcular promedios con réplicas"):
        try:
            tabla = cache.replicas(configuracion, num_replicas, semilla)
            st.session_state["tabla_replicas"] = tabla
            st.session_state["resumen_replicas"] = servicios.resumir_replicas(tabla)
        except Exception as e:  # noqa: BLE001
            st.error(f"No se pudieron calcular las réplicas: {e}")

    resumen = st.session_state.get("resumen_replicas")
    tabla = st.session_state.get("tabla_replicas")
    if tabla is None:
        st.info("Pulsa «Calcular promedios con réplicas» para agregar varias réplicas.")
        return

    st.markdown("**Resumen por réplicas (medias e intervalos de confianza)**")
    st.dataframe(resumen, use_container_width=True)
    st.download_button(
        "Descargar resumen (CSV)",
        data=archivos.tabla_a_csv_bytes(resumen),
        file_name="resumen_replicas.csv",
        mime="text/csv",
    )
    with st.expander("Ver tabla por réplica"):
        st.dataframe(tabla, use_container_width=True)


def render() -> None:
    st.subheader("Ejecución y resultados")
    configuracion = estado.configuracion_actual()

    col_semilla, col_replicas = st.columns(2)
    semilla = col_semilla.number_input(
        "Semilla", min_value=0, max_value=1_000_000_000, key="semilla_base"
    )
    num_replicas = col_replicas.number_input(
        "Réplicas", min_value=1, max_value=200, key="replicas"
    )

    if st.button("Ejecutar simulación", type="primary"):
        try:
            ejecucion = cache.ejecucion_unica(configuracion, int(semilla))
            st.session_state["ultima_ejecucion"] = ejecucion
            st.session_state["config_ejecutada"] = configuracion
        except Exception as e:  # noqa: BLE001
            st.error(f"No se pudo ejecutar la simulación: {e}")

    ejecucion = st.session_state.get("ultima_ejecucion")
    if ejecucion is None:
        st.info("Configura los parámetros y pulsa «Ejecutar simulación».")
        return

    _mostrar_metricas(ejecucion.metricas)

    st.divider()
    col_izq, col_der = st.columns(2)
    with col_izq:
        _mostrar_figura(graficos.figura_utilizaciones(ejecucion.resultado), "Utilización de recursos")
    with col_der:
        _mostrar_figura(graficos.figura_permanencia_vs_llegada(ejecucion.resultado), "Permanencia vs llegada")
    _mostrar_figura(graficos.figura_esperas_por_grupo(ejecucion.resultado), "Esperas por grupo")
    _mostrar_figura(graficos.figura_longitudes_cola(ejecucion.resultado), "Longitud media de cola")

    st.divider()
    st.markdown("**Registros por grupo**")
    st.dataframe(ejecucion.registros, use_container_width=True)
    col_csv, col_json = st.columns(2)
    col_csv.download_button(
        "Descargar registros (CSV)",
        data=archivos.resultado_a_csv_bytes(ejecucion.resultado, ejecucion.metricas),
        file_name="registros.csv",
        mime="text/csv",
        use_container_width=True,
    )
    col_json.download_button(
        "Descargar resultado (JSON)",
        data=archivos.resultado_a_json_bytes(ejecucion.resultado),
        file_name="resultado.json",
        mime="application/json",
        use_container_width=True,
    )

    st.divider()
    st.subheader("Múltiples réplicas")
    _seccion_replicas(configuracion, int(num_replicas), int(semilla))
