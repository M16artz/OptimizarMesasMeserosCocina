"""Generación de gráficos del simulador de restaurante.

Cada función ``figura_*`` devuelve un objeto ``matplotlib.figure.Figure`` para
poder usarse tanto al guardar PNG como al renderizar en Streamlit. Las funciones
``graficar_*`` son envoltorios que guardan y/o muestran la figura.

Se aceptan tanto los nombres de campo del contrato de simulación real
(``llegada``, ``mesa_asignada``, ``inicio_pedido``, ...) como los nombres
``*_min`` del acuerdo técnico, además de un ``resultado.utilizacion`` con
claves singulares (``mesa``, ``mesero``, ``cocinero``).
"""

from __future__ import annotations

import os
from typing import Any, Optional

try:
    import matplotlib

    import matplotlib.pyplot as plt
except ImportError:  # pragma: no cover - entorno sin matplotlib
    matplotlib = None
    plt = None


# (clave interna, etiqueta, color)
_RECURSOS = (
    ("mesa", "Mesas", "#4A90E2"),
    ("mesero", "Meseros", "#50C878"),
    ("cocinero", "Cocineros", "#FFB347"),
)


def _ensure_dir(path: str) -> None:
    """Asegura que el directorio para el archivo exista."""
    directory = os.path.dirname(os.path.abspath(path))
    if directory and not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)


def _require_matplotlib() -> None:
    if plt is None:
        raise ImportError(
            "matplotlib no está instalado. Instálalo con: pip install matplotlib"
        )


def _get(obj: Any, nombre: str, predeterminado: Any = None) -> Any:
    """Obtiene un atributo o clave de un objeto/dict."""
    if obj is None:
        return predeterminado
    if isinstance(obj, dict):
        return obj.get(nombre, predeterminado)
    return getattr(obj, nombre, predeterminado)


def _campo(registro: Any, *nombres: str) -> Optional[float]:
    """Devuelve el primer campo presente y no nulo de ``registro``."""
    for nombre in nombres:
        valor = _get(registro, nombre)
        if valor is not None:
            return valor
    return None


def _registros(resultado: Any) -> list[Any]:
    return list(_get(resultado, "registros", []) or [])


def _utilizaciones(resultado: Any) -> list[float]:
    """Devuelve [mesas, meseros, cocineros] en [0, 1].

    Prioriza ``resultado.utilizacion`` (dict con claves singulares). Si no
    existe, intenta recalcular a partir de la ocupación acumulada y la
    configuración (contrato alterno).
    """
    utilizacion = _get(resultado, "utilizacion")
    valores: list[float] = []
    if isinstance(utilizacion, dict) and utilizacion:
        for clave, _, _ in _RECURSOS:
            valores.append(float(utilizacion.get(clave, 0.0)))
        return [max(0.0, min(1.0, v)) for v in valores]

    config = _get(resultado, "configuracion", {}) or {}
    horizonte = (
        _get(config, "duracion_llegadas_min")
        or _get(config, "duracion_llegadas_minutos")
        or _get(resultado, "horizonte_observado_minutos")
        or 1.0
    )
    for clave, _, _ in _RECURSOS:
        plural = {"mesa": "mesas", "mesero": "meseros", "cocinero": "cocineros"}[clave]
        capacidad = _get(config, plural, 0) or 0
        ocupacion = _get(resultado, f"ocupacion_{plural}_minutos_horizonte", 0.0) or 0.0
        util = ocupacion / (capacidad * horizonte) if capacidad > 0 else 0.0
        valores.append(max(0.0, min(1.0, util)))
    return valores


def figura_utilizaciones(resultado: Any):
    """Figura de barras con la utilización de mesas, meseros y cocineros."""
    _require_matplotlib()
    valores = _utilizaciones(resultado)
    etiquetas = [etiqueta for _, etiqueta, _ in _RECURSOS]
    colores = [color for _, _, color in _RECURSOS]

    fig, ax = plt.subplots(figsize=(8, 5))
    bars = ax.bar(etiquetas, valores, color=colores)
    ax.set_title("Utilización de recursos")
    ax.set_ylabel("Utilización [0, 1]")
    ax.set_ylim(0, 1.1)
    for bar, val in zip(bars, valores):
        ax.text(
            bar.get_x() + bar.get_width() / 2.0,
            bar.get_height() + 0.02,
            f"{val:.3f}",
            ha="center",
        )
    fig.tight_layout()
    return fig


def _longitudes_cola(resultado: Any) -> list[float]:
    """Devuelve [mesas, meseros, cocineros] como longitud media de cola.

    Se integra la longitud de la cola en el tiempo (``area_colas_minutos``) y se
    divide por el horizonte observado; si falta la informacion se reporta 0.
    """
    areas = _get(resultado, "area_colas_minutos")
    horizonte = _get(resultado, "horizonte_observado_minutos")
    if not isinstance(areas, dict) or not horizonte or horizonte <= 0:
        return [0.0, 0.0, 0.0]
    return [float(areas.get(clave, 0.0)) / float(horizonte) for clave, _, _ in _RECURSOS]


def figura_longitudes_cola(resultado: Any):
    """Barras con la longitud media de cola de cada recurso."""
    _require_matplotlib()
    valores = _longitudes_cola(resultado)
    etiquetas = [etiqueta for _, etiqueta, _ in _RECURSOS]
    colores = [color for _, _, color in _RECURSOS]

    fig, ax = plt.subplots(figsize=(8, 5))
    bars = ax.bar(etiquetas, valores, color=colores)
    ax.set_title("Longitud media de cola por recurso")
    ax.set_ylabel("Grupos en espera (promedio)")
    ax.set_ylim(0, max(valores + [0.0]) * 1.2 + 0.05)
    for bar, val in zip(bars, valores):
        ax.text(
            bar.get_x() + bar.get_width() / 2.0,
            bar.get_height() + 0.02,
            f"{val:.2f}",
            ha="center",
        )
    fig.tight_layout()
    return fig


