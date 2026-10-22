# -*- coding: utf-8 -*-
"""
casos_prueba.py  —  Fase 3 (Integrante 3)

Ejecuta los casos de prueba del día de calificación. Cada caso corre
consulta_atleta o consulta_pais con los parámetros definidos y mide el
tiempo de respuesta. Útil para ensayo y para la bitácora de rendimiento.

Uso:
    python casos_prueba.py
"""
import os
import sys
import time
from datetime import datetime

from dotenv import load_dotenv
from pymongo import MongoClient

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "consultas"))
from consulta_atleta import consultar_atleta
from consulta_pais import consultar_pais


CASOS_ATLETA = [
    {"nombre": "Phelps"},
    {"nombre": "Phelps", "anio": 2008},
    {"nombre": "Bolt", "deporte": "Athletics"},
    {"nombre": "Barrondo", "pais": "GUA"},
    {"nombre": "Ruano"},
    {"nombre": "Jean Borotra"},  # mismo caso que usa la Fase 1 en sus pruebas
]

CASOS_PAIS = [
    {"pais": "GUA"},
    {"pais": "GUA", "solo_medallas": True},
    {"pais": "FRA"},
    {"pais": "USA", "anio_inicio": 2016, "anio_fin": 2024},
    {"pais": "Guatemala"},
]


def _run(label, fn, kwargs):
    t0 = time.perf_counter()
    res = fn(**kwargs)
    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    # el propio res trae tiempo_ms interno (sin red extra)
    tiempo_interno = res.get("tiempo_ms")
    resumen = res.get("resumen") or {
        "medallero": res.get("medallero", {}),
        "fue_sede": res.get("fue_sede", {}).get("si"),
    }
    print(f"  {label:<60s} {elapsed_ms:>8.1f} ms   (interno {tiempo_interno} ms)")
    return elapsed_ms, resumen


def main():
    _env = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
    load_dotenv(_env)
    client = MongoClient(os.environ["MONGO_URI"], serverSelectionTimeoutMS=10000)
    db = client[os.environ.get("MONGO_DB", "olimpiadas")]

    print(f"=== CASOS DE PRUEBA — {datetime.now().isoformat(sep=' ', timespec='seconds')} ===\n")

    print("[consulta_atleta]")
    for caso in CASOS_ATLETA:
        label = ", ".join(f"{k}={v}" for k, v in caso.items())
        _run(label, consultar_atleta, {"db": db, **caso})

    print("\n[consulta_pais]")
    for caso in CASOS_PAIS:
        label = ", ".join(f"{k}={v}" for k, v in caso.items())
        _run(label, consultar_pais, {"db": db, **caso})

    client.close()
    print("\n[OK] fin de la suite")


if __name__ == "__main__":
    main()
