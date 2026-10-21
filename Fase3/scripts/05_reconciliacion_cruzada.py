# -*- coding: utf-8 -*-
"""
05_reconciliacion_cruzada.py — Fase 6 del Plan de Integrante 2 (Álvaro Ceballos).
Auditoría y reconciliación cruzada exhaustiva: MySQL vs MongoDB Atlas.
Certifica la paridad censal al 100% en atletas, participaciones, países, ediciones y medallas.
"""

import os
import sys
import time
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Cargar variables de entorno
ENV_PATH = Path(__file__).resolve().parent.parent / '.env'
load_dotenv(dotenv_path=ENV_PATH)

# Importar funciones de conexión de 03_cargar_datos_mongo
sys.path.append(str(Path(__file__).resolve().parent))
import importlib
etl = importlib.import_module("03_cargar_datos_mongo")

def ejecutar_reconciliacion():
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_dir = Path(__file__).resolve().parent.parent / 'logs'
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / f"reconciliacion_final_{timestamp}.log"

    lineas_log = []

    def log(msg=""):
        print(msg)
        lineas_log.append(msg)

    log("=" * 80)
    log("     FASE 6: AUDITORÍA Y RECONCILIACIÓN FINAL (MySQL vs MongoDB Atlas)         ")
    log(f"     Fecha y Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log(f"     Origen: MySQL localhost:3306 ('olimpiadas')")
    log(f"     Destino: MongoDB Atlas ('olimpiadas')")
    log("=" * 80)

    conn = etl.get_mysql_conn()
    cur = conn.cursor(dictionary=True)
    db, client = etl.get_mongo_db()

    # 1. Comparativa de Censos Principales
    log("\n[1/3] CONCILIACIÓN DE CONTEOS GLOBALES (ENTIDADES DIANA):")
    log("-" * 80)

    pruebas = [
        ("Ediciones Olímpicas", "SELECT COUNT(*) AS c FROM olimpiada;", "ediciones"),
        ("Catálogo de Países", "SELECT COUNT(*) AS c FROM pais;", "paises"),
        ("Atletas Maestros", "SELECT COUNT(*) AS c FROM atleta;", "atletas"),
        ("Participaciones (Hechos)", "SELECT COUNT(*) AS c FROM participacion;", "resultados")
    ]

    todo_paridad_ok = True

    for label, sql, col_mongo in pruebas:
        cur.execute(sql)
        cnt_mysql = cur.fetchone()['c']
        cnt_mongo = db[col_mongo].count_documents({})
        coincide = (cnt_mysql == cnt_mongo)
        if not coincide:
            todo_paridad_ok = False
        log(f"  • {label:<26} : MySQL = {cnt_mysql:>7,} | Mongo Atlas = {cnt_mongo:>7,} --> {'[PARIDAD 100% OK]' if coincide else '[DISCREPANCIA]'}")

    log("-" * 80)

    # 2. Conciliación de Distribución de Medallas
    log("\n[2/3] CONCILIACIÓN DE DISTRIBUCIÓN DE MEDALLAS EN RESULTADOS:")
    log("-" * 80)
    
    cur.execute("""
        SELECT m.tipo AS medalla, COUNT(*) AS total
        FROM participacion p
        JOIN medalla m ON p.id_medalla = m.id_medalla
        GROUP BY m.tipo
        ORDER BY FIELD(m.tipo, 'Gold', 'Silver', 'Bronze', 'NA');
    """)
    medallas_mysql = {r['medalla']: r['total'] for r in cur.fetchall()}

    med_pipeline = [
        {"$group": {"_id": "$medalla", "total": {"$sum": 1}}}
    ]
    medallas_mongo = {doc['_id']: doc['total'] for doc in db.resultados.aggregate(med_pipeline)}

    for tipo in ['Gold', 'Silver', 'Bronze', 'NA']:
        tot_sql = medallas_mysql.get(tipo, 0)
        tot_mgo = medallas_mongo.get(tipo, 0)
        coincide = (tot_sql == tot_mgo)
        if not coincide:
            todo_paridad_ok = False
        log(f"  • Medalla '{tipo:<6}' : MySQL = {tot_sql:>7,} | Mongo Atlas = {tot_mgo:>7,} --> {'[PARIDAD 100% OK]' if coincide else '[DISCREPANCIA]'}")

    log("-" * 80)

    # 3. Estado de los Índices en MongoDB Atlas
    log("\n[3/3] ESTADO DE ÍNDICES ACTIVOS EN MONGODB ATLAS:")
    for col in ['ediciones', 'paises', 'atletas', 'resultados']:
        idx_info = db[col].index_information()
        log(f"  • Colección '{col}': {len(idx_info)} índices")
        for iname, idata in idx_info.items():
            keys = idata.get('key', [])
            unique = " [UNIQUE]" if idata.get('unique') else ""
            log(f"      - {iname}{unique}: {keys}")

    # Dictamen Final
    log("\n" + "=" * 80)
    if todo_paridad_ok:
        log("  >>> RESULTADO FINAL: CERTIFICACIÓN DE PARIDAD EXITOSA AL 100% <<<")
        log("  La base de datos en MongoDB Atlas se encuentra COMPLETA, ÍNTEGRA y LISTA")
        log("  para las consultas, mediciones de rendimiento y paridad del Integrante 3.")
    else:
        log("  >>> RESULTADO FINAL: SE DETECTARON DISCREPANCIAS EN LA CONCILIACIÓN <<<")
    log("=" * 80)

    with open(log_file, 'w', encoding='utf-8') as f:
        f.write("\n".join(lineas_log) + "\n")

    log(f"\n[INFO] Registro de reconciliación guardado en: {log_file}")

    cur.close()
    conn.close()
    client.close()
    return todo_paridad_ok

if __name__ == '__main__':
    ejecutar_reconciliacion()
