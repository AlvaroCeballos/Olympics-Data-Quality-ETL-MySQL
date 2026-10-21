# -*- coding: utf-8 -*-
"""
00_auditoria_censo_mysql.py — Fase 1 del Plan de Integrante 2 (Álvaro Ceballos).
Auditoría censal completa de las 12 tablas en MySQL ('olimpiadas') e integridad referencial.
"""

import os
import sys
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
import mysql.connector

# Cargar variables de entorno de Fase 3
ENV_PATH = Path(__file__).resolve().parent.parent / '.env'
load_dotenv(dotenv_path=ENV_PATH)

MYSQL_HOST = os.getenv('MYSQL_HOST', 'localhost')
MYSQL_PORT = int(os.getenv('MYSQL_PORT', 3306))
MYSQL_USER = os.getenv('MYSQL_USER', 'root')
MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD', 'admin')
MYSQL_DB = os.getenv('MYSQL_DB', 'olimpiadas')

def auditar_mysql():
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_dir = Path(__file__).resolve().parent.parent / 'logs'
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / f"censo_mysql_{timestamp}.log"

    lineas_log = []

    def log(msg=""):
        print(msg)
        lineas_log.append(msg)

    log("=" * 70)
    log("     FASE 1: AUDITORÍA Y CENSO DE LA BASE DE DATOS MYSQL (ORIGEN)     ")
    log(f"     Fecha y Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log(f"     Servidor: {MYSQL_HOST}:{MYSQL_PORT} | Base de Datos: '{MYSQL_DB}'")
    log("=" * 70)

    try:
        conn = mysql.connector.connect(
            host=MYSQL_HOST,
            port=MYSQL_PORT,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            database=MYSQL_DB
        )
        cur = conn.cursor(dictionary=True)
    except Exception as e:
        log(f"[ERROR CRÍTICO] No se pudo conectar a MySQL: {e}")
        return False

    # 1. Censo de las 12 tablas
    log("\n[1/3] CENSO DETALLADO DE LAS 12 TABLAS RELACIONALES:")
    log("-" * 70)
    log(f"{'No.':<4} | {'Tabla':<20} | {'Total Registros':>18} | {'Estado':<15}")
    log("-" * 70)

    tablas = [
        'pais', 'noc', 'poblacion_pais', 'sede', 'olimpiada',
        'deporte', 'disciplina', 'evento', 'equipo', 'atleta',
        'medalla', 'participacion'
    ]

    conteos = {}
    vacias = 0
    total_filas = 0

    for idx, tabla in enumerate(tablas, 1):
        cur.execute(f"SELECT COUNT(*) AS total FROM {tabla};")
        row = cur.fetchone()
        cnt = row['total']
        conteos[tabla] = cnt
        total_filas += cnt
        estado = "[OK] Poblada" if cnt > 0 else "[ERROR] Vacía"
        if cnt == 0:
            vacias += 1
        log(f"{idx:<4} | {tabla:<20} | {cnt:>18,} | {estado:<15}")

    log("-" * 70)
    log(f"     TOTAL FILAS CONSOLIDADAS: {total_filas:>18,}")
    log("-" * 70)

    # 2. Auditoría de Integridad Referencial (FKs)
    log("\n[2/3] AUDITORÍA DE INTEGRIDAD REFERENCIAL (CLAVES FORÁNEAS):")
    pruebas_fk = [
        ("noc -> pais", "SELECT COUNT(*) AS h FROM noc WHERE id_pais IS NOT NULL AND id_pais NOT IN (SELECT id_pais FROM pais);"),
        ("sede -> pais", "SELECT COUNT(*) AS h FROM sede WHERE id_pais IS NOT NULL AND id_pais NOT IN (SELECT id_pais FROM pais);"),
        ("olimpiada -> sede", "SELECT COUNT(*) AS h FROM olimpiada WHERE id_sede IS NOT NULL AND id_sede NOT IN (SELECT id_sede FROM sede);"),
        ("disciplina -> deporte", "SELECT COUNT(*) AS h FROM disciplina WHERE id_deporte IS NOT NULL AND id_deporte NOT IN (SELECT id_deporte FROM deporte);"),
        ("evento -> disciplina", "SELECT COUNT(*) AS h FROM evento WHERE id_disciplina IS NOT NULL AND id_disciplina NOT IN (SELECT id_disciplina FROM disciplina);"),
        ("equipo -> noc", "SELECT COUNT(*) AS h FROM equipo WHERE id_noc IS NOT NULL AND id_noc NOT IN (SELECT id_noc FROM noc);"),
        ("atleta -> pais (nacimiento)", "SELECT COUNT(*) AS h FROM atleta WHERE id_pais_nac IS NOT NULL AND id_pais_nac NOT IN (SELECT id_pais FROM pais);"),
        ("poblacion_pais -> pais", "SELECT COUNT(*) AS h FROM poblacion_pais WHERE id_pais NOT IN (SELECT id_pais FROM pais);"),
        ("participacion -> atleta", "SELECT COUNT(*) AS h FROM participacion WHERE id_atleta NOT IN (SELECT id_atleta FROM atleta);"),
        ("participacion -> evento", "SELECT COUNT(*) AS h FROM participacion WHERE id_evento NOT IN (SELECT id_evento FROM evento);"),
        ("participacion -> olimpiada", "SELECT COUNT(*) AS h FROM participacion WHERE id_olimpiada NOT IN (SELECT id_olimpiada FROM olimpiada);"),
        ("participacion -> equipo", "SELECT COUNT(*) AS h FROM participacion WHERE id_equipo NOT IN (SELECT id_equipo FROM equipo);"),
        ("participacion -> medalla", "SELECT COUNT(*) AS h FROM participacion WHERE id_medalla NOT IN (SELECT id_medalla FROM medalla);"),
    ]

    errores_fk = 0
    for desc, sql in pruebas_fk:
        cur.execute(sql)
        h = cur.fetchone()['h']
        if h == 0:
            log(f"  • {desc:<35} : [OK] 0 huérfanas")
        else:
            log(f"  • {desc:<35} : [FALLO] {h:,} HUÉRFANAS")
            errores_fk += 1

    # 3. Métricas clave para la migración a Mongo
    log("\n[3/3] MÉTRICAS CLAVE PARA LA MIGRACIÓN A MONGODB:")
    cur.execute("SELECT MIN(anio) AS min_a, MAX(anio) AS max_a FROM olimpiada;")
    r_ed = cur.fetchone()
    log(f"  • Rango de Ediciones Olímpicas   : {r_ed['min_a']} a {r_ed['max_a']} ({conteos['olimpiada']} ediciones)")

    cur.execute("SELECT COUNT(DISTINCT id_atleta) AS atls FROM participacion;")
    atls_part = cur.fetchone()['atls']
    log(f"  • Atletas con participaciones    : {atls_part:,} de {conteos['atleta']:,}")

    cur.execute("""
        SELECT m.tipo, COUNT(*) AS total 
        FROM participacion p 
        JOIN medalla m ON p.id_medalla = m.id_medalla 
        GROUP BY m.tipo 
        ORDER BY FIELD(m.tipo, 'Gold', 'Silver', 'Bronze', 'NA');
    """)
    med_dist = cur.fetchall()
    log("  • Distribución de Medallas en Participación:")
    for md in med_dist:
        log(f"      - {md['tipo']:<8}: {md['total']:>10,} participaciones")

    # Dictamen Final
    log("\n" + "=" * 70)
    if vacias == 0 and errores_fk == 0:
        veredicto = "CERTIFICADO: BASE DE DATOS COMPLETA E ÍNTEGRA PARA MIGRACIÓN A MONGO"
        log(f"  >>> RESULTADO: {veredicto}")
    else:
        veredicto = "ALERTA: SE DETECTARON INCONSISTENCIAS EN LA BASE ORIGEN"
        log(f"  >>> RESULTADO: {veredicto}")
    log("=" * 70)

    with open(log_file, 'w', encoding='utf-8') as f:
        f.write("\n".join(lineas_log) + "\n")

    log(f"\n[INFO] Log guardado exitosamente en: {log_file}")

    cur.close()
    conn.close()
    return True

if __name__ == '__main__':
    auditar_mysql()
