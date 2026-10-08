-- ============================================================
-- validacion.sql   (Proyecto 2 - Fase 2, Integrante 2)
-- ------------------------------------------------------------
-- USO: correr DESPUES de cada carga y DESPUES de cada restauracion.
-- El censo de conteos (bloque B) es la evidencia comparable: los
-- numeros tomados antes de borrar la base deben COINCIDIR con los
-- de despues de restaurar. Si no coinciden, hubo perdida de datos.
-- ------------------------------------------------------------
-- Base objetivo: olimpiadas (instancia Docker de Fase2, 127.0.0.1:3307).
-- CUIDADO: conectarse al puerto 3307 (contenedor), NO al 3306 local
--          (ahi vive el P1 con el mismo nombre de base).
-- ============================================================
USE olimpiadas;

-- ------------------------------------------------------------
-- B. CENSO: COUNT(*) de las 12 tablas en un solo resultado.
--    Esta es la evidencia principal de carga/restauracion.
-- ------------------------------------------------------------
SELECT 'pais'           AS tabla, COUNT(*) AS total FROM pais
UNION ALL SELECT 'noc',            COUNT(*) FROM noc
UNION ALL SELECT 'sede',           COUNT(*) FROM sede
UNION ALL SELECT 'olimpiada',      COUNT(*) FROM olimpiada
UNION ALL SELECT 'atleta',         COUNT(*) FROM atleta
UNION ALL SELECT 'deporte',        COUNT(*) FROM deporte
UNION ALL SELECT 'disciplina',     COUNT(*) FROM disciplina
UNION ALL SELECT 'evento',         COUNT(*) FROM evento
UNION ALL SELECT 'equipo',         COUNT(*) FROM equipo
UNION ALL SELECT 'medalla',        COUNT(*) FROM medalla
UNION ALL SELECT 'participacion',  COUNT(*) FROM participacion
UNION ALL SELECT 'poblacion_pais', COUNT(*) FROM poblacion_pais;

-- ------------------------------------------------------------
-- C. FRAGMENTACION de las tablas (InnoDB, via information_schema).
--    'espacio_libre_kb' (DATA_FREE) es el hueco sin usar dentro del
--    tablespace; 'pct_fragmentacion' lo expresa como % del tamano.
--    Sugerencia: para refrescar TABLE_ROWS antes de medir, correr
--    primero  ANALYZE TABLE <tabla>;
-- ------------------------------------------------------------
SELECT
    TABLE_NAME                                    AS tabla,
    TABLE_ROWS                                    AS filas_aprox,
    ROUND(DATA_LENGTH  / 1024, 2)                 AS datos_kb,
    ROUND(INDEX_LENGTH / 1024, 2)                 AS indices_kb,
    ROUND(DATA_FREE    / 1024, 2)                 AS espacio_libre_kb,
    CASE WHEN (DATA_LENGTH + INDEX_LENGTH) > 0
         THEN ROUND(DATA_FREE / (DATA_LENGTH + INDEX_LENGTH) * 100, 2)
         ELSE 0 END                               AS pct_fragmentacion
FROM information_schema.TABLES
WHERE TABLE_SCHEMA = 'olimpiadas'
ORDER BY pct_fragmentacion DESC, tabla;

-- ============================================================
-- D. (Opcional) Muestras SELECT * por tabla.
--    MySQL Workbench limita a 1000 filas por defecto, suficiente
--    para evidenciar los datos. Quitar el "-- " de la linea que
--    se quiera correr, o seleccionarla y ejecutar con Ctrl+Enter.
-- ============================================================
-- SELECT * FROM pais;
-- SELECT * FROM noc;
-- SELECT * FROM sede;
-- SELECT * FROM olimpiada;
-- SELECT * FROM atleta;
-- SELECT * FROM deporte;
-- SELECT * FROM disciplina;
-- SELECT * FROM evento;
-- SELECT * FROM equipo;
-- SELECT * FROM medalla;
-- SELECT * FROM participacion;
-- SELECT * FROM poblacion_pais;
