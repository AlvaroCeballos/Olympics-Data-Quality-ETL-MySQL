# -*- coding: utf-8 -*-
"""
03_cargar_datos_mongo.py — Pipeline ETL de Extracción, Transformación y Carga a MongoDB Atlas.
Responsabilidad del Integrante 2 (Álvaro Ceballos).

Diseñado para:
  1. Extraer datos limpios y deduplicados desde MySQL ('olimpiadas').
  2. Transformar a documentos BSON desnormalizados según las 4 colecciones aprobadas:
     - 'ediciones': 63 documentos con sede embebida.
     - 'paises': 487 documentos con NOCs y sedes históricas embebidas (Req. d).
     - 'atletas': 190,471 documentos con nombre_norm y array tokens (Req. c).
     - 'resultados': 380,548 documentos de hechos desnormalizados (sin $lookup lentos).
  3. Carga en lotes con ordered=False y generación de logs con fecha/hora.
"""

import os
import sys
import time
from datetime import datetime, date
from decimal import Decimal
from pathlib import Path
from dotenv import load_dotenv
import mysql.connector
from pymongo import MongoClient

# Agregar directorio de utilidades de Fase 1 para importar normalize_name (DT-002 / DT-027)
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(ROOT_DIR / 'Fase1' / 'etl'))
try:
    from utils import normalize_name
except ImportError:
    import unicodedata, re
    def normalize_name(name):
        if not name: return ''
        res = unicodedata.normalize('NFKD', str(name).lower())
        res = ''.join(c for c in res if not unicodedata.combining(c))
        res = re.sub(r'[^\w\s]', ' ', res)
        return ' '.join(res.split()).strip()

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

def clean_val(v):
    """Convierte tipos no compatibles de MySQL a tipos nativos BSON."""
    if isinstance(v, Decimal):
        return float(v)
    if isinstance(v, (datetime, date)):
        return v.strftime('%Y-%m-%d')
    return v

def get_mysql_conn():
    return mysql.connector.connect(
        host=MYSQL_HOST,
        port=MYSQL_PORT,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DB
    )

def get_mongo_db():
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=10000)
    return client[MONGO_DB], client

def extraer_transformar_ediciones(cur):
    """Extrae las ediciones y embebe los datos de la sede."""
    cur.execute("""
        SELECT o.id_olimpiada, o.anio, o.temporada, o.nombre_juegos,
               s.ciudad AS sede_ciudad, p.codigo_pais AS sede_pais_codigo, p.nombre AS sede_pais_nombre
        FROM olimpiada o
        LEFT JOIN sede s ON o.id_sede = s.id_sede
        LEFT JOIN pais p ON s.id_pais = p.id_pais
        ORDER BY o.anio ASC;
    """)
    ediciones = []
    for r in cur.fetchall():
        doc = {
            "_id": r['id_olimpiada'],
            "anio": r['anio'],
            "temporada": r['temporada'],
            "nombre_juegos": r['nombre_juegos'],
            "sede": {
                "ciudad": r['sede_ciudad'],
                "pais_codigo": r['sede_pais_codigo'],
                "pais_nombre": r['sede_pais_nombre']
            }
        }
        ediciones.append(doc)
    return ediciones

