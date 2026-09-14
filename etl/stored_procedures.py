# -*- coding: utf-8 -*-
"""
Script de verificación y ejecución de Stored Procedures.

Este script:
  1. Conecta a la base de datos 'olimpiadas' en MySQL.
  2. Compila/Crea los dos Stored Procedures (sp_consultar_atleta y sp_consultar_pais).
  3. Ejecuta pruebas de auditoría simulando las consultas requeridas para la calificación.
"""

import sys
import os
from mysql.connector import Error

# Importar utilidades de conexión del proyecto
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from etl.utils import get_connection, print_section, print_ok, print_error, DB_NAME
except ImportError:
    from utils import get_connection, print_section, print_ok, print_error, DB_NAME


def crear_procedimientos():
    """Se conecta a MySQL y compila los procedimientos almacenados."""
    print_section("PERSONA 3: Creacion de Stored Procedures en MySQL")
    conn = get_connection(database=DB_NAME)
    cursor = conn.cursor()

    sp1_drop = "DROP PROCEDURE IF EXISTS sp_consultar_atleta;"
    sp1_create = """
    CREATE PROCEDURE sp_consultar_atleta(
        IN p_nombre VARCHAR(120),
        IN p_anio SMALLINT,
        IN p_deporte VARCHAR(120),
        IN p_pais VARCHAR(120)
    )
    BEGIN
        SELECT 
            a.id_atleta, a.id_externo AS id_olympedia, a.nombre, a.nombre_completo,
            a.sexo, a.fecha_nac, CONCAT(COALESCE(a.ciudad_nac, '-'), ', ', COALESCE(p_nac.nombre, '-')) AS lugar_nacimiento,
            CONCAT(COALESCE(a.altura_cm, '-'), ' cm') AS altura_base, CONCAT(COALESCE(a.peso_kg, '-'), ' kg') AS peso_base,
            a.apodo, a.afiliacion
        FROM atleta a
        LEFT JOIN pais p_nac ON a.id_pais_nac = p_nac.id_pais
        WHERE a.nombre LIKE CONCAT('%', p_nombre, '%')
        LIMIT 10;

        SELECT 
            a.id_atleta,
            a.nombre AS atleta, CONCAT(o.anio, ' ', o.temporada) AS edicion, s.ciudad AS ciudad_sede,
            dep.nombre AS deporte, disc.nombre AS disciplina, e.nombre AS evento, eq.nombre AS equipo,
            pa_eq.codigo_pais AS codigo_pais_rep, p.edad, p.posicion, p.es_empate, m.tipo AS medalla
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
        WHERE a.nombre LIKE CONCAT('%', p_nombre, '%')
          AND (p_anio IS NULL OR o.anio = p_anio)
          AND (p_deporte IS NULL OR dep.nombre LIKE CONCAT('%', p_deporte, '%'))
          AND (p_pais IS NULL OR pa_eq.codigo_pais = p_pais OR pa_eq.nombre LIKE CONCAT('%', p_pais, '%'))
        ORDER BY o.anio ASC, e.nombre ASC;
    END;
    """

    sp2_drop = "DROP PROCEDURE IF EXISTS sp_consultar_pais;"
    sp2_create = """
    CREATE PROCEDURE sp_consultar_pais(
        IN p_pais VARCHAR(120),
        IN p_anio_inicio SMALLINT,
        IN p_anio_fin SMALLINT,
        IN p_solo_medallas BOOLEAN
    )
    BEGIN
        SELECT p.codigo_pais, p.nombre AS pais, s.ciudad AS ciudad_sede, o.anio, o.temporada, o.nombre_juegos
        FROM sede s JOIN pais p ON s.id_pais = p.id_pais JOIN olimpiada o ON o.id_sede = s.id_sede
        WHERE (p.codigo_pais = p_pais OR p.nombre LIKE CONCAT('%', p_pais, '%'))
        ORDER BY o.anio;

        SELECT p.codigo_pais, p.nombre AS pais,
            SUM(m.tipo = 'Gold') AS total_oro, SUM(m.tipo = 'Silver') AS total_plata, SUM(m.tipo = 'Bronze') AS total_bronce,
            SUM(m.tipo IN ('Gold', 'Silver', 'Bronze')) AS total_medallas_podio, COUNT(*) AS total_participaciones_historicas
        FROM participacion part
        JOIN equipo eq ON part.id_equipo = eq.id_equipo JOIN noc n ON eq.id_noc = n.id_noc JOIN pais p ON n.id_pais = p.id_pais
        JOIN medalla m ON part.id_medalla = m.id_medalla JOIN olimpiada o ON part.id_olimpiada = o.id_olimpiada
        WHERE (p.codigo_pais = p_pais OR p.nombre LIKE CONCAT('%', p_pais, '%'))
          AND (p_anio_inicio IS NULL OR o.anio >= p_anio_inicio) AND (p_anio_fin IS NULL OR o.anio <= p_anio_fin)
        GROUP BY p.codigo_pais, p.nombre;

        SELECT o.anio, o.temporada, dep.nombre AS deporte, disc.nombre AS disciplina,
            SUM(m.tipo = 'Gold') AS oro, SUM(m.tipo = 'Silver') AS plata, SUM(m.tipo = 'Bronze') AS bronce,
            COUNT(*) AS total_atletas_participantes
        FROM participacion part
        JOIN equipo eq ON part.id_equipo = eq.id_equipo JOIN noc n ON eq.id_noc = n.id_noc JOIN pais p ON n.id_pais = p.id_pais
        JOIN medalla m ON part.id_medalla = m.id_medalla JOIN olimpiada o ON part.id_olimpiada = o.id_olimpiada
        JOIN evento e ON part.id_evento = e.id_evento JOIN disciplina disc ON e.id_disciplina = disc.id_disciplina JOIN deporte dep ON disc.id_deporte = dep.id_deporte
        WHERE (p.codigo_pais = p_pais OR p.nombre LIKE CONCAT('%', p_pais, '%'))
          AND (p_anio_inicio IS NULL OR o.anio >= p_anio_inicio) AND (p_anio_fin IS NULL OR o.anio <= p_anio_fin)
          AND (p_solo_medallas IS NULL OR p_solo_medallas IS FALSE OR (p_solo_medallas IS TRUE AND m.tipo != 'NA'))
        GROUP BY o.anio, o.temporada, dep.nombre, disc.nombre
        ORDER BY o.anio ASC, dep.nombre ASC;
    END;
    """

    try:
        cursor.execute(sp1_drop)
        cursor.execute(sp1_create)
        print_ok("Procedimiento 'sp_consultar_atleta' creado correctamente.")

        cursor.execute(sp2_drop)
        cursor.execute(sp2_create)
        print_ok("Procedimiento 'sp_consultar_pais' creado correctamente.")

        conn.commit()
    except Error as e:
        print_error(f"Error creando procedimientos almacenados: {e}")
        conn.close()
        return False

    cursor.close()
    conn.close()
    return True


