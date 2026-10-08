-- ============================================================
-- deportista/03_ronda3_londres2012.sql  (Proyecto 2 - Fase 2, Integrante 2)
-- Ronda: Usain Bolt - Londres 2012
-- Atletas nuevos: 0 | Participaciones: 3
-- Requiere 00_catalogos.sql cargado previamente.
-- IMPORTANTE: cargar contra Docker Fase2 (127.0.0.1:3307), NO el 3306 (P1).
-- Generado automaticamente. NO editar a mano.
-- ============================================================
USE olimpiadas;
SET FOREIGN_KEY_CHECKS = 0;

-- participacion: 3 filas
INSERT INTO `participacion` (`id_participacion`, `id_atleta`, `id_evento`, `id_olimpiada`, `id_equipo`, `id_medalla`, `compitio_como`, `edad`, `altura_reg`, `peso_reg`, `posicion`, `es_empate`) VALUES
(227660, 104492, 43, 52, 580, 1, 'Usain Bolt', 25, 196, 95.00, '1', 0),
(227661, 104492, 467, 52, 580, 1, 'Usain Bolt', 25, 196, 95.00, '1', 0),
(227662, 104492, 400, 52, 580, 1, 'Usain Bolt', 25, 196, 95.00, '1', 0);

SET FOREIGN_KEY_CHECKS = 1;
