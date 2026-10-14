# Acuerdos técnicos y contratos del simulador de restaurante

**Repositorio:** `M16artz/OptimizarMesasMeserosCocina`  
**Versión:** propuesta inicial 0.1  
**Estado:** BORRADOR — requiere revisión conjunta antes de considerarse un acuerdo definitivo.

## 1. Objetivo y alcance

Desarrollar en Python una simulación de eventos discretos del funcionamiento de un restaurante para **comparar cantidades de mesas, meseros y cocineros** y seleccionar configuraciones eficientes bajo indicadores y restricciones definidos.

**Dentro del alcance:** llegadas de grupos, espera por mesa, atención del pedido y del pago por meseros, preparación por cocineros, consumo, salida, colas, utilización de recursos, comparación de escenarios y optimización cuantitativa.

**Fuera del alcance:** ubicación física de mesas, recorridos, rutas, desplazamiento de trabajadores, distribución espacial, diseño de cocina, inventarios y elaboración de planos.

## 2. Responsables de los módulos

| Responsable | Carpeta / archivos principales | Entregable |
|---|---|---|
| Andrés | `src/restaurante/dominio/`: `entidades.py`, `parametros.py`, `reglas.py` | Definiciones del dominio, validación de configuraciones y contratos de datos compartidos |
| Yandry | `src/restaurante/simulacion/`: `motor.py`, `procesos.py`, `recursos.py` | Motor SimPy, manejo de recursos, eventos y registros por grupo |
| Miguel | `src/restaurante/analisis/`: `metricas.py`, `teoria_colas.py`, `experimentos.py`, `optimizador.py` | Métricas, validaciones matemáticas, réplicas, comparaciones y selección de configuraciones |
| Melissa | `src/restaurante/infraestructura/`: `archivos.py`, `graficos.py`; `src/restaurante/main.py` | Lectura y escritura de configuración/resultados, gráficos e integración ejecutable |

**Pruebas:** cada integrante implementa las pruebas relacionadas con su módulo. Todos revisan los cambios que modifiquen contratos compartidos.

## 3. Modelo conceptual — propuesta para la primera versión

1. Llegan **grupos** según un proceso de llegadas configurable.
2. Cada grupo requiere una **mesa**; si todas están ocupadas, espera en una cola FIFO.
3. Una vez sentado, solicita un **mesero** para tomar el pedido; el mesero se libera cuando termina esa tarea.
4. El pedido solicita un **cocinero**; si todos están ocupados, espera su turno.
5. Al completarse la preparación, el grupo **consume los alimentos** mientras mantiene ocupada la mesa; durante el consumo no ocupa permanentemente a un mesero ni a un cocinero.
6. Después del consumo, solicita un **mesero para pagar**; el mesero se libera al concluir el pago.
7. Tras el pago, el grupo sale y **libera la mesa**.

**Supuestos provisionales:** todas las mesas son equivalentes; una mesa aloja exactamente un grupo sin modelar el tamaño del grupo; cada grupo realiza un pedido; un cocinero procesa un pedido a la vez; un mesero atiende una tarea a la vez; las colas son FIFO y no se abandona la espera. Estos supuestos deben aprobarse y registrarse en el informe como simplificaciones.

**No confundir recursos:** la mesa queda ocupada durante toda la estancia del grupo, mientras que los meseros y los cocineros se reservan únicamente durante sus tareas.

## 4. Convenciones técnicas compartidas

- **Lenguaje:** Python 3.11 o superior; concretar una versión compatible en `pyproject.toml`.
- **Motor:** SimPy. **Análisis:** NumPy, Pandas, SciPy (si se necesita), Matplotlib. **Pruebas:** pytest.
- **Unidad de tiempo:** **minutos** para todos los instantes y duraciones internos. La tasa de llegada se configura en **grupos/hora** y se convierte a grupos/minuto en la simulación.
- **Magnitud de llegada:** grupo. La cantidad de clientes individuales solo se informará si se modela explícitamente el tamaño de cada grupo.
- **Aleatoriedad:** cada réplica utiliza su propia semilla; no usar un generador global compartido entre ejecuciones.
- **Nombres:** Python `snake_case` para atributos/funciones y `PascalCase` para clases.
- **Dependencias:** `dominio` no importa SimPy, Pandas ni Matplotlib; `simulacion` usa `dominio`; `analisis` usa las estructuras de salida del dominio, sin depender del motor; `infraestructura` se encarga de archivos y gráficos; `main.py` coordina.
- **Archivos de salida:** directorio `resultados/`, que puede excluirse de control de versiones para archivos generados.

## 5. Contrato de la configuración compartida

