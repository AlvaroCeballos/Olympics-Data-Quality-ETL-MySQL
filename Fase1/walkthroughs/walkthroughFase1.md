# Walkthrough — ETL Olimpiadas G18

## Fase 0: DDL + Utilidades ✅

### Qué se hizo

Se crearon 2 scripts en la carpeta `etl/`:

#### 1. [`utils.py`](file:///d:/Proyectos%20U/Bases%202/Proyecto%201/SBD2B_PROYECT1_2S2026_G18/etl/utils.py)
Módulo central de utilidades reutilizables:

| Función | Propósito | DT |
|---|---|---|
| `fix_mojibake(text)` | Repara doble codificación CP1252→UTF-8 y quita bullet `•` | DT-005 |
| `fix_mojibake_series(series)` | Aplica `fix_mojibake` a una columna pandas completa | DT-005 |
| `normalize_name(name)` | Normaliza nombre: minúsculas, NFKD, quitar acentos/puntuación | DT-002 |
| `get_connection(database)` | Conexión MySQL con charset `utf8mb4` | — |
| `safe_insert(cursor, sql, params)` | INSERT con manejo de duplicados | — |
| `get_or_create(cursor, table, ...)` | Buscar o insertar registro con UNIQUE KEY | — |
| `print_section/ok/warn/error` | Helpers de formato para consola | — |
| Constantes de rutas | `BIOS_RAW`, `RESULTS_RAW`, `NOC_REGIONS`, etc. | DT-006 |

**Ingeniería inversa aplicada:** La función `fix_mojibake` está inspirada en el patrón del Cell 4 del notebook de Keith Galli (`df['name'] = df['Used name'].str.replace("•", " ")`), pero extendida para reparar también la doble codificación CP1252/UTF-8.

#### 2. [`fase0_ddl.py`](file:///d:/Proyectos%20U/Bases%202/Proyecto%201/SBD2B_PROYECT1_2S2026_G18/etl/fase0_ddl.py)
Ejecuta el DDL y verifica la creación:

| Paso | Resultado |
|---|---|
| Parseo del DDL | 28 sentencias SQL extraídas de `olimpiada2s.sql` |
| Ejecución | DROP DATABASE → CREATE DATABASE → 12 CREATE TABLE → 12 CREATE INDEX → INSERT semilla |
| Verificación tablas | 12/12 tablas confirmadas |
| Verificación medallas | 4/4 registros: Gold(1), Silver(2), Bronze(3), NA(4) |

### Resultado de ejecución

```
Script DDL ejecutado exitosamente (28 sentencias)
12 tablas creadas: pais, noc, sede, olimpiada, atleta, deporte,
                   disciplina, evento, equipo, medalla, participacion,
                   poblacion_pais
Semilla de medallas: Gold(1), Silver(2), Bronze(3), NA(4)
```

### Archivos creados/modificados

| Archivo | Acción |
|---|---|
| `etl/utils.py` | ✨ Creado |
| `etl/fase0_ddl.py` | ✨ Creado |
| `aclaracionesTecnicas.md` | 🔧 Corregido (INT NULL en lugar de NOT NULL para disciplina/evento FKs) |
| `decisiones_tecnicas.md` | ✨ Creado (15 decisiones técnicas documentadas) |

---

## Fase 1: Tablas Dimensionales (`pais`, `noc`, `poblacion_pais`) ✅

### Qué se hizo

Se creó el script [`fase1_dimensionales.py`](file:///d:/Proyectos%20U/Bases%202/Proyecto%201/SBD2B_PROYECT1_2S2026_G18/etl/fase1_dimensionales.py) y se mejoró [`utils.py`](file:///d:/Proyectos%20U/Bases%202/Proyecto%201/SBD2B_PROYECT1_2S2026_G18/etl/utils.py) con `resolve_data_file()`:

1. **Carga de `pais`:**
   - Ingesta desde `populations.csv` (Banco Mundial) usando código ISO de 3 letras (`ABW`, `AFE`, `AFG`, `AFW`, `AGO`).
   - Clasificación de agregados regionales con `region = 'Agregado Regional'` (cumpliendo Regla 4 y 7 de no descartar datos).
   - Complemento desde `noc_regions.csv` incorporando entidades como `AHO` (Curacao / Netherlands Antilles), `ALB`, `ALG`, `AND`.
   - Total resultante: **9 países/territorios**.

2. **Carga de `noc`:**
   - Ingesta desde `noc_regions.csv` mapeando código NOC, nombre oficial y notas.
   - Resolución jerárquica de la clave foránea `id_pais` mediante caché en memoria: código exacto → nombre normalizado → nombre alternativo.
   - Total resultante: **5 comités olímpicos**, 100% vinculados a su respectivo `id_pais`.

3. **Carga de `poblacion_pais`:**
   - Transformación de la matriz ancha (64 columnas anuales de 1960 a 2023) a formato relacional largo mediante `pandas.melt()`.
   - Inserción por lotes (`executemany`) omitiendo valores nulos.
   - Total resultante: **320 registros demográficos** (5 países × 64 años).

4. **Documentación:**
   - Registradas decisiones **DT-016**, **DT-017** y **DT-018** en [`decisiones_tecnicas.md`](file:///d:/Proyectos%20U/Bases%202/Proyecto%201/SBD2B_PROYECT1_2S2026_G18/decisiones_tecnicas.md).

### Resultado de ejecución

```
Tablas cargadas:
- pais: 9 registros
- noc: 5 registros (100% vinculados a id_pais)
- poblacion_pais: 320 registros (rango 1960 - 2023)
Violaciones de FK: 0
```

