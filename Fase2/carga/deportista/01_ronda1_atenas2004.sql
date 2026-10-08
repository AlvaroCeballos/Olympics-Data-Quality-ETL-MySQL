-- ============================================================
-- deportista/01_ronda1_atenas2004.sql  (Proyecto 2 - Fase 2, Integrante 2)
-- Ronda: Usain Bolt - Atenas 2004
-- Atletas nuevos: 1 | Participaciones: 1
-- Requiere 00_catalogos.sql cargado previamente.
-- IMPORTANTE: cargar contra Docker Fase2 (127.0.0.1:3307), NO el 3306 (P1).
-- Generado automaticamente. NO editar a mano.
-- ============================================================
USE olimpiadas;
SET FOREIGN_KEY_CHECKS = 0;

-- atleta: 1 filas nuevas
INSERT INTO `atleta` (`id_atleta`, `id_externo`, `nombre`, `nombre_completo`, `otros_nombres`, `nombre_original`, `orden_nombre`, `apodo`, `titulo`, `afiliacion`, `sexo`, `fecha_nac`, `ciudad_nac`, `region_nac`, `id_pais_nac`, `fecha_muerte`, `altura_cm`, `peso_kg`, `roles`, `nacionalidad`, `latitud`, `longitud`) VALUES
(104492, 105512, 'Usain Bolt', 'Usain St. Leo Bolt', NULL, NULL, NULL, 'Lightning Bolt', NULL, 'Racers Track Club, Kingston (JAM)', 'M', '1986-08-21', 'Sherwood Content', 'Trelawny', 118, NULL, 196.00, 95.00, 'Competed in Olympic Games Other', NULL, NULL, NULL);

-- participacion: 1 filas
INSERT INTO `participacion` (`id_participacion`, `id_atleta`, `id_evento`, `id_olimpiada`, `id_equipo`, `id_medalla`, `compitio_como`, `edad`, `altura_reg`, `peso_reg`, `posicion`, `es_empate`) VALUES
(227656, 104492, 467, 47, 580, 4, 'Usain Bolt', 17, 196, 95.00, '5 h4 r1/4', 0);

SET FOREIGN_KEY_CHECKS = 1;