def figura_esperas_por_grupo(resultado: Any):
    """Boxplot de esperas por etapa (mesa, pedido, cocina, pago, total)."""
    _require_matplotlib()
    registros = _registros(resultado)

    fig, ax = plt.subplots(figsize=(10, 6))
    if not registros:
        ax.text(0.5, 0.5, "No hay registros para graficar esperas", ha="center", va="center")
        ax.axis("off")
        fig.tight_layout()
        return fig

    espera_mesa: list[float] = []
    espera_pedido: list[float] = []
    espera_cocina: list[float] = []
    espera_pago: list[float] = []
    espera_total: list[float] = []

    for r in registros:
        llegada = _campo(r, "llegada", "llegada_min")
        mesa = _campo(r, "mesa_asignada", "mesa_inicio_min")
        pedido_inicio = _campo(r, "inicio_pedido", "pedido_inicio_min")
        pedido_fin = _campo(r, "fin_pedido", "pedido_fin_min")
        cocina_inicio = _campo(r, "inicio_cocina", "cocina_inicio_min")
        consumo_fin = _campo(r, "fin_consumo", "consumo_fin_min")
        pago_inicio = _campo(r, "inicio_pago", "pago_inicio_min")

        if None in (llegada, mesa, pedido_inicio, pedido_fin, cocina_inicio, consumo_fin, pago_inicio):
            continue

        em = mesa - llegada
        ep = pedido_inicio - mesa
        ec = cocina_inicio - pedido_fin
        epg = pago_inicio - consumo_fin
        espera_mesa.append(max(0.0, em))
        espera_pedido.append(max(0.0, ep))
        espera_cocina.append(max(0.0, ec))
        espera_pago.append(max(0.0, epg))
        espera_total.append(max(0.0, em + ep + ec + epg))

    if not espera_total:
        ax.text(0.5, 0.5, "No hay grupos finalizados para graficar esperas", ha="center", va="center")
        ax.axis("off")
        fig.tight_layout()
        return fig

    datos_box = [espera_mesa, espera_pedido, espera_cocina, espera_pago, espera_total]
    etiquetas = [
        "Espera mesa",
        "Espera mesero\n(pedido)",
        "Espera cocina",
        "Espera mesero\n(pago)",
        "Espera total",
    ]
    try:
        ax.boxplot(datos_box, tick_labels=etiquetas, showmeans=True)
    except TypeError:  # matplotlib < 3.9 usa ``labels``
        ax.boxplot(datos_box, labels=etiquetas, showmeans=True)
    ax.set_title("Distribución de esperas por grupo")
    ax.set_ylabel("Tiempo (minutos)")
    ax.grid(axis="y", linestyle="--", alpha=0.3)
    fig.tight_layout()
    return fig


def figura_permanencia_vs_llegada(resultado: Any):
    """Dispersión de permanencia total vs instante de llegada."""
    _require_matplotlib()
    registros = _registros(resultado)

    fig, ax = plt.subplots(figsize=(8, 5))
    llegadas: list[float] = []
    permanencias: list[float] = []
    for r in registros:
        llegada = _campo(r, "llegada", "llegada_min")
        salida = _campo(r, "salida", "salida_min")
        if llegada is None or salida is None:
            continue
        llegadas.append(llegada)
        permanencias.append(max(0.0, salida - llegada))

    if not llegadas:
        ax.text(0.5, 0.5, "No hay grupos finalizados para graficar", ha="center", va="center")
        ax.axis("off")
        fig.tight_layout()
        return fig

    ax.scatter(llegadas, permanencias, alpha=0.6, s=20)
    ax.set_title("Permanencia total vs tiempo de llegada")
    ax.set_xlabel("Tiempo de llegada (min)")
    ax.set_ylabel("Permanencia total (min)")
    ax.grid(True, linestyle="--", alpha=0.3)
    fig.tight_layout()
    return fig


def _guardar_y_cerrar(fig, ruta: Optional[str], mostrar: bool) -> None:
    if ruta:
        _ensure_dir(ruta)
        fig.savefig(ruta, dpi=300, bbox_inches="tight")
    if mostrar:
        plt.show()
    plt.close(fig)


def graficar_utilizaciones(resultado: Any, ruta: Optional[str] = None, mostrar: bool = False) -> None:
    """Genera y guarda/muestra el gráfico de utilizaciones."""
    _guardar_y_cerrar(figura_utilizaciones(resultado), ruta, mostrar)


def graficar_esperas_por_grupo(resultado: Any, ruta: Optional[str] = None, mostrar: bool = False) -> None:
    """Genera y guarda/muestra el boxplot de esperas."""
    _guardar_y_cerrar(figura_esperas_por_grupo(resultado), ruta, mostrar)


def graficar_longitudes_cola(resultado: Any, ruta: Optional[str] = None, mostrar: bool = False) -> None:
    """Genera y guarda/muestra el gráfico de longitudes medias de cola."""
    _guardar_y_cerrar(figura_longitudes_cola(resultado), ruta, mostrar)


def graficar_permanencia_vs_llegada(resultado: Any, ruta: Optional[str] = None, mostrar: bool = False) -> None:
    """Genera y guarda/muestra la dispersión de permanencia vs llegada."""
    _guardar_y_cerrar(figura_permanencia_vs_llegada(resultado), ruta, mostrar)
