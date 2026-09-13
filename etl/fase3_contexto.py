# -*- coding: utf-8 -*-
"""
fase3_contexto.py — Pipeline ETL Fase 3: Limpieza de results1.csv y Carga de Tablas de Contexto.

Tablas procesadas:
  1. sede        — Ciudades anfitrionas (City, id_pais)
  2. olimpiada   — Ediciones de los juegos (anio, temporada, nombre_juegos, id_sede)
  3. deporte     — Nombres unicos de deportes (Sport / Discipline)
  4. disciplina  — Disciplinas vinculadas a deporte (incluye disciplina puente)
  5. evento      — Pruebas olimpicas vinculadas a disciplina
  6. equipo      — Equipos y delegaciones deportivas vinculadas a NOC

Archivos de entrada:
  - results.csv_sample.csv (o results1.csv / results.csv crudo)
  - athlete_events_sample.csv (o athlete_events.csv completo)

Decisiones tecnicas aplicadas:
  - DT-003: Disciplina puente (disciplina.nombre = deporte.nombre cuando no hay disciplina)
  - DT-005: Saneamiento universal de mojibake (fix_mojibake)
  - DT-006: Entrada via resolve_data_file()
  - DT-008: Secuencia FK estricta: sede -> olimpiada, deporte -> disciplina -> evento, equipo
  - DT-022: Catalogo historico de ciudades sede (fallback robusto)
  - DT-023: Tratamiento de equipos para pruebas individuales
  - DT-024: Creacion on-the-fly de NOCs y paises requeridos
"""

import os
import sys
import re
import pandas as pd
from mysql.connector import Error

# Agregar directorio etl al sys.path para imports relativos
_CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if _CURRENT_DIR not in sys.path:
    sys.path.insert(0, _CURRENT_DIR)

from utils import (
    get_connection,
    fix_mojibake,
    normalize_name,
    resolve_data_file,
    print_section,
    print_ok,
    print_warn,
    print_error,
    DB_NAME
)


