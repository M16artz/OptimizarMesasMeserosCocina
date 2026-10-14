# Defensa del proyecto: Optimización de mesas, meseros y cocineros

**Proyecto:** Simulación de una red de colas del servicio de un restaurante
**Método:** Simulación de eventos discretos en Python + análisis de teoría de colas
**Documento:** guía de defensa, cumplimiento de objetivos y casos de ejemplo

---

## 1. Resumen ejecutivo (para abrir la exposición)

El proyecto **modela el servicio de un restaurante como una red de colas en serie (tándem)** y lo resuelve mediante **simulación de eventos discretos** en Python. Cada grupo de clientes recorre cinco etapas —mesa, pedido, cocina, consumo y pago— compitiendo por tres recursos limitados: **mesas, meseros y cocineros**.

El sistema permite **evaluar distintas configuraciones de recursos** y **seleccionar una alternativa eficiente** según indicadores operativos (utilización, esperas, permanencia, capacidad de atención) y un criterio de costo ponderado con restricciones.

**Hallazgo central:** en la configuración base el sistema está **saturado** (utilización de mesas ~95%) y la espera explota. La mejora proviene de aliviar el **cuello de botella** correcto (primero mesas y cocina, no meseros).

---

## 2. El modelo: red de colas del restaurante

### 2.1 Diagrama de la red

```
Grupo llega (Poisson: λ grupos/hora)
        │
        ▼
┌──────────┐   ┌────────────┐   ┌──────────┐   ┌───────────┐   ┌───────────┐
│  MESA    │──▶│  MESERO    │──▶│  COCINA  │──▶│  CONSUMO  │──▶│  MESERO   │──▶ salida
│ 1 grupo  │   │  (pedido)  │   │(cocinero)│   │ (retardo) │   │  (pago)   │  libera mesa
└──────────┘   └────────────┘   └──────────┘   └───────────┘   └───────────┘
  recurso        recurso          recurso        sin recurso      recurso
  = mesa         = mesero         = cocinero     (retiene mesa)   = mesero
```

- Es una **red de colas tipo tándem** (como pide el objetivo general).
- **No** es una red de Jackson: hay **recursos compartidos** (el mesero atiende pedido y pago), **capacidades finitas** y **mesa retenida durante toda la estancia**. Por eso **se resuelve por simulación**, no con una fórmula cerrada global.

## 2.2 Ciclo de vida de un grupo (máquina de estados)

Definido en `src/restaurante/dominio/reglas.py`:

```
LLEGADA → ESPERANDO_MESA → TOMANDO_PEDIDO → EN_COCINA → EN_CONSUMO → PAGANDO → FINALIZADO
```

| Etapa | Recurso que ocupa | Se libera cuando |
|---|---|---|
| Espera por mesa | — (cola FIFO) | se asigna una mesa |
| Sentado / pedido | **mesa + mesero** | termina el pedido |
| Cocina | mesa + **cocinero** | termina la preparación |
| Consumo | **solo mesa** | termina de comer |
| Pago | mesa + mesero | termina el cobro |
| Salida | — | se libera la mesa |

> **Punto clave:** la **mesa se ocupa durante TODA la estancia**; los **meseros y cocineros solo durante su tarea**. Es una de las confusiones más probables en preguntas.

---

## 2.3 Cómo se configura y por qué

La configuración tiene **demanda + recursos** (`dominio/parametros.py`) y **tiempos de servicio** (`simulacion/procesos.py`). En el YAML se usan nombres de negocio:

| Parámetro | Representa | Unidad | Por qué |
|---|---|---|---|
| `mesas` | Capacidad de la estación "mesa" | entero > 0 | Variable de decisión |
| `meseros` | Servidores de pedido y pago | entero > 0 | Variable de decisión |
| `cocineros` | Servidores de cocina | entero > 0 | Variable de decisión |
| `tasa_llegadas_grupos_hora` (λ) | Ritmo de llegada de grupos | grupos/hora | Demanda |
| `tiempo_pedido_media_min` | Duración media de tomar pedido | min | Se convierte a `μ = 60 / tiempo` (pedidos/mesero·hora) |
| `tiempo_preparacion_media_min` | Duración media de preparar | min | Servicio de cocina |
| `tiempo_consumo_media_min` | Duración media de comer | min | Retardo (ocupa mesa, no trabajadores) |
| `tiempo_pago_media_min` | Duración media de cobrar | min | Servicio del mesero |
| `duracion_llegadas_min` (H) | Horario en que se admiten llegadas | min | Define la jornada; luego hay vaciado (*drain*) |
| `tamano_grupo` | Personas por grupo | entero ≥ 1 | Solo reporta personas atendidas |
| `distribucion` | `"exponencial"` o `"fija"` | — | Realismo vs. casos deterministas |

