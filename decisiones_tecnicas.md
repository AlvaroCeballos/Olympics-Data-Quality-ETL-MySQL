# DECISIONES TÉCNICAS — ETL Olimpiadas G18

> Documento vivo que registra cada decisión técnica tomada durante el desarrollo del pipeline ETL.  
> Se actualiza fase por fase conforme avanza la implementación.

---

## DT-001: Fuente maestra de atletas

- **Decisión:** `bios_sample.csv` (representando `bios1.csv` crudo) es la fuente maestra para la tabla `atleta`.
- **Razón:** Es la fuente con más columnas biográficas (16 columnas: roles, títulos, afiliaciones, nombre original, etc.). Cumple con la instrucción del catedrático de procesar data cruda como insumo primario.
- **Implicación:** El campo `atleta.id_externo` almacena el `athlete_id` de Olympedia. Los IDs de Kaggle (`ID`, `player_id`) no se almacenan.

## DT-002: Clave de cruce cross-source (deduplicación)

- **Decisión:** Matching key = `(nombre_normalizado, sexo, anio_nacimiento_aprox)`.
- **Normalización del nombre:** minúsculas → NFKD (quitar acentos) → quitar puntuación → quitar bullet (`•`).
- **Razón:** Los `athlete_id` / `ID` / `player_id` son secuenciales independientes entre fuentes y no son cruzables. El nombre + sexo + año de nacimiento es la tupla más discriminante disponible.
- **Resolución:** Si match existe → reutilizar `id_atleta`. Si no → insertar nuevo atleta con `id_externo = NULL`.

## DT-003: Disciplina puente

- **Decisión:** Cuando la fuente no provee `Discipline` (Fuentes 2, 3, 4), se crea un registro en `disciplina` con `disciplina.nombre = deporte.nombre`.
- **Razón:** Garantiza integridad referencial en la jerarquía `deporte → disciplina → evento`. Ningún evento queda huérfano.
- **Caso Olympedia:** Provee `Discipline` directamente → se usa tal cual. Si no existe un `deporte` padre equivalente, se crea un `deporte` con `deporte.nombre = Discipline`.

## DT-004: Vínculo poblaciones → país

- **Decisión:** `populations.Country Code` se enlaza contra `pais.codigo_pais` directamente.
- **Razón:** Los Country Codes del Banco Mundial son ISO 3166-1 alpha-3 (datos geográficos), no códigos NOC del COI. La tabla `pais` almacena datos geográficos, no deportivos.
- **Implicación:** Algunos Country Codes no tendrán match con NOC (ej: `ABW` Aruba en BM vs `ARU` en NOC). Esto es correcto por diseño.

## DT-005: Tratamiento de mojibake

- **Decisión:** Función universal de saneamiento: `texto.encode('cp1252').decode('utf-8')` con fallback, aplicada a **todas** las cadenas de texto de **todas** las fuentes antes de cualquier procesamiento.
- **Razón:** Incluso los archivos "clean" de Keith Galli presentan mojibake (ej: `PyrÃ©nÃ©es-Atlantiques` debería ser `Pyrénées-Atlantiques`).
- **Adicionalmente:** Se reemplaza el carácter bullet `•` (mojibake de `â€¢`) por espacio.

## DT-006: Archivos de entrada del ETL

| Archivo | Rol | Capa |
|---|---|---|
| `bios_sample.csv` (= `bios1.csv`) | Fuente maestra biográfica cruda | Base |
| `bios_locs_sample.csv` (= `bios_locs.csv`) | Enriquecimiento lat/long vía merge por `athlete_id` | Base |
| `results.csv_sample.csv` (= `results1.csv`) | Resultados crudos con `Discipline`, `Pos`, `As` | Base |
| `noc_regions_sample.csv` (= `noc_regions.csv`) | Catálogo dimensional NOC/región | Base |
| `populations_sample.csv` (= `populations.csv`) | Serie demográfica 1960–2023 (Banco Mundial) | Base |
| `athlete_events_sample.csv` (= `athlete_events.csv`) | Kaggle 120 Years (1896–2016): Age, Height, Weight | Enriquecimiento |
| `olympics_dataset.csv` (= `olympics_dataset.csv`) | Kaggle Summer (1896–2024): Tokio 2020 + París 2024 | Actualización |
| `athlete_events_datalab_sample.csv` (= datalab) | Idéntico a Fuente 2 → solo validación cruzada | Validación |
| `bios_clean_sample.csv` / `results_clean_sample.csv` | Referencia de comparación, no ingesta directa | Referencia |