# =====================================================================
# CATÁLOGO HISTÓRICO OFICIAL DE SEDES OLÍMPICAS (DT-022)
# =====================================================================
# Mapeo: (anio, temporada) -> (ciudad, codigo_pais_iso, nombre_pais)
# Respaldo robusto para resolver 100% de sedes aun con muestras reducidas.
OLYMPIC_HOST_CATALOG = {
    (1896, 'Summer'): ('Athina', 'GRE', 'Greece'),
    (1900, 'Summer'): ('Paris', 'FRA', 'France'),
    (1904, 'Summer'): ('St. Louis', 'USA', 'United States'),
    (1906, 'Intercalated'): ('Athina', 'GRE', 'Greece'),
    (1908, 'Summer'): ('London', 'GBR', 'Great Britain'),
    (1912, 'Summer'): ('Stockholm', 'SWE', 'Sweden'),
    (1920, 'Summer'): ('Antwerpen', 'BEL', 'Belgium'),
    (1924, 'Summer'): ('Paris', 'FRA', 'France'),
    (1924, 'Winter'): ('Chamonix', 'FRA', 'France'),
    (1928, 'Summer'): ('Amsterdam', 'NED', 'Netherlands'),
    (1928, 'Winter'): ('St. Moritz', 'SUI', 'Switzerland'),
    (1932, 'Summer'): ('Los Angeles', 'USA', 'United States'),
    (1932, 'Winter'): ('Lake Placid', 'USA', 'United States'),
    (1936, 'Summer'): ('Berlin', 'GER', 'Germany'),
    (1936, 'Winter'): ('Garmisch-Partenkirchen', 'GER', 'Germany'),
    (1948, 'Summer'): ('London', 'GBR', 'Great Britain'),
    (1948, 'Winter'): ('St. Moritz', 'SUI', 'Switzerland'),
    (1952, 'Summer'): ('Helsinki', 'FIN', 'Finland'),
    (1952, 'Winter'): ('Oslo', 'NOR', 'Norway'),
    (1956, 'Summer'): ('Melbourne', 'AUS', 'Australia'),
    (1956, 'Winter'): ("Cortina d'Ampezzo", 'ITA', 'Italy'),
    (1960, 'Summer'): ('Roma', 'ITA', 'Italy'),
    (1960, 'Winter'): ('Squaw Valley', 'USA', 'United States'),
    (1964, 'Summer'): ('Tokyo', 'JPN', 'Japan'),
    (1964, 'Winter'): ('Innsbruck', 'AUT', 'Austria'),
    (1968, 'Summer'): ('Mexico City', 'MEX', 'Mexico'),
    (1968, 'Winter'): ('Grenoble', 'FRA', 'France'),
    (1972, 'Summer'): ('Munich', 'GER', 'Germany'),
    (1972, 'Winter'): ('Sapporo', 'JPN', 'Japan'),
    (1976, 'Summer'): ('Montreal', 'CAN', 'Canada'),
    (1976, 'Winter'): ('Innsbruck', 'AUT', 'Austria'),
    (1980, 'Summer'): ('Moskva', 'RUS', 'Russia'),
    (1980, 'Winter'): ('Lake Placid', 'USA', 'United States'),
    (1984, 'Summer'): ('Los Angeles', 'USA', 'United States'),
    (1984, 'Winter'): ('Sarajevo', 'BIH', 'Bosnia and Herzegovina'),
    (1988, 'Summer'): ('Seoul', 'KOR', 'South Korea'),
    (1988, 'Winter'): ('Calgary', 'CAN', 'Canada'),
    (1992, 'Summer'): ('Barcelona', 'ESP', 'Spain'),
    (1992, 'Winter'): ('Albertville', 'FRA', 'France'),
    (1994, 'Winter'): ('Lillehammer', 'NOR', 'Norway'),
    (1996, 'Summer'): ('Atlanta', 'USA', 'United States'),
    (1998, 'Winter'): ('Nagano', 'JPN', 'Japan'),
    (2000, 'Summer'): ('Sydney', 'AUS', 'Australia'),
    (2002, 'Winter'): ('Salt Lake City', 'USA', 'United States'),
    (2004, 'Summer'): ('Athina', 'GRE', 'Greece'),
    (2006, 'Winter'): ('Torino', 'ITA', 'Italy'),
    (2008, 'Summer'): ('Beijing', 'CHN', 'China'),
    (2010, 'Winter'): ('Vancouver', 'CAN', 'Canada'),
    (2012, 'Summer'): ('London', 'GBR', 'Great Britain'),
    (2014, 'Winter'): ('Sochi', 'RUS', 'Russia'),
    (2016, 'Summer'): ('Rio de Janeiro', 'BRA', 'Brazil'),
    (2018, 'Winter'): ('Pyeongchang', 'KOR', 'South Korea'),
    (2020, 'Summer'): ('Tokyo', 'JPN', 'Japan'),
    (2022, 'Winter'): ('Beijing', 'CHN', 'China'),
    (2024, 'Summer'): ('Paris', 'FRA', 'France'),
}

# Nombres comunes de códigos olímpicos para paises y NOCs
_COMMON_COUNTRIES = {
    'FRA': ('France', 'FRA'),
    'SWE': ('Sweden', 'SWE'),
    'BEL': ('Belgium', 'BEL'),
    'USA': ('United States', 'USA'),
    'ESP': ('Spain', 'ESP'),
    'GBR': ('Great Britain', 'GBR'),
    'CAN': ('Canada', 'CAN'),
    'NOR': ('Norway', 'NOR'),
    'NED': ('Netherlands', 'NED'),
    'CHN': ('China', 'CHN'),
    'DEN': ('Denmark', 'DEN'),
    'AUS': ('Australia', 'AUS'),
    'FIN': ('Finland', 'FIN'),
    'ITA': ('Italy', 'ITA'),
    'JPN': ('Japan', 'JPN'),
    'GER': ('Germany', 'GER'),
    'GRE': ('Greece', 'GRE'),
    'RUS': ('Russia', 'RUS'),
    'SUI': ('Switzerland', 'SUI'),
    'AUT': ('Austria', 'AUT'),
    'BRA': ('Brazil', 'BRA'),
    'KOR': ('South Korea', 'KOR'),
    'GUA': ('Guatemala', 'GUA'),
    'MEX': ('Mexico', 'MEX'),
}


