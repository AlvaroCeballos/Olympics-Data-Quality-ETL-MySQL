
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


-- CONTROL 1: Métricas Globales de Completitud y Calidad en 'atleta'

SELECT 
    COUNT(*) AS total_atletas,
    SUM(id_externo IS NOT NULL) AS con_id_externo,
    SUM(sexo IN ('M', 'F')) AS sexo_valido,
    SUM(fecha_nac IS NOT NULL) AS con_fecha_nac,
    SUM(id_pais_nac IS NOT NULL) AS con_pais_nac_fk,
    SUM(latitud IS NOT NULL AND longitud IS NOT NULL) AS con_coords_gps,
    SUM(nombre LIKE '%•%' OR nombre LIKE '%â€¢%') AS con_bullets_error,
    SUM(apodo IS NOT NULL OR titulo IS NOT NULL OR afiliacion IS NOT NULL) AS con_datos_crudos
FROM atleta;

-- CONTROL 4: Muestra Consolidada con Cruce Geográfico y Medidas

SELECT 
    a.id_externo,
    a.nombre,
    a.sexo,
    a.fecha_nac,
    CONCAT(COALESCE(a.ciudad_nac, '-'), ', ', COALESCE(p.codigo_pais, '-')) AS lugar_nac,
    CONCAT(COALESCE(a.altura_cm, '-'), ' cm / ', COALESCE(a.peso_kg, '-'), ' kg') AS medidas,
    ROUND(a.latitud, 4) AS lat,
    ROUND(a.longitud, 4) AS lon
FROM atleta a
LEFT JOIN pais p ON a.id_pais_nac = p.id_pais
ORDER BY a.id_externo
LIMIT 5;

-- 1. Conteo de registros en las 6 tablas de contexto
SELECT 'sede' AS tabla, COUNT(*) AS total FROM sede
UNION ALL SELECT 'olimpiada', COUNT(*) FROM olimpiada
UNION ALL SELECT 'deporte', COUNT(*) FROM deporte
UNION ALL SELECT 'disciplina', COUNT(*) FROM disciplina
UNION ALL SELECT 'evento', COUNT(*) FROM evento
UNION ALL SELECT 'equipo', COUNT(*) FROM equipo;

SELECT 
    (SELECT COUNT(*) FROM sede WHERE id_pais IS NOT NULL AND id_pais NOT IN (SELECT id_pais FROM pais)) AS huerfanas_sede_pais,
    (SELECT COUNT(*) FROM olimpiada WHERE id_sede IS NOT NULL AND id_sede NOT IN (SELECT id_sede FROM sede)) AS huerfanas_olimpiada_sede,
    (SELECT COUNT(*) FROM disciplina WHERE id_deporte IS NOT NULL AND id_deporte NOT IN (SELECT id_deporte FROM deporte)) AS huerfanas_disciplina_deporte,
    (SELECT COUNT(*) FROM evento WHERE id_disciplina IS NOT NULL AND id_disciplina NOT IN (SELECT id_disciplina FROM disciplina)) AS huerfanas_evento_disciplina,
    (SELECT COUNT(*) FROM equipo WHERE id_noc IS NOT NULL AND id_noc NOT IN (SELECT id_noc FROM noc)) AS huerfanas_equipo_noc;


-- 3. Muestra de relaciones resueltas
SELECT o.anio, o.temporada, s.ciudad, p.codigo_pais 
FROM olimpiada o 
JOIN sede s ON o.id_sede = s.id_sede 
LEFT JOIN pais p ON s.id_pais = p.id_pais 
ORDER BY o.anio 
LIMIT 4;

-- 1. Métricas de participaciones y distribución de medallas
SELECT 
    COUNT(*) AS total_participaciones,
    SUM(id_medalla = 4) AS sin_medalla_NA,
    SUM(id_medalla = 3) AS bronce,
    SUM(id_medalla = 2) AS plata,
    SUM(id_medalla = 1) AS oro
FROM participacion;

