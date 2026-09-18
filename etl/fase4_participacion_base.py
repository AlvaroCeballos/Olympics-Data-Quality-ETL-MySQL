# -*- coding: utf-8 -*-
"""
fase4_participacion_base.py — Pipeline ETL Fase 4: Carga de Participación — Capa Base (Fuente 1).

Tabla procesada:
  - participacion: Tabla transaccional de hechos que registra cada participación
                   de un atleta en un evento de una edición olímpica.

Archivo de entrada:
  - results.csv_sample.csv (o results1.csv / results.csv crudo de Olympedia)

Decisiones técnicas aplicadas:
  - DT-001: id_externo del atleta como clave foránea a atleta
  - DT-005: Saneamiento universal de mojibake (fix_mojibake)
  - DT-006: Entrada vía resolve_data_file()
  - DT-008: Secuencia FK estricta (participación depende de atleta, evento, olimpiada, equipo, medalla)
  - DT-010: Homologación de medallas (Gold, Silver, Bronze, NA)
  - DT-011: Tratamiento de posiciones y empates (flag es_empate = TRUE si Pos contiene '=')
  - DT-012: Omitir columna Unnamed: 7 (100% vacía)
  - DT-013: Omitir Nationality de results1 (redundante con atleta.nacionalidad)
  - DT-023: Resolución de equipos para eventos individuales
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
    resolve_data_file,
    print_section,
    print_ok,
    print_warn,
    print_error,
    DB_NAME
)


def parsear_games(games_text):
    """Parsea una cadena Games a (anio, temporada)."""
    if not games_text or pd.isna(games_text):
        return None, None
    texto = fix_mojibake(str(games_text)).strip()
    m = re.match(r'^(\d{4})\s+([A-Za-z]+)', texto)
    if m:
        return int(m.group(1)), m.group(2)
    return None, None


def homologar_medalla(medalla_raw, cache_medallas):
    """
    Homologa el valor textual de medalla al id_medalla del catálogo.
    DT-010: Gold, Silver, Bronze, y cualquier valor nulo/vacío/'No medal' -> 'NA'.
    """
    if pd.isna(medalla_raw) or not str(medalla_raw).strip():
        return cache_medallas.get('NA')
    
    med = str(medalla_raw).strip().capitalize()
    if med in ('Gold', 'Silver', 'Bronze'):
        return cache_medallas.get(med)
    
    return cache_medallas.get('NA')


def procesar_posicion_y_empate(pos_raw):
    """
    Procesa la columna Pos (DT-011):
      - Si contiene '=' -> es_empate = True, posicion = número limpio
      - Si es texto ('DNS', 'DNF', 'DQ') o número -> posicion = texto, es_empate = False
      - Si es nulo -> posicion = None, es_empate = False
    """
    if pd.isna(pos_raw) or not str(pos_raw).strip():
        return None, False
    
    texto = fix_mojibake(str(pos_raw)).strip()
    if '=' in texto:
        pos_limpia = texto.replace('=', '').strip()[:30]
        return pos_limpia, True
    
    return texto[:30], False


def cargar_participacion_base():
    """
    Lee results1.csv e inserta las participaciones base en MySQL.
    """
    print_section("INICIO DE EJECUCIÓN: FASE 4 (Participación — Capa Base)")
    
    path_results = resolve_data_file('results')
    if not path_results or not os.path.isfile(path_results):
        print_error(f"No se encontró archivo de results: {path_results}")
        return False
    
    print(f"  Archivo results: {path_results}")
    results_df = pd.read_csv(path_results)
    print_ok(f"results leído: {len(results_df)} registros")
    
    conn = None
    try:
        conn = get_connection(database=DB_NAME)
        cursor = conn.cursor()
        
        # =====================================================================
        # 1. CARGA DE CATÁLOGOS EN MEMORIA PARA LOOKUPS RÁPIDOS
        # =====================================================================
        print_section("4.1 Carga de catálogos y cachés en memoria")
        
        # Atletas: athlete_id (id_externo) -> id_atleta
        cursor.execute("SELECT id_externo, id_atleta FROM atleta WHERE id_externo IS NOT NULL;")
        cache_atletas = {r[0]: r[1] for r in cursor.fetchall()}
        print_ok(f"Atletas en caché: {len(cache_atletas)}")
        
        # Medallas: tipo -> id_medalla
        cursor.execute("SELECT tipo, id_medalla FROM medalla;")
        cache_medallas = {r[0]: r[1] for r in cursor.fetchall()}
        print_ok(f"Medallas en caché: {len(cache_medallas)} (Gold, Silver, Bronze, NA)")
        
        # Olimpiadas: (anio, temporada) -> id_olimpiada
        cursor.execute("SELECT anio, temporada, id_olimpiada FROM olimpiada;")
        cache_olimpiadas = {(r[0], r[1]): r[2] for r in cursor.fetchall()}
        print_ok(f"Olimpiadas en caché: {len(cache_olimpiadas)}")
        
        # NOCs: codigo_noc -> id_noc
        cursor.execute("SELECT codigo_noc, id_noc, nombre_noc FROM noc;")
        cache_nocs = {r[0]: (r[1], r[2]) for r in cursor.fetchall()}
        
        # Equipos: (nombre, id_noc) -> id_equipo
        cursor.execute("SELECT nombre, id_noc, id_equipo FROM equipo;")
        cache_equipos = {(r[0], r[1]): r[2] for r in cursor.fetchall()}
        print_ok(f"Equipos en caché: {len(cache_equipos)}")
        
        # Disciplinas: nombre -> id_disciplina
        cursor.execute("SELECT nombre, id_disciplina FROM disciplina;")
        cache_disciplinas = {r[0]: r[1] for r in cursor.fetchall()}
        
        # Eventos: (nombre, id_disciplina) -> id_evento
        cursor.execute("SELECT nombre, id_disciplina, id_evento FROM evento;")
        cache_eventos = {(r[0], r[1]): r[2] for r in cursor.fetchall()}
        print_ok(f"Eventos en caché: {len(cache_eventos)}")
        
        # Participaciones existentes para evitar duplicados: (id_atleta, id_evento, id_olimpiada) -> id_participacion
        cursor.execute("SELECT id_atleta, id_evento, id_olimpiada, id_participacion FROM participacion;")
        cache_participaciones = {(r[0], r[1], r[2]): r[3] for r in cursor.fetchall()}
        print(f"  Participaciones previas registradas: {len(cache_participaciones)}")
        
        # =====================================================================
        # 2. PROCESAMIENTO E INSERCIÓN DE PARTICIPACIONES
        # =====================================================================
        print_section("4.2 Procesamiento de participaciones de Fuente 1")
        
        sql_insert = """
            INSERT INTO participacion (
                id_atleta, id_evento, id_olimpiada, id_equipo, id_medalla,
                compitio_como, edad, altura_reg, peso_reg, posicion, es_empate
            ) VALUES (
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s
            );
        """
        
        insertadas = 0
        omitidas_duplicadas = 0
        omitidas_sin_atleta = 0
        
        for idx, (_, row) in enumerate(results_df.iterrows()):
            aid_raw = row.get('athlete_id')
            if pd.isna(aid_raw):
                continue
            aid = int(aid_raw)
            
            # 1. Resolver id_atleta
            id_atleta = cache_atletas.get(aid)
            if not id_atleta:
                omitidas_sin_atleta += 1
                continue
            
            # 2. Resolver id_olimpiada
            anio, temp = parsear_games(row.get('Games'))
            id_olimpiada = cache_olimpiadas.get((anio, temp))
            if not id_olimpiada:
                print_warn(f"Olimpiada no encontrada para games: {row.get('Games')}")
                continue
            
            # 3. Resolver id_evento (vía disciplina)
            nom_disc = fix_mojibake(str(row.get('Discipline'))).strip() if pd.notna(row.get('Discipline')) else 'General'
            nom_ev = fix_mojibake(str(row.get('Event'))).strip() if pd.notna(row.get('Event')) else 'General'
            
            id_disc = cache_disciplinas.get(nom_disc)
            if not id_disc:
                # Asegurar disciplina si no estuviera
                cursor.execute("INSERT INTO deporte (nombre) VALUES (%s) ON DUPLICATE KEY UPDATE nombre = VALUES(nombre);", (nom_disc,))
                cursor.execute("SELECT id_deporte FROM deporte WHERE nombre = %s;", (nom_disc,))
                id_dep = cursor.fetchone()[0]
                cursor.execute("INSERT INTO disciplina (nombre, id_deporte) VALUES (%s, %s);", (nom_disc, id_dep))
                id_disc = cursor.lastrowid
                cache_disciplinas[nom_disc] = id_disc
                
            id_evento = cache_eventos.get((nom_ev, id_disc))
            if not id_evento:
                # Asegurar evento si no estuviera
                cursor.execute("INSERT INTO evento (nombre, id_disciplina) VALUES (%s, %s);", (nom_ev, id_disc))
                id_evento = cursor.lastrowid
                cache_eventos[(nom_ev, id_disc)] = id_evento
            
            # 4. Resolver id_equipo
            noc_code = str(row.get('NOC')).strip().upper()[:3] if pd.notna(row.get('NOC')) else 'UNK'
            if noc_code in cache_nocs:
                id_noc, nom_noc = cache_nocs[noc_code]
            else:
                cursor.execute("INSERT INTO noc (codigo_noc, nombre_noc) VALUES (%s, %s) ON DUPLICATE KEY UPDATE nombre_noc = VALUES(nombre_noc);", (noc_code, noc_code))
                cursor.execute("SELECT id_noc, nombre_noc FROM noc WHERE codigo_noc = %s;", (noc_code,))
                r_n = cursor.fetchone()
                id_noc, nom_noc = r_n[0], r_n[1]
                cache_nocs[noc_code] = (id_noc, nom_noc)
                
            team_raw = row.get('Team')
            if pd.isna(team_raw) or not str(team_raw).strip():
                team_name = nom_noc or noc_code
            else:
                team_name = fix_mojibake(str(team_raw)).strip()[:120]
                
            key_eq = (team_name, id_noc)
            if key_eq in cache_equipos:
                id_equipo = cache_equipos[key_eq]
            else:
                cursor.execute(
                    "INSERT INTO equipo (nombre, id_noc) VALUES (%s, %s) "
                    "ON DUPLICATE KEY UPDATE nombre = VALUES(nombre);",
                    (team_name, id_noc)
                )
                cursor.execute("SELECT id_equipo FROM equipo WHERE nombre = %s AND (id_noc = %s OR (id_noc IS NULL AND %s IS NULL));", (team_name, id_noc, id_noc))
                id_equipo = cursor.fetchone()[0]
                cache_equipos[key_eq] = id_equipo
            
            # 5. Resolver id_medalla
            id_medalla = homologar_medalla(row.get('Medal'), cache_medallas)
            
            # 6. Compitió como
            compitio_como = fix_mojibake(str(row.get('As'))).strip()[:120] if pd.notna(row.get('As')) else None
            
            # 7. Posición y empate
            posicion, es_empate = procesar_posicion_y_empate(row.get('Pos'))
            
            # 8. Comprobar existencia previa (idempotencia)
            key_part = (id_atleta, id_evento, id_olimpiada)
            if key_part in cache_participaciones:
                omitidas_duplicadas += 1
                continue
            
            # 9. Inserción
            cursor.execute(sql_insert, (
                id_atleta,
                id_evento,
                id_olimpiada,
                id_equipo,
                id_medalla,
                compitio_como,
                None,  # edad (se enriquece en Fase 5)
                None,  # altura_reg (se enriquece en Fase 5)
                None,  # peso_reg (se enriquece en Fase 5)
                posicion,
                es_empate
            ))
            cache_participaciones[key_part] = cursor.lastrowid
            insertadas += 1
            
            if (idx + 1) % 25000 == 0:
                conn.commit()
                print(f"  -> Progreso: {idx + 1}/{len(results_df)} participaciones ({((idx + 1)/len(results_df)*100):.1f}%)...")
            
        conn.commit()
        print_ok(f"Participaciones procesadas: {len(results_df)} "
                 f"(nuevas insertadas: {insertadas}, duplicadas omitidas: {omitidas_duplicadas}, "
                 f"omitidas sin atleta: {omitidas_sin_atleta})")
        
        # =====================================================================
        # 3. VERIFICACIÓN DE LA FASE 4
        # =====================================================================
        exito = verificar_fase4(cursor)
        
        cursor.close()
        conn.close()
        return exito
        
    except Error as e:
        if conn and conn.is_connected():
            conn.rollback()
            conn.close()
        print_error(f"Fallo durante la ejecución de la Fase 4 en MySQL: {e}")
        return False
    except Exception as e:
        if conn and conn.is_connected():
            conn.rollback()
            conn.close()
        print_error(f"Error general en Fase 4: {e}")
        return False


def verificar_fase4(cursor):
    """
    Ejecuta consultas de control para validar el estado de la tabla participacion.
    """
    print_section("4.3 Verificación de Fase 4")
    
    cursor.execute("SELECT COUNT(*) FROM participacion;")
    total_part = cursor.fetchone()[0]
    print(f"  Total registros en 'participacion': {total_part}")
    
    # Comprobar claves foráneas huérfanas
    consultas_fk = [
        ("atleta", "SELECT COUNT(*) FROM participacion p LEFT JOIN atleta a ON p.id_atleta = a.id_atleta WHERE p.id_atleta IS NOT NULL AND a.id_atleta IS NULL;"),
        ("evento", "SELECT COUNT(*) FROM participacion p LEFT JOIN evento e ON p.id_evento = e.id_evento WHERE p.id_evento IS NOT NULL AND e.id_evento IS NULL;"),
        ("olimpiada", "SELECT COUNT(*) FROM participacion p LEFT JOIN olimpiada o ON p.id_olimpiada = o.id_olimpiada WHERE p.id_olimpiada IS NOT NULL AND o.id_olimpiada IS NULL;"),
        ("equipo", "SELECT COUNT(*) FROM participacion p LEFT JOIN equipo eq ON p.id_equipo = eq.id_equipo WHERE p.id_equipo IS NOT NULL AND eq.id_equipo IS NULL;"),
        ("medalla", "SELECT COUNT(*) FROM participacion p LEFT JOIN medalla m ON p.id_medalla = m.id_medalla WHERE p.id_medalla IS NOT NULL AND m.id_medalla IS NULL;"),
    ]
    
    todas_fk_ok = True
    print("\n  Comprobando integridad de claves foráneas en 'participacion':")
    for entidad, sql in consultas_fk:
        cursor.execute(sql)
        huerfanas = cursor.fetchone()[0]
        print(f"    FK participacion -> {entidad} huérfanas: {huerfanas}")
        if huerfanas > 0:
            todas_fk_ok = False
            
    # Distribución de medallas
    print("\n  Distribución de medallas en 'participacion':")
    cursor.execute("""
        SELECT m.tipo, COUNT(*) AS cantidad
        FROM participacion p
        JOIN medalla m ON p.id_medalla = m.id_medalla
        GROUP BY m.tipo
        ORDER BY cantidad DESC;
    """)
    for r in cursor.fetchall():
        print(f"    Medalla: {r[0]:6} -> {r[1]} participaciones")
        
    # Conteo de empates
    cursor.execute("SELECT COUNT(*) FROM participacion WHERE es_empate = TRUE;")
    con_empate = cursor.fetchone()[0]
    print(f"\n  Participaciones marcadas con es_empate = TRUE: {con_empate}")
    
    # Muestra de participaciones
    print("\n  Muestra de 5 participaciones registradas:")
    cursor.execute("""
        SELECT 
            a.nombre AS atleta,
            CONCAT(o.anio, ' ', o.temporada) AS edicion,
            e.nombre AS prueba,
            eq.nombre AS equipo,
            p.posicion,
            m.tipo AS medalla
        FROM participacion p
        JOIN atleta a ON p.id_atleta = a.id_atleta
        JOIN olimpiada o ON p.id_olimpiada = o.id_olimpiada
        JOIN evento e ON p.id_evento = e.id_evento
        JOIN equipo eq ON p.id_equipo = eq.id_equipo
        JOIN medalla m ON p.id_medalla = m.id_medalla
        ORDER BY p.id_participacion
        LIMIT 5;
    """)
    for r in cursor.fetchall():
        print(f"    Atleta: {r[0]} | {r[1]} | {r[2]} | Eq: {r[3]} | Pos: {r[4]} | Medalla: {r[5]}")
        
    if total_part > 0 and todas_fk_ok:
        print_ok("Verificación de Fase 4 EXITOSA. Participaciones base cargadas e íntegras.")
        return True
    else:
        print_error("Verificación de Fase 4 INCOMPLETA o con errores de integridad.")
        return False


if __name__ == '__main__':
    ok = cargar_participacion_base()
    sys.exit(0 if ok else 1)