## DT-007: Estrategia de carga por capas

- **Capa Base (Fuente 1):** Olympedia cruda (bios + results) → puebla atletas maestros + participaciones históricas con `Discipline`, `Pos`, `As`.
- **Capa Enriquecimiento (Fuente 2/4):** Kaggle `athlete_events.csv` → agrega `edad`, `altura_reg`, `peso_reg` por edición a `participacion`. Aporta `City` (sede) y `Sport`.
- **Capa Actualización (Fuente 3):** Kaggle `olympics_dataset.csv` → incorpora resultados de Tokio 2020 y París 2024 no presentes en otras fuentes.

## DT-008: Orden de inserción en MySQL

Secuencia estricta respetando dependencias FK:
```
1. medalla (semilla DDL)
2. pais
3. poblacion_pais
4. noc
5. sede
6. olimpiada
7. deporte
8. disciplina
9. evento
10. equipo
11. atleta
12. participacion
```

## DT-009: Homologación categórica de sexo

- **Decisión:** `'Male'` → `'M'`, `'Female'` → `'F'`. Fuentes 2/3/4 ya usan `'M'`/`'F'`.
- **Razón:** El DDL define `atleta.sexo ENUM('M','F')`.

## DT-010: Homologación de medallas

- **Decisión:** `NaN` / `''` / `'No medal'` → `'NA'`. Valores válidos: `'Gold'`, `'Silver'`, `'Bronze'`.
- **Razón:** Tabla `medalla` tiene semilla con exactamente 4 valores. `participacion.id_medalla NOT NULL` obliga siempre a referenciar uno.

## DT-011: Tratamiento de posiciones y empates

- **Decisión:** Si `Pos` contiene `=` (ej: `=17`) → `es_empate = TRUE`, `posicion = '17'`. Valores textuales como `'DNS'`, `'DNF'`, `'DQ'` se almacenan tal cual en `posicion VARCHAR(30)`.
- **Razón:** El campo `posicion` es texto por diseño para soportar toda la variedad de formatos.

## DT-012: Columna `Unnamed: 7` de `results1.csv`

- **Decisión:** Se elimina. 100% vacía en todos los registros.
- **Razón:** Regla 12 del catedrático: solo se omite una columna si el 100% de sus tuplas carece de datos.

## DT-013: Columna `Nationality` de `results1.csv`

- **Decisión:** Se descarta de la carga a `participacion`. Ya existe `atleta.nacionalidad` proveniente de `bios1.csv`.
- **Razón:** Información redundante. La nacionalidad es un atributo del atleta, no de la participación.

## DT-014: FK de disciplina y evento admiten NULL en DDL

- **Decisión:** Aunque `aclaracionesTecnicas.md` menciona que `evento.id_disciplina` y `disciplina.id_deporte` son `NOT NULL`, el DDL real (`olimpiada2s.sql`) los define como `INT NULL`. Se respeta el DDL como fuente de verdad, pero la disciplina puente (DT-003) garantiza que en la práctica siempre tendrán valor.
- **Razón:** El DDL ya está aprobado por Persona 1 y no se modifica.

## DT-015: Fuente 4 (DataCamp) = Fuente 2 (Kaggle 120 Years)

- **Decisión:** Los datos son idénticos (confirmado comparando samples). Fuente 4 se usa únicamente para validación cruzada, no se carga de forma independiente.
- **Razón:** Evita duplicación de registros.

