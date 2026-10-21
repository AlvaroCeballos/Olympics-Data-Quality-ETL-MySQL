# ARQUITECTURA DEL PIPELINE ETL Y GUÍA DE SCRIPTS PYTHON
**Proyecto: Base de Datos Unificada de Juegos Olímpicos (1896–2024)**  
**Curso: Sistemas de Bases de Datos 2 — USAC**  
**Fase 3 — Grupo 18**  

---

## 1. Proceso ETL de Carga de Datos para MongoDB

El proceso de **Extracción, Transformación y Carga (ETL)** de esta fase constituye la transición técnica desde el modelo relacional normalizado (MySQL en 3NF con 12 tablas) hacia un modelo no relacional orientado a documentos en MongoDB Atlas.

El diseño evita replicar la estructura tabular relacional de forma aislada. La arquitectura se fundamenta en una **desnormalización funcional por caso de uso**, estructurando los documentos en torno a las entidades pivote del negocio olímpico (atleta y país). Esta estrategia garantiza que las consultas analíticas respondan en orden de milisegundos, eliminando la sobrecarga computacional de múltiples etapas `$lookup` o recorridos iterativos entre colecciones.

### Bloque de Extracción (MySQL Origen)
* **Origen de datos:** Instancia de MySQL local ejecutándose en el puerto 3306 sobre la base de datos `olimpiadas`.
* **Mecanismo de conexión:** Se emplea la librería oficial `mysql.connector` utilizando cursores en modo diccionario (`dictionary=True`), permitiendo manipular cada tupla extraída como un mapa asociativo clave-valor en Python.
* **Técnica de lectura:**
  * Para las entidades dimensionales (`olimpiada`, `sede`, `pais`, `noc`), se extrae el conjunto consolidado mediante sentencias `SELECT` con `LEFT JOIN`.
  * Para los atletas y las participaciones masivas, se implementa una extracción paginada mediante lotes secuenciales (`LIMIT` y `OFFSET`), evitando saturar la memoria RAM del equipo y previniendo desconexiones por timeout en el socket de MySQL.

### Bloque de Transformación (Python en Memoria)
* **Desnormalización funcional:** Se unifican atributos de tablas que en el modelo relacional estaban separadas por reglas de normalización. La información de la sede se incrusta en la edición, y los datos del atleta, evento, disciplina, deporte y medalla se consolidan en cada participación.
* **Construcción jerárquica de documentos:** Los valores planos se agrupan en subdocumentos anidados (objetos BSON) y arreglos, estructurando los documentos según su entidad pivote.
* **Normalización de texto y tokens:** En la colección de atletas se ejecuta la función `normalize_name` heredada de la Fase 1, la cual convierte a minúsculas, elimina tildes y diacríticos (Unicode NFKD), remueve viñetas y puntuación, restaura apellidos hispanos mediante `_CORRUPTED_MAP` y genera un arreglo de palabras clave (`tokens`) para indexación multikey.
* **Conversión de tipos de datos:** Los tipos específicos de MySQL no compatibles de forma nativa con BSON se transforman mediante la función auxiliar `clean_val` (los objetos `Decimal` se convierten a `float` y las fechas `date`/`datetime` a cadenas ISO-8601 `YYYY-MM-DD`).

### Bloque de Carga (MongoDB Atlas Destino)
* **Destino de datos:** Clúster oficial en la nube de MongoDB Atlas (`olimpiadas.vowmkp2.mongodb.net`) sobre la base de datos `olimpiadas`.
* **Mecanismo de inserción:** Se utiliza el driver oficial `pymongo` invocando el método `insert_many(lote, ordered=False)`. La bandera `ordered=False` permite que MongoDB procese las inserciones en paralelo en el servidor sin detener la ejecución si un registro individual presentara alguna excepción no fatal.
* **Auditoría y trazabilidad:** Cada lote insertado registra el tiempo de transferencia, la tasa de documentos por segundo y emite una bitácora persistente con fecha y hora dentro de la carpeta `Fase3/logs/`.

---

## 2. Decisiones de Desnormalización y Modelo Documental (4 Colecciones)

El diseño adopta el principio de desnormalización estratégica en bases documentales: la redundancia controlada de datos se prioriza sobre la normalización estricta cuando el objetivo es maximizar la velocidad de lectura y simplificar la jerarquía de los documentos resultantes. Separar en exceso las entidades obligaría a encadenar múltiples lecturas o agregaciones complejas en tiempo de ejecución, lo que degradaría el tiempo de respuesta.

La base de datos se estructura en cuatro colecciones documentales:

### Bloque Colección: `ediciones` (63 documentos)
* **Entidad Pivote:** Edición histórica de los Juegos Olímpicos (desde Atenas 1896 hasta París 2024).
* **Campos Principales:**
  * `_id`: Identificador numérico coincidente con `id_olimpiada` de MySQL.
  * `anio`: Año de celebración de los juegos (ejemplo: 2024).
  * `temporada`: Temporada deportiva (`Summer` o `Winter`).
  * `nombre_juegos`: Denominación formal (ejemplo: `2024 Summer`).
  * `sede`: Subdocumento embebido con `ciudad`, `pais_codigo` y `pais_nombre`.
