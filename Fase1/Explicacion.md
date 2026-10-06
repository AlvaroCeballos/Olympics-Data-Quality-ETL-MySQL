# PROYECTO FASE 1: BASE DE DATOS UNIFICADA DE JUEGOS OLÍMPICOS (1896-2024)
**Universidad de San Carlos de Guatemala (USAC)**  
**Facultad de Ingeniería — Escuela de Ciencias y Sistemas**  
**Sistemas de Bases de Datos 2 — 2do. Semestre 2026**  
**Grupo 18**  
* Yulianne Nicole Lopez Elias — 202300659 (Persona 1: DDL y Diagrama E/R)
* Álvaro Gabriel Ceballos Gil — 202300673 (Persona 2: Extracción, Limpieza ETL y Carga)
* Ottoniel Fabricio Vásquez Pineda — 202307820 (Persona 3: Procedimientos Almacenados)

---

## 1. Contexto General y División del Trabajo

El proyecto consiste en integrar y consolidar cuatro fuentes de datos olímpicos en un único repositorio relacional en MySQL (Base de Datos `olimpiadas`), garantizando calidad, consistencia histórica y normalización en Tercera Forma Normal (3NF):

* **Persona 1 (Completado):** Diseño del Diagrama E/R unificado (`ERD-OLIMIADAS-G18.png`) y codificación del script DDL (`olimpiada2s.sql`) con 12 tablas, llaves primarias, foráneas, restricciones únicas e índices de optimización.
* **Persona 2 (En ejecución - Álvaro Ceballos):** Extracción, limpieza y perfilado de la data cruda, resolución de inconsistencias semánticas/sintácticas, unificación de identidades y construcción de pipelines reproducibles en Python para la carga masiva y directa a la base de datos relacional.
* **Persona 3 (Siguiente fase):** Desarrollo de los Stored Procedures analíticos para consultas sobre atletas y países, optimizados para soportar filtros parametrizados y evitar volcados masivos de datos en consola.

---

## 2. Inventario de Fuentes de Datos

1. **Fuente 1: Repositorio Keith Galli (Scraping de Olympedia.org)**
   * *Archivos crudos:* `bios1.csv` (16 columnas) y `results1.csv` (11 columnas). Contienen mojibake de caracteres (viñetas `•`, codificación Windows-1252/UTF-8 desalineada), ubicaciones compuestas en texto plano, estatus de resultados mixtos (`DNS`, `=17`, tiempos de carrera) y metadatos no atómicos.
   * *Archivos limpios (referencia):* `clean-data/bios.csv`, `clean-data/results.csv`, `clean-data/bios_locs.csv` (añade latitud y longitud georreferenciada), `clean-data/noc_regions.csv` y `clean-data/populations.csv` (1960–2023).
2. **Fuente 2: Kaggle 120 Years of Olympic History (heesoo37 / Sports-Reference)**
   * *Archivo:* `athlete_events.csv` (15 columnas: `ID`, `Name`, `Sex`, `Age`, `Height`, `Weight`, `Team`, `NOC`, `Games`, `Year`, `Season`, `City`, `Sport`, `Event`, `Medal`). Cobertura: 1896–2016. Aporta edad, peso y altura registrados puntualmente en cada edición.
3. **Fuente 3: Kaggle Summer Olympics Medals 1896-2024 (stefanydeoliveira)**
   * *Archivo:* `olympics_dataset.csv` (11 columnas: `player_id`, `Name`, `Sex`, `Team`, `NOC`, `Year`, `Season`, `City`, `Sport`, `Event`, `Medal`). Cobertura histórica que extiende los registros hasta Tokio 2020 y París 2024.
4. **Fuente 4: DataCamp Datalab (r-olympics)**
   * *Archivo:* `athlete_events.csv.gz` (esquema idéntico a la Fuente 2, utilizado para validación cruzada y verificación de integridad).
5. **Referencia de Calidad Oficial:** `https://www.olympics.com/` para contrastar conteos de medallas y sedes históricas.

---

## 3. Directrices y Reglas de Negocio del Catedrático