## DT-016: Estrategia de homologación y resolución de claves foráneas entre `pais` y `noc`

- **Decisión:** 
  1. Se carga primero `populations.csv` hacia la tabla `pais` utilizando el código estándar de 3 letras (ISO 3166-1 alpha-3).
  2. Luego se complementa con `noc_regions.csv`: si el código NOC ya existe en `pais`, se completan sus atributos `region` y `nombre_alt` (de la columna `notes`); si no existe, se crea la entidad territorial en `pais` para asegurar integridad.
  3. Para la tabla `noc`, el campo `id_pais` se resuelve mediante un lookup jerárquico en memoria: coincidencia por código (NOC = ISO) → coincidencia por nombre normalizado → coincidencia por nombre alternativo.
  4. Si una delegación especial o histórica no corresponde a un territorio soberano (ej: equipo de refugiados `ROT`, equipo unificado `EUN`), `id_pais` permanece como `NULL` de acuerdo con la definición del DDL (`id_pais INT NULL`).
- **Razón:** El DDL separa deliberadamente `pais` (entidad geográfica) de `noc` (entidad deportiva del COI). Esta jerarquía de resolución garantiza que ningún NOC quede desvinculado por simples discrepancias de siglas (ej: `ARU` en NOC vs `ABW` en ISO).

## DT-017: Tratamiento de agregados regionales en `populations.csv`

- **Decisión:** Los registros agregados del Banco Mundial (ej: *"Africa Eastern and Southern"*, *"World"*, *"Latin America & Caribbean"*, *"Euro area"*) se conservan en la tabla `pais` asignándoles el valor `region = 'Agregado Regional'`.
- **Razón:** Regla 4 y 7 de la cátedra (*"Prohibido descartar columnas o entidades que contengan datos útiles"*). Al mantener estos agregados identificados, se evita descartar tuplas y se preserva íntegra la serie temporal de datos del Banco Mundial en `poblacion_pais` sin provocar violaciones de llave foránea.

## DT-018: Desnormalización de series demográficas con `pandas.melt()`

- **Decisión:** La matriz ancha de 64 columnas anuales (`1960` a `2023`) de `populations.csv` se transforma a formato relacional largo `(id_pais, anio, poblacion)` mediante `pandas.melt()`. Se omiten exclusivamente las filas con valores `NaN` o nulos de población.
- **Razón:** El modelo relacional en 3NF define la clave primaria compuesta `PRIMARY KEY (id_pais, anio)`. Almacenar registros con población nula saturaría la base de datos sin aportar valor analítico para el cálculo de métricas per cápita.

## DT-019: Desglose semántico multinivel de ubicación de nacimiento en `atleta`

- **Decisión:** El atributo compuesto `Born` se descompone en tres columnas atómicas: `ciudad_nac`, `region_nac` y `id_pais_nac`. Se implementó un parser con soporte jerárquico multinivel:
  1. *Tres niveles:* `"in Ciudad, Región (CÓDIGO)"` $\rightarrow$ `ciudad_nac`, `region_nac`, `id_pais_nac`.
  2. *Dos niveles:* `"in Ciudad (CÓDIGO)"` $\rightarrow$ `ciudad_nac`, `id_pais_nac`.
  3. *Un nivel:* `"in Ubicación"` $\rightarrow$ `ciudad_nac`.
- **Razón:** Primera Forma Normal (1NF) y cumplimiento del esquema DDL. Para `id_pais_nac`, se prioriza el código territorial extraído de la ubicación sobre la sigla deportiva del atleta, creando la entidad en `pais` si no existía para garantizar integridad referencial estricta.

## DT-020: Enriquecimiento georreferenciado (`bios_locs` merge)

- **Decisión:** Se realiza un merge entre la data biográfica cruda (`bios1.csv`) y el dataset geográfico (`bios_locs.csv`) por la clave común `athlete_id`, poblando los campos de coordenadas WGS84 `latitud` y `longitud` (`DECIMAL(9,6)`) en la tabla `atleta`.
- **Razón:** Aprovechar el enriquecimiento geoespacial de la referencia oficial de Keith Galli sin desechar ninguna de las 16 columnas crudas originales (cumpliendo Reglas 4 y 7).