# =====================================================================
# HELPERS DE RESOLUCIÓN DE ENTIDADES EN BASE DE DATOS
# =====================================================================
def _obtener_o_crear_pais(cursor, codigo_pais, nombre_pais=None):
    """Obtiene o inserta un país asegurando su existencia."""
    if not codigo_pais:
        return None
    cod = codigo_pais.strip().upper()[:3]
    
    cursor.execute("SELECT id_pais FROM pais WHERE codigo_pais = %s;", (cod,))
    row = cursor.fetchone()
    if row:
        return row[0]
    
    nom = nombre_pais or _COMMON_COUNTRIES.get(cod, (cod, cod))[0]
    cursor.execute(
        "INSERT INTO pais (codigo_pais, nombre, region) VALUES (%s, %s, %s) "
        "ON DUPLICATE KEY UPDATE nombre = COALESCE(pais.nombre, VALUES(nombre));",
        (cod, nom, nom)
    )
    cursor.execute("SELECT id_pais FROM pais WHERE codigo_pais = %s;", (cod,))
    return cursor.fetchone()[0]


def _obtener_o_crear_noc(cursor, codigo_noc, nombre_noc=None):
    """Obtiene o inserta un NOC asegurando su existencia y vínculo a país."""
    if not codigo_noc:
        return None
    cod = codigo_noc.strip().upper()[:3]
    
    cursor.execute("SELECT id_noc FROM noc WHERE codigo_noc = %s;", (cod,))
    row = cursor.fetchone()
    if row:
        return row[0]
    
    # Resolver o crear país correspondiente
    nom = nombre_noc or _COMMON_COUNTRIES.get(cod, (cod, cod))[0]
    id_pais = _obtener_o_crear_pais(cursor, cod, nom)
    
    cursor.execute(
        "INSERT INTO noc (codigo_noc, nombre_noc, id_pais) VALUES (%s, %s, %s) "
        "ON DUPLICATE KEY UPDATE nombre_noc = VALUES(nombre_noc), id_pais = VALUES(id_pais);",
        (cod, nom, id_pais)
    )
    cursor.execute("SELECT id_noc FROM noc WHERE codigo_noc = %s;", (cod,))
    return cursor.fetchone()[0]


def parsear_games(games_text):
    """
    Parsea una cadena Games a (anio, temporada, nombre_limpio).
    Ejemplos:
      '1912 Summer Olympics' -> (1912, 'Summer', '1912 Summer Olympics')
      '1992 Summer'          -> (1992, 'Summer', '1992 Summer')
      '1906 Intercalated'    -> (1906, 'Intercalated', '1906 Intercalated')
    """
    if not games_text or pd.isna(games_text):
        return None, None, None
    texto = fix_mojibake(str(games_text)).strip()
    m = re.match(r'^(\d{4})\s+([A-Za-z]+)', texto)
    if m:
        anio = int(m.group(1))
        temporada = m.group(2)
        return anio, temporada, texto
    return None, None, texto


