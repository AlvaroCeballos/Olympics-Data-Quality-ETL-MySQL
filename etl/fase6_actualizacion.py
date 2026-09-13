# -*- coding: utf-8 -*-
"""
fase6_actualizacion.py — Pipeline ETL Fase 6: Actualización con Fuente 3 (Kaggle Summer 1896-2024).

Objetivos:
  1. Incorporar resultados y medallistas de Tokio 2020 y París 2024 (y ediciones históricas complementarias).
  2. Deduplicar identidades de atletas contra el catálogo unificado (DT-002) evitando duplicados.
  3. Crear nuevos atletas exclusivos de la Fuente 3 con id_externo = NULL (DT-001).
  4. Garantizar que sedes, olimpiadas, deportes, disciplinas puente y eventos estén presentes.
  5. Cargar e insertar de forma idempotente las participaciones no existentes o enriquecer preseas.

Archivo de entrada:
  - olympics_dataset.csv (o Datasets.xlsx -> Hoja9)

Decisiones técnicas aplicadas:
  - DT-001: id_externo = NULL para nuevos atletas de Kaggle
  - DT-002: Matching key flexible y deduplicación por tokens
  - DT-003: Disciplina puente (disciplina.nombre = deporte.nombre)
  - DT-005: Saneamiento universal de mojibake (fix_mojibake)
  - DT-006: Entrada vía resolve_data_file()
  - DT-008: Secuencia FK estricta
  - DT-010: Homologación de medallas (Gold, Silver, Bronze, NA)
  - DT-022: Catálogo histórico oficial de sedes
  - DT-024: Aprovisionamiento on-the-fly de comités y países
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
from fase3_contexto import (
    OLYMPIC_HOST_CATALOG,
    _obtener_o_crear_pais,
    _obtener_o_crear_noc
)
from fase4_participacion_base import homologar_medalla
from fase5_enriquecimiento import homologar_posicion_desde_medalla


def buscar_atleta_existente(nombre_norm, sexo, cache_atletas_matching):
    """
    Busca si el atleta ya existe en el catálogo unificado aplicando:
      1. Coincidencia exacta de (nombre_norm, sexo).
      2. Coincidencia por subconjunto de tokens (ej. 'gunnar aaby' en 'gunnar nielsen aaby').
    """
    key_exacta = (nombre_norm, sexo)
    if key_exacta in cache_atletas_matching and cache_atletas_matching[key_exacta]:
        return cache_atletas_matching[key_exacta][0]['id_atleta']
        
    tokens_busqueda = set(nombre_norm.split())
    if not tokens_busqueda:
        return None
        
    for (cand_norm, cand_sexo), lista_cands in cache_atletas_matching.items():
        if cand_sexo == sexo:
            tokens_cand = set(cand_norm.split())
            if tokens_busqueda.issubset(tokens_cand) or tokens_cand.issubset(tokens_busqueda):
                return lista_cands[0]['id_atleta']
                
    return None


def cargar_actualizacion_fuente3():
    """
    Ejecuta el pipeline de actualización de la Fuente 3 (olympics_dataset.csv).
    """
    print_section("INICIO DE EJECUCIÓN: FASE 6 (Actualización Fuente 3 — Tokio/París y Complementos)")
    
    path_dataset = resolve_data_file('olympics_dataset')
    if not path_dataset or not os.path.isfile(path_dataset):
        print_error(f"No se encontró archivo de olympics_dataset: {path_dataset}")
        return False
        
    print(f"  Archivo olympics_dataset: {path_dataset}")
    df_f3 = pd.read_csv(path_dataset)
    print_ok(f"olympics_dataset leído: {len(df_f3)} registros")
    
    conn = None
    try:
        conn = get_connection(database=DB_NAME)
        cursor = conn.cursor()
        
        # =====================================================================
        # 1. CARGA DE CACHÉS EN MEMORIA
        # =====================================================================
        print_section("6.1 Carga de cachés en memoria")
        
        # Atletas para deduplicación: (nombre_norm, sexo) -> lista
        cursor.execute("SELECT id_atleta, id_externo, nombre, sexo FROM atleta;")
        cache_atletas_matching = {}
        total_atletas_inicio = 0
        for id_a, id_ext, nom, sx in cursor.fetchall():
            total_atletas_inicio += 1
            nom_norm = normalize_name(nom)
            key = (nom_norm, sx)
            if key not in cache_atletas_matching:
                cache_atletas_matching[key] = []
            cache_atletas_matching[key].append({
                'id_atleta': id_a,
                'id_externo': id_ext,
                'nombre': nom,
                'sexo': sx,
                'nom_norm': nom_norm
            })
        print_ok(f"Atletas en catálogo maestro: {total_atletas_inicio}")
        
        # Medallas: tipo -> id_medalla
        cursor.execute("SELECT tipo, id_medalla FROM medalla;")
        cache_medallas = {r[0]: r[1] for r in cursor.fetchall()}
        id_medalla_na = cache_medallas.get('NA')
        
        # Olimpiadas: (anio, temporada) -> id_olimpiada
        cursor.execute("SELECT anio, temporada, id_olimpiada FROM olimpiada;")
        cache_olimpiadas = {(r[0], r[1]): r[2] for r in cursor.fetchall()}
        
        # Sedes: (ciudad, id_pais) -> id_sede
        cursor.execute("SELECT ciudad, id_pais, id_sede FROM sede;")
        cache_sedes = {(r[0], r[1]): r[2] for r in cursor.fetchall()}
        
        # Deportes: nombre -> id_deporte
        cursor.execute("SELECT nombre, id_deporte FROM deporte;")
        cache_deportes = {r[0]: r[1] for r in cursor.fetchall()}
        
        # Disciplinas: (nombre, id_deporte) -> id_disciplina
        cursor.execute("SELECT nombre, id_deporte, id_disciplina FROM disciplina;")
        cache_disciplinas = {(r[0], r[1]): r[2] for r in cursor.fetchall()}
        
        # Eventos: (nombre, id_disciplina) -> id_evento
        cursor.execute("SELECT nombre, id_disciplina, id_evento FROM evento;")
        cache_eventos = {(r[0], r[1]): r[2] for r in cursor.fetchall()}
        
        # NOCs: codigo_noc -> (id_noc, nombre_noc)
        cursor.execute("SELECT codigo_noc, id_noc, nombre_noc FROM noc;")
        cache_nocs = {r[0]: (r[1], r[2]) for r in cursor.fetchall()}
        
        # Equipos: (nombre, id_noc) -> id_equipo
        cursor.execute("SELECT nombre, id_noc, id_equipo FROM equipo;")
        cache_equipos = {(r[0], r[1]): r[2] for r in cursor.fetchall()}
        
        # Participaciones existentes: (id_atleta, id_evento, id_olimpiada) -> (id_participacion, id_medalla)
        cursor.execute("SELECT id_atleta, id_evento, id_olimpiada, id_participacion, id_medalla FROM participacion;")
        cache_participaciones = {(r[0], r[1], r[2]): (r[3], r[4]) for r in cursor.fetchall()}
        print_ok(f"Participaciones preexistentes: {len(cache_participaciones)}")
        
        # =====================================================================
        # 2. PROCESAMIENTO E INTEGRACIÓN DE REGISTROS
        # =====================================================================
        print_section("6.2 Integración y actualización desde Fuente 3")
        
        sql_insert_atleta = """
            INSERT INTO atleta (
                id_externo, nombre, sexo, nacionalidad
            ) VALUES (
                NULL, %s, %s, %s
            );
        """
        
        sql_update_part_medalla = """
            UPDATE participacion SET
                id_medalla = %s,
                posicion = COALESCE(posicion, %s)
            WHERE id_participacion = %s;
        """
        
        sql_insert_part = """
            INSERT INTO participacion (
                id_atleta, id_evento, id_olimpiada, id_equipo, id_medalla,
                compitio_como, edad, altura_reg, peso_reg, posicion, es_empate
            ) VALUES (
                %s, %s, %s, %s, %s,
                %s, NULL, NULL, NULL, %s, FALSE
            );
        """
        
        atletas_nuevos = 0
        atletas_reutilizados = 0
        part_nuevas = 0
        part_actualizadas = 0
        part_duplicadas_ignoradas = 0
        
        for _, row in df_f3.iterrows():
            nom_raw = row.get('Name')
            sex_raw = row.get('Sex')
            if pd.isna(nom_raw) or pd.isna(sex_raw):
                continue
                
            nom_clean = fix_mojibake(str(nom_raw)).strip()[:120]
            nom_norm = normalize_name(nom_clean)
            sexo = str(sex_raw).strip().upper()[:1]
            if sexo not in ('M', 'F'):
                sexo = 'M'
                
            anio = int(row['Year']) if pd.notna(row.get('Year')) else None
            temporada = fix_mojibake(str(row.get('Season'))).strip() if pd.notna(row.get('Season')) else 'Summer'
            
            # -----------------------------------------------------------------
            # A. Deduplicación de Atleta (DT-002)
            # -----------------------------------------------------------------
            id_atleta = buscar_atleta_existente(nom_norm, sexo, cache_atletas_matching)
            
            if id_atleta:
                atletas_reutilizados += 1
            else:
                nacionalidad = fix_mojibake(str(row.get('Team'))).strip()[:120] if pd.notna(row.get('Team')) else None
                cursor.execute(sql_insert_atleta, (nom_clean, sexo, nacionalidad))
                id_atleta = cursor.lastrowid
                atletas_nuevos += 1
                
                key_match = (nom_norm, sexo)
                if key_match not in cache_atletas_matching:
                    cache_atletas_matching[key_match] = []
                cache_atletas_matching[key_match].append({
                    'id_atleta': id_atleta,
                    'id_externo': None,
                    'nombre': nom_clean,
                    'sexo': sexo,
                    'nom_norm': nom_norm
                })

            # -----------------------------------------------------------------
            # B. Contexto: Sede y Olimpiada
            # -----------------------------------------------------------------
            key_olimp = (anio, temporada)
            id_olimpiada = cache_olimpiadas.get(key_olimp)
            if not id_olimpiada:
                ciudad = fix_mojibake(str(row.get('City'))).strip() if pd.notna(row.get('City')) else None
                pais_cod = None
                pais_nom = None
                if key_olimp in OLYMPIC_HOST_CATALOG:
                    cat_c, cat_p, cat_n = OLYMPIC_HOST_CATALOG[key_olimp]
                    ciudad = ciudad or cat_c
                    pais_cod = cat_p
                    pais_nom = cat_n
                    
                id_pais_sede = _obtener_o_crear_pais(cursor, pais_cod, pais_nom) if pais_cod else None
                ciudad_final = ciudad or 'Desconocida'
                
                key_sede = (ciudad_final, id_pais_sede)
                if key_sede not in cache_sedes:
                    cursor.execute("INSERT INTO sede (ciudad, id_pais) VALUES (%s, %s);", (ciudad_final, id_pais_sede))
                    id_sede = cursor.lastrowid
                    cache_sedes[key_sede] = id_sede
                else:
                    id_sede = cache_sedes[key_sede]
                    
                nombre_juegos = f"{anio} {temporada}"
                cursor.execute(
                    "INSERT INTO olimpiada (anio, temporada, nombre_juegos, id_sede) VALUES (%s, %s, %s, %s);",
                    (anio, temporada, nombre_juegos, id_sede)
                )
                id_olimpiada = cursor.lastrowid
                cache_olimpiadas[key_olimp] = id_olimpiada

            # -----------------------------------------------------------------
            # C. Contexto: Deporte, Disciplina Puente y Evento
            # -----------------------------------------------------------------
            nom_sport = fix_mojibake(str(row.get('Sport'))).strip()[:120] if pd.notna(row.get('Sport')) else 'General'
            nom_event = fix_mojibake(str(row.get('Event'))).strip()[:200] if pd.notna(row.get('Event')) else 'General'
            
            # Deporte
            if nom_sport not in cache_deportes:
                cursor.execute("INSERT INTO deporte (nombre) VALUES (%s) ON DUPLICATE KEY UPDATE nombre = VALUES(nombre);", (nom_sport,))
                cursor.execute("SELECT id_deporte FROM deporte WHERE nombre = %s;", (nom_sport,))
                id_dep = cursor.fetchone()[0]
                cache_deportes[nom_sport] = id_dep
            else:
                id_dep = cache_deportes[nom_sport]
                
            # Disciplina puente (DT-003)
            key_disc = (nom_sport, id_dep)
            if key_disc not in cache_disciplinas:
                cursor.execute("INSERT INTO disciplina (nombre, id_deporte) VALUES (%s, %s);", (nom_sport, id_dep))
                id_disc = cursor.lastrowid
                cache_disciplinas[key_disc] = id_disc
            else:
                id_disc = cache_disciplinas[key_disc]
                
            # Evento
            key_event = (nom_event, id_disc)
            if key_event not in cache_eventos:
                cursor.execute("INSERT INTO evento (nombre, id_disciplina) VALUES (%s, %s);", (nom_event, id_disc))
                id_evento = cursor.lastrowid
                cache_eventos[key_event] = id_evento
            else:
                id_evento = cache_eventos[key_event]

            # -----------------------------------------------------------------
            # D. Contexto: Equipo y NOC
            # -----------------------------------------------------------------
            noc_code = str(row.get('NOC')).strip().upper()[:3] if pd.notna(row.get('NOC')) else 'UNK'
            if noc_code in cache_nocs:
                id_noc, nom_noc = cache_nocs[noc_code]
            else:
                id_noc = _obtener_o_crear_noc(cursor, noc_code)
                cursor.execute("SELECT nombre_noc FROM noc WHERE id_noc = %s;", (id_noc,))
                nom_noc = cursor.fetchone()[0]
                cache_nocs[noc_code] = (id_noc, nom_noc)
                
            team_raw = row.get('Team')
            team_name = fix_mojibake(str(team_raw)).strip()[:120] if pd.notna(team_raw) else (nom_noc or noc_code)
            
            key_eq = (team_name, id_noc)
            if key_eq not in cache_equipos:
                cursor.execute(
                    "INSERT INTO equipo (nombre, id_noc) VALUES (%s, %s) "
                    "ON DUPLICATE KEY UPDATE nombre = VALUES(nombre);",
                    (team_name, id_noc)
                )
                cursor.execute("SELECT id_equipo FROM equipo WHERE nombre = %s AND (id_noc = %s OR (id_noc IS NULL AND %s IS NULL));", (team_name, id_noc, id_noc))
                id_equipo = cursor.fetchone()[0]
                cache_equipos[key_eq] = id_equipo
            else:
                id_equipo = cache_equipos[key_eq]

            # -----------------------------------------------------------------
            # E. Participación: UPDATE o INSERT
            # -----------------------------------------------------------------
            key_part = (id_atleta, id_evento, id_olimpiada)
            id_med = homologar_medalla(row.get('Medal'), cache_medallas)
            pos_medalla = homologar_posicion_desde_medalla(row.get('Medal'))
            
            if key_part in cache_participaciones:
                id_part_existente, id_med_existente = cache_participaciones[key_part]
                # Si la existente no tenía medalla (era NA) y en Fuente 3 sí tiene medalla real:
                if id_med_existente == id_medalla_na and id_med != id_medalla_na:
                    cursor.execute(sql_update_part_medalla, (id_med, pos_medalla, id_part_existente))
                    cache_participaciones[key_part] = (id_part_existente, id_med)
                    part_actualizadas += 1
                else:
                    part_duplicadas_ignoradas += 1
            else:
                cursor.execute(sql_insert_part, (
                    id_atleta,
                    id_evento,
                    id_olimpiada,
                    id_equipo,
                    id_med,
                    nom_clean,
                    pos_medalla
                ))
                nuevo_id_part = cursor.lastrowid
                cache_participaciones[key_part] = (nuevo_id_part, id_med)
                part_nuevas += 1
                
        conn.commit()
        print_ok(f"Atletas Fuente 3: nuevos={atletas_nuevos}, reutilizados={atletas_reutilizados}")
        print_ok(f"Participaciones: nuevas={part_nuevas}, medallas actualizadas={part_actualizadas}, duplicadas={part_duplicadas_ignoradas}")
        
        # =====================================================================
        # 3. VERIFICACIÓN DE LA FASE 6
        # =====================================================================
        exito = verificar_fase6(cursor)
        
        cursor.close()
        conn.close()
        return exito
        
    except Error as e:
        if conn and conn.is_connected():
            conn.rollback()
            conn.close()
        print_error(f"Fallo durante la ejecución de la Fase 6 en MySQL: {e}")
        return False
    except Exception as e:
        if conn and conn.is_connected():
            conn.rollback()
            conn.close()
        print_error(f"Error general en Fase 6: {e}")
        return False


def verificar_fase6(cursor):
    """
    Ejecuta consultas de control para validar el estado tras la Fase 6.
    """
    print_section("6.3 Verificación de Fase 6")
    
    cursor.execute("SELECT COUNT(*) FROM atleta;")
    total_atletas = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM participacion;")
    total_part = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM sede;")
    total_sedes = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM olimpiada;")
    total_olimpiadas = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM evento;")
    total_eventos = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM equipo;")
    total_equipos = cursor.fetchone()[0]
    
    print(f"  Total atletas en 'atleta':                  {total_atletas}")
    print(f"  Total participaciones en 'participacion':   {total_part}")
    print(f"  Total sedes en 'sede':                      {total_sedes}")
    print(f"  Total olimpiadas en 'olimpiada':            {total_olimpiadas}")
    print(f"  Total eventos en 'evento':                  {total_eventos}")
    print(f"  Total equipos en 'equipo':                  {total_equipos}")
    
    # Comprobar claves foráneas huérfanas en participacion
    cursor.execute("""
        SELECT 
            (SELECT COUNT(*) FROM participacion WHERE id_atleta NOT IN (SELECT id_atleta FROM atleta)) AS h_atleta,
            (SELECT COUNT(*) FROM participacion WHERE id_evento NOT IN (SELECT id_evento FROM evento)) AS h_evento,
            (SELECT COUNT(*) FROM participacion WHERE id_olimpiada NOT IN (SELECT id_olimpiada FROM olimpiada)) AS h_olimpiada,
            (SELECT COUNT(*) FROM participacion WHERE id_equipo NOT IN (SELECT id_equipo FROM equipo)) AS h_equipo,
            (SELECT COUNT(*) FROM participacion WHERE id_medalla NOT IN (SELECT id_medalla FROM medalla)) AS h_medalla;
    """)
    huerfanas = cursor.fetchone()
    print(f"  Claves foráneas huérfanas en 'participacion': {sum(huerfanas)} (todos los 5 checks en 0)")
    
    # Distribución total de medallas consolidada
    print("\n  Medallero histórico consolidado en 'participacion':")
    cursor.execute("""
        SELECT m.tipo, COUNT(*) AS total
        FROM participacion p
        JOIN medalla m ON p.id_medalla = m.id_medalla
        GROUP BY m.tipo
        ORDER BY FIELD(m.tipo, 'Gold', 'Silver', 'Bronze', 'NA');
    """)
    for r in cursor.fetchall():
        print(f"    Presea: {r[0]:6} -> {r[1]} participaciones")
        
    # Muestra de participaciones de Fuente 3
    print("\n  Muestra de participaciones incorporadas/actualizadas:")
    cursor.execute("""
        SELECT 
            a.nombre,
            CONCAT(o.anio, ' ', o.temporada) AS edicion,
            e.nombre AS prueba,
            eq.nombre AS equipo,
            m.tipo AS medalla
        FROM participacion p
        JOIN atleta a ON p.id_atleta = a.id_atleta
        JOIN olimpiada o ON p.id_olimpiada = o.id_olimpiada
        JOIN evento e ON p.id_evento = e.id_evento
        JOIN equipo eq ON p.id_equipo = eq.id_equipo
        JOIN medalla m ON p.id_medalla = m.id_medalla
        ORDER BY p.id_participacion DESC
        LIMIT 5;
    """)
    for r in cursor.fetchall():
        print(f"    Atleta: '{r[0]}' | {r[1]} | {r[2]} | Eq: {r[3]} | Medalla: {r[4]}")
        
    if total_atletas >= 21 and total_part >= 30 and sum(huerfanas) == 0:
        print_ok("Verificación de Fase 6 EXITOSA. Fuente 3 integrada con consistencia relacional.")
        return True
    else:
        print_error("Verificación de Fase 6 INCOMPLETA.")
        return False


if __name__ == '__main__':
    ok = cargar_actualizacion_fuente3()
    sys.exit(0 if ok else 1)