Andrés define esta entidad en `dominio/parametros.py`. Los nombres y tipos siguientes son una **propuesta de interfaz**; cualquier cambio debe aprobarse antes de su integración.

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class ConfiguracionRestaurante:
    mesas: int
    meseros: int
    cocineros: int
    tasa_llegadas_grupos_hora: float
    tiempo_pedido_media_min: float
    tiempo_preparacion_media_min: float
    tiempo_consumo_media_min: float
    tiempo_pago_media_min: float
    duracion_llegadas_min: float
```

Validaciones mínimas: `mesas`, `meseros`, `cocineros` enteros positivos; tiempos, tasa y duración positivos; sin atributos de distancia, coordenadas ni recorridos.

**Distribuciones provisionales:** intervalos entre llegadas exponenciales (proceso de Poisson homogéneo). La distribución de cada tiempo de servicio deberá elegirse explícitamente: puede iniciarse con exponenciales para prototipado y sustituirse por distribuciones ajustadas a datos cuando se disponga de observaciones. No interpretar los parámetros de ejemplo como mediciones reales.

**Configuraciones experimentales:** los conteos de mesas, meseros y cocineros son variables de decisión; los parámetros de demanda y servicio deben mantenerse equivalentes al comparar alternativas.

## 6. Contrato de registros y resultado de la simulación

Andrés define en `dominio/entidades.py` las estructuras de datos y Yandry las completa durante cada ejecución. La propuesta mínima es:

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class RegistroGrupo:
    grupo_id: int
    llegada_min: float
    mesa_inicio_min: float
    pedido_inicio_min: float
    pedido_fin_min: float
    cocina_inicio_min: float
    cocina_fin_min: float
    consumo_fin_min: float
    pago_inicio_min: float
    salida_min: float

@dataclass(frozen=True)
class ResultadoSimulacion:
    configuracion: ConfiguracionRestaurante
    semilla: int
    registros: tuple[RegistroGrupo, ...]
    grupos_llegados_horizonte: int
    grupos_salidos_horizonte: int
    grupos_pendientes_al_cierre: int
    ocupacion_mesas_minutos_horizonte: float
    ocupacion_meseros_minutos_horizonte: float
    ocupacion_cocineros_minutos_horizonte: float
    tiempo_ultima_salida_min: float
```

**Significado de la ocupación acumulada:** minutos-recurso ocupados, sumados entre todos los recursos de la misma categoría, solo dentro del horizonte de llegadas `0 <= t <= duracion_llegadas_min`. Ejemplo: dos meseros ocupados durante 5 minutos acumulan 10 minutos-mesero.

**Contrato del motor** (`simulacion/motor.py`):

```python
class MotorSimulacion:
    def __init__(self, configuracion: ConfiguracionRestaurante, semilla: int):
        ...

    def ejecutar(self) -> ResultadoSimulacion:
        ...
```

En el mismo escenario y con la misma semilla, el resultado debe ser reproducible.

## 7. Política temporal del experimento

**Propuesta de referencia:** admitir llegadas desde `t = 0` hasta antes del cierre de llegadas `H = duracion_llegadas_min`, y después **dejar terminar** a los grupos que ya ingresaron (fase de vaciado o *drain*). Esto evita que las medidas de permanencia excluyan artificialmente a clientes que aún están dentro al terminar el horario de llegada.

Para las comparaciones se registrarán, de manera separada:

- Grupos que llegaron antes de `H`.
- Grupos que completaron la atención antes de `H`.
- Grupos pendientes en `H`.
- Tiempo del último grupo en salir, que puede ser mayor que `H`.
- Utilización de recursos medida **dentro de `[0, H]`**, para compartir el mismo denominador temporal entre configuraciones.
- Esperas y permanencia total de todos los grupos admitidos, incluso si finalizan después de `H`.

## 8. Métricas y definiciones

Miguel implementa estas métricas en `analisis/metricas.py`, calculadas **desde los registros** entregados por Yandry:

| Indicador | Definición |
|---|---|
| Espera por mesa | `mesa_inicio_min - llegada_min` |
| Espera por mesero para pedido | `pedido_inicio_min - mesa_inicio_min` |
| Espera por cocinero | `cocina_inicio_min - pedido_fin_min` |
| Espera por mesero para pago | `pago_inicio_min - consumo_fin_min` |
| Espera total | Suma de las cuatro esperas anteriores |
| Permanencia total | `salida_min - llegada_min` |
| Utilización de mesas | `ocupacion_mesas_minutos_horizonte / (mesas * H)` |
| Utilización de meseros | `ocupacion_meseros_minutos_horizonte / (meseros * H)` |
| Utilización de cocineros | `ocupacion_cocineros_minutos_horizonte / (cocineros * H)` |
| Salidas dentro del horario | Número de grupos con `salida_min <= H` |
| Pendientes al cierre | Grupos llegados antes de `H` que no han salido en `H` |