def extraer_transformar_paises(cur):
    """
    Extrae los países, embebe sus comités NOC y sus sedes históricas.
    Cumple con el Req. d: 'si ha sido sede en alguna ocasión y qué años' de forma instantánea.
    """
    cur.execute("""
        SELECT s.id_pais, o.anio, o.temporada, s.ciudad
        FROM olimpiada o
        JOIN sede s ON o.id_sede = s.id_sede
        WHERE s.id_pais IS NOT NULL
        ORDER BY o.anio ASC;
    """)
    sedes_por_pais = {}
    for s in cur.fetchall():
        pid = s['id_pais']
        if pid not in sedes_por_pais:
            sedes_por_pais[pid] = []
        sedes_por_pais[pid].append({
            "anio": s['anio'],
            "temporada": s['temporada'],
            "ciudad": s['ciudad']
        })

    cur.execute("SELECT id_pais, codigo_noc, nombre_noc, notas FROM noc WHERE id_pais IS NOT NULL;")
    nocs_por_pais = {}
    for n in cur.fetchall():
        pid = n['id_pais']
        if pid not in nocs_por_pais:
            nocs_por_pais[pid] = []
        nocs_por_pais[pid].append({
            "codigo": n['codigo_noc'],
            "nombre": n['nombre_noc'],
            "notas": n['notas']
        })

    cur.execute("SELECT id_pais, codigo_pais, nombre, nombre_alt, region FROM pais;")
    paises = []
    for p in cur.fetchall():
        pid = p['id_pais']
        norm = normalize_name(p['nombre']) if p['nombre'] else ''
        doc = {
            "_id": pid,
            "codigo": p['codigo_pais'],
            "nombre": p['nombre'],
            "nombre_norm": norm,
            "nombre_alt": p['nombre_alt'],
            "region": p['region'],
            "sedes_historicas": sedes_por_pais.get(pid, []),
            "es_sede_historica": len(sedes_por_pais.get(pid, [])) > 0,
            "nocs": nocs_por_pais.get(pid, [])
        }
        paises.append(doc)
    return paises

def extraer_transformar_atletas(cur, offset=0, limit=None):
    """
    Extrae atletas calculando nombre_norm y array de tokens (Req. c e índice multikey).
    """
    sql = """
        SELECT a.id_atleta, a.id_externo, a.nombre, a.nombre_completo, a.otros_nombres,
               a.nombre_original, a.orden_nombre, a.apodo, a.titulo, a.afiliacion,
               a.sexo, a.fecha_nac, a.ciudad_nac, a.region_nac, a.fecha_muerte,
               a.altura_cm, a.peso_kg, a.roles, a.nacionalidad,
               p.codigo_pais AS pais_nac_codigo, p.nombre AS pais_nac_nombre
        FROM atleta a
        LEFT JOIN pais p ON a.id_pais_nac = p.id_pais
        ORDER BY a.id_atleta ASC
    """
    if limit:
        sql += f" LIMIT {limit} OFFSET {offset}"
    
    cur.execute(sql)
    atletas = []
    for a in cur.fetchall():
        norm = normalize_name(a['nombre']) if a['nombre'] else ''
        tokens = [t for t in norm.split() if len(t) >= 2]
        
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
            "pais_nacimiento": {
                "codigo": a['pais_nac_codigo'],
                "nombre": a['pais_nac_nombre']
            } if a['pais_nac_codigo'] else None,
            "altura_cm": clean_val(a['altura_cm']),
            "peso_kg": clean_val(a['peso_kg']),
            "roles": a['roles'],
            "nacionalidad": a['nacionalidad']
        }
        doc_filtrado = {k: v for k, v in doc.items() if v is not None}
        atletas.append(doc_filtrado)
    return atletas

def extraer_lote_resultados(cur, offset=0, limit=10000):
    """
    Extrae un bloque de participaciones desnormalizadas para la colección 'resultados'.
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
        ORDER BY p.id_participacion ASC
        LIMIT {limit} OFFSET {offset};
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

def cargar_lote_piloto_10k():
    """
    Carga el lote piloto de 10,000 registros para la prueba de volumetría (Fase 2).
    """
    print(f"[{datetime.now().isoformat()}] Iniciando extracción de lote piloto (10,000 resultados)...")
    conn = get_mysql_conn()
    cur = conn.cursor(dictionary=True)
    db, client = get_mongo_db()
    
    t0 = time.time()
    lote = extraer_lote_resultados(cur, offset=0, limit=10000)
    t_extr = time.time() - t0
    print(f"[{datetime.now().isoformat()}] 10,000 documentos extraídos de MySQL en {t_extr:.2f} s")
    
    t0 = time.time()
    # Limpiar si ya había prueba previa
    db.resultados.delete_many({})
    res = db.resultados.insert_many(lote, ordered=False)
    t_ins = time.time() - t0
    print(f"[{datetime.now().isoformat()}] 10,000 documentos insertados en Atlas en {t_ins:.2f} s")
    
    # Obtener estadísticas de la colección
    stats = db.command('collStats', 'resultados')
    cur.close()
    conn.close()
    client.close()
    return stats

if __name__ == '__main__':
    print("Módulo de transformación ETL listo.")