* **Beneficio Técnico:** Elimina la necesidad de consultar la tabla `sede` por separado. Al consultar cualquier edición se obtiene de forma inmediata la ciudad y el país organizador.

### Bloque Colección: `paises` (487 documentos)
* **Entidad Pivote:** Catálogo de países soberanos y delegaciones deportivas históricas.
* **Campos Principales:**
  * `_id`: Identificador numérico de país.
  * `codigo`: Código ISO o territorial de 3 letras (ejemplo: `FRA`, `GUA`).
  * `nombre`: Nombre oficial del país.
  * `nombre_norm`: Nombre normalizado en minúsculas y sin acentos para búsquedas.
  * `es_sede_historica`: Booleano (`true` / `false`) que indica si el país albergó alguna edición olímpica.
  * `sedes_historicas`: Arreglo de subdocumentos con cada una de las ediciones albergadas, conteniendo `anio`, `temporada` y `ciudad`.
  * `nocs`: Arreglo de comités olímpicos asociados con `codigo`, `nombre` y `notas`.
* **Beneficio Técnico:** Resuelve de manera inmediata el **Requerimiento (d)** del proyecto (*"desplegar si ha sido sede en alguna ocasión y qué años"*). Una sola lectura al documento del país retorna el listado de años y ciudades anfitrionas sin recorrer millones de participaciones.

### Bloque Colección: `atletas` (190,471 documentos)
* **Entidad Pivote:** Ficha biográfica maestra del deportista olímpico.
* **Campos Principales:**
  * `_id`: Identificador único del atleta (`id_atleta`).
  * `id_externo`: Identificador biográfico original de Olympedia (o `null` si proviene de fuentes Kaggle).
  * `nombre`: Nombre del atleta en formato original.
  * `nombre_norm`: Cadena en minúsculas, sin diacríticos ni viñetas, con corrección fonética.
  * `tokens`: Arreglo de palabras individuales ($\ge 2$ caracteres) derivado de `nombre_norm`.
  * `sexo`: Género homologado (`M` o `F`).
  * `fecha_nac`: Fecha de nacimiento en formato `YYYY-MM-DD`.
  * `pais_nacimiento`: Subdocumento con `codigo` y `nombre` del país de nacimiento.
  * `altura_cm` y `peso_kg`: Métricas antropométricas base.
  * `afiliacion`, `apodo`, `titulo`: Metadatos preservados de la data cruda original.
* **Beneficio Técnico:** Mediante el índice multikey sobre `tokens`, el script de consulta por atleta puede encontrar coincidencias exactas o parciales por nombre o apellido en menos de 5 milisegundos.

### Bloque Colección: `resultados` (380,548 documentos)
* **Entidad Pivote:** Hecho transaccional aplanado de cada participación olímpica.
* **Campos Principales:**
  * `_id`: Identificador único de participación (`id_participacion`).
  * `atleta`: Subdocumento con `id`, `nombre` y `sexo`.
  * `olimpiada`: Subdocumento con `id`, `anio`, `temporada` y `nombre_juegos`.
  * `pais`: Subdocumento con `codigo` y `nombre` de la delegación representada.
  * `noc`: Subdocumento con `codigo` del comité olímpico.
  * `equipo`: Nombre del representativo deportivo o pareja.
  * `deporte` y `disciplina`: Clasificación deportiva (con disciplina puente incluida).
  * `evento`: Nombre específico de la prueba deportiva.
  * `medalla`: Presea obtenida (`Gold`, `Silver`, `Bronze` o `NA`).
  * `posicion`: Puesto registrado (numérico o texto como `DNS`, `DNF`).
  * `es_empate`: Booleano indicador de empate deportivo.
  * `edad`, `altura_reg`, `peso_reg`: Métricas físicas específicas registradas en dicha edición.
* **Beneficio Técnico:** La colección no requiere operaciones de combinación (`$lookup`). Consultar el medallero o el historial de un atleta o país se ejecuta directamente sobre los índices B-Tree (`idx_resultados_atleta_anio` e `idx_resultados_pais_anio_deporte`).

---

## 3. Inventario y Explicación Detallada de los Scripts en `Fase3/scripts/`

El pipeline se encuentra modularizado en scripts ejecutables independientes:

### Script: `test_conexion.py`
* **Propósito:** Verificación preliminar de conectividad y handshake de red (Fase 0).
* **Operación:**
  1. Carga las variables desde `Fase3/.env`.
  2. Conecta con MySQL local ejecutando `SELECT DATABASE(), VERSION()` y emite el censo de atletas y participaciones.
  3. Ejecuta un comando de control `client.admin.command('ping')` contra el clúster de MongoDB Atlas con un timeout corto de 5 segundos.
  4. Lista las colecciones presentes en el clúster para certificar permisos de lectura y escritura.