1. **Prioridad de la data cruda:** Se debe procesar la data cruda como fuente primaria y usar la data limpia exclusivamente como patrón de referencia comparativa.
2. **Códigos de país:** Uso obligatorio de códigos estándar de país (3 letras).
3. **Trazabilidad:** Cualquier transformación sobre los datasets originales debe estar programada y documentada en scripts de Python.
4. **Preservación de columnas (Regla 4 y 7):** Prohibido descartar columnas que posean al menos un dato útil, sin importar qué tan baja sea su densidad. Las columnas con pocos datos se conservan como atributos anulables (`NULL`).
5. **Regla de eliminación (Regla 12):** Solo se permite omitir una columna si el 100% de sus tuplas carecen de datos en la totalidad del dataset.
6. **Entidad Sede independiente (Regla 6 y 13):** `sede` debe ser una entidad separada de `pais`, ya que la sede es una ciudad (frecuentemente la capital) y los juegos se identifican históricamente por la sede y el año.
7. **Homologación semántica (Regla 11):** Normalizar discrepancias entre datasets (ej. sexo `'Male'`/`'Female'` vs `'M'`/`'F'`, o representaciones divergentes de países).
8. **Stored Procedures de alto desempeño (Reglas 5, 8 y 9):**
   * Parámetros de filtrado específicos (año, deporte, país).
   * Restricción de salida: prohibido emitir millones de filas o realizar `SELECT *` descontrolados durante la calificación en vivo. Debe emplearse agregación, resumen estructurado y paginación.
9. **Cero asistentes gráficos (Regla 10):** Toda la estructura y carga debe realizarse mediante código SQL y scripts automatizados de ingeniería de datos.
10. **Tratamiento Sede-Año (Regla 15):** Modelado en 3NF donde `sede` almacena la ciudad asociada al país, y `olimpiada` almacena el año, temporada y referencia foránea a la sede. El cruce de ciudad y año se resuelve vía `JOIN` relacional.

---

## 4. Decisiones Técnicas y Medidas de Arquitectura

### A. Desacoplamiento de Entidades Geográficas y Deportivas
* `pais` representa la entidad política territorial (con código ISO de 3 letras).
* `noc` representa el Comité Olímpico Nacional. Esta separación es obligatoria porque existen delegaciones que no corresponden a un único país moderno (ej. `URS`, `GDR`, `EUN` - Equipo Unificado, `ROT` - Equipo de Refugiados).
* `sede` vincula la ciudad anfitriona con su respectivo `id_pais`.
* `olimpiada` representa el evento cuatrienal, desacoplado de la sede mediante `id_sede`. Para soportar los Juegos Intercalados de Atenas 1906 y posibles ediciones juveniles o extraordinarias, `temporada` se configuró como `VARCHAR(30)` en lugar de un `ENUM` cerrado.

### B. Recuperación de Columnas Crudas en `atleta`
A diferencia del notebook de Keith Galli (que eliminó 9 columnas), se preservaron en la tabla `atleta`:
* `nombre_original`: Para caracteres en alfabeto cirílico, chino, japonés o coreano (ej. `姚•明`).
* `orden_nombre`: Para indicar convenciones como "Oriental" u "Occidental".
* `apodo`: Nicknames registrados en la data cruda (`Nick/petnames`, ej. "Toto", "Sabas").
* `titulo`: Títulos nobiliarios o de honor (`Title(s)`, ej. "Comte", "Baron").
* `afiliacion`: Clubes y universidades deportivas (`Affiliations`).

### C. Normalización de Medallas y Posiciones
* Se mantiene un catálogo estricto `medalla` con los valores `('Gold', 'Silver', 'Bronze', 'NA')`. La tabla de hechos `participacion` tiene `id_medalla INT NOT NULL` apuntando obligatoriamente a `'NA'` cuando el atleta no obtuvo presea. Esto indexa y acelera drásticamente los cálculos de podio.
* Se agregó la columna booleana `es_empate` en `participacion` para almacenar si la posición contenía el carácter `=`, manteniendo el campo `posicion VARCHAR(30)` para almacenar valores textuales como `"DNS"`, `"DNF"`, `"DQ"` o puestos de ronda.

### D. Normalización de Poblaciones Históricas
* El archivo `populations.csv` viene en formato ancho (64 columnas: 1960 a 2023). En la base de datos se almacena en la tabla normalizada `poblacion_pais(id_pais, anio, poblacion)` con clave primaria compuesta `(id_pais, anio)`. El pipeline en Python transforma esto mediante `pandas.melt()`.

### E. Jerarquía Deporte -> Disciplina -> Evento
* Se implementa la jerarquía de 3 niveles requerida por la cátedra:
  $$\text{deporte} \longrightarrow \text{disciplina} \longrightarrow \text{evento}$$
