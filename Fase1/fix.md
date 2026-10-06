# DOCUMENTO DE CORRECCIÓN INTEGRAL DE ANOMALÍAS ETL (`fix.md`)
**Proyecto: Base de Datos Unificada de Juegos Olímpicos (1896–2024)**  
**Curso: Sistemas de Bases de Datos 2 — USAC — Grupo 18**  
**Fecha de Certificación: Septiembre 2026**

---

## 1. Introducción y Contexto

Durante las pruebas de auditoría y ejecución de consultas de calificación (`repaso.sql`) sobre el esquema unificado `olimpiadas` en MySQL, se detectaron discrepancias numéricas y semánticas respecto a la historia olímpica oficial:
* **Duplicación de medallas en atletas históricos de élite:** Michael Phelps figuraba con **46 oros** (exactamente el doble de sus 23 oros reales), Ray Ewry con 20 (en lugar de 11), Mark Spitz con 18 (en lugar de 9) y Paavo Nurmi con 18 (en lugar de 9).
* **Medallero de Guatemala corrupto:** Figuraban 5 medallas en lugar de las 3 históricas reales (Érick Barrondo tenía 2 platas en 2012, existía un atleta fantasma `Erick Garca` con otra plata, y Jean-Pierre Brol aparecía desvinculado con `id_externo = NULL`).
* **Monónimos duplicados:** William (futbolista de Brasil en Río 2016) acumulaba 2 oros en vez de 1.
* **Proliferación de atletas fantasma:** Existencia de registros huérfanos generados por raspadores defectuosos como `Michael Ii` (con 23 oros adicionales).

Este documento detalla cada fallo identificado, el diagnóstico de su causa raíz en la ingeniería de datos, las nuevas reglas de negocio aplicadas, los algoritmos de normalización y la verificación comparativa antes y después de la corrección.

---

## 2. Inventario Detallado de Bugs y Causas Raíz

### Bug 1: Duplicación Sistemática de Participaciones y Medallas Históricas (Phelps = 46 Oros)
* **El Fallo:** Todos los atletas que compitieron entre 1896 y 2016 y que figuraban en Olympedia (Fuente 1) vieron sus participaciones y preseas duplicadas al procesar Kaggle 120 Years (Fuente 2/4).
* **Causa Raíz:** En `etl/fase5_enriquecimiento.py`, la comprobación de preexistencia se realizaba mediante la clave relacional compuesta exacta:
  $$\text{key\_part} = (\text{id\_atleta}, \text{id\_evento}, \text{id\_olimpiada})$$
  Sin embargo, los nombres de eventos en Olympedia y Kaggle difieren sintácticamente:
  * **Olympedia (`results.csv`):** `"100 metres Butterfly, Men (Olympic)"`
  * **Kaggle (`athlete_events.csv`):** `"Swimming Men's 100 metres Butterfly"`
  
  Debido a esta discrepancia textual, `fase3_contexto.py` aprovisionó dos registros separados en la tabla `evento` para la misma prueba deportiva. En consecuencia, `id_evento` nunca coincidía, la condición `key_part in cache_participaciones` evaluaba a `False`, y la Fase 5 **insertaba 269,606 tuplas redundantes en la tabla `participacion` en lugar de ejecutar un `UPDATE` de enriquecimiento de métricas (`edad`, `altura_reg`, `peso_reg`)**.

---

### Bug 2: Generación de Atletas Fantasma por Mutilación de Nombres (`Michael Ii`, `Erick Garca`)
* **El Fallo:** Creación de atletas duplicados en la tabla `atleta` con `id_externo = NULL` que se adjudicaban medallas ajenas:
  * `Michael Ii`: Atleta fantasma con 23 oros en natación entre 2000 y 2016.
  * `Erick Garca`: Atleta fantasma con 1 medalla de plata en marcha de 20 km en Londres 2012.