> **Aclaración de diseño:** `μ` (`mu_servicio`) es una **tasa** (pedidos por mesero/hora), no un tiempo. La media de tomar pedido es `60/μ`. Los tres recursos son las **variables de decisión** que se optimizan.

---

## 3. El azar: distribuciones y ¿se ajustó el modelo?

- **Llegadas:** proceso de **Poisson** → intervalos entre llegadas **exponenciales** con media `1/λ`. Esperanza de grupos en la jornada: `E[N] = λ · H`.
- **Servicios:** `expovariate(media)` si `distribucion="exponencial"`; valor fijo si `="fija"`.
- **Reproducibilidad:** cada réplica usa `random.Random(semilla)`. Misma configuración + misma semilla ⇒ mismo resultado (hay una prueba automática que lo verifica). En los experimentos se usan **semillas comunes por réplica** para comparar alternativas con menos ruido.

**¿El modelo se ajustó a datos reales? NO.**
- Los tiempos son **supuestos de prototipo**, no mediciones de un restaurante real.
- La distribución de servicios por defecto es **exponencial** (suposición de prototipo); puede cambiarse a determinista, pero **no se realizó un ajuste estadístico** (bondad de ajuste, Kolmogorov–Smirnov, etc.).
- Esto es una **decisión pendiente** y debe reconocerse como limitación.

> Mensaje honesto para el jurado: "El modelo reproduce la **estructura** de la red y permite comparar configuraciones; el ajuste fino de las distribuciones a datos observados queda como trabajo futuro."

---

## 4. El motor de simulación

Implementado en `simulacion/motor.py`:

1. **Agenda de eventos** = cola de prioridad (`heapq`) ordenada por tiempo; empates por orden de creación.
2. **Eventos:** `llegada`, `fin_pedido`, `fin_cocina`, `fin_consumo`, `fin_pago`.
3. En cada paso se **acumula el área de ocupación y de colas** durante el intervalo transcurrido y se avanza el reloj.
4. **Colas FIFO por recurso** (`simulacion/recursos.py`): asigna si hay capacidad, si no encola; al liberar, cede el recurso al primero de la cola.
5. Al terminar, **verifica invariantes**: sin solicitudes pendientes y sin recursos ocupados.
6. **Política temporal:** las llegadas cesan en `H`; los grupos ya admitidos **terminan** (fase de vaciado). La última salida puede ocurrir después de `H`.

> **Punto fino:** el motor es **propio** (no usa SimPy, aunque figure como dependencia). Es un simulador de eventos discretos equivalente y con validación de invariantes. Conviene decirlo con transparencia.

---

## 5. Métricas y fórmulas (`analisis/metricas.py`)

**Por grupo:**

| Métrica | Fórmula |
|---|---|
| Espera por mesa | `mesa_asignada − llegada` |
| Espera por mesero (pedido) | `inicio_pedido − mesa_asignada` |
| Espera por cocina | `inicio_cocina − fin_pedido` |
| Espera por mesero (pago) | `inicio_pago − fin_consumo` |
| Espera total | suma de las cuatro anteriores |
| Permanencia total | `salida − llegada` |

**Agregadas:**

| Métrica | Fórmula |
|---|---|
| Utilización | `área ocupada / (capacidad × tiempo observado)` |
| Grupos llegados / salidos / pendientes | conteos respecto a `H` |
| Capacidad de atención | `grupos salidos / H horas` (throughput) |
| Longitud media de cola | `área de cola / tiempo observado` |

Se exponen como `longitud_media_cola_mesas`, `longitud_media_cola_meseros` y
`longitud_media_cola_cocineros` (número medio de grupos en espera por recurso).
El motor acumula el área de cola en `area_colas_minutos` y se divide por el
horizonte observado (Ley de Little). También están disponibles en la consola, en
la web (métrica y gráfico) y como columna de los experimentos.

