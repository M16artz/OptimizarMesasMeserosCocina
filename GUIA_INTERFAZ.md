# Guía de uso de la interfaz

Guía práctica del simulador de restaurante (mesas, meseros y cocineros): **qué
hace cada cosa, qué representa y cómo saber que encontraste lo que buscabas**.

---

## 0. Dos formas de usar el simulador

| Forma | Comando | Para qué sirve |
|---|---|---|
| **Web (Streamlit)** | `streamlit run app.py` | Explorar, comparar escenarios y optimizar con controles y gráficos |
| **Consola** | `python -m restaurante.main --config configs/base.yaml` | Ejecución rápida y reproducible; guarda resultados en `resultados/` |

Instalación (una vez):

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

Ambas formas usan la **misma lógica interna** (`restaurante.interfaz.servicios`),
así que con la misma configuración y semilla producen los **mismos números**.

---

## 1. Mapa mental: qué representa cada cosa

El restaurante se modela como una **red de colas en serie**. Cada **grupo** de
clientes atraviesa cinco etapas compitiendo por tres recursos:

```
Llegada ─▶ [MESA] ─▶ [MESERO: pedido] ─▶ [COCINERO] ─▶ [consumo] ─▶ [MESERO: pago] ─▶ Salida
```

| Concepto | Qué representa | Unidad |
|---|---|---|
| **Mesa** | Recurso ocupado por el grupo **toda** su estadía | entero ≥ 1 |
| **Mesero** | Recurso usado al **tomar el pedido** y al **cobrar** | entero ≥ 1 |
| **Cocinero** | Recurso que **prepara** el pedido | entero ≥ 1 |
| **λ (tasa de llegadas)** | Ritmo con que llegan grupos (Poisson) | grupos/hora |
| **Tiempo de pedido** | Duración media de tomar el pedido | minutos |
| **Tiempo de preparación** | Duración media de cocinar | minutos |
| **Tiempo de consumo** | Duración media de comer (ocupa mesa, no trabajadores) | minutos |
| **Tiempo de pago** | Duración media de cobrar | minutos |
| **H (duración de llegadas)** | Horario en que se admiten llegadas; luego hay vaciado | minutos |
| **Tamaño de grupo** | Personas por grupo (solo afecta el conteo de personas) | entero ≥ 1 |
| **Distribución** | `exponencial` (realista) o `fija` (determinista, para pruebas) | — |

> Regla de oro: las **mesas** son el recurso que más limita, porque se ocupan
> durante pedido + cocina + consumo + pago.

---

## 2. Interfaz web (Streamlit)

Ejecuta `streamlit run app.py`. Verás una **barra lateral** (configuración) y
**tres pestañas**.

### 2.1 Barra lateral — Configuración

Formulario con los parámetros del modelo. Al pulsar **Aplicar configuración** se
valida y se usa en lo que ejecutes después.

| Campo | Qué representa | Cómo elegirlo |
|---|---|---|
| **Mesas / Meseros / Cocineros** | Recursos a asignar (variables de decisión) | Es lo que quieres **probar u optimizar** |
| **Tamaño de grupo** | Personas por grupo | 1–5 típico; no cambia recursos |
| **Tasa de llegadas (grupos/hora)** | Demanda | Súbela para ver saturación |
| **Tiempo de pedido / preparación / consumo / pago** | Duraciones medias por etapa | Ajústalas a tu caso real |
| **Duración de llegadas H** | Jornada en minutos | 120 = 2 h; 480 = 8 h |
| **Distribución** | `exponencial` (realista) / `fija` (pruebas) | Usa `exponencial` salvo que quieras reproducir a mano |

**Archivo de configuración (YAML):**

- **Ruta YAML:** dónde leer/guardar (`configs/base.yaml` por defecto).
- **Cargar:** toma una configuración existente desde ese archivo.
- **Guardar:** escribe la configuración activa en el archivo.
- **Restaurar valores por defecto:** vuelve a la configuración base.

Abajo se muestra un **resumen activo**: `X mesas · Y meseros · Z cocineros · λ · H`.

### 2.2 Pestaña «Ejecución y resultados»

