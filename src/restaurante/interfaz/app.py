"""Aplicación Streamlit del simulador de restaurante."""

from __future__ import annotations

import streamlit as st

from . import estado
from .vistas import configuracion, escenarios, optimizacion, resultados


def main() -> None:
    st.set_page_config(
        page_title="Simulador de restaurante",
        page_icon=":material/restaurant:",
        layout="wide",
    )
    estado.inicializar_estado()

    st.title("Simulador de restaurante: mesas, meseros y cocineros")
    st.caption(
        "Simulación de eventos discretos. Ajusta la configuración en la barra "
        "lateral y explora resultados, escenarios y optimización."
    )

    configuracion.render_sidebar()

    pestana_resultados, pestana_escenarios, pestana_optimizacion = st.tabs(
        ["Ejecución y resultados", "Escenarios", "Optimización"]
    )
    with pestana_resultados:
        resultados.render()
    with pestana_escenarios:
        escenarios.render()
    with pestana_optimizacion:
        optimizacion.render()


if __name__ == "__main__":
    main()
