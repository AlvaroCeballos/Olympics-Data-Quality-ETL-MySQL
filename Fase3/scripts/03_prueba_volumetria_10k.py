# -*- coding: utf-8 -*-
"""
03_prueba_volumetria_10k.py — Prueba Piloto de Volumetría y Proyección de Capacidad en Atlas.
Fase 2 del Plan de Integrante 2 (Álvaro Ceballos).

Objetivo:
  1. Cargar 10,000 documentos desnormalizados en la colección 'resultados' de MongoDB Atlas.
  2. Medir métricas exactas del motor WiredTiger (dataSize, storageSize, indexSize, avgObjSize).
  3. Proyectar formalmente la volumetría total del proyecto frente al límite de 512 MB de Atlas M0.
"""

import os
import sys
import time
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
import mysql.connector
from pymongo import MongoClient

# Cargar variables de entorno
ENV_PATH = Path(__file__).resolve().parent.parent / '.env'
load_dotenv(dotenv_path=ENV_PATH)

MYSQL_HOST = os.getenv('MYSQL_HOST', 'localhost')
MYSQL_PORT = int(os.getenv('MYSQL_PORT', 3306))
MYSQL_USER = os.getenv('MYSQL_USER', 'root')
MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD', 'admin')
MYSQL_DB = os.getenv('MYSQL_DB', 'olimpiadas')

MONGO_URI = os.getenv('MONGO_URI')
MONGO_DB = os.getenv('MONGO_DB', 'olimpiadas')

sys.path.append(str(Path(__file__).resolve().parent))
import importlib
etl = importlib.import_module("03_cargar_datos_mongo")

