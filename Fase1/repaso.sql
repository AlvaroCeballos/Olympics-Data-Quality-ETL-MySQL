-- Quien gano oro en atletismo en 2008?

-- Quien -> nombre -> TABLA ATLETA 
-- Gano oro -> TABLA MEDALLA  -> where = oro
-- Atletismo -> TABLA DEPORTE -> Atletismo                        deporte <- disciplina <- evento <- p
-- En 2008 -> TABLA OLIMPIADA  -> anio =  2008 

SELECT a.nombre
FROM participacion p 
JOIN atleta a ON p.id_atleta = a.id_atleta 
JOIN medalla m ON p.id_medalla = m.id_medalla
JOIN evento e ON p.id_evento = e.id_evento 
JOIN disciplina d ON e.id_disciplina = d.id_disciplina
JOIN deporte dep ON d.id_deporte = dep.id_deporte
JOIN olimpiada o ON p.id_olimpiada = o.id_olimpiada
WHERE m.tipo = 'Gold'
	AND dep.nombre = 'Athletics'
    AND o.anio = 2008;
    
-- Quienes son los medallistas de guate 
    
-- nombre TABLA ATLETA     
-- TABLA MEDALLA  -> cualquiera
-- tabla pais    -> GUA                 pais <- noc <- equipo <-p

SELECT a.nombre, m.tipo
FROM participacion p 
JOIN atleta a ON p.id_atleta = a.id_atleta
JOIN medalla m ON p.id_medalla = m.id_medalla
JOIN equipo eq ON p.id_equipo = eq.id_equipo
JOIN noc n ON eq.id_noc = n.id_noc 
JOIN pais pa ON n.id_pais = pa.id_pais
WHERE pa.nombre = 'Guatemala'
	AND m.tipo != 'NA';
    
-- quien ganó la medalla de oro en 100 metros planos en el año 2004 (variantes: diferentes disciplinas o diferentes años) 
    
-- TABLA ATLETA
-- TABLA MEDALLA filtro: gold
-- TABLA EVENTO 
-- TABLA DEPORTE filtro: atletismo, 100 metros
-- TABLA OLIMPIADA filtro: anio 2004

SELECT a.nombre
FROM participacion p
JOIN atleta a ON p.id_atleta = a.id_atleta 
JOIN medalla m ON p.id_medalla = m.id_medalla
JOIN evento e ON p.id_evento = e.id_evento 
JOIN disciplina d ON e.id_disciplina = d.id_disciplina
JOIN deporte dep ON d.id_deporte = dep.id_deporte
JOIN olimpiada o ON p.id_olimpiada = o.id_olimpiada
WHERE m.tipo = 'Gold'
	AND dep.nombre LIKE '%Athletics%' 
    AND e.nombre LIKE '%100 metres%'
    AND o.anio = 2004;

-- quien es el atleta con más medallas de oro y de que pais y que sea mujer (variantes: menos medallas, más de bronce, más de plata... definiendo o no definiendo un deporte en específico) 

-- TABLA ATLETA
-- TABLA MEDALLA
-- TABLA PAIS 

SELECT a.nombre, m.tipo, pa.nombre AS pais, a.sexo, COUNT(*) AS total 
FROM participacion p
JOIN atleta a ON p.id_atleta = a.id_atleta
JOIN medalla m ON p.id_medalla = m.id_medalla
JOIN equipo eq ON p.id_equipo = eq.id_equipo
JOIN noc n ON eq.id_noc = n.id_noc 
JOIN pais pa ON n.id_pais = pa.id_pais
WHERE m.tipo = 'Gold'
	AND a.sexo = 'F'
  group by  a.id_atleta, a.nombre_completo, pa.nombre
  ORDER BY total DESC LIMIT 1;


-- quien ganó medalla de oro siendo el más joven (para utilizar campo edad) */

SELECT a.nombre, p.edad
FROM participacion p
JOIN atleta a ON p.id_atleta = a.id_atleta
JOIN medalla m ON p.id_medalla = m.id_medalla
WHERE m.tipo = 'Gold'
  AND p.edad IS NOT NULL
ORDER BY p.edad ASC LIMIT 1;



	
    