# =====================================================================
# 1. CARGA DE SEDE Y OLIMPIADA
# =====================================================================
def cargar_sedes_y_olimpiadas(cursor, conn, results_df, athlete_df):
    """
    Identifica todas las ediciones de los juegos y pobla 'sede' y 'olimpiada'.
    """
    print_section("3.1 Carga de SEDE y OLIMPIADA")
    
    # 1. Extraer mapeos Games -> City de athlete_events
    games_to_city = {}
    if athlete_df is not None and not athlete_df.empty:
        for _, row in athlete_df.iterrows():
            g = row.get('Games')
            c = row.get('City')
            if pd.notna(g) and pd.notna(c):
                anio, temp, _ = parsear_games(g)
                if anio and temp:
                    games_to_city[(anio, temp)] = fix_mojibake(str(c)).strip()
    
    # 2. Recopilar todas las ediciones únicas de ambas fuentes
    ediciones_encontradas = set()
    
    if results_df is not None and not results_df.empty:
        for _, row in results_df.iterrows():
            g = row.get('Games')
            anio, temp, raw_g = parsear_games(g)
            if anio and temp:
                ediciones_encontradas.add((anio, temp, raw_g))
                
    if athlete_df is not None and not athlete_df.empty:
        for _, row in athlete_df.iterrows():
            g = row.get('Games')
            anio, temp, raw_g = parsear_games(g)
            if anio and temp:
                ediciones_encontradas.add((anio, temp, raw_g))
    
    print(f"  Ediciones olímpicas detectadas entre ambas fuentes: {len(ediciones_encontradas)}")
    
    sedes_insertadas = 0
    olimpiadas_insertadas = 0
    
    # Cache de sedes (ciudad, id_pais) -> id_sede
    cursor.execute("SELECT id_sede, ciudad, id_pais FROM sede;")
    cache_sedes = {(r[1], r[2]): r[0] for r in cursor.fetchall()}
    
    # Cache de olimpiadas (anio, temporada) -> id_olimpiada
    cursor.execute("SELECT id_olimpiada, anio, temporada FROM olimpiada;")
    cache_olimpiadas = {(r[1], r[2]): r[0] for r in cursor.fetchall()}
    
    for anio, temp, raw_g in sorted(ediciones_encontradas):
        # Resolver ciudad y país
        ciudad = games_to_city.get((anio, temp))
        pais_cod = None
        pais_nom = None
        
        # Fallback al catálogo histórico oficial
        if (anio, temp) in OLYMPIC_HOST_CATALOG:
            cat_ciudad, cat_cod, cat_nom = OLYMPIC_HOST_CATALOG[(anio, temp)]
            if not ciudad:
                ciudad = cat_ciudad
            pais_cod = cat_cod
            pais_nom = cat_nom
        
        if not ciudad:
            ciudad = "Desconocida"
            
        # Resolver o crear país de la sede
        id_pais = _obtener_o_crear_pais(cursor, pais_cod, pais_nom) if pais_cod else None
        
        # Insertar o recuperar sede
        key_sede = (ciudad, id_pais)
        if key_sede not in cache_sedes:
            cursor.execute(
                "INSERT INTO sede (ciudad, id_pais) VALUES (%s, %s) "
                "ON DUPLICATE KEY UPDATE ciudad = VALUES(ciudad);",
                (ciudad, id_pais)
            )
            cursor.execute("SELECT id_sede FROM sede WHERE ciudad = %s AND (id_pais = %s OR (id_pais IS NULL AND %s IS NULL));", (ciudad, id_pais, id_pais))
            id_sede = cursor.fetchone()[0]
            cache_sedes[key_sede] = id_sede
            sedes_insertadas += 1
        else:
            id_sede = cache_sedes[key_sede]
            
        # Insertar o recuperar olimpiada
        key_olimp = (anio, temp)
        if key_olimp not in cache_olimpiadas:
            cursor.execute(
                "INSERT INTO olimpiada (anio, temporada, nombre_juegos, id_sede) "
                "VALUES (%s, %s, %s, %s) "
                "ON DUPLICATE KEY UPDATE nombre_juegos = VALUES(nombre_juegos), id_sede = VALUES(id_sede);",
                (anio, temp, raw_g, id_sede)
            )
            cursor.execute("SELECT id_olimpiada FROM olimpiada WHERE anio = %s AND temporada = %s;", (anio, temp))
            id_olimp = cursor.fetchone()[0]
            cache_olimpiadas[key_olimp] = id_olimp
            olimpiadas_insertadas += 1
            
    conn.commit()
    print_ok(f"Sedes procesadas: {len(cache_sedes)} (nuevas insertadas: {sedes_insertadas})")
    print_ok(f"Olimpiadas procesadas: {len(cache_olimpiadas)} (nuevas insertadas: {olimpiadas_insertadas})")
    return cache_sedes, cache_olimpiadas