1. **Semilla**: número que fija el azar. *Misma semilla ⇒ mismo resultado*.
2. Pulsa **Ejecutar simulación**.
3. Revisa las **tarjetas de indicadores** (ver glosario en §6):

   | Indicador | Qué te dice |
   |---|---|
   | Espera total media (min) | Tiempo medio que un grupo espera en total |
   | Permanencia media (min) | Tiempo medio desde que llega hasta que sale |
   | Utilización de mesas/meseros/cocineros | Fracción de tiempo que cada recurso está ocupado (0–1) |
   | Cola media de mesas/meseros/cocineros (grupos) | Nº medio de grupos esperando por ese recurso |
   | Capacidad de atención (grupos/hora) | Grupos atendidos por hora (throughput) |
   | Grupos salidos / pendientes en H | Carga atendida dentro de la jornada |

4. **Gráficos**:
   - *Utilización de recursos*: barras por recurso. La barra más alta es el **cuello de botella**.
   - *Permanencia vs llegada*: dispersión; si sube hacia el final, el sistema se saturó.
   - *Esperas por grupo*: caja por etapa (mesa, pedido, cocina, pago, total).
   - *Longitud media de cola*: barras de grupos en espera por recurso.
5. **Registros por grupo**: tabla con las marcas de tiempo de cada grupo.
6. **Descargas**: registros en **CSV**, resultado completo en **JSON**.
7. **Múltiples réplicas**: pulsa *Calcular promedios con réplicas* para obtener
   medias e **intervalos de confianza** (más confiable que una sola corrida).

### 2.3 Pestaña «Escenarios»

Compara varias configuraciones a la vez (definidas en `configs/escenarios.yaml`).

1. **Ruta YAML** de escenarios (cada escenario tiene `nombre` + parámetros).
2. **Réplicas** y **semilla base** (se usan las mismas semillas por réplica para comparar con menos ruido).
3. Pulsa **Comparar escenarios**.
4. Verás:
   - **Resumen por escenario** (una fila por configuración).
   - *Espera total media por escenario* (barras).
   - *Espera vs permanencia* (dispersión).
   - Botón **Descargar resumen (CSV)** y tabla por réplica.

### 2.4 Pestaña «Optimización»

Elige la **configuración factible de menor costo** dentro de los escenarios.

1. **Pesos** de mesas, meseros y cocineros (hipótesis de costo, no dinero real).
   El costo de recursos es `peso_mesas·mesas + peso_meseros·meseros + peso_cocineros·cocineros`.
2. **Restricciones**:
   - *Espera total media máxima (min)* → p. ej. `≤ 20`.
   - *(Opcional)* *Cola media de mesas máxima (grupos)* → activa la casilla e ingresa el límite.
3. Pulsa **Seleccionar configuración**. Verás la config elegida, su costo y sus métricas.
4. **Frontera de compromiso** (Pareto): tabla y gráfico de las alternativas **no
   dominadas** (costo de recursos vs espera), para elegir el mejor intercambio.

> Requiere haber pulsado antes **Comparar escenarios** (esa tabla es la entrada).

---

## 3. Consola (`python -m restaurante.main`)

```bash
python -m restaurante.main --config configs/base.yaml
python -m restaurante.main --config configs/base.yaml --replicas 10 --semilla 7
```

| Flag | Significado | Default |
|---|---|---|
| `--config` | Ruta del YAML de configuración | `configs/base.yaml` |
| `--semilla` | Semilla aleatoria base | `123` |
| `--replicas` | Nº de réplicas para el resumen estadístico | `1` |
| `--resultados-dir` | Carpeta de salida | `resultados` |

**Imprime** en pantalla: configuración, grupos llegados/salidos/pendientes,
colas medias, utilizaciones, espera/permanencia y capacidad.

**Guarda** en `resultados/`: `registros.csv`, `registros_resumen.csv`,
`resultado.json`, `resumen_replicas.csv` (si `--replicas > 1`) y gráficos PNG
(`utilizaciones.png`, `esperas_por_grupo.png`, `permanencia_vs_llegada.png`,
`longitudes_cola.png`).

---

## 4. ¿Cómo sé que encontré lo que buscaba?

Buscas **la combinación de mesas, meseros y cocineros que atiende la demanda sin
saturarse y con el menor costo**. Estas son las señales:

### 4.1 Señales de diagnóstico

| Señal en los resultados | Qué significa |
|---|---|
| Utilización > 0.90 y **cola creciente** | **Saturación**: ese recurso es el cuello de botella |
| Grupos **pendientes al cierre** altos | No alcanza el tiempo; falta capacidad |
| Espera total muy por encima del tiempo de servicio | Los clientes esperan más de lo razonable |
| Utilización **0.60–0.85** y colas bajas | Operación **sana con holgura** |
| Utilización < 0.50 | **Recurso sobredimensionado** (dinero/recursos desperdiciados) |

