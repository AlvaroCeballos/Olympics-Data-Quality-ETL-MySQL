# -*- coding: utf-8 -*-
"""
prueba_paridad.py  —  Fase 3 (Integrante 3)

Ejecuta en paralelo:
  (a) los stored procedures de MySQL de la Fase 1 (sp_consultar_atleta y sp_consultar_pais)
  (b) los scripts equivalentes de MongoDB (consulta_atleta y consulta_pais)

y compara los conteos clave para certificar paridad. Esto es lo que pide el
plan del equipo ('prueba de paridad: ejecutar cada SP y su script de Mongo
con los mismos datos y comparar').

Uso:
    python prueba_paridad.py
"""
import os
import sys
from datetime import datetime

from dotenv import load_dotenv
import mysql.connector
from pymongo import MongoClient

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "consultas"))
from consulta_atleta import consultar_atleta
from consulta_pais import consultar_pais


def _sp_atleta(cnx, nombre, anio=None, deporte=None, pais=None):
    cur = cnx.cursor(dictionary=True)
    cur.callproc("sp_consultar_atleta", (nombre, anio, deporte, pais))
    ficha, hist = [], []
    for i, result in enumerate(cur.stored_results()):
        if i == 0:
            ficha = result.fetchall()
        else:
            hist = result.fetchall()
    cur.close()
    return {"fichas": len(ficha), "participaciones": len(hist)}


def _sp_pais(cnx, pais, anio_inicio=None, anio_fin=None, solo_medallas=False):
    cur = cnx.cursor(dictionary=True)
    cur.callproc("sp_consultar_pais", (pais, anio_inicio, anio_fin, solo_medallas))
    sedes, medallero, desglose = [], None, []
    for i, result in enumerate(cur.stored_results()):
        rows = result.fetchall()
        if i == 0:
            sedes = rows
        elif i == 1:
            medallero = rows[0] if rows else None
        else:
            desglose = rows
    cur.close()
    return {"sedes": len(sedes), "medallero": medallero, "desglose_rows": len(desglose)}


CASOS_ATLETA = [
    {"nombre": "Phelps"},
    {"nombre": "Bolt", "deporte": "Athletics"},
    {"nombre": "Barrondo", "pais": "GUA"},
]
CASOS_PAIS = [
    {"pais": "GUA"},
    {"pais": "FRA"},
    {"pais": "USA", "anio_inicio": 2016, "anio_fin": 2024},
]


def _diff_row(label, mysql_v, mongo_v):
    ok = "OK" if mysql_v == mongo_v else "DIFIERE"
    print(f"    {label:<30s} MySQL={mysql_v}   Mongo={mongo_v}   [{ok}]")


def main():
    _env = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
    load_dotenv(_env)

    # MySQL
    cnx = mysql.connector.connect(
        host=os.environ.get("MYSQL_HOST", "localhost"),
        port=int(os.environ.get("MYSQL_PORT", "3306")),
        user=os.environ.get("MYSQL_USER", "root"),
        password=os.environ["MYSQL_PASSWORD"],
        database=os.environ.get("MYSQL_DB", "olimpiadas"),
    )
    # Mongo
    client = MongoClient(os.environ["MONGO_URI"], serverSelectionTimeoutMS=10000)
    db = client[os.environ.get("MONGO_DB", "olimpiadas")]

    print(f"=== PRUEBA DE PARIDAD — {datetime.now().isoformat(sep=' ', timespec='seconds')} ===")

    print("\n[sp_consultar_atleta vs consulta_atleta]")
    for caso in CASOS_ATLETA:
        print(f"\n  Caso: {caso}")
        mysql_r = _sp_atleta(cnx, **caso)
        mongo_r = consultar_atleta(db, **caso)
        _diff_row("fichas",           mysql_r["fichas"],         mongo_r["resumen"]["fichas_mostradas"])
        _diff_row("participaciones",  mysql_r["participaciones"], mongo_r["resumen"]["participaciones"])

    print("\n[sp_consultar_pais vs consulta_pais]")
    for caso in CASOS_PAIS:
        print(f"\n  Caso: {caso}")
        mysql_r = _sp_pais(cnx, **caso)
        mongo_r = consultar_pais(db, **caso)
        _diff_row("sedes",            mysql_r["sedes"],
                  len(mongo_r.get("fue_sede", {}).get("ediciones", [])))
        if mysql_r["medallero"] is not None:
            _diff_row("total_oro",    mysql_r["medallero"].get("total_oro"),
                      mongo_r["medallero"].get("total_oro"))
            _diff_row("total_plata",  mysql_r["medallero"].get("total_plata"),
                      mongo_r["medallero"].get("total_plata"))
            _diff_row("total_bronce", mysql_r["medallero"].get("total_bronce"),
                      mongo_r["medallero"].get("total_bronce"))

    cnx.close()
    client.close()
    print("\n[OK] fin de la prueba de paridad")


if __name__ == "__main__":
    main()
