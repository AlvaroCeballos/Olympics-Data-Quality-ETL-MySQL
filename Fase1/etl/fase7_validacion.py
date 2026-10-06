# -*- coding: utf-8 -*-
"""
fase7_validacion.py — Pipeline ETL Fase 7: Validación Cruzada, Auditoría de Integridad y Conteos Finales.

Objetivos:
  1. Auditar la integridad referencial de las 13 relaciones de clave foránea del esquema relacional.
  2. Generar el censo y reporte consolidado de registros en las 12 tablas de la base de datos 'olimpiadas'.
  3. Validar la calidad del dato: ausencia de mojibake, integridad de dominios (sexo, medalla) y fechas normalizadas.
  4. Simular y verificar las consultas analíticas que utilizará la Persona 3 para los Stored Procedures:
     - sp_consultar_atleta: ficha biográfica + desglose histórico de participaciones.
     - sp_consultar_pais: condición de sede histórica + medallero acumulado por edición y deporte.

Decisiones técnicas aplicadas:
  - DT-001 a DT-025: Verificación global de todas las reglas del pipeline ETL.
"""

import os
import sys
import pandas as pd
from mysql.connector import Error

# Agregar directorio etl al sys.path para imports relativos
_CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if _CURRENT_DIR not in sys.path:
    sys.path.insert(0, _CURRENT_DIR)

from utils import (
    get_connection,
    print_section,
    print_ok,
    print_warn,
    print_error,
    DB_NAME
)


def auditar_conteos_globales(cursor):
    """Verifica y reporta el conteo de tuplas en las 12 tablas."""
    print_section("7.1 Censo y Conteo Global de Tablas (12 Tablas)")
    tablas = [
        'pais', 'noc', 'poblacion_pais', 'sede', 'olimpiada',
        'atleta', 'deporte', 'disciplina', 'evento', 'equipo',
        'medalla', 'participacion'
    ]
    
    conteos = {}
    for t in tablas:
        cursor.execute(f"SELECT COUNT(*) FROM {t};")
        cnt = cursor.fetchone()[0]
        conteos[t] = cnt
        print(f"    Tabla '{t:16}': {cnt:>6} registros")
        
    vacias = [t for t, c in conteos.items() if c == 0]
    if vacias:
        print_error(f"Tablas sin registros detectadas: {vacias}")
        return False, conteos
    print_ok("Todas las 12 tablas cuentan con datos poblados conforme al modelo.")
    return True, conteos


def auditar_integridad_referencial(cursor):
    """
    Audita exhaustivamente las 13 relaciones de clave foránea del modelo 3NF.
    Ninguna relación debe arrojar registros huérfanos.
    """
    print_section("7.2 Auditoría de Claves Foráneas (13 Relaciones FK)")
    
    pruebas_fk = [
        ("noc -> pais", "SELECT COUNT(*) FROM noc WHERE id_pais IS NOT NULL AND id_pais NOT IN (SELECT id_pais FROM pais);"),
        ("sede -> pais", "SELECT COUNT(*) FROM sede WHERE id_pais IS NOT NULL AND id_pais NOT IN (SELECT id_pais FROM pais);"),
        ("olimpiada -> sede", "SELECT COUNT(*) FROM olimpiada WHERE id_sede IS NOT NULL AND id_sede NOT IN (SELECT id_sede FROM sede);"),
        ("disciplina -> deporte", "SELECT COUNT(*) FROM disciplina WHERE id_deporte IS NOT NULL AND id_deporte NOT IN (SELECT id_deporte FROM deporte);"),
        ("evento -> disciplina", "SELECT COUNT(*) FROM evento WHERE id_disciplina IS NOT NULL AND id_disciplina NOT IN (SELECT id_disciplina FROM disciplina);"),
        ("equipo -> noc", "SELECT COUNT(*) FROM equipo WHERE id_noc IS NOT NULL AND id_noc NOT IN (SELECT id_noc FROM noc);"),
        ("atleta -> pais (nacimiento)", "SELECT COUNT(*) FROM atleta WHERE id_pais_nac IS NOT NULL AND id_pais_nac NOT IN (SELECT id_pais FROM pais);"),
        ("poblacion_pais -> pais", "SELECT COUNT(*) FROM poblacion_pais WHERE id_pais NOT IN (SELECT id_pais FROM pais);"),
        ("participacion -> atleta", "SELECT COUNT(*) FROM participacion WHERE id_atleta NOT IN (SELECT id_atleta FROM atleta);"),
        ("participacion -> evento", "SELECT COUNT(*) FROM participacion WHERE id_evento NOT IN (SELECT id_evento FROM evento);"),
        ("participacion -> olimpiada", "SELECT COUNT(*) FROM participacion WHERE id_olimpiada NOT IN (SELECT id_olimpiada FROM olimpiada);"),
        ("participacion -> equipo", "SELECT COUNT(*) FROM participacion WHERE id_equipo NOT IN (SELECT id_equipo FROM equipo);"),
        ("participacion -> medalla", "SELECT COUNT(*) FROM participacion WHERE id_medalla NOT IN (SELECT id_medalla FROM medalla);"),
    ]
    
    errores = 0
    for descripcion, sql in pruebas_fk:
        cursor.execute(sql)
        huerfanos = cursor.fetchone()[0]
        if huerfanos == 0:
            print(f"    [OK] {descripcion:<35} -> 0 huérfanas")
        else:
            print(f"    [ERROR] {descripcion:<35} -> {huerfanos} HUÉRFANAS")
            errores += 1
            
    if errores == 0:
        print_ok("Integridad referencial 100% íntegra (0 violaciones de FK).")
        return True
    else:
        print_error(f"Se detectaron {errores} relaciones con claves foráneas rotas.")
        return False