# =====================================================================
# 2. CARGA DE DEPORTE, DISCIPLINA Y EVENTO
# =====================================================================
def cargar_jerarquia_deportiva(cursor, conn, results_df, athlete_df):
    """
    Pobla deporte -> disciplina -> evento cumpliendo la jerarquia de 3 niveles
    y la regla de disciplina puente (DT-003).
    """
    print_section("3.2 Carga de DEPORTE, DISCIPLINA y EVENTO (Jerarquía 3NF)")
    
    # Cargar caches existentes
    cursor.execute("SELECT id_deporte, nombre FROM deporte;")
    cache_deportes = {r[1]: r[0] for r in cursor.fetchall()}
    
    cursor.execute("SELECT id_disciplina, nombre, id_deporte FROM disciplina;")
    cache_disciplinas = {(r[1], r[2]): r[0] for r in cursor.fetchall()}
    
    cursor.execute("SELECT id_evento, nombre, id_disciplina FROM evento;")
    cache_eventos = {(r[1], r[2]): r[0] for r in cursor.fetchall()}
    
    deportes_nuevos = 0
    disciplinas_nuevas = 0
    eventos_nuevos = 0
    
    # Helper interno para asegurar deporte
    def asegurar_deporte(nombre_dep):
        nonlocal deportes_nuevos
        nom = fix_mojibake(nombre_dep).strip()[:120]
        if nom not in cache_deportes:
            cursor.execute(
                "INSERT INTO deporte (nombre) VALUES (%s) "
                "ON DUPLICATE KEY UPDATE nombre = VALUES(nombre);",
                (nom,)
            )
            cursor.execute("SELECT id_deporte FROM deporte WHERE nombre = %s;", (nom,))
            id_dep = cursor.fetchone()[0]
            cache_deportes[nom] = id_dep
            deportes_nuevos += 1
        return cache_deportes[nom]

    # Helper interno para asegurar disciplina
    def asegurar_disciplina(nombre_disc, id_dep):
        nonlocal disciplinas_nuevas
        nom = fix_mojibake(nombre_disc).strip()[:120]
        key = (nom, id_dep)
        if key not in cache_disciplinas:
            cursor.execute(
                "INSERT INTO disciplina (nombre, id_deporte) VALUES (%s, %s);",
                (nom, id_dep)
            )
            id_disc = cursor.lastrowid
            cache_disciplinas[key] = id_disc
            disciplinas_nuevas += 1
        return cache_disciplinas[key]

    # Helper interno para asegurar evento
    def asegurar_evento(nombre_ev, id_disc):
        nonlocal eventos_nuevos
        nom = fix_mojibake(nombre_ev).strip()[:200]
        key = (nom, id_disc)
        if key not in cache_eventos:
            cursor.execute(
                "INSERT INTO evento (nombre, id_disciplina) VALUES (%s, %s);",
                (nom, id_disc)
            )
            id_ev = cursor.lastrowid
            cache_eventos[key] = id_ev
            eventos_nuevos += 1
        return cache_eventos[key]

    # 1. Ingesta desde results1.csv (Olympedia: trae Discipline y Event)
    if results_df is not None and not results_df.empty:
        for _, row in results_df.iterrows():
            disc_raw = row.get('Discipline')
            ev_raw = row.get('Event')
            
            if pd.notna(disc_raw) and pd.notna(ev_raw):
                nom_disc = fix_mojibake(str(disc_raw)).strip()
                nom_ev = fix_mojibake(str(ev_raw)).strip()
                
                # Deporte = Discipline (Olympedia nombra el deporte como Discipline)
                id_dep = asegurar_deporte(nom_disc)
                id_disc = asegurar_disciplina(nom_disc, id_dep)
                asegurar_evento(nom_ev, id_disc)
                
    # 2. Ingesta desde athlete_events.csv (Kaggle: trae Sport y Event, sin Discipline)
    if athlete_df is not None and not athlete_df.empty:
        for _, row in athlete_df.iterrows():
            sport_raw = row.get('Sport')
            ev_raw = row.get('Event')
            
            if pd.notna(sport_raw) and pd.notna(ev_raw):
                nom_sport = fix_mojibake(str(sport_raw)).strip()
                nom_ev = fix_mojibake(str(ev_raw)).strip()
                
                id_dep = asegurar_deporte(nom_sport)
                # Disciplina puente: disciplina.nombre = deporte.nombre
                id_disc = asegurar_disciplina(nom_sport, id_dep)
                asegurar_evento(nom_ev, id_disc)
                
    conn.commit()
    print_ok(f"Deportes: {len(cache_deportes)} (nuevos: {deportes_nuevos})")
    print_ok(f"Disciplinas: {len(cache_disciplinas)} (nuevas: {disciplinas_nuevas})")
    print_ok(f"Eventos: {len(cache_eventos)} (nuevos: {eventos_nuevos})")
    return cache_deportes, cache_disciplinas, cache_eventos


