# -*- coding: utf-8 -*-
"""Genera las 9 rondas de carga (atleta + participacion) desde P1 'olimpiadas'.

3 tipos (anio, deporte, deportista) x 3 rondas. Dedup de atletas dentro de cada
tipo: un atleta que compite en varias ediciones se inserta solo en la primera
ronda donde aparece. Preserva PK originales para que las FK calcen con
00_catalogos.sql.

Uso:  python Fase2/carga/_generadores/gen_rondas.py
Requiere: Fase1/etl/utils.py (get_connection) y la base 'olimpiadas' del P1.
"""
import sys, os, datetime
from decimal import Decimal

# Rutas portables: <repo>/Fase2/carga/_generadores/gen_rondas.py
_GEN = os.path.dirname(os.path.abspath(__file__))
CARGA = os.path.dirname(_GEN)                   # <repo>/Fase2/carga
REPO = os.path.dirname(os.path.dirname(CARGA))  # <repo>
sys.path.insert(0, os.path.join(REPO, "Fase1", "etl"))
from utils import get_connection

# Base destino = la que crea el contenedor Docker de Fase2 (olimpiada2s.sql).
DB_DESTINO = "olimpiadas"
BATCH = 200

NOMBRES_100M = ("100 metres, Women (Olympic)", "Athletics Women's 100 metres", "Women's 100m")

# tipo -> [(archivo, etiqueta, clausula_where, params)]
# La clausula filtra PARTICIPACION (alias p), con JOIN a olimpiada o / evento e / atleta a.
TIPOS = {
    "anio": [
        ("01_ronda1_rio2016.sql",   "Rio 2016",   "o.anio=2016 AND o.temporada='Summer'", ()),
        ("02_ronda2_tokio2020.sql", "Tokio 2020", "o.anio=2020 AND o.temporada='Summer'", ()),
        ("03_ronda3_paris2024.sql", "Paris 2024", "o.anio=2024 AND o.temporada='Summer'", ()),
    ],
    "deporte": [
        ("01_ronda1_rio2016.sql",   "100m femenino - Rio 2016",   "o.anio=2016 AND e.nombre IN (%s,%s,%s)", NOMBRES_100M),
        ("02_ronda2_tokio2020.sql", "100m femenino - Tokio 2020", "o.anio=2020 AND e.nombre IN (%s,%s,%s)", NOMBRES_100M),
        ("03_ronda3_paris2024.sql", "100m femenino - Paris 2024", "o.anio=2024 AND e.nombre IN (%s,%s,%s)", NOMBRES_100M),
    ],
    "deportista": [
        ("01_ronda1_atenas2004.sql",  "Usain Bolt - Atenas 2004",  "o.anio=2004 AND a.nombre LIKE '%Usain%' AND a.nombre LIKE '%Bolt%'", ()),
        ("02_ronda2_pekin2008.sql",   "Usain Bolt - Pekin 2008",   "o.anio=2008 AND a.nombre LIKE '%Usain%' AND a.nombre LIKE '%Bolt%'", ()),
        ("03_ronda3_londres2012.sql", "Usain Bolt - Londres 2012", "o.anio=2012 AND a.nombre LIKE '%Usain%' AND a.nombre LIKE '%Bolt%'", ()),
    ],
}


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


def batched_inserts(tabla, cols, rows):
    out = []
    collist = ", ".join("`" + c + "`" for c in cols)
    for i in range(0, len(rows), BATCH):
        chunk = rows[i:i + BATCH]
        vals = ",\n".join("(" + ", ".join(sqlval(v) for v in r) + ")" for r in chunk)
        out.append(f"INSERT INTO `{tabla}` ({collist}) VALUES\n{vals};")
    return out


def main():
    conn = get_connection(database="olimpiadas")
    cur = conn.cursor()

    resumen = []
    for tipo, rondas in TIPOS.items():
        seen_atletas = set()
        carpeta = os.path.join(CARGA, tipo)
        os.makedirs(carpeta, exist_ok=True)
        for archivo, etiqueta, where, params in rondas:
            cur.execute(f"""SELECT p.* FROM participacion p
                JOIN olimpiada o ON p.id_olimpiada=o.id_olimpiada
                JOIN evento e ON p.id_evento=e.id_evento
                JOIN atleta a ON p.id_atleta=a.id_atleta
                WHERE {where}""", params)
            pcols = cur.column_names
            prows = cur.fetchall()
            idx_atleta = pcols.index("id_atleta")
            ids_ronda = {r[idx_atleta] for r in prows}
            nuevos = sorted(ids_ronda - seen_atletas)
            arows, acols = [], []
            if nuevos:
                fmt = ",".join(["%s"] * len(nuevos))
                cur.execute(f"SELECT * FROM atleta WHERE id_atleta IN ({fmt})", tuple(nuevos))
                acols = cur.column_names
                arows = cur.fetchall()
            seen_atletas |= ids_ronda

            lines = [
                "-- ============================================================",
                f"-- {tipo}/{archivo}  (Proyecto 2 - Fase 2, Integrante 2)",
                f"-- Ronda: {etiqueta}",
                f"-- Atletas nuevos: {len(arows)} | Participaciones: {len(prows)}",
                "-- Requiere 00_catalogos.sql cargado previamente.",
                "-- IMPORTANTE: cargar contra Docker Fase2 (127.0.0.1:3307), NO el 3306 (P1).",
                "-- Generado automaticamente. NO editar a mano.",
                "-- ============================================================",
                f"USE {DB_DESTINO};",
                "SET FOREIGN_KEY_CHECKS = 0;",
                "",
            ]
            if arows:
                lines.append(f"-- atleta: {len(arows)} filas nuevas")
                lines += batched_inserts("atleta", acols, arows)
                lines.append("")
            lines.append(f"-- participacion: {len(prows)} filas")
            lines += batched_inserts("participacion", pcols, prows)
            lines.append("")
            lines.append("SET FOREIGN_KEY_CHECKS = 1;")
            lines.append("")
            with open(os.path.join(carpeta, archivo), "w", encoding="utf-8") as f:
                f.write("\n".join(lines))
            resumen.append((tipo, archivo, len(arows), len(prows)))

    conn.close()
    for t, a, na, npart in resumen:
        print(f"{t}/{a}: atletas={na}, participaciones={npart}")


if __name__ == "__main__":
    main()
