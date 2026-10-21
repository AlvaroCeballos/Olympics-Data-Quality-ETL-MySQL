# -*- coding: utf-8 -*-
"""
02_cargar_atletas.py — Fase 4 del Plan de Integrante 2 (Álvaro Ceballos).
Extracción, transformación y carga masiva de los 190,471 atletas a MongoDB Atlas en lotes.
Incluye cálculo de nombre_norm y arreglo de tokens multikey con normalize_name (DT-002 / DT-027).
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

# Importar funciones de extracción de 03_cargar_datos_mongo
sys.path.append(str(Path(__file__).resolve().parent))
import importlib
etl = importlib.import_module("03_cargar_datos_mongo")
normalize_name = etl.normalize_name
clean_val = etl.clean_val

def extraer_transformar_lote_atletas(cur, offset, limit):
    """Extrae un lote de atletas y calcula nombre_norm y tokens multikey."""
    sql = f"""
        SELECT a.id_atleta, a.id_externo, a.nombre, a.nombre_completo, a.otros_nombres,
               a.nombre_original, a.orden_nombre, a.apodo, a.titulo, a.afiliacion,
               a.sexo, a.fecha_nac, a.ciudad_nac, a.region_nac, a.fecha_muerte,
               a.altura_cm, a.peso_kg, a.roles, a.nacionalidad,
               p.codigo_pais AS pais_nac_codigo, p.nombre AS pais_nac_nombre
        FROM atleta a
        LEFT JOIN pais p ON a.id_pais_nac = p.id_pais
        ORDER BY a.id_atleta ASC
        LIMIT {limit} OFFSET {offset};
    """
    cur.execute(sql)
    atletas = []
    for a in cur.fetchall():
        norm = normalize_name(a['nombre']) if a['nombre'] else ''
        norm_comp = normalize_name(a['nombre_completo']) if a.get('nombre_completo') else ''
        # Tokens únicos de nombre y nombre_completo (longitud >= 2)
        palabras = (norm + ' ' + norm_comp).split()
        tokens = list(dict.fromkeys([t for t in palabras if len(t) >= 2]))

        doc = {
            "_id": a['id_atleta'],
            "id_externo": a['id_externo'],
            "nombre": a['nombre'],
            "nombre_norm": norm,
            "tokens": tokens,
            "nombre_completo": a['nombre_completo'],
            "otros_nombres": a['otros_nombres'],
            "nombre_original": a['nombre_original'],
            "apodo": a['apodo'],
            "titulo": a['titulo'],
            "afiliacion": a['afiliacion'],
            "sexo": a['sexo'],
            "fecha_nac": clean_val(a['fecha_nac']),
            "ciudad_nac": a['ciudad_nac'],
            "region_nac": a['region_nac'],
            "fecha_muerte": clean_val(a['fecha_muerte']),
            "pais_nacimiento": {
                "codigo": a['pais_nac_codigo'],
                "nombre": a['pais_nac_nombre']
            } if a['pais_nac_codigo'] else None,
            "altura_cm": clean_val(a['altura_cm']),
            "peso_kg": clean_val(a['peso_kg']),
            "roles": a['roles'],
            "nacionalidad": a['nacionalidad']
        }
        # Filtrar atributos nulos para optimizar almacenamiento BSON
        doc_filtrado = {k: v for k, v in doc.items() if v is not None}
        atletas.append(doc_filtrado)
    return atletas

def ejecutar_carga_atletas(batch_size=20000, force_reload=False):
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_dir = Path(__file__).resolve().parent.parent / 'logs'
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / f"carga_atletas_{timestamp}.log"

    lineas_log = []

    def log(msg=""):
        print(msg)
        lineas_log.append(msg)

    log("=" * 75)
    log("       FASE 4: EXTRACCIÓN Y CARGA MASIVA DE ATLETAS ('atletas')        ")
    log(f"       Fecha y Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log(f"       Destino: MongoDB Atlas ('olimpiadas.atletas')")
    log("=" * 75)

    conn = etl.get_mysql_conn()
    cur = conn.cursor(dictionary=True)
    db, client = etl.get_mongo_db()

    # Total de atletas a procesar
    cur.execute("SELECT COUNT(*) AS total FROM atleta;")
    total_atletas = cur.fetchone()['total']
    log(f"\n[1/4] CENSO DE ATLETAS EN ORIGEN (MySQL): {total_atletas:,} registros.")

    conteo_previo = db.atletas.count_documents({})
    if not force_reload and conteo_previo == total_atletas:
        log(f"\n[2/4] [INFO] La colección 'atletas' ya cuenta con los {conteo_previo:,} documentos cargados.")
        log("      Se omite la reinserción en red (modo idempotente).")
        total_insertados = conteo_previo
    else:
        log("\n[2/4] LIMPIEZA PREVIA E INSERCIÓN EN LOTES EN MONGODB ATLAS...")
        db.atletas.delete_many({})
        log("      Colección 'atletas' vaciada para carga limpia y reproducible.")

        total_insertados = 0
        offset = 0
        lote_num = 1
        total_lotes = (total_atletas + batch_size - 1) // batch_size
        t_inicio_global = time.time()

        while offset < total_atletas:
            limite_actual = min(batch_size, total_atletas - offset)
            t0 = time.time()
            lote = extraer_transformar_lote_atletas(cur, offset=offset, limit=limite_actual)
            t_extr = time.time() - t0

            t0 = time.time()
            res = db.atletas.insert_many(lote, ordered=False)
            t_ins = time.time() - t0
            cant_ins = len(res.inserted_ids)
            total_insertados += cant_ins

            tasa = cant_ins / t_ins if t_ins > 0 else 0
            pct = (total_insertados / total_atletas) * 100

            log(f"      • Lote {lote_num:02d}/{total_lotes:02d}: Insertados {cant_ins:>6,} docs | Extr: {t_extr:.2f}s | Ins: {t_ins:.2f}s ({tasa:,.0f} docs/s) | Progreso: {pct:>5.1f}%")

            offset += limite_actual
            lote_num += 1

        t_total_global = time.time() - t_inicio_global
        tasa_global = total_insertados / t_total_global if t_total_global > 0 else 0

        log("\n" + "-" * 75)
        log(f"      RESUMEN CARGA: {total_insertados:,} atletas insertados en {t_total_global:.2f} s ({tasa_global:,.0f} docs/s promedio)")
        log("-" * 75)

    # 3. Verificación de conteo e inspección de muestras
    log("\n[3/4] VERIFICACIÓN DE CONTEO Y DOCUMENTOS DE MUESTRA EN ATLAS:")
    conteo_atlas = db.atletas.count_documents({})
    log(f"      Conteo oficial en Atlas: {conteo_atlas:,} documentos.")

    # Muestra 1: Atleta olímpico histórico (Usain Bolt)
    sample_bolt = db.atletas.find_one({"nombre_norm": "usain bolt"})
    if sample_bolt:
        log(f"\n  • Muestra Atleta 1 (Usain Bolt):")
        log(f"    - ID: {sample_bolt.get('_id')} | ID Olympedia: {sample_bolt.get('id_externo')}")
        log(f"    - Nombre: {sample_bolt.get('nombre')}")
        log(f"    - Nombre Normalizado: '{sample_bolt.get('nombre_norm')}'")
        log(f"    - Tokens para búsqueda: {sample_bolt.get('tokens')}")
        log(f"    - Nacimiento: {sample_bolt.get('fecha_nac')} en {sample_bolt.get('pais_nacimiento')}")
        log(f"    - Medidas: {sample_bolt.get('altura_cm')} cm / {sample_bolt.get('peso_kg')} kg")

    # Muestra 2: Atleta con tokens dinásticos y apellidos corregidos (Erick Barrondo)
    sample_erick = db.atletas.find_one({"tokens": "barrondo"})
    if sample_erick:
        log(f"\n  • Muestra Atleta 2 (Erick Barrondo):")
        log(f"    - ID: {sample_erick.get('_id')} | Nombre: {sample_erick.get('nombre')}")
        log(f"    - Tokens para búsqueda: {sample_erick.get('tokens')}")
        log(f"    - Nacionalidad: {sample_erick.get('nacionalidad')}")

    # 4. Verificación de Índices en Atlas
    log("\n[4/4] VALIDACIÓN DEL USO DE ÍNDICES:")
    exp = db.command('explain', {'find': 'atletas', 'filter': {'tokens': 'bolt'}}, verbosity='executionStats')
    stats = exp.get("executionStats", {})
    planner = exp.get("queryPlanner", {})
    winning_plan = planner.get("winningPlan", {})
    stage = winning_plan.get("stage", "")
    if stage == "FETCH" and winning_plan.get("inputStage"):
        stage = winning_plan["inputStage"].get("stage", "") + " -> FETCH"

    log(f"  • Plan ganador para búsqueda por token 'bolt': {stage}")
    log(f"  • Tiempo de ejecución: {stats.get('executionTimeMillis', 0)} ms")
    log(f"  • Documentos examinados: {stats.get('totalDocsExamined', 0)}")
    log(f"  • Documentos devueltos: {stats.get('nReturned', 0)}")
    es_idx = "IXSCAN" in stage or "IDHACK" in stage
    log(f"  • Estado del índice: {'[OK] Utiliza ÍNDICE MULTIKEY' if es_idx else '[ALERTA] COLLSCAN detectado'}")

    # Dictamen
    log("\n" + "=" * 75)
    paridad_ok = (conteo_atlas == total_atletas)
    log(f"  DICTAMEN PARIDAD: Esperados: {total_atletas:,} | Obtenidos: {conteo_atlas:,} --> {'[PARIDAD 100% CERTIFICADA]' if paridad_ok else '[DISCREPANCIA]'}")
    log("=" * 75)

    with open(log_file, 'w', encoding='utf-8') as f:
        f.write("\n".join(lineas_log) + "\n")

    log(f"\n[INFO] Bitácora guardada exitosamente en: {log_file}")

    cur.close()
    conn.close()
    client.close()
    return paridad_ok

if __name__ == '__main__':
    ejecutar_carga_atletas()