> **Nota de precisión:** la utilización se normaliza sobre el **tiempo observado** (incluye el vaciado). Es una convención a declarar en el informe.

---

## 6. Teoría de colas M/M/s (`analisis/teoria_colas.py`)

Se usa como **referencia de verificación**, no como sustituto de la simulación. Con λ (llegada), μ (servicio **por servidor**) y s servidores:

- Carga ofrecida: `a = λ / μ`
- Utilización: `ρ = a / s` → **estabilidad:** `λ < s·μ` (`ρ < 1`)
- **Erlang B** (recurrencia estable): `B(0)=1`, `B(n) = a·B(n-1)/(n + a·B(n-1))`
- **Erlang C** (prob. de esperar): `C = B(s) / (1 − ρ + ρ·B(s))`
- `P0` calculada en escala logarítmica (evita desbordes)
- Longitud media de cola: `Lq = C · ρ / (1 − ρ)`
- Tiempo medio de cola: `Wq = Lq / λ`
- Tiempo medio en sistema: `Ws = Wq + 1/μ`
- Longitud media del sistema: `Ls = λ · Ws`

> **Por qué no basta:** el restaurante es tándem con recursos compartidos y mesa retenida; no son estaciones M/M/s independientes. La fórmula **valida estaciones aisladas** bajo supuestos, y sirve para comprobar órdenes de magnitud.

---

## 7. Optimización (`analisis/optimizador.py`)

- **Variables de decisión:** `mesas, meseros, cocineros` (enteros positivos).
- **Costo:** `C = a·mesas + b·meseros + c·cocineros`.
- **Restricciones:** límites sobre métricas (por defecto `máx`), p. ej. `espera_total_media_min ≤ umbral`, `utilizacion_mesas ≤ 0.85` o `longitud_media_cola_mesas ≤ umbral`.
- **Método:** búsqueda **exhaustiva** sobre las configuraciones evaluadas; elige la **factible de menor costo**; empata por menor espera y menos recursos.
- **Frontera de Pareto:** alternativas **no dominadas** para mostrar el compromiso recursos ↔ espera.

> **Advertencia (§10 de los acuerdos):** sin costos reales, los pesos son **hipótesis**. La solución **no** debe presentarse como "óptimo financiero", sino como **alternativa eficiente bajo pesos hipotéticos**.

---

## 7.1 ¿Se cumplen los objetivos? (evaluación honesta)

### Objetivo general
> Optimizar la distribución de mesas, meseros y cocineros mediante una red de colas y su simulación en Python, para evaluar configuraciones e identificar una alternativa que mejore la eficiencia operativa.

**✅ Cumplido.** Red de colas tándem implementada + simulación en Python + comparación de configuraciones + optimización + interfaz (consola y web).

### Objetivo específico 1 — Implementar el modelo de red de colas
> Tasas de llegada, tiempos de atención, capacidad de estaciones, disponibilidad de mesas/meseros/cocineros.

| Requisito | Estado | Evidencia |
|---|---|---|
| Tasas de llegada (Poisson) | ✅ | `motor.ejecutar` con `expovariate(λ/60)` |
| Tiempos de atención (pedido, preparación, consumo, pago) | ✅ | `procesos.duracion_actividad` |
| Capacidad de las estaciones | ✅ | `GestorRecursos` (mesas/meseros/cocineros) |
| Colas FIFO | ✅ | `recursos.GestorRecursos` |
| Mesa disponible durante toda la estancia | ✅ | `motor._fin_pago` libera la mesa al salir |

### Objetivo específico 2 — Evaluar configuraciones con indicadores
> Utilización, tiempos de espera, longitud de colas y capacidad de atención; identificar la distribución más eficiente.

| Indicador pedido | Estado | Evidencia |
|---|---|---|
| Utilización (mesas/meseros/cocineros) | ✅ | `metricas.utilizacion_*` |
| Tiempos de espera (4 etapas + total) | ✅ | `metricas.espera_*` |
| Capacidad de atención (grupos/hora) | ✅ | `metricas.tasa_salida_horizonte_grupos_hora` |
| Longitud de colas | ✅ | `metricas.longitud_media_cola_*` (integral `area_colas_minutos` / horizonte) |
| Criterio de selección | ✅ | pesos + restricciones + frontera de Pareto (`optimizador`) |