# =====================================================================
# 3. CARGA DE LA TABLA EQUIPO
# =====================================================================
def cargar_equipos(cursor, conn, results_df, athlete_df):
    """
    Pobla 'equipo' vinculando con el respectivo NOC (DT-023 y DT-024).
    Maneja pruebas individuales en results asignando la delegacion correspondiente.
    """
    print_section("3.3 Carga de la tabla EQUIPO")
    
    cursor.execute("SELECT id_equipo, nombre, id_noc FROM equipo;")
    cache_equipos = {(r[1], r[2]): r[0] for r in cursor.fetchall()}
    equipos_nuevos = 0
    
    # 1. Equipos de results1.csv
    if results_df is not None and not results_df.empty:
        for _, row in results_df.iterrows():
            noc_raw = str(row.get('NOC')).strip().upper()[:3] if pd.notna(row.get('NOC')) else None
            team_raw = row.get('Team')
            
            if not noc_raw:
                continue
                
            id_noc = _obtener_o_crear_noc(cursor, noc_raw)
            
            # Si Team es vacio (individual), usar nombre del pais/delegacion
            if pd.isna(team_raw) or not str(team_raw).strip():
                # Nombre del pais asociado a ese NOC
                cursor.execute("SELECT nombre_noc FROM noc WHERE id_noc = %s;", (id_noc,))
                nom_noc = cursor.fetchone()[0]
                team_name = nom_noc or noc_raw
            else:
                team_name = fix_mojibake(str(team_raw)).strip()[:120]
                
            key = (team_name, id_noc)
            if key not in cache_equipos:
                cursor.execute(
                    "INSERT INTO equipo (nombre, id_noc) VALUES (%s, %s) "
                    "ON DUPLICATE KEY UPDATE nombre = VALUES(nombre);",
                    (team_name, id_noc)
                )
                cursor.execute("SELECT id_equipo FROM equipo WHERE nombre = %s AND (id_noc = %s OR (id_noc IS NULL AND %s IS NULL));", (team_name, id_noc, id_noc))
                id_eq = cursor.fetchone()[0]
                cache_equipos[key] = id_eq
                equipos_nuevos += 1
                
    # 2. Equipos de athlete_events.csv
    if athlete_df is not None and not athlete_df.empty:
        for _, row in athlete_df.iterrows():
            team_raw = row.get('Team')
            noc_raw = str(row.get('NOC')).strip().upper()[:3] if pd.notna(row.get('NOC')) else None
            
            if pd.isna(team_raw) or not noc_raw:
                continue
                
            team_name = fix_mojibake(str(team_raw)).strip()[:120]
            id_noc = _obtener_o_crear_noc(cursor, noc_raw)
            
            key = (team_name, id_noc)
            if key not in cache_equipos:
                cursor.execute(
                    "INSERT INTO equipo (nombre, id_noc) VALUES (%s, %s) "
                    "ON DUPLICATE KEY UPDATE nombre = VALUES(nombre);",
                    (team_name, id_noc)
                )
                cursor.execute("SELECT id_equipo FROM equipo WHERE nombre = %s AND (id_noc = %s OR (id_noc IS NULL AND %s IS NULL));", (team_name, id_noc, id_noc))
                id_eq = cursor.fetchone()[0]
                cache_equipos[key] = id_eq
                equipos_nuevos += 1
                
    conn.commit()
    print_ok(f"Equipos procesados: {len(cache_equipos)} (nuevos insertados: {equipos_nuevos})")
    return cache_equipos