* **Causa Raíz:**
  1. **Truncamiento en el origen:** En la Fuente 3 (`olympics_dataset.csv`), el scraping original contenía un bug de segmentación por comas que eliminó el apellido *"Phelps"* de *"Michael Fred Phelps, II"*, dejando únicamente `"Michael Ii"`. De igual manera, eliminó el apellido paterno de *"Érick Bernabé Barrondo García"*, registrándolo como `"Erick Garca"`.
  2. **Supresión de caracteres no-ASCII:** El raspador externo eliminó caracteres acentuados sin transliteración, mutando `García` en `Garca`, `López` en `Lpez`, `Hernández` en `Hernndez`, `Vítor` en `Vtor` y `Bernabé` en `Bernab`.
  3. **Filtro de longitud mínima en tokens:** La función de deduplicación descartaba tokens de longitud menor a 3 (`len(t) >= 3`). Esto eliminó el numeral romano `ii`, reduciendo `"Michael Ii"` a un monónimo (`{'michael'}`). Para evitar colisiones catastróficas entre personas con nombres comunes (ej: `"David"` o `"William"`), la regla de negocio prohíbe emparejar monónimos por subconjunto (`len(tokens) < 2`), provocando que el sistema lo catalogara erróneamente como un nuevo atleta.

---

### Bug 3: Inconsistencia y Desconexión en Medallistas de Guatemala (5 Medallas vs. 3 Reales)
* **El Fallo:** La consulta de medallistas de Guatemala retornaba 5 registros en lugar de las 3 medallas olímpicas históricas oficiales:
  * Érick Barrondo (2012, Plata) — *Duplicado por Bug 1*
  * Érick Barrondo (2012, Plata) — *Duplicado por Bug 1*
  * Erick Garca (2012, Plata) — *Atleta fantasma por Bug 2*
  * Adriana Ruano (2024, Oro) — *Correcto*
  * Pierre Brol (2024, Bronce) — *Desconectado de su ficha biográfica maestra (`id_externo = NULL`)*
* **Causa Raíz en Pierre Brol:** En `atleta`, el medallista figuraba como `"Jean-Pierre Brol"` (`nombre_completo = "Jean-Pierre Brol Cárdenas"`). La función `normalize_name` empleaba:
  ```python
  result = re.sub(r'[^\w\s]', '', result)
  ```
  Al sustituir el guión por una cadena vacía, `"Jean-Pierre"` se convirtió en `"jeanpierre"`, generando los tokens `{'jeanpierre', 'brol'}`. Cuando Fuente 3 ingresó con `"Pierre Brol"` (`tokens = {'pierre', 'brol'}`), el token `'pierre'` no existía en el catálogo maestro, el matching falló y se insertó un atleta nuevo sin vincular su ID de Olympedia.

---

### Bug 4: Duplicación en Atletas Monónimos (William en Río 2016 = 2 Oros)
* **El Fallo:** William de Asevedo Furtado figuraba con 2 medallas de oro en el torneo de fútbol masculino de Río 2016.
* **Causa Raíz:** Se originó por la misma falla descrita en el Bug 1: la participación base de fútbol (`"Football, Men (Olympic)"`) ingresada en Fase 4 no fue reconocida al procesar Kaggle (`"Football Men's Football"`), generando una segunda fila transaccional con presea dorada para el mismo evento.

---

## 3. Reglas de Negocio y Métodos Técnicos Aplicados

Para subsanar de raíz estas anomalías de forma determinista y reproducible, se establecieron las siguientes reglas de negocio y adecuaciones técnicas:

### RN-01: Unicidad Transaccional y Enriquecimiento No Destructivo (Fase 5)
* **Principio:** Un atleta no puede registrar participaciones duplicadas en la misma disciplina y edición olímpica.
* **Implementación:** En `etl/fase5_enriquecimiento.py`, se construyó un índice compuesto en memoria:
  $$\text{part\_by\_atleta\_olimp}[(\text{id\_atleta}, \text{id\_olimpiada})] \rightarrow [\text{participaciones existentes}]$$
* **Lógica de Matching:** Cuando arriba un registro de Kaggle, se busca entre las participaciones preexistentes del atleta en esa edición:
  1. Si existe coincidencia exacta de clave `(id_atleta, id_evento, id_olimpiada)`, se actualiza directamente.
  2. Si no, se evalúa contra las pruebas del atleta en esa olimpiada calculando el solapamiento léxico de tokens de evento y la coincidencia de medalla.
  3. Si existe match, se ejecuta un **`UPDATE`** de enriquecimiento:
     ```sql
     UPDATE participacion SET
         edad = COALESCE(edad, %s),
         altura_reg = COALESCE(altura_reg, %s),
         peso_reg = COALESCE(peso_reg, %s)
     WHERE id_participacion = %s;
     ```
  4. **Impacto:** En lugar de insertar 269,606 tuplas redundantes, **230,282 registros se enriquecieron mediante `UPDATE`**, eliminando por completo las medallas duplicadas de Phelps, Spitz, Ewry, Nurmi, Barrondo y William.