-- 2. Integridad de Claves Foráneas (todas deben retornar 0)
SELECT 
    (SELECT COUNT(*) FROM participacion WHERE id_atleta NOT IN (SELECT id_atleta FROM atleta)) AS h_atleta,
    (SELECT COUNT(*) FROM participacion WHERE id_evento NOT IN (SELECT id_evento FROM evento)) AS h_evento,
    (SELECT COUNT(*) FROM participacion WHERE id_olimpiada NOT IN (SELECT id_olimpiada FROM olimpiada)) AS h_olimpiada,
    (SELECT COUNT(*) FROM participacion WHERE id_equipo NOT IN (SELECT id_equipo FROM equipo)) AS h_equipo,
    (SELECT COUNT(*) FROM participacion WHERE id_medalla NOT IN (SELECT id_medalla FROM medalla)) AS h_medalla;


-- 3. Muestra de hechos registrados
SELECT 
    a.nombre AS atleta,
    CONCAT(o.anio, ' ', o.temporada) AS edicion,
    e.nombre AS prueba,
    p.posicion,
    m.tipo AS medalla
FROM participacion p
JOIN atleta a ON p.id_atleta = a.id_atleta
JOIN olimpiada o ON p.id_olimpiada = o.id_olimpiada
JOIN evento e ON p.id_evento = e.id_evento
JOIN medalla m ON p.id_medalla = m.id_medalla
ORDER BY p.id_participacion
LIMIT 5;

-- 1. Métricas de Atletas y Participaciones enriquecidas
SELECT 
    (SELECT COUNT(*) FROM atleta) AS total_atletas,
    (SELECT COUNT(*) FROM atleta WHERE id_externo IS NULL) AS atletas_nuevos_kaggle,
    (SELECT COUNT(*) FROM participacion) AS total_participaciones,
    (SELECT COUNT(*) FROM participacion WHERE edad IS NOT NULL) AS participaciones_con_metricas;

-- 2. Integridad de Claves Foráneas (debe retornar 0 huérfanas)
SELECT 
    (SELECT COUNT(*) FROM participacion WHERE id_atleta NOT IN (SELECT id_atleta FROM atleta)) AS h_atleta,
    (SELECT COUNT(*) FROM participacion WHERE id_evento NOT IN (SELECT id_evento FROM evento)) AS h_evento,
    (SELECT COUNT(*) FROM participacion WHERE id_olimpiada NOT IN (SELECT id_olimpiada FROM olimpiada)) AS h_olimpiada,
    (SELECT COUNT(*) FROM participacion WHERE id_equipo NOT IN (SELECT id_equipo FROM equipo)) AS h_equipo,
    (SELECT COUNT(*) FROM participacion WHERE id_medalla NOT IN (SELECT id_medalla FROM medalla)) AS h_medalla;


-- 3. Muestra de participaciones enriquecidas con edad, altura y peso
SELECT 
    a.nombre,
    CONCAT(o.anio, ' ', o.temporada) AS edicion,
    e.nombre AS prueba,
    p.edad,
    CONCAT(COALESCE(p.altura_reg, '-'), ' cm') AS altura,
    CONCAT(COALESCE(p.peso_reg, '-'), ' kg') AS peso,
    m.tipo AS medalla
FROM participacion p
JOIN atleta a ON p.id_atleta = a.id_atleta
JOIN olimpiada o ON p.id_olimpiada = o.id_olimpiada
JOIN evento e ON p.id_evento = e.id_evento
JOIN medalla m ON p.id_medalla = m.id_medalla
WHERE p.edad IS NOT NULL
ORDER BY p.id_participacion DESC
LIMIT 5;


-- 1. Totales consolidados tras la integración de las 3 fuentes
SELECT 
    (SELECT COUNT(*) FROM atleta) AS total_atletas,
    (SELECT COUNT(*) FROM participacion) AS total_participaciones,
    (SELECT COUNT(*) FROM sede) AS total_sedes,
    (SELECT COUNT(*) FROM olimpiada) AS total_olimpiadas,
    (SELECT COUNT(*) FROM evento) AS total_eventos;
    
    
-- 2. Medallero olímpico acumulado en 'participacion'
SELECT 
    m.tipo AS medalla, 
    COUNT(*) AS total_participaciones
FROM participacion p
JOIN medalla m ON p.id_medalla = m.id_medalla
GROUP BY m.tipo
ORDER BY FIELD(m.tipo, 'Gold', 'Silver', 'Bronze', 'NA');