# =====================================================================
# 4. VERIFICACIÓN DE LA FASE 3
# =====================================================================
def verificar_fase3(cursor):
    """
    Ejecuta consultas de control para validar el estado de las 6 tablas de contexto.
    """
    print_section("3.4 Verificación de Fase 3")
    
    consultas = [
        ("sede", "SELECT COUNT(*) FROM sede;"),
        ("olimpiada", "SELECT COUNT(*) FROM olimpiada;"),
        ("deporte", "SELECT COUNT(*) FROM deporte;"),
        ("disciplina", "SELECT COUNT(*) FROM disciplina;"),
        ("evento", "SELECT COUNT(*) FROM evento;"),
        ("equipo", "SELECT COUNT(*) FROM equipo;"),
    ]
    
    conteos = {}
    for tabla, sql in consultas:
        cursor.execute(sql)
        cnt = cursor.fetchone()[0]
        conteos[tabla] = cnt
        print(f"  Total registros en '{tabla}': {cnt}")
        
    # Verificar integridades foráneas
    print("\n  Comprobando integridad de claves foráneas:")
    
    # 1. Sede -> Pais
    cursor.execute("SELECT COUNT(*) FROM sede s LEFT JOIN pais p ON s.id_pais = p.id_pais WHERE s.id_pais IS NOT NULL AND p.id_pais IS NULL;")
    h_sede = cursor.fetchone()[0]
    print(f"    FK sede -> pais huérfanas: {h_sede}")
    
    # 2. Olimpiada -> Sede
    cursor.execute("SELECT COUNT(*) FROM olimpiada o LEFT JOIN sede s ON o.id_sede = s.id_sede WHERE o.id_sede IS NOT NULL AND s.id_sede IS NULL;")
    h_olimp = cursor.fetchone()[0]
    print(f"    FK olimpiada -> sede huérfanas: {h_olimp}")
    
    # 3. Disciplina -> Deporte
    cursor.execute("SELECT COUNT(*) FROM disciplina d LEFT JOIN deporte dep ON d.id_deporte = dep.id_deporte WHERE d.id_deporte IS NOT NULL AND dep.id_deporte IS NULL;")
    h_disc = cursor.fetchone()[0]
    print(f"    FK disciplina -> deporte huérfanas: {h_disc}")
    
    # 4. Evento -> Disciplina
    cursor.execute("SELECT COUNT(*) FROM evento e LEFT JOIN disciplina d ON e.id_disciplina = d.id_disciplina WHERE e.id_disciplina IS NOT NULL AND d.id_disciplina IS NULL;")
    h_ev = cursor.fetchone()[0]
    print(f"    FK evento -> disciplina huérfanas: {h_ev}")
    
    # 5. Equipo -> NOC
    cursor.execute("SELECT COUNT(*) FROM equipo eq LEFT JOIN noc n ON eq.id_noc = n.id_noc WHERE eq.id_noc IS NOT NULL AND n.id_noc IS NULL;")
    h_eq = cursor.fetchone()[0]
    print(f"    FK equipo -> noc huérfanas: {h_eq}")
    
    print("\n  Muestra de Olimpiadas y Sedes vinculadas:")
    cursor.execute("""
        SELECT o.anio, o.temporada, o.nombre_juegos, s.ciudad, p.codigo_pais
        FROM olimpiada o
        JOIN sede s ON o.id_sede = s.id_sede
        LEFT JOIN pais p ON s.id_pais = p.id_pais
        ORDER BY o.anio
        LIMIT 5;
    """)
    for r in cursor.fetchall():
        print(f"    [{r[0]} {r[1]}] Juegos: '{r[2]}', Sede: {r[3]} ({r[4]})")
        
    print("\n  Muestra de Jerarquía Deporte -> Disciplina -> Evento:")
    cursor.execute("""
        SELECT dep.nombre AS deporte, d.nombre AS disciplina, e.nombre AS evento
        FROM evento e
        JOIN disciplina d ON e.id_disciplina = d.id_disciplina
        JOIN deporte dep ON d.id_deporte = dep.id_deporte
        ORDER BY dep.nombre, e.nombre
        LIMIT 5;
    """)
    for r in cursor.fetchall():
        print(f"    Deporte: '{r[0]}' | Disciplina: '{r[1]}' | Evento: '{r[2]}'")
        
    todo_valido = all(cnt > 0 for cnt in conteos.values()) and all(h == 0 for h in [h_sede, h_olimp, h_disc, h_ev, h_eq])
    if todo_valido:
        print_ok("Verificación de Fase 3 EXITOSA. Todas las tablas y FKs están conformes.")
        return True
    else:
        print_error("Verificación de Fase 3 con advertencias o registros faltantes.")
        return False