* Como las fuentes de Kaggle traen `Sport` y `Event`, mientras Olympedia trae `Discipline` y `Event`, el script de transformación genera una disciplina puente equivalente al deporte en caso de ausencia para evitar llaves foráneas rotas o eventos desvinculados.

---

## 5. Esquema Relacional DDL (`olimpiada2s.sql`)

```sql

DROP DATABASE IF EXISTS olimpiadas;
CREATE DATABASE olimpiadas
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;
USE olimpiadas;

-- ---------------------------------------------------------------------
-- PAIS : pais geografico. codigo_pais = codigo de 3 letras del pais.
-- ---------------------------------------------------------------------
CREATE TABLE pais (
  id_pais      INT AUTO_INCREMENT PRIMARY KEY,
  codigo_pais  CHAR(3)      NULL,          -- codigo de pais (3 letras)
  nombre       VARCHAR(120) NULL,
  nombre_alt   VARCHAR(120) NULL,          -- variantes de nombre entre fuentes
  region       VARCHAR(120) NULL,          -- noc_regions -> region
  UNIQUE KEY uq_pais_codigo (codigo_pais)
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- NOC : Comite Olimpico Nacional. Separado de PAIS porque hay codigos
-- que no son un pais (EUN Equipo Unificado, ROT refugiados, URS, GDR...).
-- ---------------------------------------------------------------------
CREATE TABLE noc (
  id_noc      INT AUTO_INCREMENT PRIMARY KEY,
  codigo_noc  CHAR(3)      NULL,           -- codigo NOC (GUA, USA, EUN...)
  nombre_noc  VARCHAR(150) NULL,
  id_pais     INT          NULL,           -- pais al que corresponde (si aplica)
  notas       VARCHAR(255) NULL,           -- noc_regions -> notes
  UNIQUE KEY uq_noc_codigo (codigo_noc),
  CONSTRAINT fk_noc_pais FOREIGN KEY (id_pais) REFERENCES pais(id_pais)
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- SEDE : ciudad anfitriona. REGLA 1: referencia al pais.
-- ---------------------------------------------------------------------
CREATE TABLE sede (
  id_sede      INT AUTO_INCREMENT PRIMARY KEY,
  ciudad       VARCHAR(120) NOT NULL,      -- City
  id_pais      INT          NULL,
  UNIQUE KEY uq_sede_ciudad_pais (ciudad, id_pais),   -- evita duplicar sede en cargas
  CONSTRAINT fk_sede_pais FOREIGN KEY (id_pais) REFERENCES pais(id_pais)
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- OLIMPIADA : cada edicion. 'temporada' es VARCHAR porque en los datos
-- crudos hay mas que Summer/Winter: Intercalated (1906), Youth, Zappas,
-- Equestrian. UNIQUE(anio,temporada) evita ediciones duplicadas.
-- ---------------------------------------------------------------------
CREATE TABLE olimpiada (
  id_olimpiada  INT AUTO_INCREMENT PRIMARY KEY,
  anio          SMALLINT NULL,             -- Year
  temporada     VARCHAR(30) NULL,          -- Summer/Winter/Intercalated/Youth/Zappas/Equestrian...
  nombre_juegos VARCHAR(60) NULL,          -- Games ("2016 Summer")
  id_sede       INT NULL,
  UNIQUE KEY uq_olimpiada_anio_temp (anio, temporada),  -- una edicion por anio+temporada
  CONSTRAINT fk_olimpiada_sede FOREIGN KEY (id_sede) REFERENCES sede(id_sede)
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- ATLETA : persona unica. Campos LIMPIOS de bios_locs.csv (ya separados).
-- altura_cm / peso_kg = valor base del atleta. Nacimiento desglosado.
-- ---------------------------------------------------------------------
CREATE TABLE atleta (
  id_atleta        INT AUTO_INCREMENT PRIMARY KEY,
  id_externo       INT           NULL,     -- ID / athlete_id
  nombre           VARCHAR(120)  NULL,     -- name
  nombre_completo  VARCHAR(150)  NULL,     -- Full name
  otros_nombres    VARCHAR(255)  NULL,     -- Other names
  nombre_original  VARCHAR(150)  NULL,     -- Original name (21% lleno: cirilico/asiatico)
  orden_nombre     VARCHAR(50)   NULL,     -- Name order (5% lleno)
  apodo            VARCHAR(150)  NULL,     -- Nick/petnames (6% lleno)
  titulo           VARCHAR(100)  NULL,     -- Title(s) (0.3% = 399 filas; regla 12: se conserva)
  afiliacion       VARCHAR(255)  NULL,     -- Affiliations (66% lleno: clubes)
  sexo             ENUM('M','F') NULL,
  fecha_nac        DATE          NULL,     -- born_date (99% presente)
  ciudad_nac       VARCHAR(120)  NULL,     -- born_city
  region_nac       VARCHAR(120)  NULL,     -- born_region
  id_pais_nac      INT           NULL,     -- born_country -> pais
  fecha_muerte     DATE          NULL,     -- died_date (23% presente)
  altura_cm        DECIMAL(5,2)  NULL,     -- height_cm (base)
  peso_kg          DECIMAL(5,2)  NULL,     -- weight_kg (base)
  roles            VARCHAR(150)  NULL,     -- Roles
  nacionalidad     VARCHAR(120)  NULL,     -- Nationality
  latitud          DECIMAL(9,6)  NULL,     -- lat (opcional, 48% presente)
  longitud         DECIMAL(9,6)  NULL,     -- long (opcional)
  CONSTRAINT fk_atleta_pais_nac FOREIGN KEY (id_pais_nac) REFERENCES pais(id_pais)
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- DEPORTE -> DISCIPLINA -> EVENTO (jerarquia de 3 niveles, pedida por
-- el catedratico). athlete_events trae Sport; results trae Discipline.
-- Cada fuente llena el nivel que tenga; el resto queda NULL.
-- ---------------------------------------------------------------------
CREATE TABLE deporte (
  id_deporte  INT AUTO_INCREMENT PRIMARY KEY,
  nombre      VARCHAR(120) NULL,           -- Sport
  UNIQUE KEY uq_deporte_nombre (nombre)
) ENGINE=InnoDB;

CREATE TABLE disciplina (
  id_disciplina INT AUTO_INCREMENT PRIMARY KEY,
  nombre        VARCHAR(120) NULL,         -- Discipline (results)
  id_deporte    INT NULL,
  CONSTRAINT fk_disciplina_deporte FOREIGN KEY (id_deporte) REFERENCES deporte(id_deporte)
) ENGINE=InnoDB;

CREATE TABLE evento (
  id_evento     INT AUTO_INCREMENT PRIMARY KEY,
  nombre        VARCHAR(200) NULL,         -- Event (real max 157)
  id_disciplina INT NULL,
  CONSTRAINT fk_evento_disciplina FOREIGN KEY (id_disciplina) REFERENCES disciplina(id_disciplina)
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- EQUIPO : el 'Team' con que compite el atleta. Apunta al NOC.
-- ---------------------------------------------------------------------
CREATE TABLE equipo (
  id_equipo   INT AUTO_INCREMENT PRIMARY KEY,
  nombre      VARCHAR(120) NOT NULL,       -- Team
  id_noc      INT NULL,
  UNIQUE KEY uq_equipo_nombre_noc (nombre, id_noc),   -- evita duplicar equipos en cargas
  CONSTRAINT fk_equipo_noc FOREIGN KEY (id_noc) REFERENCES noc(id_noc)
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- MEDALLA : catalogo. Normaliza los 4 formatos de "sin medalla" -> 'NA'.
-- ---------------------------------------------------------------------
CREATE TABLE medalla (
  id_medalla  INT AUTO_INCREMENT PRIMARY KEY,
  tipo        ENUM('Gold','Silver','Bronze','NA') NOT NULL,
  UNIQUE KEY uq_medalla_tipo (tipo)
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- PARTICIPACION : tabla de hechos. Una fila = un atleta en un evento de
-- una edicion. altura_reg/peso_reg = valor REGISTRADO esa edicion
-- (de athlete_events), distinto del valor base en ATLETA.
-- 'posicion' es TEXTO (Pos: "DNS","=17","1 h1 r1/4").
-- ---------------------------------------------------------------------
CREATE TABLE participacion (
  id_participacion BIGINT AUTO_INCREMENT PRIMARY KEY,
  id_atleta        INT NULL,
  id_evento        INT NULL,
  id_olimpiada     INT NULL,
  id_equipo        INT NULL,
  id_medalla       INT NOT NULL,           -- apunta a 'NA' si no gano
  compitio_como    VARCHAR(120) NULL,      -- As (results)
  edad             SMALLINT     NULL,      -- Age
  altura_reg       SMALLINT     NULL,      -- Height registrada esa edicion
  peso_reg         DECIMAL(5,2) NULL,      -- Weight registrado esa edicion
  posicion         VARCHAR(30)  NULL,      -- Pos: "1","=17","DNS"
  es_empate        BOOLEAN      DEFAULT FALSE,  -- TRUE si Pos traia "=" (44,115 casos)
  CONSTRAINT fk_part_atleta    FOREIGN KEY (id_atleta)    REFERENCES atleta(id_atleta),
  CONSTRAINT fk_part_evento    FOREIGN KEY (id_evento)    REFERENCES evento(id_evento),
  CONSTRAINT fk_part_olimpiada FOREIGN KEY (id_olimpiada) REFERENCES olimpiada(id_olimpiada),
  CONSTRAINT fk_part_equipo    FOREIGN KEY (id_equipo)    REFERENCES equipo(id_equipo),
  CONSTRAINT fk_part_medalla   FOREIGN KEY (id_medalla)   REFERENCES medalla(id_medalla)
) ENGINE=InnoDB;


-- ---------------------------------------------------------------------
-- POBLACION_PAIS : poblacion por pais y anio (populations.csv, Banco
-- Mundial, 1960-2023). PK compuesta (id_pais, anio). El CSV viene en
-- formato ancho (un anio por columna); en la carga se pivotea a filas.
-- Permite consultas de medallas per capita.
-- ---------------------------------------------------------------------
CREATE TABLE poblacion_pais (
  id_pais    INT      NOT NULL,
  anio       SMALLINT NOT NULL,
  poblacion  BIGINT   NULL,
  PRIMARY KEY (id_pais, anio),
  CONSTRAINT fk_pob_pais FOREIGN KEY (id_pais) REFERENCES pais(id_pais)
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- INDICES para los stored procedures (Persona 3).
-- ---------------------------------------------------------------------
CREATE INDEX idx_atleta_nombre  ON atleta(nombre);
CREATE INDEX idx_atleta_ext     ON atleta(id_externo);
CREATE INDEX idx_pais_nombre    ON pais(nombre);
CREATE INDEX idx_noc_codigo     ON noc(codigo_noc);
CREATE INDEX idx_part_atleta    ON participacion(id_atleta);
CREATE INDEX idx_part_olimpiada ON participacion(id_olimpiada);
CREATE INDEX idx_part_equipo    ON participacion(id_equipo);
CREATE INDEX idx_part_medalla   ON participacion(id_medalla);
CREATE INDEX idx_part_evento    ON participacion(id_evento);
CREATE INDEX idx_evento_disc    ON evento(id_disciplina);
CREATE INDEX idx_disc_deporte   ON disciplina(id_deporte);
CREATE INDEX idx_pob_anio       ON poblacion_pais(anio);

-- ---------------------------------------------------------------------
-- Semilla del catalogo de medallas.
-- ---------------------------------------------------------------------
INSERT INTO medalla (tipo) VALUES ('Gold'),('Silver'),('Bronze'),('NA');
```