Los indicadores de utilización se reportan como fracción o porcentaje, con convención uniforme. El denominador de las esperas promediadas debe declararse claramente; para el primer modelo se consideran todos los grupos admitidos.

Las longitudes medias de cola requieren registrar eventos de entrada y salida de cada cola o integrar su longitud en el tiempo; **no pueden reconstruirse únicamente a partir de los instantes resumidos si falta la evolución de la cola**. Antes de incluirlas como resultado obligatorio, Yandry y Miguel deberán acordar un registro de eventos adecuado.

## 9. Análisis matemático y límites de aplicación

`analisis/teoria_colas.py` contendrá funciones para calcular indicadores de una cola M/M/s bajo los supuestos de llegadas de Poisson, servicios exponenciales, servidores equivalentes, cola ilimitada y condiciones de estabilidad (`rho < 1`).

Estas fórmulas serán **referencia de verificación para estaciones compatibles**, no sustitutos automáticos de la simulación completa: una mesa ocupada durante pedido, preparación, consumo y pago genera dependencias que impiden modelar todo el restaurante como colas independientes sin justificación.

## 10. Contrato de experimentos y optimización

Interfaz propuesta:

```python
def calcular_metricas(resultado: ResultadoSimulacion) -> dict[str, float]:
    ...

def ejecutar_experimentos(
    configuraciones: list[ConfiguracionRestaurante],
    replicas: int,
    semilla_base: int,
):
    """Devuelve una tabla con indicadores por configuración y réplica."""
    ...

def seleccionar_configuracion(tabla_experimentos, restricciones, pesos):
    """Selecciona configuración bajo criterios acordados y reporta factibilidad."""
    ...
```

La optimización considera exclusivamente los conteos enteros positivos de mesas, meseros y cocineros. Para una primera versión se recomienda búsqueda exhaustiva en intervalos acotados y las mismas condiciones de demanda en todas las configuraciones.

**Criterio aún pendiente de aprobación:** minimizar un costo/peso de recursos `a * mesas + b * meseros + c * cocineros`, sujeto a límites definidos de espera y servicio. Sin costos económicos observados, los pesos serán **hipótesis de trabajo** y la solución no debe presentarse como óptimo financiero. También puede reportarse la frontera de compromiso entre recursos y tiempo de espera.

## 11. Pruebas de aceptación mínimas

1. No existen mesas ocupadas simultáneamente por dos grupos.
2. Ningún mesero o cocinero atiende dos tareas al mismo tiempo.
3. Una mesa se libera solo después de la salida del grupo.
4. En una configuración válida, las esperas y duraciones registradas son no negativas y los hitos temporales están ordenados.
5. Repetir una ejecución con la misma configuración y la misma semilla reproduce los resultados.
6. Las tasas de utilización están entre 0 y 1, considerando tolerancia numérica.
7. Las métricas de un escenario determinístico sencillo coinciden con cálculos realizados manualmente.
8. Una estación M/M/s estable usada como prueba reproduce aproximadamente sus valores teóricos dentro de tolerancias estadísticas apropiadas.
9. El proceso no confunde cantidad de **grupos** con cantidad de **personas**.
10. La aplicación se ejecuta desde `main.py` sin rutas locales específicas del equipo de un integrante.

## 12. Flujo de GitHub para el equipo

- `main` mantiene una versión integrable; evitar commits directos de trabajo individual.
- Trabajar en ramas `feature/dominio`, `feature/simulacion`, `feature/analisis` y `feature/infraestructura-main`.
- Cada integrante crea un *pull request* y solicita al menos una revisión antes de integrar.
- Antes de integrar cambios que afecten contratos compartidos, actualizar este documento y avisar a los demás.
- No subir credenciales, entornos virtuales, cachés ni archivos temporales; configurar `.gitignore`.
- Si se usa una rama `develop`, debe crearse y acordarse explícitamente; no asumir que ya existe en GitHub.

## 13. Decisiones pendientes de aprobación

- [ ] ¿Todas las mesas serán equivalentes y atenderán exactamente un grupo, sin diferenciar tamaños?
- [ ] ¿La llegada de grupos será Poisson homogénea o se usarán tasas distintas según hora?
- [ ] ¿Qué distribuciones representarán toma de pedido, preparación, consumo y pago?
- [ ] ¿La duración del experimento será una jornada finita con vaciado posterior como se propone?
- [ ] ¿Los clientes siempre esperan o pueden retirarse sin ser atendidos?
- [ ] ¿Qué límites máximos de espera y mínimos de atención se exigirán?
- [ ] ¿Existen costos reales de mesas, meseros y cocineros o se evaluarán pesos hipotéticos?
- [ ] ¿Quién revisará cada *pull request* y cuál será la versión de Python adoptada?