### Script: `00_auditoria_censo_mysql.py`
* **Propósito:** Certificación censal de la base de datos relacional de la Fase 1 antes de migrar (Fase 1 del plan).
* **Operación:**
  1. Ejecuta conteos sobre las **12 tablas relacionales** (`pais`, `noc`, `poblacion_pais`, `sede`, `olimpiada`, `deporte`, `disciplina`, `evento`, `equipo`, `atleta`, `medalla`, `participacion`).
  2. Audita **13 relaciones de clave foránea** en busca de registros huérfanos.
  3. Verifica la distribución de las 380,548 medallas por tipo.
  4. Emite un log fechado en `Fase3/logs/censo_mysql_*.log` que certifica 0 claves rotas y 613,078 filas totales.

### Script: `03_prueba_volumetria_10k.py`
* **Propósito:** Prueba de capacidad física y proyección de almacenamiento en Atlas M0 (Fase 2 del plan).
* **Operación:**
  1. Extrae un bloque de **10,000 participaciones desnormalizadas** de MySQL.
  2. Inserta el lote en la colección `resultados` de MongoDB Atlas.
  3. Invoca la instrucción administrativa `collStats` para interrogar al motor **WiredTiger**.
  4. Obtiene el tamaño promedio (`avgObjSize` de 455 bytes), el almacenamiento comprimido (`storageSize`) y el tamaño de índices (`totalIndexSize`).
  5. Calcula la proyección global de almacenamiento (~139 MB totales frente al límite de 512 MB de la capa gratuita M0).
  6. Guarda la bitácora técnica en `Fase3/logs/volumetria_piloto_10k_*.log`.

### Script: `01_cargar_ediciones_paises.py`
* **Propósito:** Ejecución de la Fase 3 del plan: carga completa de las colecciones dimensionales de contexto.
* **Operación:**
  1. Extrae y transforma las **63 ediciones olímpicas** embebiendo la información de la sede (`ciudad`, `pais_codigo`, `pais_nombre`).
  2. Extrae y transforma los **487 países** calculando en memoria los arreglos `sedes_historicas` y `nocs`.
  3. Inserta ambos bloques en MongoDB Atlas con `ordered=False`.
  4. Verifica documentos de muestra (Francia con sus 6 ediciones albergadas, Guatemala como participante, y París 2024).
  5. Genera la bitácora con fecha y hora en `Fase3/logs/carga_ediciones_paises_*.log`.

### Script: `03_cargar_datos_mongo.py`
* **Propósito:** Módulo central con las funciones de transformación y carga masiva del proyecto.
* **Funciones Clave:**
  * `clean_val(v)`: Convierte tipos `Decimal` y `date`/`datetime` a formatos compatibles con BSON.
  * `normalize_name(name)`: Carga dinámica con `importlib.util` de la lógica de normalización de nombres y mitigación de errores de scraping (DT-002 y DT-027).
  * `extraer_transformar_ediciones(cur)`: Consulta `olimpiada`, `sede` y `pais` retornando la lista de 63 documentos.
  * `extraer_transformar_paises(cur)`: Procesa las sedes históricas y los comités para los 487 países.
  * `extraer_transformar_atletas(cur, offset, limit)`: Extrae atletas por bloques, computa `nombre_norm`, genera el arreglo `tokens` y descarta campos nulos.
  * `extraer_lote_resultados(cur, offset, limit)`: Ejecuta la consulta masiva con 9 `LEFT JOIN` para armar lotes de participaciones desnormalizadas.

---

## 4. Guía de Verificación de Censos en MongoDB Atlas

Para corroborar en cualquier momento la cantidad de documentos almacenados en el clúster:

### Verificación por Consola (PowerShell / Terminal)
Instrucción de consulta directa:
```powershell
python -c "import os, pymongo, dotenv; dotenv.load_dotenv('Fase3/.env'); c = pymongo.MongoClient(os.getenv('MONGO_URI')); db = c['olimpiadas']; print({col: db[col].count_documents({}) for col in ['ediciones', 'paises', 'atletas', 'resultados']})"
```

### Verificación Visual en MongoDB Cloud
1. Acceder al portal web de **MongoDB Atlas** e ingresar a **Data Explorer** (Browse Collections).
2. Seleccionar la base de datos `olimpiadas`.
3. El panel lateral mostrará el conteo de documentos por colección:
   * **`ediciones`:** 63 documentos (Cargados al 100%).
   * **`paises`:** 487 documentos (Cargados al 100%).
   * **`atletas`:** 190,471 documentos (Pendiente Fase 4).
   * **`resultados`:** 380,548 documentos (Pendiente Fase 5).

---
*Documento técnico de arquitectura y referencia de ejecución — Grupo 18.*
