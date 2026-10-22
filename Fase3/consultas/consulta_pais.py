# -*- coding: utf-8 -*-
"""
consulta_pais.py  —  Fase 3 (Integrante 3)

Equivalente MongoDB del stored procedure sp_consultar_pais(p_pais, p_anio_inicio, p_anio_fin, p_solo_medallas).
Devuelve:
  (1) Historial de sedes albergadas por el país.
  (2) Medallero histórico acumulado.
  (3) Desglose por edición y deporte/disciplina.

Uso:
    python consulta_pais.py FRA
    python consulta_pais.py "Guatemala"
    python consulta_pais.py USA --anio-inicio 2000 --anio-fin 2024
    python consulta_pais.py GUA --solo-medallas
"""
import argparse
import json
import os
import sys
import time
from datetime import datetime, date
from decimal import Decimal

from dotenv import load_dotenv
from pymongo import MongoClient

# Forzar UTF-8 en la salida (Windows por defecto usa cp1252)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def _json_default(o):
    if isinstance(o, (datetime, date)):
        return o.isoformat()
    if isinstance(o, Decimal):
        return float(o)
    return str(o)


def consultar_pais(db, pais, anio_inicio=None, anio_fin=None, solo_medallas=False):
    t0 = time.perf_counter()
    p = pais.strip()

    # Resolver el país (acepta código de 3 letras o nombre)
    if len(p) == 3:
        pais_doc = db.paises.find_one({"codigo": p.upper()})
    else:
        pais_doc = db.paises.find_one({
            "$or": [
                {"nombre": {"$regex": f"^{p}$", "$options": "i"}},
                {"nombre": {"$regex": p, "$options": "i"}},
                {"nombre_norm": {"$regex": p.lower()}},
            ]
        })

    if not pais_doc:
        return {
            "parametros": {"pais": pais, "anio_inicio": anio_inicio, "anio_fin": anio_fin,
                           "solo_medallas": solo_medallas},
            "error": f"País '{pais}' no encontrado",
            "tiempo_ms": round((time.perf_counter() - t0) * 1000.0, 2),
        }

    codigo_pais = pais_doc["codigo"]
    nombre_pais = pais_doc.get("nombre", codigo_pais)

    # 1) Sedes: viene embebido en el documento del país.
    # NOTA: el SP de MySQL devuelve TODAS las sedes historicas sin filtrar por
    # anio (los filtros p_anio_inicio/p_anio_fin solo aplican al medallero).
    # Mantenemos la misma logica para preservar la paridad.
    sedes = pais_doc.get("sedes_historicas", []) or []

    # 2) y 3) Medallero y desglose: aggregate sobre resultados
    match = {"$or": [{"pais.codigo": codigo_pais}, {"noc.codigo": codigo_pais}]}
    if anio_inicio is not None:
        match.setdefault("olimpiada.anio", {})["$gte"] = int(anio_inicio)
    if anio_fin is not None:
        match.setdefault("olimpiada.anio", {})["$lte"] = int(anio_fin)
    if solo_medallas:
        match["medalla"] = {"$in": ["Gold", "Silver", "Bronze"]}

    # (2) Medallero histórico acumulado
    medallero_pipeline = [
        {"$match": match},
        {"$group": {
            "_id": None,
            "total_oro":    {"$sum": {"$cond": [{"$eq": ["$medalla", "Gold"]},   1, 0]}},
            "total_plata":  {"$sum": {"$cond": [{"$eq": ["$medalla", "Silver"]}, 1, 0]}},
            "total_bronce": {"$sum": {"$cond": [{"$eq": ["$medalla", "Bronze"]}, 1, 0]}},
            "total_participaciones": {"$sum": 1},
        }},
        {"$project": {
            "_id": 0, "total_oro": 1, "total_plata": 1, "total_bronce": 1,
            "total_medallas_podio": {"$add": ["$total_oro", "$total_plata", "$total_bronce"]},
            "total_participaciones_historicas": "$total_participaciones",
        }},
    ]
    medallero_list = list(db.resultados.aggregate(medallero_pipeline))
    medallero = medallero_list[0] if medallero_list else {
        "total_oro": 0, "total_plata": 0, "total_bronce": 0,
        "total_medallas_podio": 0, "total_participaciones_historicas": 0
    }
    medallero.update({"codigo_pais": codigo_pais, "pais": nombre_pais})

    # (3) Desglose por edición y disciplina
    desglose_pipeline = [
        {"$match": match},
        {"$group": {
            "_id": {"anio": "$olimpiada.anio", "temporada": "$olimpiada.temporada",
                    "deporte": "$deporte", "disciplina": "$disciplina"},
            "oro":    {"$sum": {"$cond": [{"$eq": ["$medalla", "Gold"]},   1, 0]}},
            "plata":  {"$sum": {"$cond": [{"$eq": ["$medalla", "Silver"]}, 1, 0]}},
            "bronce": {"$sum": {"$cond": [{"$eq": ["$medalla", "Bronze"]}, 1, 0]}},
            "atletas": {"$sum": 1},
        }},
        {"$project": {
            "_id": 0, "anio": "$_id.anio", "temporada": "$_id.temporada",
            "deporte": "$_id.deporte", "disciplina": "$_id.disciplina",
            "oro": 1, "plata": 1, "bronce": 1, "atletas": 1,
        }},
        {"$sort": {"anio": 1, "deporte": 1}},
    ]
    desglose = list(db.resultados.aggregate(desglose_pipeline))

    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    return {
        "parametros": {"pais": pais, "anio_inicio": anio_inicio, "anio_fin": anio_fin,
                       "solo_medallas": solo_medallas},
        "fue_sede": {"si": len(sedes) > 0, "ediciones": sedes},
        "medallero": medallero,
        "desglose_por_edicion_disciplina": desglose,
        "tiempo_ms": round(elapsed_ms, 2),
    }


def _mostrar(res):
    print(json.dumps(res, indent=2, ensure_ascii=False, default=_json_default))
    print(f"\n[TIEMPO] {res['tiempo_ms']} ms")


def main():
    ap = argparse.ArgumentParser(description="Consulta por país (equivalente a sp_consultar_pais)")
    ap.add_argument("pais", help="Código (ej. 'GUA', 'FRA') o nombre del país")
    ap.add_argument("--anio-inicio", dest="anio_inicio", type=int, default=None)
    ap.add_argument("--anio-fin",    dest="anio_fin",    type=int, default=None)
    ap.add_argument("--solo-medallas", action="store_true", help="Filtrar solo participaciones con medalla")
    args = ap.parse_args()

    _env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
    load_dotenv(_env_path)
    uri = os.environ["MONGO_URI"]
    dbname = os.environ.get("MONGO_DB", "olimpiadas")

    client = MongoClient(uri, serverSelectionTimeoutMS=10000)
    try:
        db = client[dbname]
        res = consultar_pais(db, args.pais, args.anio_inicio, args.anio_fin, args.solo_medallas)
        _mostrar(res)
    finally:
        client.close()


if __name__ == "__main__":
    main()