### 4.2 Tabla rápida «si quiero saber… → mira…»

| Si quiero saber… | Mira… |
|---|---|
| ¿Dónde está el cuello de botella? | Mayor **utilización** y mayor **cola media** |
| ¿Cuánto espera un cliente? | **Espera total media** |
| ¿Cuánta capacidad tengo? | **Capacidad de atención (grupos/hora)** |
| ¿Me alcanza la jornada? | **Grupos pendientes al cierre** (debería ser ≈ 0) |
| ¿Estoy desperdiciando recursos? | Recursos con utilización baja |
| ¿Cuál es el mejor compromiso costo/servicio? | **Frontera de Pareto** en «Optimización» |

### 4.3 Ejemplo real de lectura

Con 4 mesas, 2 meseros y 1 cocinero, λ=30 g/h, H=120 min:

- Utilización de mesas **0.95** y cola media de mesas **≈ 24 grupos** → **las mesas
  son el cuello de botella**.
- Al subir a 8 mesas, la utilización de cocina llega a **0.83** y su cola a
  **2.76 grupos** → **ahora el cuello es la cocina**.
- Sumar meseros **no cambia nada** (su utilización baja) → recurso mal asignado.
- Duplicar cocineros reduce la espera de 95 a **38 min**; escalar todo la lleva a
  **7 min** con rendimiento de **21 g/h**.

**Conclusión:** encontraste lo que buscabas cuando identificas **qué recurso limita**
y demuestras que ampliarlo mejora, mientras los demás quedan con holgura.

---

## 5. ¿Cuándo sé que terminé? (criterios de éxito)

Considera que **ya cumpliste** cuando, sobre la configuración elegida:

- [ ] **Grupos pendientes al cierre ≈ 0** (se atiende toda la demanda admitida).
- [ ] **Ningún recurso con utilización > 0.90 de forma sostenida** (sin saturar).
- [ ] **Espera total media aceptable** para tu criterio (p. ej. ≤ 20 min).
- [ ] **Colas medias bajas** en el recurso que solía ser cuello de botella.
- [ ] **Sin recursos sobredimensionados** (utilización muy baja e innecesaria).
- [ ] Resultado **reproducible**: misma semilla ⇒ mismo resultado.
- [ ] Hay una **alternativa eficiente** identificada (config + costo) y, si aplica,
      una **frontera de Pareto** que muestre el compromiso.

Si todos se cumplen, tienes un resultado **defendible**: una distribución que
**mejora la eficiencia** frente a la configuración base, respaldada por
indicadores de **utilización, esperas, colas y capacidad de atención**.

> Recuerda declarar en el informe: la distribución por defecto es un **supuesto
> de prototipo** (Poisson + exponencial, no ajustada a datos), los pesos son
> **hipotéticos**, y la utilización se mide sobre el **tiempo observado**
> (incluye el vaciado).

---

## 6. Glosario de métricas

| Métrica (nombre interno) | Significado | Fórmula |
|---|---|---|
| `espera_total_media_min` | Espera media total por grupo | suma de esperas por etapa |
| `permanencia_media_min` | Tiempo medio en el sistema | `salida − llegada` |
| `utilizacion_mesas/meseros/cocineros` | Fracción de ocupación | `área ocupada / (capacidad × tiempo observado)` |
| `longitud_media_cola_mesas/meseros/cocineros` | Grupos medios en espera | `área de cola / tiempo observado` |
| `tasa_salida_horizonte_grupos_hora` | Capacidad de atención | `grupos salidos / H horas` |
| `grupos_llegados_horizonte` | Demanda admitida en H | conteo |
| `grupos_salidos_horizonte` | Atendidos dentro de H | conteo |
| `grupos_pendientes_al_cierre` | Aún en el sistema al cerrar | `llegados − salidos` |

---

## 7. Problemas comunes

| Situación | Causa probable / qué hacer |
|---|---|
| Todo saturado, esperas enormes | Faltan **mesas** (recurso que se ocupa toda la estadía) |
| Añado meseros y no mejora | El cuello de botella es mesa o cocina, no meseros |
| Cocina al 100 % | Faltan **cocineros** aunque sobren mesas/meseros |
| Pendientes al cierre > 0 | Sube recursos o reduce λ / la duración de servicios |
| «No se pudieron comparar los escenarios» | Revisa la ruta/formato del YAML de escenarios |
| La optimización dice «no factible» | Relaja las restricciones (espera/cola) o amplía escenarios |
| Resultados distintos cada vez | Estás cambiando la **semilla**; fíjala para reproducir |
