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

---

*Última actualización: 2026-09-10 — Análisis inicial y planificación de fases.*