# =====================================================================
# EJECUTOR PRINCIPAL DE FASE 3
# =====================================================================
def ejecutar_fase3():
    """Ejecuta el pipeline completo de la Fase 3."""
    print_section("INICIO DE EJECUCION: FASE 3 (Carga de Contexto)")
    
    path_results = resolve_data_file('results')
    path_athlete = resolve_data_file('athlete_events')
    
    if not path_results or not os.path.isfile(path_results):
        print_error(f"No se encontró archivo de results: {path_results}")
        return False
        
    print(f"  Archivo results: {path_results}")
    results_df = pd.read_csv(path_results)
    print_ok(f"results leído: {len(results_df)} registros")
    
    athlete_df = None
    if path_athlete and os.path.isfile(path_athlete):
        print(f"  Archivo athlete_events: {path_athlete}")
        athlete_df = pd.read_csv(path_athlete)
        print_ok(f"athlete_events leído: {len(athlete_df)} registros")
    else:
        print_warn("athlete_events no encontrado, se utilizará solo catálogo de respaldo.")
        
    conn = None
    try:
        conn = get_connection(database=DB_NAME)
        cursor = conn.cursor()
        
        # 1. Cargar sedes y olimpiadas
        cargar_sedes_y_olimpiadas(cursor, conn, results_df, athlete_df)
        
        # 2. Cargar deportes, disciplinas y eventos
        cargar_jerarquia_deportiva(cursor, conn, results_df, athlete_df)
        
        # 3. Cargar equipos
        cargar_equipos(cursor, conn, results_df, athlete_df)
        
        # 4. Verificación
        exito = verificar_fase3(cursor)
        
        cursor.close()
        conn.close()
        return exito
        
    except Error as e:
        if conn and conn.is_connected():
            conn.rollback()
            conn.close()
        print_error(f"Fallo durante la ejecución de la Fase 3 en MySQL: {e}")
        return False
    except Exception as e:
        if conn and conn.is_connected():
            conn.rollback()
            conn.close()
        print_error(f"Error general en Fase 3: {e}")
        return False


if __name__ == '__main__':
    ok = ejecutar_fase3()
    sys.exit(0 if ok else 1)
