# -*- coding: utf-8 -*-
"""Genera Fase2/carga/00_catalogos.sql desde la base del Proyecto 1 ('olimpiadas').

Extrae las 10 tablas de dimension (medalla ya la siembra el DDL) preservando
los PK originales para que las FK de las rondas sigan siendo validas.

Uso:  python Fase2/carga/_generadores/gen_catalogos.py
Requiere: Fase1/etl/utils.py con las credenciales de MySQL (get_connection)
          y la base 'olimpiadas' del Proyecto 1 cargada.
"""
import sys, os, datetime
from decimal import Decimal

# Rutas portables calculadas desde la ubicacion de este script:
# <repo>/Fase2/carga/_generadores/gen_catalogos.py
_GEN = os.path.dirname(os.path.abspath(__file__))
CARGA = os.path.dirname(_GEN)                 # <repo>/Fase2/carga
REPO = os.path.dirname(os.path.dirname(CARGA))  # <repo>
sys.path.insert(0, os.path.join(REPO, "Fase1", "etl"))
from utils import get_connection

OUT = os.path.join(CARGA, "00_catalogos.sql")
# Base destino = la que crea el contenedor Docker de Fase2 (olimpiada2s.sql).
DB_DESTINO = "olimpiadas"
# Orden FK-safe. medalla se excluye (sembrada por el DDL).
TABLAS = ["pais", "noc", "sede", "olimpiada", "deporte",
          "disciplina", "evento", "equipo", "poblacion_pais"]
BATCH = 200


def sqlval(v):
    if v is None:
        return "NULL"
    if isinstance(v, bool):
        return "1" if v else "0"
    if isinstance(v, (int, Decimal)):
        return str(v)
    if isinstance(v, datetime.datetime):
        return "'" + v.isoformat(sep=" ") + "'"
    if isinstance(v, datetime.date):
        return "'" + v.isoformat() + "'"
    if isinstance(v, (bytes, bytearray)):
        v = v.decode("utf-8", "replace")
    return "'" + str(v).replace("\\", "\\\\").replace("'", "\\'") + "'"


def main():
    conn = get_connection(database="olimpiadas")
    cur = conn.cursor()

    lines = [
        "-- ============================================================",
        "-- 00_catalogos.sql  (Proyecto 2 - Fase 2, Integrante 2)",
        "-- Carga inicial de catalogos (10 dimensiones) para " + DB_DESTINO,
        "-- Origen: base de datos del Proyecto 1 ('olimpiadas', MySQL local 3306).",
        "-- Se preservan los PK originales para mantener integridad de FK.",
        "-- IMPORTANTE: cargar contra la instancia Docker de Fase2 (127.0.0.1:3307),",
        "--            NO contra el MySQL local 3306 (ahi vive el P1).",
        "-- Generado automaticamente. NO editar a mano.",
        "-- ============================================================",
        "USE " + DB_DESTINO + ";",
        "SET FOREIGN_KEY_CHECKS = 0;",
        "",
    ]

    total = 0
    for t in TABLAS:
        cur.execute(f"SELECT * FROM {t}")
        cols = cur.column_names
        rows = cur.fetchall()
        total += len(rows)
        collist = ", ".join("`" + c + "`" for c in cols)
        lines.append(f"-- {t}: {len(rows)} filas")
        for i in range(0, len(rows), BATCH):
            chunk = rows[i:i + BATCH]
            vals = ",\n".join("(" + ", ".join(sqlval(v) for v in r) + ")" for r in chunk)
            lines.append(f"INSERT INTO `{t}` ({collist}) VALUES\n{vals};")
        lines.append("")

    lines.append("SET FOREIGN_KEY_CHECKS = 1;")
    lines.append("-- Total filas de catalogos: " + str(total))
    lines.append("")

    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    conn.close()
    print("Escrito:", OUT)
    print("Total filas:", total)


if __name__ == "__main__":
    main()