def probar_procedimientos():
    """Ejecuta consultas de prueba llamando a los Stored Procedures con callproc."""
    print_section("PERSONA 3: Ejecucion de Pruebas con Python (callproc)")
    conn = get_connection(database=DB_NAME)
    cursor = conn.cursor()

    try:
        # Prueba 1: sp_consultar_atleta
        print("\n  1. Probando 'sp_consultar_atleta' para 'Jean Borotra':")
        cursor.callproc('sp_consultar_atleta', ['Jean Borotra', None, None, None])
        for result in cursor.stored_results():
            rows = result.fetchall()
            cols = [col[0] for col in result.description]
            print(f"     [Resultado ({len(rows)} filas)]: Columnas: {cols}")
            for r in rows[:3]:
                print(f"       -> {r}")

        # Prueba 2: sp_consultar_pais
        print("\n  2. Probando 'sp_consultar_pais' para 'FRA':")
        cursor.callproc('sp_consultar_pais', ['FRA', 1900, 2024, True])
        for result in cursor.stored_results():
            rows = result.fetchall()
            cols = [col[0] for col in result.description]
            print(f"     [Resultado ({len(rows)} filas)]: Columnas: {cols}")
            for r in rows[:3]:
                print(f"       -> {r}")

        print_ok("Pruebas de Stored Procedures desde Python completadas exitosamente.")
    except Error as e:
        print_error(f"Error ejecutando pruebas de Stored Procedures: {e}")
    finally:
        cursor.close()
        conn.close()


if __name__ == '__main__':
    if crear_procedimientos():
        probar_procedimientos()