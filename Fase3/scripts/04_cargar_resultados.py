# -*- coding: utf-8 -*-
"""
04_cargar_resultados.py — Fase 5 del Plan de Integrante 2 (Álvaro Ceballos).
Extracción, transformación y carga masiva de los 380,548 hechos aplanados a la colección 'resultados' en MongoDB Atlas.
Implementa paginación por clave primaria (keyset) e inserciones en lotes de alto rendimiento con pymongo.
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

# Importar funciones de 03_cargar_datos_mongo
sys.path.append(str(Path(__file__).resolve().parent))
import importlib
etl = importlib.import_module("03_cargar_datos_mongo")
clean_val = etl.clean_val

def extraer_lote_resultados_keyset(cur, last_id, limit):
    """
    Extrae un bloque de participaciones aplanadas usando paginación por clave primaria (keyset).
    Garantiza tiempo de extracción constante en cada lote (O(1)).
    """
    sql = f"""
        SELECT 
            p.id_participacion,
            p.id_atleta, a.nombre AS atleta_nombre, a.sexo AS atleta_sexo,
            p.edad, p.altura_reg, p.peso_reg, p.posicion, p.es_empate, p.compitio_como,
            m.tipo AS medalla,
            d.nombre AS deporte,
            disc.nombre AS disciplina,
            e.nombre AS evento,
            o.id_olimpiada, o.anio, o.temporada, o.nombre_juegos,
            eq.nombre AS equipo,
            n.codigo_noc,
            pais_rep.codigo_pais AS pais_codigo,
            pais_rep.nombre AS pais_nombre
        FROM participacion p
        JOIN atleta a ON p.id_atleta = a.id_atleta
        JOIN medalla m ON p.id_medalla = m.id_medalla
        JOIN evento e ON p.id_evento = e.id_evento
        LEFT JOIN disciplina disc ON e.id_disciplina = disc.id_disciplina
        LEFT JOIN deporte d ON disc.id_deporte = d.id_deporte
        JOIN olimpiada o ON p.id_olimpiada = o.id_olimpiada
        LEFT JOIN equipo eq ON p.id_equipo = eq.id_equipo
        LEFT JOIN noc n ON eq.id_noc = n.id_noc
        LEFT JOIN pais pais_rep ON n.id_pais = pais_rep.id_pais
        WHERE p.id_participacion > {last_id}
        ORDER BY p.id_participacion ASC
        LIMIT {limit};
    """
    cur.execute(sql)
    resultados = []
    for r in cur.fetchall():
        doc = {
            "_id": r['id_participacion'],
            "atleta": {
                "id": r['id_atleta'],
                "nombre": r['atleta_nombre'],
                "sexo": r['atleta_sexo']
            },
            "olimpiada": {
                "id": r['id_olimpiada'],
                "anio": r['anio'],
                "temporada": r['temporada'],
                "nombre_juegos": r['nombre_juegos']
            },
            "pais": {
                "codigo": r['pais_codigo'],
                "nombre": r['pais_nombre']
            } if r['pais_codigo'] else None,
            "noc": {
                "codigo": r['codigo_noc']
            } if r['codigo_noc'] else None,
            "equipo": r['equipo'],
            "deporte": r['deporte'],
            "disciplina": r['disciplina'],
            "evento": r['evento'],
            "medalla": r['medalla'],
            "posicion": r['posicion'],
            "es_empate": bool(r['es_empate']),
            "edad": r['edad'],
            "altura_reg": r['altura_reg'],
            "peso_reg": clean_val(r['peso_reg']),
            "compitio_como": r['compitio_como']
        }
        doc_filtrado = {k: v for k, v in doc.items() if v is not None}
        resultados.append(doc_filtrado)
    return resultados

def ejecutar_carga_resultados(batch_size=15000, force_reload=True):
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_dir = Path(__file__).resolve().parent.parent / 'logs'
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / f"carga_resultados_{timestamp}.log"

    lineas_log = []

    def log(msg=""):
        print(msg)
        lineas_log.append(msg)

    log("=" * 75)
    log("     FASE 5: CARGA MASIVA DE HECHOS APLANADOS ('resultados')           ")
    log(f"     Fecha y Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log(f"     Destino: MongoDB Atlas ('olimpiadas.resultados')")
    log("=" * 75)

    conn = etl.get_mysql_conn()
    cur = conn.cursor(dictionary=True)
    db, client = etl.get_mongo_db()

    cur.execute("SELECT COUNT(*) AS total FROM participacion;")
    total_part = cur.fetchone()['total']
    log(f"\n[1/4] CENSO DE PARTICIPACIONES EN ORIGEN (MySQL): {total_part:,} registros.")

    conteo_previo = db.resultados.count_documents({})
    if not force_reload and conteo_previo == total_part:
        log(f"\n[2/4] [INFO] La colección 'resultados' ya cuenta con los {conteo_previo:,} documentos cargados.")
        log("      Se omite la reinserción en red (modo idempotente).")
        total_insertados = conteo_previo
    else:
        log("\n[2/4] LIMPIEZA PREVIA E INSERCIÓN EN LOTES EN MONGODB ATLAS...")
        db.resultados.delete_many({})
        log("      Colección 'resultados' vaciada para carga limpia y completa.")

        total_insertados = 0
        last_id = 0
        lote_num = 1
        total_lotes = (total_part + batch_size - 1) // batch_size
        t_inicio_global = time.time()

        while total_insertados < total_part:
            t0 = time.time()
            lote = extraer_lote_resultados_keyset(cur, last_id=last_id, limit=batch_size)
            t_extr = time.time() - t0

            if not lote:
                break

            last_id = lote[-1]['_id']

            t0 = time.time()
            res = db.resultados.insert_many(lote, ordered=False)
            t_ins = time.time() - t0
            cant_ins = len(res.inserted_ids)
            total_insertados += cant_ins

            tasa = cant_ins / t_ins if t_ins > 0 else 0
            pct = (total_insertados / total_part) * 100

            log(f"      • Lote {lote_num:02d}/{total_lotes:02d}: Insertados {cant_ins:>6,} docs | Last ID: {last_id:>7} | Extr: {t_extr:.2f}s | Ins: {t_ins:.2f}s ({tasa:,.0f} docs/s) | Progreso: {pct:>5.1f}%")

            lote_num += 1

        t_total_global = time.time() - t_inicio_global
        tasa_global = total_insertados / t_total_global if t_total_global > 0 else 0

        log("\n" + "-" * 75)
        log(f"      RESUMEN CARGA: {total_insertados:,} resultados insertados en {t_total_global:.2f} s ({tasa_global:,.0f} docs/s promedio)")
        log("-" * 75)

    # 3. Verificación de conteo e inspección de muestras
    log("\n[3/4] VERIFICACIÓN DE CONTEO Y DOCUMENTOS DE MUESTRA EN ATLAS:")
    conteo_atlas = db.resultados.count_documents({})
    log(f"      Conteo oficial en Atlas: {conteo_atlas:,} documentos.")

    # Muestra 1: Resultado histórico podio (Michael Phelps)
    sample_phelps = db.resultados.find_one({"atleta.nombre": {"$regex": "Michael Fred Phelps"}, "medalla": "Gold"})
    if sample_phelps:
        log(f"\n  • Muestra Resultado 1 (Michael Phelps - Oro Olímpico):")
        log(f"    - ID Participación: {sample_phelps.get('_id')}")
        log(f"    - Atleta: {sample_phelps.get('atleta')}")
        log(f"    - Edición: {sample_phelps.get('olimpiada')}")
        log(f"    - País: {sample_phelps.get('pais')} | NOC: {sample_phelps.get('noc')}")
        log(f"    - Deporte/Disciplina: {sample_phelps.get('deporte')} / {sample_phelps.get('disciplina')}")
        log(f"    - Evento: {sample_phelps.get('evento')}")
        log(f"    - Medalla: {sample_phelps.get('medalla')} | Posición: {sample_phelps.get('posicion')}")

    # Muestra 2: Resultado de atleta nacional (Erick Barrondo - Plata 2012)
    sample_barrondo = db.resultados.find_one({"atleta.nombre": {"$regex": "Barrondo"}, "medalla": "Silver"})
    if sample_barrondo:
        log(f"\n  • Muestra Resultado 2 (Érick Barrondo - Plata Londres 2012):")
        log(f"    - ID Participación: {sample_barrondo.get('_id')}")
        log(f"    - Atleta: {sample_barrondo.get('atleta')}")
        log(f"    - Edición: {sample_barrondo.get('olimpiada')}")
        log(f"    - País: {sample_barrondo.get('pais')}")
        log(f"    - Evento: {sample_barrondo.get('evento')}")
        log(f"    - Medalla: {sample_barrondo.get('medalla')} | Posición: {sample_barrondo.get('posicion')}")

    # 4. Verificación de Índices Compuestos en 'resultados'
    log("\n[4/4] VALIDACIÓN DEL USO DE ÍNDICES EN 'resultados':")

    # Caso A: Consulta Atleta + Año (idx_resultados_atleta_anio)
    exp_a = db.command('explain', {'find': 'resultados', 'filter': {'atleta.id': 104492, 'olimpiada.anio': 2008}}, verbosity='executionStats')
    stats_a = exp_a.get("executionStats", {})
    plan_a = exp_a.get("queryPlanner", {}).get("winningPlan", {})
    stage_a = plan_a.get("stage", "")
    if stage_a == "FETCH" and plan_a.get("inputStage"):
        stage_a = plan_a["inputStage"].get("stage", "") + " -> FETCH"
    log(f"  • Caso A (Atleta ID + Año): Plan: {stage_a} | Docs examinados: {stats_a.get('totalDocsExamined', 0)} | Tiempo: {stats_a.get('executionTimeMillis', 0)} ms")

    # Caso B: Consulta País + Año + Deporte (idx_resultados_pais_anio_deporte)
    exp_b = db.command('explain', {'find': 'resultados', 'filter': {'pais.codigo': 'FRA', 'olimpiada.anio': 2024, 'deporte': 'Swimming'}}, verbosity='executionStats')
    stats_b = exp_b.get("executionStats", {})
    plan_b = exp_b.get("queryPlanner", {}).get("winningPlan", {})
    stage_b = plan_b.get("stage", "")
    if stage_b == "FETCH" and plan_b.get("inputStage"):
        stage_b = plan_b["inputStage"].get("stage", "") + " -> FETCH"
    log(f"  • Caso B (País + Año + Deporte): Plan: {stage_b} | Docs examinados: {stats_b.get('totalDocsExamined', 0)} | Tiempo: {stats_b.get('executionTimeMillis', 0)} ms")

    # Dictamen de Paridad
    log("\n" + "=" * 75)
    paridad_ok = (conteo_atlas == total_part)
    log(f"  DICTAMEN PARIDAD: Esperados: {total_part:,} | Obtenidos: {conteo_atlas:,} --> {'[PARIDAD 100% CERTIFICADA]' if paridad_ok else '[DISCREPANCIA]'}")
    log("=" * 75)

    with open(log_file, 'w', encoding='utf-8') as f:
        f.write("\n".join(lineas_log) + "\n")

    log(f"\n[INFO] Bitácora guardada exitosamente en: {log_file}")

    cur.close()
    conn.close()
    client.close()
    return paridad_ok

if __name__ == '__main__':
    ejecutar_carga_resultados(batch_size=15000, force_reload=True)