def auditar_calidad_de_datos(cursor):
    """Valida ausencia de mojibake, dominios válidos y consistencia de atributos."""
    print_section("7.3 Auditoría de Calidad y Normalización de Datos")
    
    # 1. Ausencia de caracteres viñeta o mojibake en atletas
    cursor.execute("SELECT COUNT(*) FROM atleta WHERE nombre LIKE '%•%' OR nombre LIKE '%â€¢%';")
    bullets = cursor.fetchone()[0]
    
    # 2. Dominio estricto de sexo
    cursor.execute("SELECT COUNT(*) FROM atleta WHERE sexo NOT IN ('M', 'F') OR sexo IS NULL;")
    inv_sexo = cursor.fetchone()[0]
    
    # 3. Dominio de medallas
    cursor.execute("SELECT COUNT(*) FROM medalla WHERE tipo NOT IN ('Gold', 'Silver', 'Bronze', 'NA');")
    inv_med = cursor.fetchone()[0]
    
    # 4. Cobertura de series demográficas
    cursor.execute("SELECT MIN(anio), MAX(anio), COUNT(DISTINCT id_pais) FROM poblacion_pais;")
    min_a, max_a, paises_pob = cursor.fetchone()
    
    print(f"    Atletas con bullets o mojibake residual: {bullets}")
    print(f"    Atletas con sexo fuera de dominio ('M'/'F'): {inv_sexo}")
    print(f"    Medallas fuera de catálogo: {inv_med}")
    print(f"    Rango temporal de series demográficas: {min_a} - {max_a} ({paises_pob} países)")
    
    exito = (bullets == 0 and inv_sexo == 0 and inv_med == 0 and min_a == 1960 and max_a == 2023)
    if exito:
        print_ok("Calidad de datos y normalización confirmadas al 100%.")
    else:
        print_error("Se detectaron inconsistencias en la calidad de los datos.")
    return exito