## DT-021: Conversión robusta de fechas históricas olímpicas a MySQL DATE

- **Decisión:** Las fechas en texto libre de `Born` y `Died` (ej. `"12 December 1886"`, `"1969-04-01"`, o solo año `"1886"`) se normalizan al estándar ISO-8601 `YYYY-MM-DD`. Cuando únicamente se dispone del año, se asume el primer día del año (`YYYY-01-01`).
- **Razón:** El tipo de dato en MySQL es `DATE`. Esta normalización garantiza que las fechas sean indexables y comparables cronológicamente por los Stored Procedures de Persona 3.

## DT-022: Catálogo histórico oficial de sedes y resolución contextual

- **Decisión:** Se implementa un catálogo histórico oficial de respaldo para mapear `(anio, temporada) -> (ciudad, codigo_pais_iso)`. Se consulta primero el dataset `athlete_events.csv`, y si la edición no contiene ciudad o no está presente en la muestra (ej: 1912 Summer en muestras reducidas), se recurre al catálogo histórico.
- **Razón:** La tabla `results1.csv` carece de la columna `City`, conteniendo únicamente el texto de los juegos (ej: `"1912 Summer Olympics"`). Este catálogo garantiza que el 100% de las ediciones en `olimpiada` tengan una `sede` real y vinculada a un `pais` geográfico sin violar claves foráneas.

## DT-023: Tratamiento de equipos para pruebas individuales en `results1.csv`

- **Decisión:** Para registros de `results1.csv` donde la columna `Team` es nula o vacía (correspondiente a pruebas individuales como *"Singles, Men"*), se asigna como nombre del equipo el nombre oficial de la delegación o país asociado a su código NOC (ej. `"France"` para `NOC = 'FRA'`). Para pruebas colectivas o dobles, se mantiene el nombre del equipo o pareja registrado en la data cruda.
- **Razón:** El DDL define `equipo.nombre VARCHAR(120) NOT NULL`. Asignar la delegación nacional evita nulos y permite asociar de forma natural las participaciones individuales a un equipo representativo vinculado a su NOC.

## DT-024: Resolución y aprovisionamiento on-the-fly de NOCs y países

- **Decisión:** Si durante la carga de sedes o equipos se identifica un código NOC o de país que no fue cargado en la fase dimensional (por pertenecer a filas fuera de la muestra inicial o por delegaciones de sedes históricas), el pipeline lo resuelve o aprovisiona automáticamente en las tablas `pais` y `noc` antes de insertar en `sede` o `equipo`.
- **Razón:** Cumplimiento estricto del orden de dependencias de claves foráneas (DT-008). Evita que la inserción de una sede o equipo falle por integridad referencial ante datos de diferentes capas.

## DT-025: Deduplicación por tokens y enriquecimiento de preseas entre fuentes Kaggle

- **Decisión:** En la Fuente 3 (`olympics_dataset.csv`), se implementó matching de atletas por coincidencia de subconjunto de tokens de nombres normalizados (ej. `"gunnar aaby"` como subconjunto de `"gunnar nielsen aaby"`), evitando duplicar atletas que aparecen con segundo nombre en una fuente y abreviados en otra. Si una participación ya existía registrada como `'NA'` pero la Fuente 3 reporta medalla de podio (`Gold`, `Silver`, `Bronze`), se actualiza la medalla en `participacion` de forma idempotente sin duplicar el hecho.
- **Razón:** Integridad del modelo de hechos. Garantiza que la tabla `participacion` refleje la versión más precisa del resultado olímpico sin incurrir en duplicaciones de la clave compuesta natural `(id_atleta, id_evento, id_olimpiada)`.

---

*Última actualización: 2026-09-13 — Ejecución y documentación de la Fase 6 (Actualización Fuente 3: olympics_dataset.csv).*