---

## 6. Pipeline ETL de Limpieza y Transformación en Python

El flujo de procesamiento programático para la Persona 2 consta de las siguientes fases automatizadas:

```text
[Data Cruda + Limpia de Referencia]
   │
   ├── 1. Normalización de Encodings (CP1252 / Mojibake -> UTF-8)
   ├── 2. Parseo de Fechas, Medidas y Geografía (Regex sobre Born/Died/Measurements)
   ├── 3. Homologación Categórica (Sex: 'Male'/'Female' -> 'M'/'F'; Medallas: NaN -> 'NA')
   ├── 4. Estandarización de Sedes y Ediciones (Games -> Year + Season + City)
   ├── 5. Construcción de Jerarquía Deportiva (Sport -> Discipline -> Event)
   ├── 6. Pivoteo Demográfico (populations.csv de ancho a largo)
   └── 7. Inserción Relacional Transaccional con Respeto de Dependencias
```

### Detalle Operativo por Fase de Transformación

1. **Normalización de Codificación y Caracteres Especiales:**
   * Detección y reparación de caracteres mojibake en nombres y ubicaciones (e.g., `Jean-FranÃ§ois` $\rightarrow$ `Jean-François`).
   * Eliminación del separador bullet (`•`) en nombres de competidores para generar nombres de uso limpios sin alterar grafías originales.
