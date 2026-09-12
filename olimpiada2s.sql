
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


USE olimpiadas;
-- Listar todas las tablas creadas en el esquema
SHOW FULL TABLES;

SELECT * FROM medalla;


SELECT 'pais' AS tabla, COUNT(*) AS total FROM pais
UNION ALL SELECT 'noc', COUNT(*) FROM noc
UNION ALL SELECT 'sede', COUNT(*) FROM sede
UNION ALL SELECT 'olimpiada', COUNT(*) FROM olimpiada
UNION ALL SELECT 'deporte', COUNT(*) FROM deporte
UNION ALL SELECT 'disciplina', COUNT(*) FROM disciplina
UNION ALL SELECT 'evento', COUNT(*) FROM evento
UNION ALL SELECT 'equipo', COUNT(*) FROM equipo
UNION ALL SELECT 'atleta', COUNT(*) FROM atleta
UNION ALL SELECT 'participacion', COUNT(*) FROM participacion
UNION ALL SELECT 'medalla', COUNT(*) FROM medalla
UNION ALL SELECT 'poblacion_pais', COUNT(*) FROM poblacion_pais;

SELECT id_pais, codigo_pais, nombre, nombre_alt, region 
FROM pais 
ORDER BY id_pais;


-- Demuestra que los Comités Olímpicos están correctamente vinculados a su país
SELECT 
    n.id_noc,
    n.codigo_noc, 
    n.nombre_noc, 
    n.notas,
    p.id_pais,
    p.codigo_pais, 
    p.nombre AS nombre_pais_asociado
FROM noc n
JOIN pais p ON n.id_pais = p.id_pais
ORDER BY n.id_noc;

-- Resumen de años y conteo de registros por país (pivoteo de 1960 a 2023)
SELECT 
    p.codigo_pais, 
    p.nombre, 
    COUNT(*) AS total_anios_registrados, 
    MIN(pp.anio) AS anio_inicio, 
    MAX(pp.anio) AS anio_fin,
    MIN(pp.poblacion) AS pob_minima,
    MAX(pp.poblacion) AS pob_maxima
FROM poblacion_pais pp
JOIN pais p ON pp.id_pais = p.id_pais
GROUP BY p.codigo_pais, p.nombre
ORDER BY p.nombre;