-- 3. Integridad de Claves Foráneas (debe retornar 0 huérfanas)
SELECT 
    (SELECT COUNT(*) FROM participacion WHERE id_atleta NOT IN (SELECT id_atleta FROM atleta)) AS h_atleta,
    (SELECT COUNT(*) FROM participacion WHERE id_evento NOT IN (SELECT id_evento FROM evento)) AS h_evento,
    (SELECT COUNT(*) FROM participacion WHERE id_olimpiada NOT IN (SELECT id_olimpiada FROM olimpiada)) AS h_olimpiada,
    (SELECT COUNT(*) FROM participacion WHERE id_equipo NOT IN (SELECT id_equipo FROM equipo)) AS h_equipo,
    (SELECT COUNT(*) FROM participacion WHERE id_medalla NOT IN (SELECT id_medalla FROM medalla)) AS h_medalla;




-- 1. CENSO GLOBAL DE LAS 12 TABLAS POBLADAS
-- ============================================================================
SELECT 'pais' AS tabla, COUNT(*) AS total FROM pais
UNION ALL SELECT 'noc', COUNT(*) FROM noc
UNION ALL SELECT 'poblacion_pais', COUNT(*) FROM poblacion_pais
UNION ALL SELECT 'sede', COUNT(*) FROM sede
UNION ALL SELECT 'olimpiada', COUNT(*) FROM olimpiada
UNION ALL SELECT 'atleta', COUNT(*) FROM atleta
UNION ALL SELECT 'deporte', COUNT(*) FROM deporte
UNION ALL SELECT 'disciplina', COUNT(*) FROM disciplina
UNION ALL SELECT 'evento', COUNT(*) FROM evento
UNION ALL SELECT 'equipo', COUNT(*) FROM equipo
UNION ALL SELECT 'medalla', COUNT(*) FROM medalla
UNION ALL SELECT 'participacion', COUNT(*) FROM participacion;



-- 2. AUDITORÍA DE LAS 13 CLAVES FORÁNEAS (Todas deben dar 0 huérfanas)
-- ============================================================================
SELECT 
    (SELECT COUNT(*) FROM noc WHERE id_pais IS NOT NULL AND id_pais NOT IN (SELECT id_pais FROM pais)) AS h_noc_pais,
    (SELECT COUNT(*) FROM sede WHERE id_pais IS NOT NULL AND id_pais NOT IN (SELECT id_pais FROM pais)) AS h_sede_pais,
    (SELECT COUNT(*) FROM olimpiada WHERE id_sede IS NOT NULL AND id_sede NOT IN (SELECT id_sede FROM sede)) AS h_olimp_sede,
    (SELECT COUNT(*) FROM disciplina WHERE id_deporte IS NOT NULL AND id_deporte NOT IN (SELECT id_deporte FROM deporte)) AS h_disc_dep,
    (SELECT COUNT(*) FROM evento WHERE id_disciplina IS NOT NULL AND id_disciplina NOT IN (SELECT id_disciplina FROM disciplina)) AS h_ev_disc,
    (SELECT COUNT(*) FROM equipo WHERE id_noc IS NOT NULL AND id_noc NOT IN (SELECT id_noc FROM noc)) AS h_eq_noc,
    (SELECT COUNT(*) FROM atleta WHERE id_pais_nac IS NOT NULL AND id_pais_nac NOT IN (SELECT id_pais FROM pais)) AS h_atl_pais,
    (SELECT COUNT(*) FROM poblacion_pais WHERE id_pais NOT IN (SELECT id_pais FROM pais)) AS h_pob_pais,
    (SELECT COUNT(*) FROM participacion WHERE id_atleta NOT IN (SELECT id_atleta FROM atleta)) AS h_part_atl,
    (SELECT COUNT(*) FROM participacion WHERE id_evento NOT IN (SELECT id_evento FROM evento)) AS h_part_ev,
    (SELECT COUNT(*) FROM participacion WHERE id_olimpiada NOT IN (SELECT id_olimpiada FROM olimpiada)) AS h_part_olimp,
    (SELECT COUNT(*) FROM participacion WHERE id_equipo NOT IN (SELECT id_equipo FROM equipo)) AS h_part_eq,
    (SELECT COUNT(*) FROM participacion WHERE id_medalla NOT IN (SELECT id_medalla FROM medalla)) AS h_part_med;




