# FASE 3: MIGRACIÓN, MODELADO NOSQL E INTEGRACIÓN EN MONGODB ATLAS
**Proyecto: Base de Datos Unificada de Juegos Olímpicos (1896–2024)**  
**Curso: Sistemas de Bases de Datos 2 — USAC**  
**Grupo 18**  

---

## 1. Descripción General del Proyecto

Esta tercera fase implementa la migración integral de la base de datos histórica de los Juegos Olímpicos desde un esquema relacional normalizado en MySQL hacia una base de datos documental en **MongoDB Atlas**.

El diseño no replica las 12 tablas relacionales, sino que adopta una **arquitectura desnormalizada por caso de uso** organizada en torno a cuatro colecciones optimizadas para responder a las consultas analíticas de atletas y países en orden de milisegundos sin requerir operaciones `$lookup` lentas:

* **`ediciones` (63 documentos):** Ediciones olímpicas históricas con la sede y el país organizador embebidos.
* **`paises` (487 documentos):** Catálogo de naciones con sus códigos NOCs y el historial completo de sedes albergadas.
* **`atletas` (190,471 documentos):** Fichas biográficas con `nombre_norm` y el arreglo de `tokens` para búsqueda rápida multikey.
* **`resultados` (380,548 documentos):** Hechos transaccionales aplanados que consolidan atleta, olimpiada, país, deporte, disciplina, evento, posición y medalla.

---

## 2. Inventario y Función de los Scripts de Python (`scripts/`)

El pipeline se encuentra modularizado en scripts ejecutables independientes:

### Script: `test_conexion.py`
* **Función:** Verificación de conectividad y handshake de red.
* **Detalle:** Lee las variables de entorno desde `.env`, comprueba la conexión a MySQL local ejecutando `SELECT DATABASE(), VERSION()` y emite un ping administrativo a MongoDB Atlas (`client.admin.command('ping')`) con timeout de 5 segundos.

### Script: `00_auditoria_censo_mysql.py`
* **Función:** Auditoría censal y verificación de integridad referencial en MySQL previo a la migración.
* **Detalle:** Verifica los conteos de las 12 tablas relacionales (613,078 filas consolidadas) y audita 13 relaciones de clave foránea certificando cero tuplas huérfanas antes de iniciar la carga.

### Script: `03_prueba_volumetria_10k.py`
* **Función:** Prueba piloto de volumetría y dimensionamiento de almacenamiento.
* **Detalle:** Carga un lote de 10,000 participaciones desnormalizadas en Atlas, consulta las estadísticas físicas del motor WiredTiger (`collStats`) y proyecta formalmente el uso de almacenamiento total (~139 MB frente al límite de 512 MB de la capa gratuita M0).

### Script: `01_cargar_ediciones_paises.py`
* **Función:** Extracción, transformación y carga de las colecciones dimensionales de contexto.
* **Detalle:** Extrae de MySQL las 63 ediciones olímpicas embebiendo su sede, y los 487 países calculando en memoria los arreglos `sedes_historicas` y `nocs`. Inserta ambos conjuntos en Atlas y valida documentos de muestra.

### Script: `02_cargar_atletas.py`
* **Función:** Extracción, transformación y carga masiva de los 190,471 atletas.
* **Detalle:** Extrae atletas en lotes de 20,000 registros, genera el campo `nombre_norm` mediante normalización Unicode NFKD y el arreglo de `tokens` para búsqueda por palabras clave, inserta con `ordered=False` y valida el índice multikey con `explain()` (tiempo de respuesta de 0 ms).

### Script: `04_cargar_resultados.py`
* **Función:** Extracción y carga masiva de las 380,548 participaciones aplanadas en la colección `resultados`.
* **Detalle:** Implementa paginación por clave primaria (*keyset pagination*: `WHERE p.id_participacion > last_id`) en bloques de 15,000 registros para garantizar tiempo constante $O(1)$ por lote. Aplana las 9 tablas relacionales e inserta en Atlas, validando con `explain()` los índices compuestos B-Tree.