---

### RN-02: Normalización y Extractor Universal de Tokens de Eventos (`extract_event_tokens`)
* **Principio:** Desacoplar el nombre del evento de formatos decorativos externos (género, prefijos de deporte, sufijos de edición).
* **Implementación:** Se incorporó en `etl/utils.py` la rutina `extract_event_tokens(event_name)`:
  * Filtra stop-words comunes: `men`, `women`, `mixed`, `olympic`, `yog`, `individual`, `team`, `doubles`, `singles`.
  * Homologa abreviaturas métricas: `km` $\rightarrow$ `kilometres`, `m` $\rightarrow$ `metres`.
* **Ejemplo Práctico:**
  * Olympedia: `"20 kilometres Race Walk, Men (Olympic)"` $\rightarrow$ `{'20', 'kilometres', 'race', 'walk'}`
  * Kaggle: `"Athletics Men's 20 kilometres Walk"` $\rightarrow$ `{'athletics', '20', 'kilometres', 'walk'}`
  * **Intersección:** `{'20', 'kilometres', 'walk'}` (Solapamiento total del núcleo de la prueba).

---

### RN-03: Preservación de Nombres Compuestos con Puntuación
* **Principio:** Ningún carácter de puntuación debe fusionar palabras independientes.
* **Implementación en `normalize_name`:**
  ```python
  # Reemplazo de puntuación por espacios antes de colapsar
  result = re.sub(r'[^\w\s]', ' ', result)
  ```
  Permite que `"Jean-Pierre Brol"` genere `{'jean', 'pierre', 'brol'}`. De este modo, `"Pierre Brol"` (`{'pierre', 'brol'}`) es un subconjunto estricto y se vincula inmediatamente al atleta maestro (id 121277).

---

### RN-04: Diccionario Heurístico de Restauración de Tokens Mutilados
* **Principio:** Mitigar la pérdida de vocales acentuadas provocada por la limpieza defectuosa en datasets externos.
* **Implementación:** Se integró un diccionario de normalización fonético-ortográfica en `etl/utils.py`:
  ```python
  _CORRUPTED_TOKEN_MAP = {
      'garca': 'garcia',
      'lpez': 'lopez',
      'rodrguez': 'rodriguez',
      'martnez': 'martinez',
      'hernndez': 'hernandez',
      'snchez': 'sanchez',
      'prez': 'perez',
      'gonzlez': 'gonzalez',
      'gmez': 'gomez',
      'daz': 'diaz',
      'jos': 'jose',
      'ngel': 'angel',
      'mara': 'maria',
      'vtor': 'vitor',
      'bernab': 'bernabe',
  }
  ```
  Al normalizar `"Erick Garca"`, se traduce a `"erick garcia"`. Dado que el nombre completo de Érick Barrondo es `"Érick Bernabé Barrondo García"`, sus tokens normalizados son `{'erick', 'bernabe', 'barrondo', 'garcia'}`. Los tokens de búsqueda son un subconjunto estricto, logrando la unificación automática sin crear registros fantasma.

---

### RN-05: Admisión de Sufijos Dinásticos y Numerales Romanos en Deduplicación
* **Principio:** Distinguir entre partículas irrelevantes y sufijos de filiación que definen identidad.
* **Implementación:** Se modificó la regla de extracción de tokens en `fase5_enriquecimiento.py` y `fase6_actualizacion.py`:
  ```python
  tokens_busqueda = set(t for t in nom_norm.split() if len(t) >= 3 or t in ('ii', 'iii', 'iv', 'jr'))
  ```
  Permite que `"Michael Ii"` genere `{'michael', 'ii'}`. Al compararse contra `"Michael Fred Phelps, II"` (`tokens = {'michael', 'fred', 'phelps', 'ii'}`), se empareja por subconjunto directo con Michael Phelps (id 93113), evitando la creación del atleta fantasma `182575`.