-- 3. SIMULACIÓN 'sp_consultar_atleta' (Búsqueda de 'Jean Borotra')
-- ============================================================================
SELECT 
    a.nombre AS atleta,
    CONCAT(o.anio, ' ', o.temporada) AS edicion,
    s.ciudad AS sede,
    dep.nombre AS deporte,
    e.nombre AS prueba,
    eq.nombre AS equipo,
    p.posicion,
    m.tipo AS medalla
FROM participacion p
JOIN atleta a ON p.id_atleta = a.id_atleta
JOIN olimpiada o ON p.id_olimpiada = o.id_olimpiada
JOIN sede s ON o.id_sede = s.id_sede
JOIN evento e ON p.id_evento = e.id_evento
JOIN disciplina d ON e.id_disciplina = d.id_disciplina
JOIN deporte dep ON d.id_deporte = dep.id_deporte
JOIN equipo eq ON p.id_equipo = eq.id_equipo
JOIN medalla m ON p.id_medalla = m.id_medalla
WHERE a.nombre LIKE '%Jean Borotra%'
ORDER BY o.anio;




-- 4. SIMULACIÓN 'sp_consultar_pais' (Medallero Histórico de 'FRA')
-- ============================================================================
SELECT 
    pa.codigo_pais,
    pa.nombre AS pais,
    SUM(m.tipo = 'Gold') AS oro,
    SUM(m.tipo = 'Silver') AS plata,
    SUM(m.tipo = 'Bronze') AS bronce,
    COUNT(*) AS total_participaciones
FROM participacion p
JOIN equipo eq ON p.id_equipo = eq.id_equipo
JOIN noc n ON eq.id_noc = n.id_noc
LEFT JOIN pais pa ON n.id_pais = pa.id_pais
JOIN medalla m ON p.id_medalla = m.id_medalla
WHERE pa.codigo_pais = 'FRA'
GROUP BY pa.codigo_pais, pa.nombre;





-- VISTA GENERAL DE LA BASE DE DATOS


SELECT 
    -- 1. HECHO PRINCIPAL
    p.id_participacion,
    
    -- 2. DATOS BIOGRÁFICOS DEL ATLETA
    a.id_atleta,
    a.id_externo AS id_olympedia,
    a.nombre AS atleta,
    a.sexo,
    a.fecha_nac,
    a.ciudad_nac,
    pa_nac.codigo_pais AS pais_nacimiento,
    a.altura_cm AS alt_base,
    a.peso_kg AS peso_base,
    a.apodo,
    a.afiliacion,
    a.latitud,
    a.longitud,
    
    -- 3. MÉTRICAS REGISTRADAS EN LA EDICIÓN
    p.edad,
    p.altura_reg,
    p.peso_reg,
    p.posicion,
    p.es_empate,
    m.tipo AS medalla,
    p.compitio_como,
    
    -- 4. JERARQUÍA DEPORTIVA (3 NIVELES)
    dep.nombre AS deporte,
    d.nombre AS disciplina,
    e.nombre AS evento,
    
    -- 5. EDICIÓN OLÍMPICA Y SEDE
    o.anio,
    o.temporada,
    o.nombre_juegos,
    s.ciudad AS ciudad_sede,
    pa_sede.nombre AS pais_sede,
    
    -- 6. EQUIPO Y DELEGACIÓN
    eq.nombre AS equipo,
    n.codigo_noc,
    pa_noc.nombre AS pais_delegacion
FROM participacion p
JOIN atleta a ON p.id_atleta = a.id_atleta
LEFT JOIN pais pa_nac ON a.id_pais_nac = pa_nac.id_pais
JOIN evento e ON p.id_evento = e.id_evento
JOIN disciplina d ON e.id_disciplina = d.id_disciplina
JOIN deporte dep ON d.id_deporte = dep.id_deporte
JOIN olimpiada o ON p.id_olimpiada = o.id_olimpiada
JOIN sede s ON o.id_sede = s.id_sede
LEFT JOIN pais pa_sede ON s.id_pais = pa_sede.id_pais
JOIN equipo eq ON p.id_equipo = eq.id_equipo
JOIN noc n ON eq.id_noc = n.id_noc
LEFT JOIN pais pa_noc ON n.id_pais = pa_noc.id_pais
JOIN medalla m ON p.id_medalla = m.id_medalla
ORDER BY p.id_participacion;




