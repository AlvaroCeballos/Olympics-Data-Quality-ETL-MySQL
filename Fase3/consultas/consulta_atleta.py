# -*- coding: utf-8 -*-
"""
consulta_atleta.py  —  Fase 3 (Integrante 3)

Equivalente MongoDB del stored procedure sp_consultar_atleta(p_nombre, p_anio, p_deporte, p_pais).
Devuelve:
  (1) Ficha(s) del atleta (hasta 10 coincidencias por nombre).
  (2) Historial de participaciones, filtrable por año, deporte y país (código NOC o nombre).

Uso:
    python consulta_atleta.py "Phelps"
    python consulta_atleta.py "Phelps" --anio 2008
    python consulta_atleta.py "Bolt" --deporte Athletics
    python consulta_atleta.py "Barrondo" --pais GUA

Devuelve además el tiempo de respuesta en milisegundos.
"""
import argparse
import io
import json
import os
import sys
import time
from datetime import datetime, date
from decimal import Decimal

from dotenv import load_dotenv
from pymongo import MongoClient

# Forzar salida UTF-8 (Windows por defecto usa cp1252 y falla con chino/cirilico)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def _json_default(o):
    if isinstance(o, (datetime, date)):
        return o.isoformat()
    if isinstance(o, Decimal):
        return float(o)
    return str(o)


def consultar_atleta(db, nombre, anio=None, deporte=None, pais=None, limit_participaciones=200):
    t0 = time.perf_counter()

    # 1) Ficha(s): búsqueda por nombre o nombre_norm (índice idx_atletas_nombre_norm)
    nombre_lower = nombre.strip().lower()
    ficha_filter = {
        "$or": [
            {"nombre": {"$regex": nombre, "$options": "i"}},
            {"nombre_completo": {"$regex": nombre, "$options": "i"}},
            {"nombre_norm": {"$regex": nombre_lower}},
        ]
    }
    # Traemos TODAS las coincidencias (no solo 10) para no perder atletas
    # cuyo nombre es un apellido común (ej. Phelps -> hay 10 Phelps distintos y
    # Michael Phelps podria quedar fuera del limit).
    fichas = list(db.atletas.find(ficha_filter).limit(100))
    ids_atleta = [f.get("id_atleta") or f.get("_id") for f in fichas]
    # Para la UI, limitamos la ficha a mostrar al top 10 (igual que el SP).
    fichas_mostrar = fichas[:10]

    # 2) Historial de participaciones
    hist_filter = {"atleta.id": {"$in": ids_atleta}} if ids_atleta else {
        "atleta.nombre": {"$regex": nombre, "$options": "i"}
    }
    if anio is not None:
        hist_filter["olimpiada.anio"] = int(anio)
    if deporte:
        hist_filter["deporte"] = {"$regex": deporte, "$options": "i"}
    if pais:
        p = pais.strip()
        if len(p) == 3:  # código NOC/país
            hist_filter["$or"] = [{"pais.codigo": p.upper()}, {"noc.codigo": p.upper()}]
        else:
            hist_filter["pais.nombre"] = {"$regex": p, "$options": "i"}

    proy = {
        "_id": 0, "atleta.nombre": 1, "olimpiada.anio": 1, "olimpiada.temporada": 1,
        "deporte": 1, "disciplina": 1, "evento": 1, "equipo": 1,
        "pais.codigo": 1, "pais.nombre": 1, "medalla": 1, "posicion": 1,
        "es_empate": 1, "edad": 1,
    }
    participaciones = list(
        db.resultados.find(hist_filter, proy)
        .sort([("olimpiada.anio", 1), ("evento", 1)])
        .limit(limit_participaciones)
    )

    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    return {
        "parametros": {"nombre": nombre, "anio": anio, "deporte": deporte, "pais": pais},
        "fichas": fichas_mostrar,
        "participaciones": participaciones,
        "resumen": {
            "fichas_coincidentes_total": len(fichas),
            "fichas_mostradas": len(fichas_mostrar),
            "participaciones": len(participaciones),
        },
        "tiempo_ms": round(elapsed_ms, 2),
    }


def _mostrar(res):
    print(json.dumps(res, indent=2, ensure_ascii=False, default=_json_default))
    print(f"\n[TIEMPO] {res['tiempo_ms']} ms   "
          f"[fichas={res['resumen']['fichas_mostradas']}/{res['resumen']['fichas_coincidentes_total']}  "
          f"participaciones={res['resumen']['participaciones']}]")


def main():
    ap = argparse.ArgumentParser(description="Consulta por atleta (equivalente a sp_consultar_atleta)")
    ap.add_argument("nombre", help="Nombre o fragmento del atleta (ej. 'Phelps')")
    ap.add_argument("--anio", type=int, default=None, help="Año olímpico (opcional)")
    ap.add_argument("--deporte", default=None, help="Nombre del deporte (opcional)")
    ap.add_argument("--pais", default=None, help="Código NOC/país (3 letras) o nombre (opcional)")
    ap.add_argument("--limit", type=int, default=200, help="Máximo de participaciones a devolver")
    args = ap.parse_args()

    _env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
    load_dotenv(_env_path)
    uri = os.environ["MONGO_URI"]
    dbname = os.environ.get("MONGO_DB", "olimpiadas")

    client = MongoClient(uri, serverSelectionTimeoutMS=10000)
    try:
        db = client[dbname]
        res = consultar_atleta(db, args.nombre, args.anio, args.deporte, args.pais, args.limit)
        _mostrar(res)
    finally:
        client.close()


if __name__ == "__main__":
    main()