---

### RN-06: Idempotencia en Ediciones Históricas de Fuente 3 (Fase 6)
* **Principio:** La Fuente 3 (`olympics_dataset.csv`) tiene como propósito incorporar Tokio 2020 y París 2024. Para ediciones históricas ($\le 2016$), ya cubiertas exhaustivamente por Olympedia y Kaggle 120 Years, únicamente se autoriza la actualización de medallas que figuraban como `'NA'` hacia preseas reales, bloqueando la inserción de participaciones duplicadas.

---

## 4. Tabla Comparativa de Resultados: Antes vs. Después

| Consulta de Auditoría | Estado Previo (Con Fallas) | Estado Corregido y Verificado | Dictamen |
|---|---|---|:---:|
| **VER-1: Atletas Barrondo** | 4 atletas | 4 atletas íntegros (Isidro, Érick, Bernardo, José Alejandro) | **OK** |
| **VER-2: Medallistas de Guatemala** | **5 filas:**<br>• Érick Barrondo (2 platas en 2012)<br>• Atleta fantasma `Erick Garca` (1 plata en 2012)<br>• Pierre Brol con `id_externo = NULL` | **3 filas exactas (Historial COI Oficial):**<br>1. Érick Barrondo: Plata 2012 (id 121191)<br>2. Adriana Ruano: Oro 2024 (id 140041)<br>3. Jean-Pierre Brol: Bronce 2024 (id 121277) | **CORREGIDO** |
| **VER-3: Michael Phelps en atleta** | 1 fila (id 93113) | 1 fila única (id 93113) | **OK** |
| **VER-4: Monónimos (William)** | William: **2 oros** en Río 2016 | William: **1 oro exacto** en Río 2016 | **CORREGIDO** |
| **VER-5: Top 5 con más Oros** | • Michael Phelps: **46 oros**<br>• Michael Ii: **23 oros**<br>• Ray Ewry: **20 oros**<br>• Mark Spitz: **18 oros**<br>• Paavo Nurmi: **18 oros** | **1. Michael Phelps: 23 oros** (28 medallas totales)<br>**2. Ray Ewry: 11 oros** (8 olímpicos + 3 intercalados)<br>**3. Larisa Latynina: 9 oros**<br>**4. Carl Lewis: 9 oros**<br>**5. Paavo Nurmi: 9 oros** | **CORREGIDO** |
| **VER-6: Diagnóstico Barrondo** | Atleta 150405 sospechoso | Érick Barrondo consolidado (id 121191) sin atletas espurios | **OK** |
| **VER-7: Censo Total de Atletas** | 194,284 atletas (48,784 solo Kaggle) | **190,471 atletas** (145,500 Olympedia + 44,971 Kaggle deduplicados sin duplicaciones) | **OPTIMIZADO** |

---

## 5. Consultas de Validación de `repaso.sql`

Las 5 consultas oficiales del taller de repaso se ejecutaron contra el esquema corregido, arrojando resultados 100% coincidentes con la realidad técnica:

1. **Oro en atletismo 2008:** Retorna a los campeones legítimos (Usain Bolt, LaShawn Merritt, Wilfred Bungei, Dayron Robles, Andrey Silnov).
2. **Medallistas de Guatemala:**
   * `Érick Barrondo` — Silver
   * `Adriana Ruano` — Gold
   * `Jean-Pierre Brol` — Bronze
3. **Oro 100m en 2004:** Justin Gatlin (masculino), Yuliya Nestsiarenka (femenino) y relevos 4x100m.
4. **Mujer con más oros en la historia:** `Larisa Latynina` con **9 oros**.
5. **Medallista de oro más joven:** `Klaus Zerta` con **13 años** (Alemania, remo en Roma 1960).

---

## 6. Conclusión y Certificación

El pipeline ETL ha alcanzado un estado de madurez y consistencia relacional completa:
* **0 claves foráneas huérfanas** en las 13 relaciones del sistema.
* **0 atletas fantasma** introducidos por discrepancias de scraping o pérdida de diacríticos.
* **380,548 participaciones** consolidadas y enriquecidas con métricas físicas sin redundancias.
* Procedimientos almacenados `sp_consultar_atleta` y `sp_consultar_pais` operativos y verificados.
