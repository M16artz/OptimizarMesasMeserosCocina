# Optimización de la distribución de mesas, meseros y cocineros

Simulación de eventos discretos de un restaurante (mesas, meseros y cocineros)
para comparar configuraciones y seleccionar alternativas eficientes bajo
indicadores y restricciones.

## Requisitos

- Python 3.11 o superior.
- Dependencias en `requirements.txt` (SimPy, NumPy, Pandas, SciPy, Matplotlib,
  PyYAML, pytest y Streamlit para la interfaz web).

## Instalación

Con `pip`:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

Con `uv` (más rápido):

```bash
uv venv .venv
uv pip install --python .venv/bin/python -e .
```

## Uso

### Interfaz web (Streamlit)

```bash
streamlit run app.py
```

Incluye pestañas de:

- **Ejecución y resultados:** indicadores, gráficos de utilización y esperas,
  registros por grupo y descarga en CSV/JSON.
- **Escenarios:** comparación de una lista de escenarios (`configs/escenarios.yaml`).
- **Optimización:** selección de una configuración bajo restricciones y pesos.

### Consola

```bash
python -m restaurante.main --config configs/base.yaml
python -m restaurante.main --config configs/base.yaml --replicas 10 --semilla 7
```

Guarda en `resultados/` los registros (`registros.csv`), el resumen
(`registros_resumen.csv`), el resultado completo (`resultado.json`), el resumen
de réplicas (`resumen_replicas.csv`) y los gráficos en PNG.

Guarda en `resultados/` los registros (`registros.csv`), el resumen
(`registros_resumen.csv`), el resultado completo (`resultado.json`), el resumen
de réplicas (`resumen_replicas.csv`) y los gráficos en PNG.

Indicadores calculados por ejecución: grupos llegados/salidos/pendientes, esperas
por etapa y total, permanencia, utilización por recurso, capacidad de atención
(grupos/hora) y **longitud media de cola** por recurso
(`longitud_media_cola_mesas`, `longitud_media_cola_meseros`,
`longitud_media_cola_cocineros`), obtenida como `area_colas_minutos / horizonte
observado`.

## Pruebas

```bash
pytest
```

## Estructura del proyecto

```
src/restaurante/
├── dominio/           # Entidades, parámetros y reglas
├── simulacion/        # Motor de eventos discretos, procesos y recursos
├── analisis/          # Métricas, teoría de colas, experimentos y optimización
├── infraestructura/   # Lectura/escritura de archivos y gráficos
├── interfaz/          # Capa de aplicación y vistas Streamlit
└── main.py            # Punto de entrada de consola
```

## Unidades y convenciones

- Tiempos y duraciones en **minutos**.
- Tasa de llegadas en **grupos/hora**.
- La magnitud de llegada es un **grupo**.
- Reproducibilidad por semilla: misma configuración y semilla producen el mismo
  resultado.
