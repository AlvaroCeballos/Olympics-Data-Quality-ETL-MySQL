# ARQUITECTURA DEL PIPELINE ETL Y GUÍA DE SCRIPTS PYTHON
**Proyecto: Base de Datos Unificada de Juegos Olímpicos (1896–2024)**  
**Curso: Sistemas de Bases de Datos 2 — USAC**  
**Fase 3 — Integrante 2: Álvaro Gabriel Ceballos Gil (202300673)**  

---

## 1. ¿Qué es el Proceso ETL en esta Fase?

El proceso **ETL** (*Extract, Transform, Load* — Extracción, Transformación y Carga) es el puente entre el modelo relacional (MySQL en 3NF) y el modelo documental NoSQL (MongoDB Atlas). 

No se trata de una simple exportación de tablas, sino de una **reestructuración arquitectónica** orientada a optimizar las consultas en tiempo de ejecución:

```
┌─────────────────────────────────┐
│     1. EXTRACCIÓN (MySQL)       │
│ Conexión a 'olimpiadas' local.  │
│ Lectura de tablas con SELECT y  │
│ JOINs relacionales controlados. │
└───────────────┬─────────────────┘
                │
                ▼
┌─────────────────────────────────┐
│   2. TRANSFORMACIÓN (Python)    │
│ • Desnormalización funcional.   │
│ • Conversión a documentos BSON. │
│ • Normalización léxica (NFKD).  │
│ • Generación de tokens multikey.│
│ • Embebido de sedes y NOCs.     │
└───────────────┬─────────────────┘
                │
                ▼
┌─────────────────────────────────┐
│       3. CARGA (MongoDB)        │
│ Inserción masiva en la nube vía │
│ pymongo en lotes ordered=False. │
│ Generación de bitácoras y logs. │
└─────────────────────────────────┘
```

1. **Extracción (Extract):** Se conecta mediante `mysql.connector` a la base de datos local `olimpiadas` (puerto 3306), donde residen los datos saneados y deduplicados de la Fase 1.
2. **Transformación (Transform):** Los registros relacionales se transforman en memoria en documentos JSON/BSON jerárquicos. Aquí se aplica la regla del catedrático: **no crear una colección por cada tabla relacional**, sino desnormalizar y agrupar la información según el pivote de consulta (atleta y país).
3. **Carga (Load):** Utilizando el driver oficial `pymongo`, los documentos se transmiten por la red al clúster de **MongoDB Atlas** (`olimpiadas.vowmkp2.mongodb.net`) mediante lotes (`insert_many` con `ordered=False`) para garantizar alta velocidad y tolerancia a fallos.

---

## 2. Decisiones de Desnormalización y Modelo NoSQL (4 Colecciones)

El diseño atiende estrictamente las observaciones del catedrático (Ing. Luis Alberto Arias):
> *"Allí estás pensando en normalizar; no normalices, que repita la info, lo que importa aquí es mostrar la data correctamente... entre más ciclos, más recorridos y más juntas (lookups) le pones a tu script, haces lento el Mongo."*

```
                     ┌────────────────────────┐
                     │   ediciones (63 docs)  │
                     │  Sede y país embebido  │
                     └────────────────────────┘
                                 ▲
                                 │
┌───────────────────────┐        │        ┌────────────────────────┐
│  atletas (190k docs)  │        │        │   paises (487 docs)    │
│  nombre_norm + tokens ├────────┼───────►│ NOCs + Sedes embebidas │
└───────────┬───────────┘        │        └───────────┬────────────┘
            │                    │                    │
            │        ┌───────────┴────────────┐       │
            └───────►│ resultados (380k docs) │◄──────┘
                     │ Participación aplanada │
                     │ Cero $lookup costosos  │
                     └────────────────────────┘
```

### A. Colección `ediciones` (63 documentos)
* **Pivote:** Cada edición de los Juegos Olímpicos (1896 Atenas hasta 2024 París).
* **Transformación:** En lugar de dejar la tabla `sede` por separado, se embeben la ciudad y el país organizador directamente dentro del documento (`sede.ciudad`, `sede.pais_codigo`, `sede.pais_nombre`).
* **Propósito:** Responder en 1 solo paso datos de la sede y el año olímpico.