2. **Parseo Biográfico con Expresiones Regulares:**
   * `Born` y `Died`: Extracción de fechas mediante patrones regex flexibles (`r'(\d+ \w+ \d{4}|\d{4})'`) casteados a formato estándar `DATE` (`YYYY-MM-DD`).
   * Ubicación de nacimiento: Aislamiento de componentes con `r'in ([\w\s()-]+), ([\w\s-]+) \((\w+)\)'` para mapear `ciudad_nac`, `region_nac` y código de país de nacimiento.
   * Mediciones físicas: Separación de cadenas `"183 cm / 76 kg"` hacia `altura_cm` y `peso_kg` numéricos continuos.
3. **Mapeo Categórico y Resolución de Nulos:**
   * Unificación de género a dominio estricto: `'Male'` $\rightarrow$ `'M'`, `'Female'` $\rightarrow$ `'F'`.
   * Medallas: Transformación de `NaN`, `'No medal'` o cadenas vacías al valor semilla `'NA'`.
   * Puestos de competencia: Detección del carácter `=` en la columna `Pos` para poblar el flag `es_empate = TRUE` y limpieza del puesto numérico cuando aplique.
4. **Pivoteo Demográfico (World Bank):**
   * Transformación del archivo `populations.csv` aplicando `pandas.melt()` para convertir las columnas `1960` a `2023` en registros individuales de series de tiempo `(id_pais, anio, poblacion)`.

