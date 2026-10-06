# MANUAL INTEGRAL DE ARQUITECTURA, REPRODUCCIÓN Y AUDITORÍA ETL
**Proyecto: Base de Datos Unificada de Juegos Olímpicos (1896–2024)**  
**Curso: Sistemas de Bases de Datos 2 — 2do. Semestre 2026 — USAC**  
**Grupo 18**  
* **Persona 1:** Yulianne Nicole López Elías — 202300659 (Modelo E/R y DDL)  
* **Persona 2:** Álvaro Gabriel Ceballos Gil — 202300673 (Ingeniería de Datos, Limpieza y Carga ETL)  
* **Persona 3:** Ottoniel Fabricio Vásquez Pineda — 202307820 (Procedimientos Almacenados)  

---

## 1. Mapa e Inventario de Archivos del Repositorio

A continuación se detalla la función de cada archivo y carpeta dentro del proyecto:

### A. Archivos en la Raíz
| Archivo | Rol y Descripción |
|---|---|
| [`README.md`](file:///d:/Proyectos%20U/Bases%202/Proyecto%201/SBD2B_PROYECT1_2S2026_G18/README.md) | Enunciado oficial del proyecto con los requerimientos de la cátedra (incisos a, b, c, d, e). |
| [`olimpiada2s.sql`](file:///d:/Proyectos%20U/Bases%202/Proyecto%201/SBD2B_PROYECT1_2S2026_G18/olimpiada2s.sql) | Script maestro SQL: contiene el DDL de creación de la base `olimpiadas`, las 12 tablas en 3NF, llaves primarias/foráneas, 12 índices de rendimiento, semilla de medallas y todas las consultas de control/auditoría. |
| [`DiagramaER.png`](file:///d:/Proyectos%20U/Bases%202/Proyecto%201/SBD2B_PROYECT1_2S2026_G18/DiagramaER.png) | Diagrama Entidad-Relación consolidado que ilustra las 12 entidades del esquema normalizado. |
| [`Datasets.xlsx`](file:///d:/Proyectos%20U/Bases%202/Proyecto%201/SBD2B_PROYECT1_2S2026_G18/Datasets.xlsx) | Libro Excel con las 10 hojas de datos originales correspondientes a las 4 fuentes. |
| [`DataCSV.py`](file:///d:/Proyectos%20U/Bases%202/Proyecto%201/SBD2B_PROYECT1_2S2026_G18/DataCSV.py) | Script utilitario que lee `Datasets.xlsx` y exporta las primeras 15 filas de cada hoja hacia la carpeta `data_samples/` para desarrollo y pruebas. |
| [`decisiones_tecnicas.md`](file:///d:/Proyectos%20U/Bases%202/Proyecto%201/SBD2B_PROYECT1_2S2026_G18/decisiones_tecnicas.md) | Bitácora técnica viva con 25 decisiones de arquitectura (DT-001 a DT-025) que justifican el tratamiento de datos y casos borde. |
| [`aclaracionesTecnicas.md`](file:///d:/Proyectos%20U/Bases%202/Proyecto%201/SBD2B_PROYECT1_2S2026_G18/aclaracionesTecnicas.md) | Documento con las respuestas técnicas y reglas de negocio acordadas para la cátedra. |
| [`Explicacion.md`](file:///d:/Proyectos%20U/Bases%202/Proyecto%201/SBD2B_PROYECT1_2S2026_G18/Explicacion.md) | Documento explicativo de entrega del grupo con antecedentes, división de trabajo y las 15 directrices del catedrático. |
| [`implementation_plan.md`](file:///d:/Proyectos%20U/Bases%202/Proyecto%201/SBD2B_PROYECT1_2S2026_G18/implementation_plan.md) | Plan de trabajo estructurado en 8 fases consecutivas (Fase 0 a Fase 7) para la ingeniería ETL. |

### B. Carpeta `data_samples/` (Insumos de Carga)
Contiene las muestras de 15 filas generadas por `DataCSV.py`. Los scripts están diseñados para operar de forma idéntica con estos archivos o con los CSVs completos:
* `bios_sample.csv`: Insumo crudo maestro de atletas (16 columnas con afiliaciones, apodos, títulos, etc.).
* `results.csv_sample.csv`: Insumo crudo de resultados olímpicos históricos de Olympedia.
* `bios_locs_sample.csv`: Coordenadas georreferenciadas (`lat`, `long`) cruzadas por `athlete_id`.
* `noc_regions_sample.csv`: Catálogo de comités olímpicos del COI, regiones y notas territoriales.
* `populations_sample.csv`: Matriz ancha con series demográficas anuales del Banco Mundial (1960–2023).
* `athlete_events_sample.csv`: Dataset Kaggle 120 Years (1896–2016) con edad, altura y peso.
* `olympics_dataset.csv`: Dataset Kaggle Summer (1896–2024) con Tokio 2020 y París 2024.
* `athlete_events_datalab_sample.csv`: Espejo de Fuente 4 para validación cruzada.
* `bios_clean_sample.csv` y `results_clean_sample.csv`: Referencias procesadas por Keith Galli para comparar paridad algorítmica.

### C. Carpeta `etl/` (Scripts del Pipeline de Persona 2)
* [`utils.py`](file:///d:/Proyectos%20U/Bases%202/Proyecto%201/SBD2B_PROYECT1_2S2026_G18/etl/utils.py): Conexión a MySQL, saneamiento de mojibake (`fix_mojibake`), normalización de nombres para deduplicación (`normalize_name`) y resolución automática de rutas de datos (`resolve_data_file`).
* [`fase0_ddl.py`](file:///d:/Proyectos%20U/Bases%202/Proyecto%201/SBD2B_PROYECT1_2S2026_G18/etl/fase0_ddl.py): Ejecuta el DDL de `olimpiada2s.sql`, crea la base de datos, 12 tablas, 12 índices y la semilla de medallas.
* [`fase1_dimensionales.py`](file:///d:/Proyectos%20U/Bases%202/Proyecto%201/SBD2B_PROYECT1_2S2026_G18/etl/fase1_dimensionales.py): Carga y desnormaliza `pais`, `noc` y `poblacion_pais` (con `pandas.melt`).
* [`fase2_atletas.py`](file:///d:/Proyectos%20U/Bases%202/Proyecto%201/SBD2B_PROYECT1_2S2026_G18/etl/fase2_atletas.py): Limpia la data biográfica cruda, desglosa ubicaciones de nacimiento, normaliza fechas a formato `DATE` de MySQL y enriquece con coordenadas WGS84 para poblar `atleta`.
* [`fase3_contexto.py`](file:///d:/Proyectos%20U/Bases%202/Proyecto%201/SBD2B_PROYECT1_2S2026_G18/etl/fase3_contexto.py): Pobla `sede`, `olimpiada`, `deporte`, `disciplina`, `evento` y `equipo`, aplicando la regla de disciplina puente y catálogo histórico de sedes.
* [`fase4_participacion_base.py`](file:///d:/Proyectos%20U/Bases%202/Proyecto%201/SBD2B_PROYECT1_2S2026_G18/etl/fase4_participacion_base.py): Carga las participaciones base históricas de Olympedia en la tabla transaccional de hechos `participacion`.
* [`fase5_enriquecimiento.py`](file:///d:/Proyectos%20U/Bases%202/Proyecto%201/SBD2B_PROYECT1_2S2026_G18/etl/fase5_enriquecimiento.py): Cruza Kaggle 120 Years para actualizar `edad`, `altura_reg` y `peso_reg`, incorpora nuevos atletas exclusivos y valida con Fuente 4.
* [`fase6_actualizacion.py`](file:///d:/Proyectos%20U/Bases%202/Proyecto%201/SBD2B_PROYECT1_2S2026_G18/etl/fase6_actualizacion.py): Integra la Fuente 3 con deduplicación por tokens e incorpora participaciones y medallistas.
* [`fase7_validacion.py`](file:///d:/Proyectos%20U/Bases%202/Proyecto%201/SBD2B_PROYECT1_2S2026_G18/etl/fase7_validacion.py): Suite de auditoría que verifica las 13 relaciones foráneas, censo de tablas, calidad de datos y simula los Stored Procedures.

### D. Carpeta `walkthroughs/`
Contiene la bitácora paso a paso y evidencia fotográfica/textual de cada fase ejecutada (`walkthroughFase0.md` hasta `walkthroughFase7.md`).

---

## 2. Arquitectura por Fases: ¿Qué se hizo y Por Qué?

### Fase 0: DDL y Utilidades Base
* **¿Qué se hizo?:** Se implementó `fase0_ddl.py` para parsear y ejecutar `olimpiada2s.sql` en MySQL, creando el esquema `olimpiadas`, las 12 tablas en 3NF, 12 índices y la semilla de 4 medallas (`Gold`, `Silver`, `Bronze`, `NA`). Se construyó `utils.py` con funciones centralizadas.
* **¿Por qué?:** Regla 10 del catedrático (cero asistentes gráficos). Garantiza que la estructura nazca limpia, reproducible y con codificación `utf8mb4_unicode_ci`.

### Fase 1: Tablas Dimensionales (`pais`, `noc`, `poblacion_pais`)
* **¿Qué se hizo?:** Se cargaron los catálogos territoriales y deportivos desde `populations.csv` y `noc_regions.csv`. La matriz ancha de 64 columnas anuales (1960–2023) se transformó a formato largo mediante `pandas.melt()`.
* **¿Por qué?:**
  * Desacoplamiento de `pais` (entidad geográfica ISO) de `noc` (entidad deportiva COI), permitiendo delegaciones sin país único como `URS`, `EUN` o `ROT` (DT-016).
  * Reglas 4 y 7: Se preservaron los agregados supranacionales (*"World"*, *"Latin America"*) bajo `region = 'Agregado Regional'` en vez de descartarlos (DT-017).
  * 3NF: Normalizar la población por año en tuplas `(id_pais, anio, poblacion)` permite consultas per cápita en los Stored Procedures (DT-018).

### Fase 2: Limpieza de `bios1.csv` y Carga de `atleta`
* **¿Qué se hizo?:** Se tomó la data biográfica cruda de Olympedia como insumo maestro. Se extrajeron fechas con regex a formato MySQL `DATE` (`YYYY-MM-DD` o `YYYY-01-01`), se desglosó el lugar de nacimiento (`ciudad_nac`, `region_nac`, `id_pais_nac`), se aislaron medidas métricas (`altura_cm`, `peso_kg`) y se enriqueció con coordenadas WGS84 (`latitud`, `longitud`) cruzando con `bios_locs.csv`.
* **¿Por qué?:**
  * Directriz del catedrático: Procesar data cruda como fuente primaria. El notebook de Keith Galli descartó 9 columnas valiosas; nuestro pipeline las rescató (`apodo`, `titulo`, `afiliacion`, `nombre_original`, `orden_nombre`) cumpliendo la Regla 12 (DT-001, DT-019).
  * `atleta.id_externo` almacena el ID de Olympedia para trazabilidad.

### Fase 3: Tablas de Contexto (`sede`, `olimpiada`, `deporte`, `disciplina`, `evento`, `equipo`)
* **¿Qué se hizo?:** Se estructuró la jerarquía de 3 niveles (`deporte -> disciplina -> evento`). Se implementó un catálogo histórico oficial para resolver las ciudades sede de las ediciones de `results1.csv`. Para eventos individuales con `Team` vacío, se asignó la delegación nacional según el `NOC`.
* **¿Por qué?:**
  * `results1.csv` no contiene la ciudad sede, solo el texto `"1912 Summer Olympics"`. El catálogo oficial (DT-022) asegura que el 100% de las ediciones tengan sede vinculada sin importar el tamaño de la muestra.
  * Jerarquía deportiva (DT-003): Kaggle solo trae `Sport` y `Event` (omite disciplina). La **disciplina puente** (`disciplina.nombre = deporte.nombre`) garantiza que ningún evento quede huérfano.
  * `equipo.nombre` es `NOT NULL` en el DDL; asignar el país a atletas individuales (DT-023) cumple la integridad del esquema.

### Fase 4: Participación Base (Fuente 1: Olympedia)
* **¿Qué se hizo?:** Se insertaron las participaciones históricas en la tabla de hechos `participacion`. Se mapeó `Pos` detectando empates (bandera `es_empate = TRUE` si contenía `=`), se homologaron medallas nulas obligatoriamente a `'NA'` y se mantuvo idempotencia en memoria.
* **¿Por qué?:**
  * Respeto estricto del orden de inserción relacional (DT-008).
  * Tabla `medalla` (DT-010): Almacenar preseas vacías como `'NA'` acelera las agrupaciones e indexaciones de podio para la Persona 3 sin lidiar con nulos trivalentes en SQL.

### Fase 5: Enriquecimiento con Fuentes 2 y 4 (Kaggle 120 Years)
* **¿Qué se hizo?:** Se cruzó `athlete_events.csv` aplicando la matching key `(nombre_normalizado, sexo, anio_nacimiento_aprox)`. Se actualizaron las participaciones con `edad`, `altura_reg` y `peso_reg` registrados en cada edición. Se insertaron nuevos atletas exclusivos de Kaggle (`id_externo = NULL`) y se validó la paridad con Fuente 4.
* **¿Por qué?:**
  * Olympedia no contiene edad ni medidas por edición; Kaggle aporta esa granularidad histórica (DT-007).
  * DT-015: Fuente 4 (DataCamp) es idéntica a Fuente 2; procesarla de forma independiente crearía millones de duplicados, por lo que se empleó como validación cruzada.

### Fase 6: Actualización con Fuente 3 (Kaggle Summer 1896–2024)
* **¿Qué se hizo?:** Se integró `olympics_dataset.csv`. Se implementó deduplicación por subconjunto de tokens de nombres (reconociendo que `"Gunnar Aaby"` es `"Gunnar Nielsen Aaby"` y `"Edgar Aabye"` es `"Edgar Lindenau Aabye"`). Se actualizaron preseas y se insertaron atletas no existentes.
* **¿Por qué?:**
  * Incorpora la cobertura de ediciones recientes (Tokio 2020 y París 2024) que no figuraban en las fuentes históricas anteriores (DT-007, DT-025).

### Fase 7: Validación Cruzada y Cierre ETL
* **¿Qué se hizo?:** Auditoría automatizada de las 13 claves foráneas, censo completo de las 12 tablas, verificación de calidad de datos (0 bullets, 0 mojibake) y simulación de las consultas de los Stored Procedures.
* **¿Por qué?:** Entrega certificada de Persona 2 garantizando que Persona 3 reciba una base de datos 100% íntegra y sin fallas estructurales.

---

## 3. Explicación de los Scripts y Consultas SQL en `olimpiada2s.sql`

El archivo [`olimpiada2s.sql`](file:///d:/Proyectos%20U/Bases%202/Proyecto%201/SBD2B_PROYECT1_2S2026_G18/olimpiada2s.sql) contiene tanto el diseño del esquema como todas las consultas de verificación ejecutadas a lo largo del proyecto:

### Bloque 1: Definición DDL (Líneas 1 a 282)
* `DROP DATABASE / CREATE DATABASE olimpiadas`: Crea la base con cotejo `utf8mb4_unicode_ci`.
* Creación de las 12 tablas: `pais`, `noc`, `sede`, `olimpiada`, `atleta`, `deporte`, `disciplina`, `evento`, `equipo`, `medalla`, `participacion`, `poblacion_pais`.
* Restricciones `UNIQUE KEY`: Evitan duplicar códigos de país, NOCs, ciudades por país, ediciones por año/temporada y nombres de equipos.
* Creación de 12 índices (`CREATE INDEX`): Indexan nombres de atletas, códigos de país, NOCs, llaves foráneas de participación y años de población para optimizar los Stored Procedures de Persona 3.
* Semilla de catálogo `medalla`: Inserta exactamente `('Gold', 'Silver', 'Bronze', 'NA')`.

### Bloque 2: Consultas Demostrativas Iniciales (Líneas 198 a 248)
* `SHOW FULL TABLES`: Confirma la existencia de las 12 tablas relacionales.
* Consulta de comités vinculados: Comprueba mediante `JOIN noc n JOIN pais p` que los códigos NOC apuntan a su país correspondiente.
* Resumen de población: Demuestra el pivoteo de 1960 a 2023 con `COUNT(*)`, `MIN(anio)`, `MAX(anio)` y valores poblacionales extremos por país.

### Bloque 3: Consultas de Verificación Fase 2 — Atletas (Líneas 250 a 280)
* `CONTROL 1 (Métricas Globales)`: Calcula mediante sumatorias condicionales (`SUM(CASE WHEN...)`) el total de atletas con `id_externo`, sexo válido `'M'`/`'F'`, fechas de nacimiento parseadas, coordenadas WGS84 presentes, 0 bullets (`•`) y datos crudos preservados.
* `CONTROL 4 (Muestra Geográfica)`: Muestra 5 atletas con su fecha ISO, lugar de nacimiento cruzado con la tabla `pais`, medidas y coordenadas GPS redondeadas.

### Bloque 4: Consultas de Verificación Fase 3 — Contexto (Líneas 281 a 310)
* `Conteo de tablas de contexto`: `UNION ALL` que reporta los registros de `sede`, `olimpiada`, `deporte`, `disciplina`, `evento` y `equipo`.
* `Auditoría de 5 FKs de contexto`: Subconsultas que verifican que no existan sedes sin país, olimpiadas sin sede, disciplinas sin deporte, eventos sin disciplina ni equipos sin NOC (todas deben dar 0).
* `Muestra de Olimpiada -> Sede -> País`: `JOIN` que ilustra la edición olímpica, ciudad y país anfitrión.

### Bloque 5: Consultas de Verificación Fase 4 — Participaciones Base (Líneas 311 a 345)
* `Distribución de medallas`: Cuenta el total de participaciones y cuántas corresponden a Oro, Plata, Bronce o `'NA'`.
* `Auditoría de 5 FKs de participacion`: Verifica que ninguna participación apunte a un atleta, evento, olimpiada, equipo o medalla inexistente.
* `Muestra de hechos`: `JOIN` entre 5 tablas mostrando atleta, edición, evento, posición y medalla.

### Bloque 6: Consultas de Verificación Fase 5 — Enriquecimiento Kaggle (Líneas 346 a 380)
* `Métricas de enriquecimiento`: Comprueba los atletas nuevos de Kaggle (`id_externo IS NULL`) y cuántas participaciones poseen métricas físicas.
* `Muestra de métricas`: Despliega participaciones con `edad`, `altura_reg` y `peso_reg`.

### Bloque 7: Consultas de Verificación Fase 6 — Actualización Fuente 3 (Líneas 381 a 415)
* `Totales consolidados`: Reporta la suma total de atletas, participaciones, sedes, olimpiadas y eventos tras la tercera capa.
* `Medallero histórico acumulado`: Agrupación por tipo de medalla ordenada según podio.

### Bloque 8: Auditoría Integral Final y Simulaciones Fase 7 (Líneas 416 a 481)
* `CENSO GLOBAL (12 Tablas)`: `UNION ALL` que lista las 12 tablas con sus conteos definitivos.
* `AUDITORÍA DE LAS 13 CLAVES FORÁNEAS`: Verificación exhaustiva de todas las relaciones FK del sistema.
* `SIMULACIÓN sp_consultar_atleta`: Demuestra la consulta que extraerá la ficha biográfica del atleta (*Jean Borotra*) y su historial completo de participaciones mediante `JOIN` entre 7 tablas.
* `SIMULACIÓN sp_consultar_pais`: Demuestra la consulta que calculará el medallero histórico consolidado de un país (*FRA*) y si ha sido sede olímpica.

---

## 4. Guía Paso a Paso para Persona 1 y Persona 3 (Reproducción desde Cero)

Cualquier integrante del grupo puede clonar el repositorio y dejar su base de datos local exactamente en el mismo estado siguiendo estos pasos:

### Requisitos Previos
1. **Python 3.10+** instalado y en el PATH del sistema.
2. **MySQL Server 8.0+** corriendo localmente en el puerto 3306.
3. Instalar las dependencias de Python:
   ```bash
   pip install mysql-connector-python pandas openpyxl
   ```

### Paso 1: Configurar Credenciales de MySQL
Abrir el archivo [`etl/utils.py`](file:///d:/Proyectos%20U/Bases%202/Proyecto%201/SBD2B_PROYECT1_2S2026_G18/etl/utils.py) y ajustar las credenciales de conexión en el diccionario `DB_CONFIG` (líneas 24–32):
```python
DB_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'user': 'root',       # Tu usuario de MySQL
    'password': 'admin',  # Tu contraseña de MySQL
    'charset': 'utf8mb4',
    'collation': 'utf8mb4_unicode_ci',
    'use_unicode': True,
}
```

### Paso 2: Ejecución Secuencial del Pipeline ETL
Ejecutar en la terminal de comandos (PowerShell o Bash), situándose en la raíz del proyecto, los scripts en el orden cronológico estricto:

```bash
# 1. Crear la base de datos, 12 tablas, 12 índices y semilla
python etl/fase0_ddl.py

# 2. Cargar países, NOCs y series de población (1960-2023)
python etl/fase1_dimensionales.py

# 3. Limpiar bios cruda y poblar catálogo maestro de atletas
python etl/fase2_atletas.py

# 4. Cargar contexto: sedes, olimpiadas, deportes, disciplinas puente, eventos y equipos
python etl/fase3_contexto.py

# 5. Cargar participaciones base de Olympedia (Fuente 1)
python etl/fase4_participacion_base.py

# 6. Enriquecer con Kaggle (Fuente 2 y 4): métricas físicas y nuevos atletas
python etl/fase5_enriquecimiento.py

# 7. Actualizar con Fuente 3: resultados complementarios y medallistas
python etl/fase6_actualizacion.py

# 8. Ejecutar auditoría final de integridad y simulación de SPs
python etl/fase7_validacion.py
```

### Paso 3: Verificación en MySQL Workbench
Abrir MySQL Workbench, abrir el archivo [`olimpiada2s.sql`](file:///d:/Proyectos%20U/Bases%202/Proyecto%201/SBD2B_PROYECT1_2S2026_G18/olimpiada2s.sql) y ejecutar las consultas del bloque final (a partir de la línea 416). Se deben obtener exactamente estos resultados:

* **Censo de Tablas — Carga Completa Real (Producción):**
  * `pais`: 487
  * `noc`: 236
  * `poblacion_pais`: 16,930 (series demográficas 1960–2023)
  * `sede`: 45
  * `olimpiada`: 63 (1896 Atenas hasta 2024 París)
  * `atleta`: 234,621
  * `deporte`: 148
  * `disciplina`: 149
  * `evento`: 3,152
  * `equipo`: 20,845
  * `medalla`: 4
  * `participacion`: 660,924 (con 44,058 empates registrados)

* **Censo de Tablas — Muestra Ligera de Pruebas (`data_samples` de 15 filas):**
  * `pais`: 35 | `noc`: 21 | `poblacion_pais`: 960 | `sede`: 12 | `olimpiada`: 13 | `atleta`: 26 | `deporte`: 11 | `disciplina`: 11 | `evento`: 20 | `equipo`: 16 | `medalla`: 4 | `participacion`: 41

* **Auditoría de Claves Foráneas:** Las 13 relaciones de integridad referencial arrojan **0 huérfanas** (100% de consistencia relacional).

---

## 5. Recomendaciones para la Persona 3 (Stored Procedures)

Para la siguiente etapa, la Persona 3 puede apoyarse directamente en las consultas de simulación ya probadas en el Bloque 8 de `olimpiada2s.sql`:

1. **Procedimiento 1: `sp_consultar_atleta`**
   * **Parámetros recomendados:** `p_nombre VARCHAR(120)`, `p_anio SMALLINT` (opcional, `NULL`), `p_deporte VARCHAR(120)` (opcional, `NULL`), `p_pais VARCHAR(120)` (opcional, `NULL`).
   * **Lógica:** Consultar primero la ficha única de `atleta` y luego un segundo set de resultados con las participaciones filtradas. Utilizar el índice `idx_atleta_nombre` para que la búsqueda con `LIKE` responda de forma instantánea.

2. **Procedimiento 2: `sp_consultar_pais`**
   * **Parámetros recomendados:** `p_pais VARCHAR(120)` (código NOC o nombre), `p_anio_inicio SMALLINT`, `p_anio_fin SMALLINT`, `p_solo_medallas BOOLEAN`.
   * **Lógica:** Desplegar si ha sido sede consultando `sede` y `olimpiada`, y retornar el medallero agregado (Oro, Plata, Bronce) agrupado por edición y disciplina deportiva para evitar un `SELECT *` masivo durante la calificación en vivo.
