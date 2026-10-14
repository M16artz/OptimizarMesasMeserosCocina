"""Vista de comparación de escenarios."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from ...infraestructura import archivos
from .. import cache, rutas

_RECURSOS = ["mesas", "meseros", "cocineros"]
_COLUMNAS_NO_METRICA = {"configuracion_id", "replica", "semilla", "escenario", *_RECURSOS}


def _resumen_por_escenario(tabla: pd.DataFrame) -> pd.DataFrame:
    metricas = [c for c in tabla.columns if c not in _COLUMNAS_NO_METRICA]
    agregacion = {recurso: "first" for recurso in _RECURSOS if recurso in tabla.columns}
    agregacion.update({metrica: "mean" for metrica in metricas})
    return tabla.groupby("escenario", as_index=False).agg(agregacion)


def render() -> None:
    st.subheader("Comparación de escenarios")
    ruta = st.text_input(
        "Archivo de escenarios (YAML)",
        value=str(rutas.DIR_CONFIGS / "escenarios.yaml"),
        key="ruta_escenarios",
    )
    col_replicas, col_semilla = st.columns(2)
    num_replicas = col_replicas.number_input(
        "Réplicas por escenario", min_value=1, max_value=200, key="replicas_escenarios"
    )
    semilla = col_semilla.number_input(
        "Semilla base", min_value=0, max_value=1_000_000_000, key="semilla_escenarios"
    )

    if st.button("Comparar escenarios", type="primary"):
        try:
            escenarios = archivos.cargar_escenarios(ruta)
            if not escenarios:
                st.warning("El archivo no contiene escenarios.")
            else:
                tabla = cache.comparar(tuple(escenarios), int(num_replicas), int(semilla))
                st.session_state["tabla_escenarios"] = tabla
        except Exception as e:  # noqa: BLE001
            st.error(f"No se pudieron comparar los escenarios: {e}")

    tabla = st.session_state.get("tabla_escenarios")
    if tabla is None:
        st.info("Carga un archivo de escenarios y pulsa «Comparar escenarios».")
        return

    resumen = _resumen_por_escenario(tabla)
    st.markdown("**Resumen por escenario**")
    st.dataframe(resumen, use_container_width=True)

    if {"escenario", "espera_total_media_min"}.issubset(resumen.columns):
        st.markdown("**Espera total media por escenario (min)**")
        st.bar_chart(resumen, x="escenario", y="espera_total_media_min")

    if {"espera_total_media_min", "permanencia_media_min"}.issubset(resumen.columns):
        st.markdown("**Espera vs permanencia**")
        st.scatter_chart(resumen, x="espera_total_media_min", y="permanencia_media_min", color="escenario")

    st.download_button(
        "Descargar resumen (CSV)",
        data=archivos.tabla_a_csv_bytes(resumen),
        file_name="resumen_escenarios.csv",
        mime="text/csv",
    )
    with st.expander("Ver tabla por réplica"):
        st.dataframe(tabla, use_container_width=True)