### Orden Estricto de Carga Relacional
Para garantizar la integridad referencial y evitar violaciones de llaves foráneas (`FOREIGN KEY`), las inserciones deben ejecutarse en la siguiente secuencia determinista:
1. `medalla` (Semilla DDL existente)
2. `pais` (derivado de `noc_regions.csv`, `populations.csv` y países de nacimiento)
3. `poblacion_pais` (cruce de `id_pais` con el dataset demográfico desanidado)
4. `noc` (Comités Olímpicos vinculados a su país territorial)
5. `sede` (Ciudades únicas anfitrionas asociadas a su país)
6. `olimpiada` (Ediciones de juegos enlazadas a `id_sede`)
7. `deporte`
8. `disciplina` (asociada a `id_deporte`)
9. `evento` (asociado a `id_disciplina`)
10. `equipo` (vinculado a `id_noc`)
11. `atleta` (maestro biográfico unificado)
12. `participacion` (tabla de hechos unificada)

---

## 7. Requerimientos para los Stored Procedures (Persona 3)

### Procedimiento 1: Historial y Ficha del Atleta
* **Nombre:** `sp_consultar_atleta`
* **Parámetros:**
  * `p_nombre VARCHAR(120)` (Obligatorio: búsqueda flexible por coincidencia de texto `LIKE`)
  * `p_anio SMALLINT` (Opcional: `NULL` para todos los años)
  * `p_deporte VARCHAR(120)` (Opcional: filtro por nombre de deporte)
  * `p_pais VARCHAR(120)` (Opcional: filtro por nombre o código del país que representó)
* **Salida esperada:** Resumen biográfico base (edad, medidas, lugar de nacimiento) y desglose tabular de participaciones (edición, evento, posición, medalla obtenida).

### Procedimiento 2: Desempeño y Registro Histórico por País
* **Nombre:** `sp_consultar_pais`
* **Parámetros:**
  * `p_pais VARCHAR(120)` (Obligatorio: código NOC o nombre del país)
  * `p_anio_inicio SMALLINT` (Opcional: rango temporal inicial)
  * `p_anio_fin SMALLINT` (Opcional: rango temporal final)
  * `p_solo_medallas BOOLEAN` (Opcional: filtrar únicamente participaciones con presea)
* **Salida esperada:** 
  1. Indicador histórico: Si el país ha sido sede olímpica y en qué años específicos (consulta sobre `sede` y `olimpiada`).
  2. Medallero histórico acumulado (Oro, Plata, Bronce, Total).
  3. Desglose agregado por edición y disciplina para evitar volcado masivo de registros en consola.

---

## 8. Diagnóstico del Script y Modelo Actualizado

El esquema `olimpiada2s.sql` y el diagrama `ERD-OLIMIADAS-G18.png` constituyen una base óptima y definitiva:
* Cumple las 15 directrices del catedrático sin omitir columnas con datos reales.
* Posee una arquitectura desacoplada en 3NF para países, comités, sedes y olimpiadas.
* Incluye las restricciones de unicidad (`UNIQUE KEY`) necesarias para evitar duplicados en cargas masivas e idempotentes.
* Cuenta con la indexación requerida para que los procedimientos almacenados de la Persona 3 respondan de forma inmediata.