### B. Colección `paises` (487 documentos)
* **Pivote:** Entidades geográficas y comités deportivos reconocidos.
* **Transformación:**
  1. Se incrusta el arreglo `nocs: [{ codigo, nombre, notas }]` para admitir múltiples códigos históricos por país.
  2. Se incrusta el arreglo `sedes_historicas: [{ anio, temporada, ciudad }]` y la bandera `es_sede_historica: true/false`.
* **Propósito:** Cumplir el **Requerimiento (d)** del enunciado (*"desplegar si ha sido sede en alguna ocasión y qué años"*) de forma **instantánea**, sin requerir consultas cruzadas a la colección de resultados.

### C. Colección `atletas` (190,471 documentos)
* **Pivote:** Ficha biográfica consolidada de cada deportista olímpico.
* **Transformación:**
  1. Se genera el atributo `nombre_norm` mediante la función [`normalize_name`](file:///d:/Proyectos%20U/Bases%202/Proyecto%201/SBD2B_PROYECT1_2S2026_G18/etl/utils.py) de la Fase 1 (minúsculas, normalización Unicode NFKD sin tildes, eliminación de viñetas `•`, reemplazo de puntuación por espacios y restauración de apellidos raspados mediante `_CORRUPTED_MAP`).
  2. Se calcula el arreglo `tokens: ["usain", "st", "leo", "bolt"]` con palabras clave $\ge 2$ caracteres.
* **Propósito:** Búsquedas por nombre completo, nombres parciales o apellidos mediante el índice multikey `idx_atletas_tokens`, permitiendo localizar al atleta en menos de 5 milisegundos.

### D. Colección `resultados` (380,548 documentos)
* **Pivote:** Hecho transaccional de cada participación olímpica.
* **Transformación:** Se desnormalizan 9 tablas relacionales en una sola estructura aplanada (`atleta`, `olimpiada`, `pais`, `noc`, `equipo`, `deporte`, `disciplina`, `evento`, `medalla`, `posicion`, `es_empate`, métricas físicas).
* **Propósito:** Permitir que el Integrante 3 ejecute consultas analíticas y medalleros acumulados filtrando por atleta o país utilizando índices compuestos B-Tree (`idx_resultados_atleta_anio`, `idx_resultados_pais_anio_deporte`), **eliminando completamente la necesidad de `$lookup` lentos**.

---

## 3. Inventario y Explicación Detallada de los Scripts en `Fase3/scripts/`

A continuación se detalla el propósito técnico, flujo de ejecución y responsabilidades de cada script de Python:

### 1. `test_conexion.py`
* **Rol:** Verificador preliminar de conectividad y handshake de red (Fase 0).
* **¿Qué hace?:**
  1. Lee variables de conexión desde `Fase3/.env` (`MYSQL_HOST`, `MYSQL_USER`, `MONGO_URI`, etc.).
  2. Ejecuta un handshake con MySQL local ejecutando `SELECT DATABASE(), VERSION()` y reporta el conteo de atletas y participaciones en el origen.
  3. Ejecuta un comando administrativo `client.admin.command('ping')` contra el clúster en la nube de MongoDB Atlas con un timeout de 5 segundos (*fail-fast*).
  4. Lista las colecciones existentes en Atlas para certificar acceso de lectura y escritura.

### 2. `00_auditoria_censo_mysql.py`
* **Rol:** Certificación censal de la base de datos origen de la Fase 1 (Fase 1 del plan).
* **¿Qué hace?:**
  1. Ejecuta `SELECT COUNT(*)` sobre las **12 tablas relacionales** de MySQL (`pais`, `noc`, `poblacion_pais`, `sede`, `olimpiada`, `deporte`, `disciplina`, `evento`, `equipo`, `atleta`, `medalla`, `participacion`).
  2. Audita **13 relaciones de clave foránea** buscando registros huérfanos.
  3. Comprueba el desglose exacto de las 380,548 medallas (Oro, Plata, Bronce, NA).
  4. Genera automáticamente un log fechado en `Fase3/logs/censo_mysql_YYYYMMDD_HHMMSS.log` con el dictamen de integridad.

### 3. `03_prueba_volumetria_10k.py`
* **Rol:** Prueba de tamaño y proyección de capacidad en Atlas M0 (Fase 2 del plan).
* **¿Qué hace?:**
  1. Extrae un bloque de **10,000 participaciones desnormalizadas** desde MySQL.
  2. Limpia e inserta el lote en la colección `resultados` de Atlas.
  3. Invoca la función administrativa `db.command('collStats', 'resultados')` para interrogar directamente al motor **WiredTiger**.
  4. Mide `avgObjSize` (455 bytes), `storageSize` (1.49 MB) y `totalIndexSize` (1.30 MB), calculando el ratio de compresión real (2.91x).
  5. Proyecta matemáticamente el almacenamiento de toda la base frente al límite de 512 MB de Atlas M0 (~139 MB de uso proyectado, ~27.1%).
  6. Guarda la bitácora técnica en `Fase3/logs/volumetria_piloto_10k_*.log`.

### 4. `03_cargar_datos_mongo.py`
* **Rol:** Motor principal del pipeline ETL para la migración completa a MongoDB Atlas.
* **Componentes y funciones internas:**
  * `clean_val(v)`: Convierte tipos no serializables en BSON nativo (objetos `Decimal` a `float`, y fechas `date`/`datetime` a cadenas ISO `YYYY-MM-DD`).
  * `normalize_name(name)`: Carga dinámica mediante `importlib.util` de la rutina de normalización de la Fase 1 (DT-002 y DT-027) para evitar errores del linter en el editor de código.
  * `extraer_transformar_ediciones(cur)`:
    * Ejecuta `SELECT` con `LEFT JOIN` entre `olimpiada`, `sede` y `pais`.
    * Retorna la lista de 63 documentos con la estructura de sede anidada.
  * `extraer_transformar_paises(cur)`:
    * Pre-calcula en memoria diccionarios de sedes y de comités NOC por país.
    * Mapea los 487 países incrustando `sedes_historicas` y `nocs`.
  * `extraer_transformar_atletas(cur, offset, limit)`:
    * Extrae la biografía de atletas desde MySQL por bloques.
    * Calcula `nombre_norm` y el arreglo de `tokens`.
    * Limpia campos nulos para optimizar espacio BSON.
  * `extraer_lote_resultados(cur, offset, limit)`:
    * Ejecuta el `SELECT` aplanado de participaciones con 9 `LEFT JOIN` hacia atletas, olimpiadas, sedes, eventos, disciplinas, deportes, equipos, comités, países y medallas.
    * Retorna lotes de documentos BSON listos para inserción masiva.

---

## 4. ¿Cómo Verificar los Datos en Cualquier Momento?

Para certificar en tiempo real qué colecciones y cuántos documentos existen en MongoDB Atlas:

### Opción 1: Consulta rápida por línea de comandos
Ejecutar desde PowerShell en la raíz del proyecto:
```powershell
python -c "import os, pymongo, dotenv; dotenv.load_dotenv('Fase3/.env'); c = pymongo.MongoClient(os.getenv('MONGO_URI')); db = c['olimpiadas']; print({col: db[col].count_documents({}) for col in ['ediciones', 'paises', 'atletas', 'resultados']})"
```

### Opción 2: MongoDB Atlas Web Explorer
1. Ingresar a [MongoDB Cloud](https://cloud.mongodb.com/).
2. Seleccionar la base de datos `olimpiadas` en el Data Explorer.
3. El panel lateral izquierdo mostrará en tiempo real el censo de documentos por colección:
   * `ediciones`: 63
   * `paises`: 487
   * `atletas`: 190,471
   * `resultados`: 380,548

---
*Documento elaborado para auditoría técnica de la Fase 3 — Grupo 18.*