### Script: `05_reconciliacion_cruzada.py`
* **Función:** Auditoría y certificación de paridad censal al 100% (MySQL vs MongoDB Atlas).
* **Detalle:** Conecta simultáneamente a ambos motores, compara conteos globales de las 4 colecciones y la distribución de medallas (Oro, Plata, Bronce, NA), certifica los 15 índices activos y emite el dictamen final.

### Script: `03_cargar_datos_mongo.py`
* **Función:** Módulo central de utilidades ETL.
* **Detalle:** Contiene las funciones compartidas de limpieza de tipos BSON (`clean_val`), normalización de nombres con corrección ortográfica de apellidos (`normalize_name`), y constructores de documentos BSON.

---

## 3. Secuencia de Ejecución para Reproducir el Proyecto

Para reproducir el pipeline completo desde una instalación limpia:

### Paso 1: Configurar Variables de Entorno
Copiar el archivo `.env.example` como `.env` dentro del directorio `Fase3/` y definir las credenciales:
```env
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=admin
MYSQL_DB=olimpiadas

MONGO_URI=mongodb+srv://<usuario>:<password>@<cluster>.mongodb.net/olimpiadas?retryWrites=true&w=majority
MONGO_DB=olimpiadas
```

### Paso 2: Crear Colecciones e Índices en MongoDB Atlas
Ejecutar el script de índices desde `mongosh`:
```bash
mongosh "<MONGO_URI>" --file scripts/01_crear_colecciones_indices.js
```

### Paso 3: Ejecución Secuencial del Pipeline ETL
Ejecutar los scripts de carga en orden cronológico:

```bash
# 1. Verificar conectividad
python scripts/test_conexion.py

# 2. Auditar base relacional de origen (MySQL)
python scripts/00_auditoria_censo_mysql.py

# 3. Cargar colecciones dimensionales (ediciones y paises)
python scripts/01_cargar_ediciones_paises.py

# 4. Cargar atletas masivos con tokens
python scripts/02_cargar_atletas.py

# 5. Cargar participaciones masivas aplanadas (resultados)
python scripts/04_cargar_resultados.py

# 6. Ejecutar reconciliación cruzada final
python scripts/05_reconciliacion_cruzada.py
```

---

## 4. Estado de Censos Oficiales en MongoDB Atlas

El clúster oficial en MongoDB Atlas cuenta con los censos finales certificados:

* **Colección `ediciones`:** **63 documentos** (100% de ediciones olímpicas de 1896 a 2024).
* **Colección `paises`:** **487 documentos** (100% de países con sedes históricas y comités NOCs).
* **Colección `atletas`:** **190,471 documentos** (100% de atletas con fichas biográficas y tokens de búsqueda).
* **Colección `resultados`:** **380,548 documentos** (100% de participaciones aplanadas con medallas).

---

## 5. Documentación Complementaria

* [[doc/ARQUITECTURA_ETL_Y_SCRIPTS.md](file:///d:/Proyectos%20U/Bases%202/Proyecto%201/SBD2B_PROYECT1_2S2026_G18/Fase3/doc/ARQUITECTURA_ETL_Y_SCRIPTS.md)]: Manual técnico detallado de desnormalización, justificación de arquitectura y diseño documental.
* [[doc/INFORME_VOLUMETRIA_ATLAS.md](file:///d:/Proyectos%20U/Bases%202/Proyecto%201/SBD2B_PROYECT1_2S2026_G18/Fase3/doc/INFORME_VOLUMETRIA_ATLAS.md)]: Informe técnico de dimensionamiento físico, métricas WiredTiger y viabilidad frente al límite de 512 MB.
* [[logs/](file:///d:/Proyectos%20U/Bases%202/Proyecto%201/SBD2B_PROYECT1_2S2026_G18/Fase3/logs/)]: Directorio con las bitácoras fechadas de cada ejecución.

---
*Grupo 18 — Sistemas de Bases de Datos 2.*