-- ============================================================================
-- 5. PROCEDIMIENTOS ALMACENADOS OFICIALES (PERSONA 3: Ottoniel Vásquez)
-- ============================================================================

DROP PROCEDURE IF EXISTS sp_consultar_atleta;
DELIMITER //
CREATE PROCEDURE sp_consultar_atleta(
    IN p_nombre VARCHAR(120),
    IN p_anio SMALLINT,
    IN p_deporte VARCHAR(120),
    IN p_pais VARCHAR(120)
)
BEGIN
    -- 1. Ficha Biográfica del Atleta
    SELECT 
        a.id_atleta, 
        a.id_externo AS id_olympedia, 
        a.nombre, 
        a.nombre_completo,
        a.sexo, 
        a.fecha_nac, 
        CONCAT(COALESCE(a.ciudad_nac, '-'), ', ', COALESCE(p_nac.nombre, '-')) AS lugar_nacimiento,
        CONCAT(COALESCE(a.altura_cm, '-'), ' cm') AS altura_base, 
        CONCAT(COALESCE(a.peso_kg, '-'), ' kg') AS peso_base,
        a.apodo, 
        a.afiliacion
    FROM atleta a
    LEFT JOIN pais p_nac ON a.id_pais_nac = p_nac.id_pais
    WHERE a.nombre LIKE CONCAT('%', p_nombre, '%')
       OR (a.nombre_completo IS NOT NULL AND a.nombre_completo LIKE CONCAT('%', p_nombre, '%'))
    LIMIT 10;

    -- 2. Historial Detallado de Participaciones
    SELECT 
        a.id_atleta,
        a.nombre AS atleta, 
        CONCAT(o.anio, ' ', o.temporada) AS edicion, 
        s.ciudad AS ciudad_sede,
        dep.nombre AS deporte, 
        disc.nombre AS disciplina, 
        e.nombre AS evento, 
        eq.nombre AS equipo,
        pa_eq.codigo_pais AS codigo_pais_rep, 
        p.edad, 
        p.posicion, 
        p.es_empate, 
        m.tipo AS medalla
    FROM participacion p
    JOIN atleta a ON p.id_atleta = a.id_atleta
    JOIN olimpiada o ON p.id_olimpiada = o.id_olimpiada
    JOIN sede s ON o.id_sede = s.id_sede
    JOIN evento e ON p.id_evento = e.id_evento
    JOIN disciplina disc ON e.id_disciplina = disc.id_disciplina
    JOIN deporte dep ON disc.id_deporte = dep.id_deporte
    JOIN equipo eq ON p.id_equipo = eq.id_equipo
    JOIN noc n ON eq.id_noc = n.id_noc
    LEFT JOIN pais pa_eq ON n.id_pais = pa_eq.id_pais
    JOIN medalla m ON p.id_medalla = m.id_medalla
    WHERE (a.nombre LIKE CONCAT('%', p_nombre, '%') OR (a.nombre_completo IS NOT NULL AND a.nombre_completo LIKE CONCAT('%', p_nombre, '%')))
      AND (p_anio IS NULL OR o.anio = p_anio)
      AND (p_deporte IS NULL OR dep.nombre LIKE CONCAT('%', p_deporte, '%'))
      AND (
          p_pais IS NULL 
          OR (LENGTH(TRIM(p_pais)) = 3 AND (pa_eq.codigo_pais = UPPER(TRIM(p_pais)) OR n.codigo_noc = UPPER(TRIM(p_pais))))
          OR (LENGTH(TRIM(p_pais)) > 3 AND (pa_eq.nombre = p_pais OR pa_eq.nombre LIKE CONCAT('%', p_pais, '%')))
      )
    ORDER BY o.anio ASC, e.nombre ASC;
END //
DELIMITER ;


