"""Punto de entrada web.

Uso:
    streamlit run app.py
"""

import sys
from pathlib import Path

# Permite ejecutar la app sin instalar el paquete (desarrollo).
_SRC = Path(__file__).resolve().parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

import matplotlib  # noqa: E402

matplotlib.use("Agg")  # Streamlit renderiza figuras por st.pyplot, no por ventanas

from restaurante.interfaz.app import main  # noqa: E402

if __name__ == "__main__":
    main()
