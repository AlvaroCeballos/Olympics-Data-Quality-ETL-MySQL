# -*- coding: utf-8 -*-
"""
01_cargar_ediciones_paises.py — Fase 3 del Plan de Integrante 2 (Álvaro Ceballos).
Extracción, transformación y carga completa de las colecciones 'ediciones' y 'paises' a MongoDB Atlas.
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

# Importar funciones de extracción y transformación de 03_cargar_datos_mongo
sys.path.append(str(Path(__file__).resolve().parent))
import importlib
etl = importlib.import_module("03_cargar_datos_mongo")

def ejecutar_carga_ediciones_paises():
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_dir = Path(__file__).resolve().parent.parent / 'logs'
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / f"carga_ediciones_paises_{timestamp}.log"

    lineas_log = []

    def log(msg=""):
        print(msg)
        lineas_log.append(msg)

    log("=" * 75)
    log("  FASE 3: CARGA DE COLECCIONES DIMENSIONALES ('ediciones' Y 'paises')   ")
    log(f"  Fecha y Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log(f"  Destino: MongoDB Atlas ('olimpiadas')")
    log("=" * 75)

    # 1. Conexiones
    conn = etl.get_mysql_conn()
    cur = conn.cursor(dictionary=True)
    db, client = etl.get_mongo_db()

    # -------------------------------------------------------------------------
    # 2. Carga de 'ediciones' (63 documentos)
    # -------------------------------------------------------------------------
    log("\n[1/4] EXTRACCIÓN Y TRANSFORMACIÓN DE 'ediciones'...")
    t0 = time.time()
    ediciones_docs = etl.extraer_transformar_ediciones(cur)
    t_extr_ed = time.time() - t0
    log(f"      [OK] Extraídas {len(ediciones_docs)} ediciones con sede embebida en {t_extr_ed:.3f} s")

    log("      Insertando en MongoDB Atlas (colección 'ediciones')...")
    t0 = time.time()
    db.ediciones.delete_many({})
    res_ed = db.ediciones.insert_many(ediciones_docs, ordered=False)
    t_ins_ed = time.time() - t0
    count_ed_mongo = db.ediciones.count_documents({})
    log(f"      [OK] Insertados {len(res_ed.inserted_ids)} documentos en {t_ins_ed:.3f} s")
    log(f"      [CONTEO OFICIAL ATLAS]: {count_ed_mongo} documentos en 'ediciones'")

    # -------------------------------------------------------------------------
    # 3. Carga de 'paises' (487 documentos con sedes y NOCs embebidos)
    # -------------------------------------------------------------------------
    log("\n[2/4] EXTRACCIÓN Y TRANSFORMACIÓN DE 'paises'...")
    t0 = time.time()
    paises_docs = etl.extraer_transformar_paises(cur)
    t_extr_pa = time.time() - t0
    log(f"      [OK] Extraídos {len(paises_docs)} países con NOCs y sedes embebidas en {t_extr_pa:.3f} s")

    log("      Insertando en MongoDB Atlas (colección 'paises')...")
    t0 = time.time()
    db.paises.delete_many({})
    res_pa = db.paises.insert_many(paises_docs, ordered=False)
    t_ins_pa = time.time() - t0
    count_pa_mongo = db.paises.count_documents({})
    log(f"      [OK] Insertados {len(res_pa.inserted_ids)} documentos en {t_ins_pa:.3f} s")
    log(f"      [CONTEO OFICIAL ATLAS]: {count_pa_mongo} documentos en 'paises'")

    # -------------------------------------------------------------------------
    # 4. Muestras de Verificación de Estructura Documental
    # -------------------------------------------------------------------------
    log("\n[3/4] VERIFICACIÓN DE DOCUMENTOS DE MUESTRA:")
    
    # Muestra de edición: París 2024
    sample_ed = db.ediciones.find_one({"anio": 2024, "temporada": "Summer"})
    log(f"\n  • Muestra Colección 'ediciones' (París 2024):")
    log(f"    - ID: {sample_ed.get('_id')}")
    log(f"    - Nombre Juegos: {sample_ed.get('nombre_juegos')}")
    log(f"    - Año/Temporada: {sample_ed.get('anio')} {sample_ed.get('temporada')}")
    log(f"    - Sede Embebida: {sample_ed.get('sede')}")

    # Muestra de país sede histórica: Francia (FRA)
    sample_fra = db.paises.find_one({"codigo": "FRA"})
    log(f"\n  • Muestra Colección 'paises' (Francia - Sede Histórica):")
    log(f"    - ID: {sample_fra.get('_id')}")
    log(f"    - Nombre: {sample_fra.get('nombre')} (Código: {sample_fra.get('codigo')})")
    log(f"    - ¿Es Sede Histórica?: {sample_fra.get('es_sede_historica')}")
    log(f"    - Sedes Albergadas ({len(sample_fra.get('sedes_historicas', []))} ediciones):")
    for s in sample_fra.get('sedes_historicas', []):
        log(f"        * {s['anio']} {s['temporada']} en {s['ciudad']}")
    log(f"    - Comités NOC vinculados: {sample_fra.get('nocs')}")

    # Muestra de país participante no sede: Guatemala (GUA)
    sample_gua = db.paises.find_one({"codigo": "GUA"})
    log(f"\n  • Muestra Colección 'paises' (Guatemala):")
    log(f"    - ID: {sample_gua.get('_id')}")
    log(f"    - Nombre: {sample_gua.get('nombre')} (Código: {sample_gua.get('codigo')})")
    log(f"    - ¿Es Sede Histórica?: {sample_gua.get('es_sede_historica')}")
    log(f"    - Comités NOC vinculados: {sample_gua.get('nocs')}")

    # -------------------------------------------------------------------------
    # 5. Dictamen Final y Validación Censal
    # -------------------------------------------------------------------------
    log("\n" + "=" * 75)
    log("[4/4] DICTAMEN DE RECONCILIACIÓN CENSO FASE 3:")
    ok_ed = (count_ed_mongo == 63)
    ok_pa = (count_pa_mongo == 487)
    
    log(f"  • 'ediciones' : Esperados: 63  | Obtenidos en Mongo: {count_ed_mongo}  --> {'[PARIDAD 100% OK]' if ok_ed else '[DISCREPANCIA]'}")
    log(f"  • 'paises'    : Esperados: 487 | Obtenidos en Mongo: {count_pa_mongo} --> {'[PARIDAD 100% OK]' if ok_pa else '[DISCREPANCIA]'}")
    
    if ok_ed and ok_pa:
        log("  >>> RESULTADO: FASE 3 COMPLETADA EXITOSAMENTE AL 100%")
    else:
        log("  >>> RESULTADO: ALERTA EN CARGA DE COLECCIONES DIMENSIONALES")
    log("=" * 75)

    with open(log_file, 'w', encoding='utf-8') as f:
        f.write("\n".join(lineas_log) + "\n")

    log(f"\n[INFO] Registro de bitácora guardado en: {log_file}")

    cur.close()
    conn.close()
    client.close()
    return ok_ed and ok_pa

if __name__ == '__main__':
    ejecutar_carga_ediciones_paises()