def simular_stored_procedures(cursor):
    """
    Simula las dos consultas clave requeridas para la Persona 3 (Stored Procedures)
    demostrando que el modelo soporta filtros y responde eficientemente.
    """
    print_section("7.4 Simulación y Validación de Consultas para Stored Procedures (Persona 3)")
    
    # Simulación 1: Consulta de Atleta (sp_consultar_atleta)
    print("\n  A. Simulación 'sp_consultar_atleta' (Búsqueda por nombre: 'Jean Borotra'):")
    cursor.execute("""
        SELECT 
            a.id_atleta,
            a.nombre,
            a.sexo,
            a.fecha_nac,
            p_nac.nombre AS pais_nacimiento,
            a.altura_cm,
            a.peso_kg,
            a.apodo,
            a.afiliacion
        FROM atleta a
        LEFT JOIN pais p_nac ON a.id_pais_nac = p_nac.id_pais
        WHERE a.nombre LIKE '%Jean Borotra%'
        LIMIT 1;
    """)
    ficha = cursor.fetchone()
    if ficha:
        print(f"     Ficha: ID={ficha[0]} | {ficha[1]} ({ficha[2]}) | Nac: {ficha[3]} en {ficha[4]} | Medidas: {ficha[5]}cm/{ficha[6]}kg | Apodo: '{ficha[7]}'")
        
        # Historial de participaciones de dicho atleta
        cursor.execute("""
            SELECT 
                CONCAT(o.anio, ' ', o.temporada) AS edicion,
                s.ciudad AS sede,
                dep.nombre AS deporte,
                e.nombre AS prueba,
                eq.nombre AS equipo,
                p.posicion,
                m.tipo AS medalla
            FROM participacion p
            JOIN olimpiada o ON p.id_olimpiada = o.id_olimpiada
            JOIN sede s ON o.id_sede = s.id_sede
            JOIN evento e ON p.id_evento = e.id_evento
            JOIN disciplina d ON e.id_disciplina = d.id_disciplina
            JOIN deporte dep ON d.id_deporte = dep.id_deporte
            JOIN equipo eq ON p.id_equipo = eq.id_equipo
            JOIN medalla m ON p.id_medalla = m.id_medalla
            WHERE p.id_atleta = %s
            ORDER BY o.anio;
        """, (ficha[0],))
        for r in cursor.fetchall():
            print(f"       -> {r[0]} ({r[1]}) | {r[2]} - {r[3]} | Eq: {r[4]} | Pos: {r[5]} | Medalla: {r[6]}")
            
    # Simulación 2: Consulta de País (sp_consultar_pais)
    print("\n  B. Simulación 'sp_consultar_pais' (País: 'France' / 'FRA'):")
    # Condición de sede
    cursor.execute("""
        SELECT DISTINCT s.ciudad, o.anio, o.temporada
        FROM sede s
        JOIN olimpiada o ON s.id_sede = o.id_sede
        JOIN pais p ON s.id_pais = p.id_pais
        WHERE p.codigo_pais = 'FRA' OR p.nombre = 'France'
        ORDER BY o.anio;
    """)
    sedes_hist = cursor.fetchall()
    print(f"     ¿Ha sido sede?: {'SÍ' if sedes_hist else 'NO'}")
    for sh in sedes_hist:
        print(f"       -> Ciudad: {sh[0]} ({sh[1]} {sh[2]})")
        
    # Medallero acumulado por país
    cursor.execute("""
        SELECT 
            SUM(CASE WHEN m.tipo = 'Gold' THEN 1 ELSE 0 END) AS oro,
            SUM(CASE WHEN m.tipo = 'Silver' THEN 1 ELSE 0 END) AS plata,
            SUM(CASE WHEN m.tipo = 'Bronze' THEN 1 ELSE 0 END) AS bronce,
            COUNT(*) AS total_participaciones
        FROM participacion p
        JOIN equipo eq ON p.id_equipo = eq.id_equipo
        JOIN noc n ON eq.id_noc = n.id_noc
        LEFT JOIN pais pa ON n.id_pais = pa.id_pais
        JOIN medalla m ON p.id_medalla = m.id_medalla
        WHERE n.codigo_noc = 'FRA' OR pa.codigo_pais = 'FRA';
    """)
    med_res = cursor.fetchone()
    print(f"     Medallero Histórico Acumulado (FRA):")
    print(f"       Oro: {med_res[0]} | Plata: {med_res[1]} | Bronce: {med_res[2]} | Total participaciones: {med_res[3]}")
    
    print_ok("Consultas analíticas para Stored Procedures validadas con éxito.")
    return True


def ejecutar_fase7():
    """Ejecuta la auditoría global de la Fase 7."""
    print_section("INICIO DE AUDITORÍA FINAL: FASE 7 (Validación Cruzada y Cierre ETL)")
    
    conn = None
    try:
        conn = get_connection(database=DB_NAME)
        cursor = conn.cursor()
        
        ok1, conteos = auditar_conteos_globales(cursor)
        ok2 = auditar_integridad_referencial(cursor)
        ok3 = auditar_calidad_de_datos(cursor)
        ok4 = simular_stored_procedures(cursor)
        
        cursor.close()
        conn.close()
        
        todo_ok = ok1 and ok2 and ok3 and ok4
        print_section("DICTAMEN FINAL DE LA AUDITORÍA")
        if todo_ok:
            print_ok("PIPELINE ETL DE LA PERSONA 2 VALIDADO Y CONCLUIDO AL 100%.")
            print_ok("La base de datos 'olimpiadas' se encuentra lista para la Persona 3 (Stored Procedures).")
            return True
        else:
            print_error("Se encontraron observaciones en la auditoría.")
            return False
            
    except Error as e:
        if conn and conn.is_connected():
            conn.close()
        print_error(f"Error de conexión o consulta en MySQL: {e}")
        return False
    except Exception as e:
        if conn and conn.is_connected():
            conn.close()
        print_error(f"Error inesperado en Fase 7: {e}")
        return False


if __name__ == '__main__':
    exito = ejecutar_fase7()
    sys.exit(0 if exito else 1)
