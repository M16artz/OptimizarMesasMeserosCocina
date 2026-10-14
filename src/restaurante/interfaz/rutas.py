"""Rutas del proyecto calculadas a partir de la ubicación del paquete.

Evita rutas absolutas locales de un integrante (prueba de aceptación #10).
"""

from __future__ import annotations

from pathlib import Path

# .../OptimizarMesasMeserosCocina
RAIZ_PROYECTO = Path(__file__).resolve().parents[3]
DIR_CONFIGS = RAIZ_PROYECTO / "configs"
DIR_RESULTADOS = RAIZ_PROYECTO / "resultados"
