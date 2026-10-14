"""Punto de entrada de consola del simulador de restaurante.

Uso:
    python -m restaurante.main --config configs/base.yaml
    python -m restaurante.main --config configs/base.yaml --replicas 10 --semilla 7

Reutiliza la misma lógica que la interfaz web (``restaurante.interfaz.servicios``)
y guarda resultados en ``resultados/`` (CSV, JSON y PNG).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Permite ejecutar como script (python src/restaurante/main.py) sin instalar.
_SRC = Path(__file__).resolve().parents[1]
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from restaurante.infraestructura import archivos, graficos  # noqa: E402
from restaurante.interfaz import servicios  # noqa: E402
from restaurante.interfaz.rutas import RAIZ_PROYECTO  # noqa: E402


def _parsear_argumentos(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Simulador de restaurante: mesas, meseros y cocineros."
    )
    parser.add_argument(
        "--config",
        default="configs/base.yaml",
        help="Ruta al archivo YAML de configuración (relativa a la raíz del proyecto).",
    )
    parser.add_argument("--semilla", type=int, default=123, help="Semilla aleatoria base.")
    parser.add_argument(
        "--replicas",
        type=int,
        default=1,
        help="Número de réplicas para el resumen estadístico (>= 1).",
    )
    parser.add_argument(
        "--resultados-dir",
        default="resultados",
        help="Directorio (relativo a la raíz) para guardar resultados.",
    )
    return parser.parse_args(argv)


def _resolver(ruta: str) -> Path:
    camino = Path(ruta)
    return camino if camino.is_absolute() else (RAIZ_PROYECTO / camino)


def _imprimir_resumen(configuracion: dict, metricas: dict, semilla: int, replicas: int) -> None:
    print("=== Simulación finalizada ===")
    print(
        f"Configuración: mesas={configuracion['mesas']}, "
        f"meseros={configuracion['meseros']}, cocineros={configuracion['cocineros']}"
    )
    print(
        f"Horizonte H={configuracion['duracion_llegadas_min']:.1f} min | "
        f"lambda={configuracion['tasa_llegadas_grupos_hora']:.1f} grupos/hora | "
        f"distribución={configuracion['distribucion']}"
    )
    print(
        f"Grupos: llegados={metricas['grupos_llegados_horizonte']}, "
        f"salidos={metricas['grupos_salidos_horizonte']}, "
        f"pendientes={metricas['grupos_pendientes_al_cierre']}"
    )
    print(
        f"Colas medias (grupos): mesas={metricas['longitud_media_cola_mesas']:.2f}, "
        f"meseros={metricas['longitud_media_cola_meseros']:.2f}, "
        f"cocineros={metricas['longitud_media_cola_cocineros']:.2f}"
    )
    print(
        f"Utilización: mesas={metricas['utilizacion_mesas']:.3f}, "
        f"meseros={metricas['utilizacion_meseros']:.3f}, "
        f"cocineros={metricas['utilizacion_cocineros']:.3f}"
    )
    print(
        f"Espera total media={metricas['espera_total_media_min']:.2f} min | "
        f"Permanencia media={metricas['permanencia_media_min']:.2f} min | "
        f"Capacidad={metricas['tasa_salida_horizonte_grupos_hora']:.2f} grupos/hora"
    )
    if replicas > 1:
        print(f"Réplicas: {replicas} (semilla base={semilla})")


def main(argv: list[str] | None = None) -> int:
    args = _parsear_argumentos(argv)

    config_path = _resolver(args.config)
    resultados_dir = _resolver(args.resultados_dir)

    try:
        datos = archivos.cargar_configuracion(str(config_path))
        configuracion = servicios.completar_con_defecto(datos)
        parametros, configuracion_sim = servicios.config_desde_dict(configuracion)
    except Exception as e:  # noqa: BLE001
        print(f"Error cargando la configuración: {e}", file=sys.stderr)
        return 1

    # Ejecución principal (una réplica) para métricas y gráficos detallados.
    try:
        ejecucion = servicios.ejecutar_una(parametros, configuracion_sim, semilla=args.semilla)
    except Exception as e:  # noqa: BLE001
        print(f"Error en la simulación: {e}", file=sys.stderr)
        return 1

    resultados_dir.mkdir(parents=True, exist_ok=True)
    archivos.guardar_resultados_json(str(resultados_dir / "resultado.json"), ejecucion.resultado)
    archivos.guardar_resultados_csv(
        str(resultados_dir / "registros.csv"), ejecucion.resultado, metricas=ejecucion.metricas
    )

    try:
        graficos.graficar_utilizaciones(ejecucion.resultado, str(resultados_dir / "utilizaciones.png"))
        graficos.graficar_esperas_por_grupo(
            ejecucion.resultado, str(resultados_dir / "esperas_por_grupo.png")
        )
        graficos.graficar_permanencia_vs_llegada(
            ejecucion.resultado, str(resultados_dir / "permanencia_vs_llegada.png")
        )
        graficos.graficar_longitudes_cola(
            ejecucion.resultado, str(resultados_dir / "longitudes_cola.png")
        )
    except ImportError as e:
        print(f"Aviso: no se generaron gráficos ({e})")
    except Exception as e:  # noqa: BLE001
        print(f"Aviso: error al generar gráficos: {e}")

    if args.replicas > 1:
        try:
            tabla = servicios.ejecutar_replicas(
                parametros, configuracion_sim, replicas=args.replicas, semilla_base=args.semilla
            )
            resumen = servicios.resumir_replicas(tabla)
            (resultados_dir / "resumen_replicas.csv").write_bytes(archivos.tabla_a_csv_bytes(resumen))
        except Exception as e:  # noqa: BLE001
            print(f"Aviso: no se pudo calcular el resumen de réplicas: {e}")

    _imprimir_resumen(configuracion, ejecucion.metricas, args.semilla, args.replicas)
    print(f"Resultados guardados en: {resultados_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
