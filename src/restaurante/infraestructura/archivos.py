"""Lectura y escritura de configuración, escenarios y resultados.

Todos los nombres ``*_bytes`` devuelven el contenido en memoria para usarse en
``st.download_button`` sin necesidad de escribir en disco.
"""

from __future__ import annotations

import csv
import io
import json
import os
from dataclasses import asdict, is_dataclass
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover - entorno sin PyYAML
    yaml = None


def _ensure_dir(path: str) -> None:
    """Asegura que el directorio para el archivo exista."""
    directory = os.path.dirname(os.path.abspath(path))
    if directory and not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)


def _to_dict(obj: Any) -> Any:
    """Convierte objetos (dataclasses, etc.) a dict recursivamente."""
    if is_dataclass(obj) and not isinstance(obj, type):
        return {k: _to_dict(v) for k, v in asdict(obj).items()}
    if isinstance(obj, dict):
        return {k: _to_dict(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_to_dict(v) for v in obj]
    return obj


def _verificar_yaml() -> None:
    if yaml is None:
        raise ValueError(
            "PyYAML no está instalado. No se puede leer/escribir .yaml/.yml. "
            "Instálalo con: pip install pyyaml"
        )


# --------------------------------------------------------------------------- #
# Configuración
# --------------------------------------------------------------------------- #
def cargar_configuracion(ruta: str) -> dict[str, Any]:
    """Lee una configuración YAML y la devuelve como diccionario.

    Raises:
        FileNotFoundError: Si no existe el archivo.
        ValueError: Si PyYAML no está instalado o el formato no es un mapeo.
    """
    _verificar_yaml()
    if not os.path.exists(ruta):
        raise FileNotFoundError(f"No se encontró el archivo de configuración: {ruta}")

    with open(ruta, "r", encoding="utf-8") as f:
        contenido = f.read()

    try:
        datos = yaml.safe_load(contenido)
    except Exception as e:
        raise ValueError(f"Error al leer YAML desde {ruta}: {e}") from e

    if datos is None:
        return {}
    if not isinstance(datos, dict):
        raise ValueError(f"La configuración en {ruta} debe ser un mapeo YAML (dict)")
    return datos


def guardar_configuracion(ruta: str, configuracion: Any) -> None:
    """Guarda una configuración (dict o dataclass) como archivo YAML."""
    _verificar_yaml()
    _ensure_dir(ruta)
    datos = _to_dict(configuracion)
    if not isinstance(datos, dict):
        raise ValueError("La configuración a guardar debe ser un mapeo (dict/dataclass)")
    with open(ruta, "w", encoding="utf-8") as f:
        yaml.safe_dump(datos, f, allow_unicode=True, sort_keys=False)


def cargar_escenarios(ruta: str) -> list[dict[str, Any]]:
    """Lee un YAML de escenarios y devuelve la lista completa de diccionarios."""
    _verificar_yaml()
    if not os.path.exists(ruta):
        raise FileNotFoundError(f"No se encontró el archivo de escenarios: {ruta}")

    with open(ruta, "r", encoding="utf-8") as f:
        contenido = f.read()
    try:
        datos = yaml.safe_load(contenido)
    except Exception as e:
        raise ValueError(f"Error al leer YAML desde {ruta}: {e}") from e

    if datos is None:
        return []
    if isinstance(datos, dict):
        return [datos]
    if isinstance(datos, list):
        return [escenario for escenario in datos if isinstance(escenario, dict)]
    raise ValueError(f"El archivo de escenarios {ruta} debe ser una lista o un mapeo")


# --------------------------------------------------------------------------- #
# Resultados
# --------------------------------------------------------------------------- #
def _obtener(obj: dict[str, Any], nombre: str, predeterminado: Any = None) -> Any:
    return obj.get(nombre, predeterminado) if isinstance(obj, dict) else predeterminado


def _filas_resumen(datos: dict[str, Any], metricas: Any = None) -> list[tuple[str, Any]]:
    """Compone filas (campo, valor) a partir de las métricas o del resultado."""
    filas: list[tuple[str, Any]] = []

    if metricas:
        for clave, valor in _to_dict(metricas).items():
            filas.append((clave, valor))
        return filas

    configuracion = _obtener(datos, "configuracion")
    if isinstance(configuracion, dict):
        for clave, valor in configuracion.items():
            filas.append((f"config_{clave}", valor))

    utilizacion = _obtener(datos, "utilizacion")
    if isinstance(utilizacion, dict):
        for recurso, valor in utilizacion.items():
            filas.append((f"utilizacion_{recurso}", valor))

    for clave in (
        "area_ocupada_minutos",
        "area_colas_minutos",
        "horizonte_observado_minutos",
        "grupos_llegados_horizonte",
        "grupos_salidos_horizonte",
        "grupos_pendientes_al_cierre",
        "tiempo_ultima_salida_min",
        "semilla",
    ):
        valor = _obtener(datos, clave)
        if isinstance(valor, dict):
            for subclave, subvalor in valor.items():
                filas.append((f"{clave}_{subclave}", subvalor))
        elif valor is not None:
            filas.append((clave, valor))

    return filas


def _escribir_csv_resultados(stream, resultado: Any, incluir_resumen: bool, metricas: Any) -> None:
    datos = _to_dict(resultado)
    registros = datos.get("registros", []) if isinstance(datos, dict) else []
    if registros is None:
        registros = []

    if registros:
        campos = list(registros[0].keys())
        writer = csv.DictWriter(stream, fieldnames=campos)
        writer.writeheader()
        writer.writerows(registros)


def guardar_resultados_csv(
    ruta: str,
    resultado: Any,
    incluir_resumen: bool = True,
    metricas: Any = None,
) -> None:
    """Guarda los registros de la simulación en CSV.

    Si ``incluir_resumen`` es True, también escribe ``<nombre>_resumen.csv`` con
    las métricas (si se reciben) o con los campos disponibles del resultado.
    """
    _ensure_dir(ruta)
    datos = _to_dict(resultado)

    with open(ruta, "w", newline="", encoding="utf-8") as f:
        _escribir_csv_resultados(f, resultado, incluir_resumen, metricas)

    if incluir_resumen:
        resumen_ruta = ruta.replace(".csv", "_resumen.csv")
        _ensure_dir(resumen_ruta)
        with open(resumen_ruta, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["campo", "valor"])
            for campo, valor in _filas_resumen(datos, metricas):
                writer.writerow([campo, valor])


def guardar_resultados_json(ruta: str, resultado: Any, indent: int = 2) -> None:
    """Guarda el resultado completo de la simulación en formato JSON."""
    _ensure_dir(ruta)
    datos = _to_dict(resultado)
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(datos, f, indent=indent, ensure_ascii=False)


def cargar_resultados_json(ruta: str) -> dict[str, Any]:
    """Carga resultados desde un archivo JSON guardado previamente."""
    if not os.path.exists(ruta):
        raise FileNotFoundError(f"No se encontró el archivo de resultados: {ruta}")
    with open(ruta, "r", encoding="utf-8") as f:
        return json.load(f)


# --------------------------------------------------------------------------- #
# Exportación en memoria (para descargas en la web)
# --------------------------------------------------------------------------- #
def resultado_a_csv_bytes(resultado: Any, metricas: Any = None) -> bytes:
    """Devuelve los registros como CSV en bytes (sin escribir en disco)."""
    stream = io.StringIO()
    datos = _to_dict(resultado)
    registros = datos.get("registros", []) if isinstance(datos, dict) else []
    if registros:
        writer = csv.DictWriter(stream, fieldnames=list(registros[0].keys()))
        writer.writeheader()
        writer.writerows(registros)
    contenido = stream.getvalue()
    if metricas:
        resumen = "\n".join(f"{campo},{valor}" for campo, valor in _filas_resumen(datos, metricas))
        contenido = contenido + "\n\n# resumen\n" + resumen + "\n"
    return contenido.encode("utf-8")


def resultado_a_json_bytes(resultado: Any, indent: int = 2) -> bytes:
    """Devuelve el resultado completo como JSON en bytes."""
    datos = _to_dict(resultado)
    return json.dumps(datos, indent=indent, ensure_ascii=False).encode("utf-8")


def tabla_a_csv_bytes(tabla: Any) -> bytes:
    """Convierte un DataFrame (u objeto con ``to_csv``) a CSV en bytes."""
    if hasattr(tabla, "to_csv"):
        return tabla.to_csv(index=False).encode("utf-8")
    return str(tabla).encode("utf-8")