DROP PROCEDURE IF EXISTS sp_consultar_pais;
DELIMITER //
CREATE PROCEDURE sp_consultar_pais(
    IN p_pais VARCHAR(120),
    IN p_anio_inicio SMALLINT,
    IN p_anio_fin SMALLINT,
    IN p_solo_medallas BOOLEAN
)
BEGIN
    -- 1. Historial de Sedes Albergadas por el País
    SELECT 
        p.codigo_pais, 
        p.nombre AS pais, 
        s.ciudad AS ciudad_sede, 
        o.anio, 
        o.temporada, 
        o.nombre_juegos
    FROM sede s 
    JOIN pais p ON s.id_pais = p.id_pais 
    JOIN olimpiada o ON o.id_sede = s.id_sede
    WHERE (
        (LENGTH(TRIM(p_pais)) = 3 AND p.codigo_pais = UPPER(TRIM(p_pais)))
        OR (LENGTH(TRIM(p_pais)) > 3 AND (p.nombre = p_pais OR p.nombre LIKE CONCAT('%', p_pais, '%') OR p.nombre_alt LIKE CONCAT('%', p_pais, '%')))
    )
    ORDER BY o.anio;

    -- 2. Medallero Histórico Consolidado del País
    SELECT 
        p.codigo_pais, 
        p.nombre AS pais,
        SUM(m.tipo = 'Gold') AS total_oro, 
        SUM(m.tipo = 'Silver') AS total_plata, 
        SUM(m.tipo = 'Bronze') AS total_bronce,
        SUM(m.tipo IN ('Gold', 'Silver', 'Bronze')) AS total_medallas_podio, 
        COUNT(*) AS total_participaciones_historicas
    FROM participacion part
    JOIN equipo eq ON part.id_equipo = eq.id_equipo 
    JOIN noc n ON eq.id_noc = n.id_noc 
    JOIN pais p ON n.id_pais = p.id_pais
    JOIN medalla m ON part.id_medalla = m.id_medalla 
    JOIN olimpiada o ON part.id_olimpiada = o.id_olimpiada
    WHERE (
        (LENGTH(TRIM(p_pais)) = 3 AND (p.codigo_pais = UPPER(TRIM(p_pais)) OR n.codigo_noc = UPPER(TRIM(p_pais))))
        OR (LENGTH(TRIM(p_pais)) > 3 AND (p.nombre = p_pais OR p.nombre LIKE CONCAT('%', p_pais, '%') OR p.nombre_alt LIKE CONCAT('%', p_pais, '%')))
    )
      AND (p_anio_inicio IS NULL OR o.anio >= p_anio_inicio) 
      AND (p_anio_fin IS NULL OR o.anio <= p_anio_fin)
    GROUP BY p.codigo_pais, p.nombre;

    -- 3. Desglose por Edición y Deporte/Disciplina (Control de volumen, sin SELECT * masivo)
    SELECT 
        o.anio, 
        o.temporada, 
        dep.nombre AS deporte, 
        disc.nombre AS disciplina,
        SUM(m.tipo = 'Gold') AS oro, 
        SUM(m.tipo = 'Silver') AS plata, 
        SUM(m.tipo = 'Bronze') AS bronce,
        COUNT(*) AS total_atletas_participantes
    FROM participacion part
    JOIN equipo eq ON part.id_equipo = eq.id_equipo 
    JOIN noc n ON eq.id_noc = n.id_noc 
    JOIN pais p ON n.id_pais = p.id_pais
    JOIN medalla m ON part.id_medalla = m.id_medalla 
    JOIN olimpiada o ON part.id_olimpiada = o.id_olimpiada
    JOIN evento e ON part.id_evento = e.id_evento 
    JOIN disciplina disc ON e.id_disciplina = disc.id_disciplina 
    JOIN deporte dep ON disc.id_deporte = dep.id_deporte
    WHERE (
        (LENGTH(TRIM(p_pais)) = 3 AND (p.codigo_pais = UPPER(TRIM(p_pais)) OR n.codigo_noc = UPPER(TRIM(p_pais))))
        OR (LENGTH(TRIM(p_pais)) > 3 AND (p.nombre = p_pais OR p.nombre LIKE CONCAT('%', p_pais, '%') OR p.nombre_alt LIKE CONCAT('%', p_pais, '%')))
    )
      AND (p_anio_inicio IS NULL OR o.anio >= p_anio_inicio) 
      AND (p_anio_fin IS NULL OR o.anio <= p_anio_fin)
      AND (p_solo_medallas IS NULL OR p_solo_medallas IS FALSE OR (p_solo_medallas IS TRUE AND m.tipo != 'NA'))
    GROUP BY o.anio, o.temporada, dep.nombre, disc.nombre
    ORDER BY o.anio ASC, dep.nombre ASC;
END //
DELIMITER ;