**Conclusión:** los objetivos se cumplen **por completo**. La longitud media de
cola se obtiene integrando la cola en el tiempo:
`L_media_cola(recurso) = area_colas_minutos[recurso] / horizonte_observado`.
Además puede usarse como **restricción** del optimizador
(p. ej. `longitud_media_cola_mesas ≤ 5`).

---

## 7.2 Casos de ejemplo: cómo se aplica el modelo y cómo se mejora

> Cifras reales del motor con **10 réplicas**, semilla base 1, λ=30 grupos/h, H=120 min, tiempos 2/5/15/2 min y tamaño de grupo 2. (λ·H ≈ **60 grupos** por jornada.)

| Escenario | Mesas | Meseros | Cocineros | Salidos (de 60) | Pendientes | Espera total (min) | Permanencia (min) | Cola mesas | Cola cocina | Util. mesas | Util. meseros | Util. cocineros | Rendimiento (grupos/h) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **E0 base** | 4 | 2 | 1 | 15.9 | 44.1 | 143.7 | 168.2 | 23.88 | 0.56 | 0.948 | 0.284 | 0.628 | 7.95 |
| **E1 +mesas** | 8 | 2 | 1 | 19.7 | 40.3 | 95.5 | 119.2 | 13.65 | 2.76 | 0.862 | 0.354 | 0.834 | 9.85 |
| **E2 +meseros** | 8 | 4 | 1 | 18.2 | 41.8 | 98.6 | 123.1 | 13.65 | 2.76 | 0.859 | 0.170 | 0.828 | 9.10 |
| **E3 +cocineros** | 8 | 4 | 2 | 29.8 | 30.2 | 37.7 | 62.1 | 8.84 | 0.62 | 0.838 | 0.253 | 0.625 | 14.90 |
| **E4 ajustado** | 12 | 5 | 3 | 43.0 | 17.0 | 7.4 | 31.5 | 1.78 | 0.64 | 0.706 | 0.268 | 0.568 | 21.50 |

> «Cola mesas» y «Cola cocina» son las longitudes medias de cola (grupos en espera). La
> cola de meseros es prácticamente 0 en todos los casos.

### Lectura de los resultados (el "cómo se mejora")

1. **E0 (4/2/1): sistema saturado.** Las mesas están al **94.8 %** de utilización y la **cola de mesas promedia 23.9 grupos**; la espera total media explota a **143.7 min**. El cuello de botella son las **mesas**.
2. **E1: duplicar mesas (4→8) reduce la espera a la mitad** (143.7 → 95.5 min) y baja la cola de mesas a 13.7 grupos, con rendimiento 7.95 → 9.85 g/h. La utilización de cocina sube a **0.834** y aparece la **cola de cocina = 2.76 grupos**: el **siguiente cuello de botella es la cocina**.
3. **E2: sumar meseros (2→4) NO mejora** (espera 98.6 min, colas idénticas a E1). **Lección clave:** si el cuello de botella es cocina/mesas, agregar meseros **desperdicia recursos** (utilización de meseros 0.170 y cola 0).
4. **E3: duplicar cocineros (1→2) sí mejora fuerte** (espera 95.5 → 37.7 min; cola de cocina 2.76 → 0.62; rendimiento 9.85 → 14.90 g/h). Confirma que la **cocina** era el cuello de botella tras E1.
5. **E4: escalar todo** (12 mesas, 5 meseros, 3 cocineros) lleva la espera a **7.4 min**, la cola de mesas a 1.78 grupos, la permanencia a 31.5 min y el rendimiento a **21.5 g/h**, con mesas al 0.706 (holgura). Es la operación fluida.

**Interpretación para la defensa:** el modelo **identifica el cuello de botella** (utilización alta **y** cola creciente en el mismo recurso) y demuestra que **no toda ampliación mejora**: hay que ampliar el recurso limitante. Eso es precisamente la "mejora de eficiencia operativa" que persigue el objetivo general.

**Interpretación para la defensa:** el modelo **identifica el cuello de botella** y demuestra que **no toda ampliación mejora**: hay que ampliar el recurso limitante. Eso es precisamente la "mejora de eficiencia operativa" que persigue el objetivo general.

### ¿Cuál es la mejor configuración?

Depende del criterio. El modelo lo resuelve así:

- **Restricciones:** `espera_total_media_min ≤ 20` y `utilizacion_mesas ≤ 0.85`; **pesos** `mesas = meseros = cocineros = 1`.
- **Resultado (búsqueda exhaustiva):** la única **factible de menor costo** es
  **E4 → 12 mesas, 5 meseros, 3 cocineros** (costo de recursos = 20).

> El criterio es configurable: también puede exigirse, por ejemplo,
> `longitud_media_cola_mesas ≤ 2` como restricción de servicio.

**Frontera de Pareto** (alternativas no dominadas = sin desperdicio):

| Mesas | Meseros | Cocineros | Costo | Espera total (min) | Salidos |
|---|---|---|---|---|---|
| 4 | 2 | 1 | 7 | 143.7 | 15.9 |
| 8 | 2 | 1 | 11 | 95.5 | 19.7 |
| 8 | 4 | 2 | 14 | 37.7 | 29.8 |
| 12 | 5 | 3 | 20 | 7.4 | 43.0 |

- **E0 → E1 → E3 → E4** forman la **frontera** (cada paso mejora sin desperdiciar).
- **E2 (8/4/1) queda FUERA de la frontera:** está **dominado** por E1 (cuesta más y tarda más). Refuerza la lección del cuello de botella.

**Recomendación:**
- **Máxima calidad de servicio** → **E4 (12/5/3)**: espera 7.4 min.
- **Mejor compromiso costo/espera** → **E3 (8/4/2)**: espera 37.7 min con costo 14 (frente a costo 20 de E4).

---

## 8. Guion de defensa (preguntas frecuentes)

1. **¿Qué es el proyecto?** Una red de colas del restaurante resuelta por simulación de eventos discretos para comparar configuraciones de mesas, meseros y cocineros.
2. **¿Por qué no M/M/s para todo?** Porque la mesa se ocupa toda la estancia y el mesero se comparte entre pedido y pago → estaciones **dependientes**; M/M/s sirve solo como verificación de estaciones aisladas.
3. **¿Usaron SimPy?** Se implementó un **motor propio** con agenda de eventos (no SimPy); es semánticamente equivalente y valida invariantes al cierre.
4. **¿Las distribuciones están ajustadas a datos?** No; son supuestos de prototipo (Poisson + exponencial). Se puede cambiar a determinista. El ajuste es trabajo futuro.
5. **¿Qué reportan como eficiencia?** Utilización, esperas, **longitudes medias de cola**, permanencia, capacidad de atención y costo de recursos con restricciones, más la frontera de Pareto.
6. **¿El resultado es "el óptimo"?** Es la mejor configuración **factible bajo pesos hipotéticos** por búsqueda exhaustiva, no un óptimo financiero.
7. **¿Miden longitud de cola?** Sí: `longitud_media_cola_mesas/meseros/cocineros`, a partir de la integral de la cola en el tiempo (`area_colas_minutos / horizonte observado`).
8. **¿Qué muestra el caso base?** Que con 4 mesas el sistema se satura (utilización 0.95, cola media de mesas ≈ 23.9 grupos) y la espera se dispara; el cuello de botella son las mesas, luego la cocina.

---

## 9. Limitaciones y trabajo futuro

1. **Registrar la evolución temporal de las colas** (por hora) para reportar máximos y no solo promedios.
2. **Ajustar distribuciones a datos reales** (o justificar formalmente la exponencial).
3. **Declarar en el informe** las cuatro transparencias: motor propio (no SimPy), distribuciones no ajustadas, pesos hipotéticos y utilización medida sobre el tiempo observado.
4. **Tamaño de grupo variable** (hoy constante) si se quiere modelar personas con más fidelidad.
5. **Más réplicas** e intervalos de confianza para robustez estadística.

---

## 10. Cierre de la exposición (frase de cierre sugerida)

"El proyecto implementa una **red de colas** del restaurante, la resuelve por **simulación de eventos discretos** y **optimiza** la asignación de mesas, meseros y cocineros. Los casos de ejemplo muestran que **ampliar el recurso cuello de botella** **mejora la eficiencia** (espera de 143.7 a 7.4 min; rendimiento de 7.95 a 21.5 grupos/hora), y la **frontera de Pareto** permite elegir entre máxima calidad de servicio y el mejor compromiso costo-beneficio."