**Criterio para iniciar el trabajo independiente:** aprobar al menos las reglas del ciclo de atención, los tipos compartidos `ConfiguracionRestaurante` / `RegistroGrupo` / `ResultadoSimulacion` y las definiciones de tiempo/unidad. Los detalles experimentales restantes pueden cerrarse antes de implementar `optimizador.py`.

## 14. Actualización de contratos e interfaz web (propuesta para revisión)

**Fecha:** 2026-10-14 · **Estado:** ACTUALIZACIÓN PROPUESTA — requiere revisión del equipo.

Al integrar la rama de simulación/análisis (`MiguelRama`), la implementación del
backend difiere de la propuesta inicial de este documento. Para evitar
desalineaciones, se registra aquí el contrato **realmente implementado**, que es
el que debe considerarse como interfaz vigente.

### 14.1 Contrato real del backend

- `dominio/parametros.py` → `ParametrosSistema(lambda_llegada, mu_servicio, mesas, meseros, cocineros)`
  - `lambda_llegada` en **grupos/hora**.
  - `mu_servicio` en **pedidos atendidos por mesero/hora** (media de pedido `= 60 / mu_servicio` minutos).
- `simulacion/procesos.py` → `ConfiguracionSimulacion` (frozen):
  `duracion_llegadas_minutos`, `preparacion_media_minutos`, `consumo_media_minutos`,
  `pago_medio_minutos`, `tamano_grupo`, `distribucion` (`"exponencial"` o `"fija"`).
- `simulacion/motor.py` → `MotorSimulacion(parametros, configuracion=None, semilla=42).ejecutar()`
  devuelve `ResultadoSimulacion` con: `registros` (lista de dicts), `utilizacion`
  (`{"mesa", "mesero", "cocinero"}`), `area_ocupada_minutos`, `area_colas_minutos`,
  `horizonte_observado_minutos` y `eventos`.
- Las marcas de tiempo de cada registro son `llegada`, `mesa_asignada`,
  `inicio_pedido`, `fin_pedido`, `inicio_cocina`, `fin_cocina`, `fin_consumo`,
  `inicio_pago` y `salida` (equivalen a los nombres `*_min` del contrato inicial).
- `analisis/` → `calcular_metricas(resultado, configuracion=None)`,
  `ejecutar_experimentos(configuraciones, replicas, semilla_base)`,
  `resumir_experimentos(tabla, ...)`, `seleccionar_configuracion(tabla, restricciones, pesos)`,
  `frontera_pareto(tabla, objetivos)`, y `teoria_colas` (M/M/s).

### 14.2 Interfaz web (Streamlit)

- Se agrega el paquete `src/restaurante/interfaz/` como **capa de presentación**:
  `servicios.py` (lógica de aplicación, sin Streamlit), `estado.py`, `cache.py`,
  `rutas.py` y `vistas/`.
- El mismo `servicios.py` alimenta la consola (`main.py`) y la web, evitando
  duplicar lógica.
- `main.py` conserva su rol de punto de entrada ejecutable (prueba de aceptación
  #10) y ahora usa el backend real.
- Streamlit se añade como dependencia de la interfaz web; el núcleo (dominio,
  simulación, análisis) no depende de él.

### 14.3 Longitud media de cola

- El motor ya acumula `area_colas_minutos` (integral de la longitud de cada cola
  en el tiempo) y `horizonte_observado_minutos`.
- `calcular_metricas` ahora expone la **longitud media de cola** por recurso:
  `longitud_media_cola_mesas`, `longitud_media_cola_meseros` y
  `longitud_media_cola_cocineros`, con
  `L_media = area_colas_minutos[recurso] / horizonte_observado_minutos`.
- Con ello se cierra el indicador de **longitud de colas** del objetivo
  específico 2 y el requisito de §8 (se registra/integra la evolución de la cola).
  Admiten usarse como restricción del optimizador (p. ej.
  `longitud_media_cola_mesas <= umbral`).

### 14.4 Pendientes de aprobación del equipo

- [ ] Confirmar el contrato real de §14.1 como vigente y reemplazar los tipos
  `ConfiguracionRestaurante` / `RegistroGrupo` / `ResultadoSimulacion` propuestos
  inicialmente por los aquí descritos.
- [ ] Aprobar `interfaz/` (Streamlit) como capa de presentación opcional.
- [ ] Acordar el responsable de la interfaz web y de las pruebas de humo (`AppTest`).
