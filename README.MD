# Olympics Data Engineering — Pipeline ETL, Aseguramiento de Calidad (Data QA), Respaldos y Migración NoSQL
> **Portafolio de Bases de Datos Relacionales (MySQL), Scripts SQL, Pruebas de Integridad de Datos y Continuidad Operativa**  
> Proyecto integral dividido en **3 Fases** que abarca desde la extracción, limpieza y auditoría relacional de más de **660,000 registros históricos** en MySQL (Fase 1), pasando por estrategias de respaldo completo/diferencial y pruebas de restauración (Fase 2), hasta la migración y conciliación hacia esquemas documentales en MongoDB (Fase 3).

[![Database](https://img.shields.io/badge/RDBMS-MySQL%208.0%20(3NF)-orange?logo=mysql)](olimpiada2s.sql)
[![ETL Pipeline](https://img.shields.io/badge/ETL%20%26%20Data%20QA-Python%20%7C%20Pandas-blue?logo=python)](etl/)
[![Data Integrity](https://img.shields.io/badge/FK%20Audit-0%20Orphan%20Records-brightgreen)](#fase-1-ingeniería-etl-calidad-de-datos-y-modelado-relacional-en-mysql)
[![Backup & Recovery](https://img.shields.io/badge/DRP%20Testing-Full%20%26%20Differential%20Backups-informational)](#fase-2-estrategias-de-respaldo-completo-y-diferencial-y-pruebas-de-recuperación)
[![NoSQL Migration](https://img.shields.io/badge/NoSQL%20Migration-MongoDB-47A248?logo=mongodb)](#fase-3-migración-a-base-de-datos-nosql-mongodb-y-conciliación)


---

## Estructura General del Proyecto por Fases

| Fase / Carpeta | Enfoque Técnico Principal | Tecnologías Clave |
| :--- | :--- | :--- |
| **Fase 1** | Extracción, limpieza (ETL), deduplicación de entidades, modelado 3NF (12 tablas), Stored Procedures y auditoría SQL. | MySQL 8.0, Python, Pandas, SQL DDL/DML |
| **Fase 2** | Cargas incrementales por lotes, ejecución de Backups Completos y Diferenciales por consola, restauración y validación de integridad post-recuperación. | MySQL CLI, Scripts de Backup/Restore, SQL de Control |
| **Fase 3** | Migración de datos relacionales saneados hacia arquitectura documental NoSQL, indexación y consultas parametrizadas equivalentes. | MongoDB, Python (`pymongo`), JSON/BSON |

---

## Fase 1: Ingeniería ETL, Calidad de Datos y Modelado Relacional en MySQL

Consolidación de **4 fuentes heterogéneas y no estandarizadas** (Olympedia crudo `bios1.csv` y `results1.csv`, Kaggle *120 Years of Olympic History*, Kaggle *Summer Olympics 1896–2024*, series del Banco Mundial `populations.csv` y DataCamp Datalab como fuente testigo de validación cruzada) hacia un único esquema relacional normalizado en **Tercera Forma Normal (3NF)**.

### 1.1. Pipeline Modular de Limpieza y Transformación (8 Etapas en `etl/`)
* **`utils.py` & `fase0_ddl.py`:** Reparación universal de corrupción binaria por doble codificación (*Mojibake* `CP1252` $\rightarrow$ `UTF-8`), eliminación de caracteres basura y ejecución automatizada de 28 sentencias DDL ([`olimpiada2s.sql`](olimpiada2s.sql)) creando **12 tablas en 3NF** y **12 índices secundarios de rendimiento**.
* **`fase1_dimensionales.py`:** Desacoplamiento entre entidades políticas (`pais` bajo estándar ISO 3166-1 alpha-3) y deportivas (`noc`), preservación de agregados regionales y pivoteo de 64 columnas anuales (1960–2023) a series de tiempo relacionales en `poblacion_pais` mediante `pandas.melt()`.
* **`fase2_atletas.py`:** Procesamiento de la fuente biográfica cruda preservando las 16 columnas originales (apodos, títulos, afiliaciones, nombres nativos), parseo con expresiones regulares hacia formato estándar `DATE` (`YYYY-MM-DD`), separación multinivel de ciudades/regiones de nacimiento e integración georreferenciada (`latitud`, `longitud`).
* **`fase3_contexto.py` & `fase4_participacion_base.py`:** Resolución de sedes históricas, implementación de la regla de **"Disciplina Puente"** para garantizar integridad en la jerarquía `deporte -> disciplina -> evento`, detección booleana de empates (`es_empate = TRUE` cuando la posición incluye `=`) y homologación del catálogo de medallas (`Gold`, `Silver`, `Bronze`, `NA`).
* **`fase5_enriquecimiento.py` & `fase6_actualizacion.py`:** Motor de **deduplicación de identidades en memoria** mediante tupla normalizada `(nombre_normalizado, sexo, anio_nacimiento_aprox)`, diccionario de restauración fonética y algoritmo de **solapamiento léxico de tokens de eventos (`extract_event_tokens`)**. Esto permitió actualizar métricas físicas (`edad`, `altura_reg`, `peso_reg`) e incorporar los resultados de Tokio 2020 y París 2024 sin duplicar participaciones ni inflar el medallero histórico.

### 1.2. Aseguramiento de Calidad de Datos (Data QA) y Procedimientos Almacenados
* **Auditoría Automatizada (`fase7_validacion.py`):** Censo global sobre el volumen de producción (**234,621 atletas** y **660,924 participaciones**) y ejecución de **13 consultas SQL de auditoría de claves foráneas** que certificaron **0 registros huérfanos** (100% de integridad referencial).
* **Stored Procedures Analíticos (`stored_procedures.py`):**
  1. `sp_consultar_atleta(p_nombre, p_anio, p_deporte, p_pais)`: Búsqueda flexible indexada que retorna la ficha biográfica consolidada y el historial detallado de participaciones filtradas.
  2. `sp_consultar_pais(p_pais, p_anio_inicio, p_anio_fin, p_solo_medallas)`: Verifica si el país ha sido sede olímpica (listando ciudades y años) y calcula el medallero histórico acumulado (Oro, Plata, Bronce) agrupado por edición y disciplina para prevenir volcados masivos en memoria.

---

## Fase 2: Estrategias de Respaldo (Completo y Diferencial) y Pruebas de Recuperación

Aplicación de prácticas de continuidad operativa y pruebas de recuperabilidad (*Disaster Recovery Testing*) sobre la base de datos relacional mediante ejecuciones desde línea de comandos (CLI):

* **Escenarios de Carga Incremental en 3 Rondas:**
  1. *Carga por Año:* Ingesta segmentada por ediciones olímpicas (ej. Río 2016, Tokio 2020, París 2024).
  2. *Carga por Deporte:* Ingesta segmentada por disciplinas y eventos específicos.
  3. *Carga por Deportista:* Ingesta longitudinal del historial de atletas específicos a través de múltiples ediciones.
* **Ejecución de Backups Completos y Diferenciales:** Generación de un **Respaldo Completo (*Full Backup*)** tras la carga base inicial y ejecución de **Respaldos Diferenciales (*Differential Backups*)** tras cada ronda de carga sucesiva, registrando estampas de tiempo, tamaño de artefactos y nivel de fragmentación de tablas.
* **Simulación de Desastre y Validación de Integridad Post-Restauración:** Eliminación total de la base de datos, ejecución de secuencias de restauración (Full + Diferencial), medición comparativa de tiempos de recuperación (RTO) y ejecución de scripts SQL de auditoría (`SELECT COUNT(*)` y verificación de muestras por tabla) para certificar **0% de pérdida de datos transaccionales**.

---

## Fase 3: Migración a Base de Datos NoSQL (MongoDB) y Conciliación

Modernización y traslado del repositorio relacional unificado de la Fase 1 hacia una arquitectura orientada a documentos en **MongoDB**, garantizando la paridad de la información entre ambos motores:

* **Diseño Documental y Carga Automatizada:** Transformación de las entidades relacionales hacia colecciones JSON/BSON optimizadas en MongoDB, integrando documentos embebidos para datos biográficos, sedes y participaciones, y creando índices compuestos para acelerar las búsquedas.
* **Pruebas de Migración y Conciliación Cruzada:** Verificación de conteos totales de documentos, validación de ausencia de truncamiento de campos y subsanación de casos borde entre el esquema MySQL y las colecciones de MongoDB.
* **Métodos de Consulta Parametrizados en NoSQL:** Implementación de scripts de consulta de alto rendimiento en MongoDB equivalentes a los procedimientos almacenados de la Fase 1 (búsqueda parametrizada por atleta y reporte histórico/medallero por país con filtros de año y deporte), garantizando tiempos de respuesta inmediatos en consola.

---

## Guía Rápida de Reproducción (Fase 1 - Pipeline ETL y Auditoría MySQL)

1. **Instalar dependencias:**
   ```bash
   pip install mysql-connector-python pandas openpyxl
   ```
2. **Configurar credenciales MySQL** en [`etl/utils.py`](etl/utils.py) (`host`, `user`, `password`).
3. **Ejecutar el pipeline secuencial y la suite de validación QA:**
   ```bash
   python etl/fase0_ddl.py
   python etl/fase1_dimensionales.py
   python etl/fase2_atletas.py
   python etl/fase3_contexto.py
   python etl/fase4_participacion_base.py
   python etl/fase5_enriquecimiento.py
   python etl/fase6_actualizacion.py
   python etl/fase7_validacion.py
   python etl/stored_procedures.py
   ```

---

## Documentación del Repositorio
* [`MANUAL_PROYECTO_G18.md`](MANUAL_PROYECTO_G18.md): Manual integral de arquitectura, inventario de archivos y guía de reproducción.
* [`decisiones_tecnicas.md`](decisiones_tecnicas.md): Bitácora detallada de las 27 decisiones de ingeniería de datos y reglas de negocio (DT-001 a DT-027).
* [`aclaracionesTecnicas.md`](aclaracionesTecnicas.md) & [`Explicacion.md`](Explicacion.md): Especificación técnica del modelo 3NF, reglas de cátedra y diccionarios de transformación.
* [`DiagramaER.png`](DiagramaER.png): Diagrama Entidad-Relación de las 12 tablas del sistema.