def ejecutar_prueba_volumetria(n_docs=10000):
    print("=" * 70)
    print("      PRUEBA PILOTO DE VOLUMETRÍA Y CAPACIDAD EN MONGODB ATLAS       ")
    print(f"      Fecha y Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  ")
    print("=" * 70)

    # 1. Conexiones
    conn = etl.get_mysql_conn()
    cur = conn.cursor(dictionary=True)
    db, client = etl.get_mongo_db()

    print(f"\n[1/4] Extrayendo {n_docs:,} registros de participaciones desde MySQL...")
    t0 = time.time()
    lote = etl.extraer_lote_resultados(cur, offset=0, limit=n_docs)
    t_extr = time.time() - t0
    print(f"      [OK] Extraídos {len(lote):,} documentos en {t_extr:.2f} segundos ({len(lote)/t_extr:.0f} docs/s)")

    print(f"\n[2/4] Insertando {n_docs:,} documentos en MongoDB Atlas (colección 'resultados')...")
    # Limpiar previamente para una medición aislada
    db.resultados.delete_many({})
    
    t0 = time.time()
    res = db.resultados.insert_many(lote, ordered=False)
    t_ins = time.time() - t0
    print(f"      [OK] Insertados {len(res.inserted_ids):,} documentos en {t_ins:.2f} segundos ({len(res.inserted_ids)/t_ins:.0f} docs/s)")

    print(f"\n[3/4] Obteniendo métricas físicas de WiredTiger vía collStats...")
    stats = db.command('collStats', 'resultados')
    
    count = stats.get('count', n_docs)
    data_size_bytes = stats.get('size', 0)
    storage_size_bytes = stats.get('storageSize', 0)
    total_index_size_bytes = stats.get('totalIndexSize', 0)
    avg_obj_size = stats.get('avgObjSize', 0)
    total_disco_bytes = storage_size_bytes + total_index_size_bytes

    # Cálculos en KB y MB
    data_size_mb = data_size_bytes / (1024 * 1024)
    storage_size_mb = storage_size_bytes / (1024 * 1024)
    index_size_mb = total_index_size_bytes / (1024 * 1024)
    total_disco_mb = total_disco_bytes / (1024 * 1024)
    ratio_compresion = (data_size_bytes / storage_size_bytes) if storage_size_bytes > 0 else 1.0

    print("-" * 70)
    print(f"  MÉTRICAS MEDIDAS DEL LOTE PILOTO ({count:,} DOCUMENTOS):")
    print(f"  • Tamaño promedio por documento (avgObjSize) : {avg_obj_size:.1f} bytes")
    print(f"  • Tamaño de datos sin comprimir (dataSize)    : {data_size_mb:.2f} MB ({data_size_bytes:,} bytes)")
    print(f"  • Almacenamiento real en disco (storageSize) : {storage_size_mb:.2f} MB ({storage_size_bytes:,} bytes)")
    print(f"  • Tamaño total de índices (totalIndexSize)   : {index_size_mb:.2f} MB ({total_index_size_bytes:,} bytes)")
    print(f"  • Espacio total en disco ocupado en Atlas     : {total_disco_mb:.2f} MB")
    print(f"  • Ratio de compresión WiredTiger             : {ratio_compresion:.2f}x (Ahorro del {(1 - 1/ratio_compresion)*100:.1f}%)")
    print("-" * 70)

    # 4. Proyección Matemática Total
    print(f"\n[4/4] PROYECCIÓN MATEMÁTICA DE VOLUMETRÍA TOTAL DEL PROYECTO:")
    total_participaciones = 380548
    total_atletas = 190471
    total_paises = 487
    total_ediciones = 63

    factor_part = total_participaciones / count
    proy_part_storage_mb = storage_size_mb * factor_part
    proy_part_index_mb = index_size_mb * factor_part
    proy_part_total_mb = proy_part_storage_mb + proy_part_index_mb

    # Estimación de Atletas (documentos más ligeros, ~180 bytes)
    proy_atletas_storage_mb = (total_atletas * 180 * (1 / ratio_compresion)) / (1024 * 1024)
    proy_atletas_index_mb = (total_atletas * 60) / (1024 * 1024) # Índices nombre_norm + tokens
    proy_atletas_total_mb = proy_atletas_storage_mb + proy_atletas_index_mb

    # Países y Ediciones (despreciable, < 1 MB)
    proy_otros_mb = 0.50

    gran_total_mb = proy_part_total_mb + proy_atletas_total_mb + proy_otros_mb
    limite_atlas_mb = 512.0
    margen_libre_mb = limite_atlas_mb - gran_total_mb
    porcentaje_uso = (gran_total_mb / limite_atlas_mb) * 100

    print("=" * 70)
    print("                    INFORME TÉCNICO DE CAPACIDAD                      ")
    print("=" * 70)
    print(f"  1. Colección 'resultados' (380,548 docs) : {proy_part_total_mb:.2f} MB (Disco: {proy_part_storage_mb:.2f} MB + Índices: {proy_part_index_mb:.2f} MB)")
    print(f"  2. Colección 'atletas'    (190,471 docs) : {proy_atletas_total_mb:.2f} MB (Disco: {proy_atletas_storage_mb:.2f} MB + Índices: {proy_atletas_index_mb:.2f} MB)")
    print(f"  3. Colecciones 'paises' y 'ediciones'    : {proy_otros_mb:.2f} MB (550 docs)")
    print("  " + "-" * 66)
    print(f"  >>> TOTAL ESTIMADO EN DISCO ATLAS        : {gran_total_mb:.2f} MB")
    print(f"  >>> LÍMITE CAPA GRATUITA ATLAS (M0)      : {limite_atlas_mb:.2f} MB")
    print(f"  >>> ESPACIO LIBRE RESTANTE               : {margen_libre_mb:.2f} MB ({100 - porcentaje_uso:.1f}% libre)")
    print(f"  >>> PORCENTAJE DE USO DE DISCO           : {porcentaje_uso:.1f}%")
    print("=" * 70)

    if gran_total_mb < limite_atlas_mb * 0.80:
        veredicto = "APROBADO PARA ATLAS (VIABILIDAD COMPLETA SIN RIESGO DE DESBORDAMIENTO)"
        print(f"\n[VEREDICTO TÉCNICO]: {veredicto}")
        print(">> No es necesario recortar campos ni recurrir a Docker local.")
    else:
        veredicto = "ALERTA: SE RECOMIENDA DOCKER O RECORTAR CAMPOS"
        print(f"\n[VEREDICTO TÉCNICO]: {veredicto}")

    # Guardar bitácora en Fase3/logs/
    log_dir = Path(__file__).resolve().parent.parent / 'logs'
    log_dir.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_file = log_dir / f"volumetria_piloto_10k_{timestamp}.log"
    with open(log_file, 'w', encoding='utf-8') as f:
        f.write("PRUEBA DE VOLUMETRIA Y CAPACIDAD EN ATLAS (FASE 2)\n")
        f.write(f"Fecha: {datetime.now().isoformat()}\n")
        f.write(f"Lote probado: {count} documentos\n")
        f.write(f"avgObjSize: {avg_obj_size:.2f} bytes\n")
        f.write(f"dataSize: {data_size_mb:.2f} MB\n")
        f.write(f"storageSize: {storage_size_mb:.2f} MB\n")
        f.write(f"totalIndexSize: {index_size_mb:.2f} MB\n")
        f.write(f"Proyeccion Gran Total: {gran_total_mb:.2f} MB / 512 MB ({porcentaje_uso:.1f}%)\n")
        f.write(f"Veredicto: {veredicto}\n")

    print(f"\n[INFO] Registro de auditoría guardado en: {log_file}")
    
    cur.close()
    conn.close()
    client.close()

if __name__ == '__main__':
    ejecutar_prueba_volumetria(10000)
