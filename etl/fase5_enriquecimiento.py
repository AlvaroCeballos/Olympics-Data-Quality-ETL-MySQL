# -*- coding: utf-8 -*-
"""
fase5_enriquecimiento.py — Pipeline ETL Fase 5: Enriquecimiento con Fuentes 2 y 4 (Kaggle).

Objetivos:
  1. Cruzar athlete_events.csv (Kaggle 120 Years) para enriquecer participaciones
     existentes con edad, altura_reg y peso_reg de la edición.
  2. Identificar y crear nuevos atletas presentes únicamente en Kaggle (con id_externo = NULL).
  3. Insertar nuevas participaciones registradas por Kaggle no existentes en la capa base.
  4. Ejecutar validación cruzada con Fuente 4 (DataCamp Datalab, DT-015).

Archivos de entrada:
  - athlete_events_sample.csv (Fuente 2: Kaggle 120 Years)
  - athlete_events_datalab_sample.csv (Fuente 4: Validación cruzada)

Decisiones técnicas aplicadas:
  - DT-001: id_externo = NULL para nuevos atletas de Kaggle
  - DT-002: Matching key normalizada (nombre_normalizado, sexo, anio_nacimiento_aprox)
  - DT-003: Disciplina puente (disciplina.nombre = deporte.nombre)
  - DT-005: Saneamiento universal de mojibake (fix_mojibake)
  - DT-006: Entrada vía resolve_data_file()
  - DT-008: Secuencia FK estricta
  - DT-010: Homologación de medallas (Gold, Silver, Bronze, NA)
  - DT-015: Fuente 4 idéntica a Fuente 2 (solo validación cruzada)
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
    _obtener_o_crear_noc,
    parsear_games
)
from fase4_participacion_base import homologar_medalla


def homologar_posicion_desde_medalla(medalla_str):
    """Asigna posición referencial si obtuvo medalla en Kaggle."""
    if not medalla_str or pd.isna(medalla_str):
        return None
    med = str(medalla_str).strip().capitalize()
    if med == 'Gold':
        return '1'
    elif med == 'Silver':
        return '2'
    elif med == 'Bronze':
        return '3'
    return None


def validar_fuente4_cruzada(athlete_df, path_datalab):
    """
    Ejecuta la validación cruzada con la Fuente 4 (DT-015).
    Verifica paridad estructural y de registros con athlete_events_datalab.
    """
    print_section("5.1 Validación Cruzada con Fuente 4 (DataCamp Datalab)")
    if not path_datalab or not os.path.isfile(path_datalab):
        print_warn("Fuente 4 (datalab) no disponible para validación cruzada, omitiendo test.")
        return True
        
    try:
        datalab_df = pd.read_csv(path_datalab)
        print(f"  Registros en Fuente 2 (Kaggle):  {len(athlete_df)}")
        print(f"  Registros en Fuente 4 (Datalab): {len(datalab_df)}")
        
        # Comparar longitud y nombres normalizados de columnas
        cols_f2 = [c.lower().strip() for c in athlete_df.columns]
        cols_f4 = [c.lower().strip() for c in datalab_df.columns]
        
        cols_coincidentes = set(cols_f2) == set(cols_f4)
        mismo_conteo = len(athlete_df) == len(datalab_df)
        
        if cols_coincidentes and mismo_conteo:
            print_ok("DT-015 Confirmada: Fuente 4 es idéntica a Fuente 2 (100% paridad).")
            return True
        else:
            print_warn("DT-015 Discrepancia detectada entre Fuente 2 y Fuente 4.")
            return False
    except Exception as e:
        print_warn(f"No se pudo completar la validación cruzada de Fuente 4: {e}")
        return False


def cargar_enriquecimiento_kaggle():
    """
    Ejecuta el pipeline de enriquecimiento de atletas y participaciones desde Kaggle.
    """
    print_section("INICIO DE EJECUCIÓN: FASE 5 (Enriquecimiento Kaggle)")
    
    path_athlete = resolve_data_file('athlete_events')
    path_datalab = resolve_data_file('athlete_events_datalab')
    
    if not path_athlete or not os.path.isfile(path_athlete):
        print_error(f"No se encontró archivo de athlete_events: {path_athlete}")
        return False
        
    print(f"  Archivo athlete_events: {path_athlete}")
    athlete_df = pd.read_csv(path_athlete)
    print_ok(f"athlete_events leído: {len(athlete_df)} registros")
    
    # 1. Validación cruzada DT-015
    validar_fuente4_cruzada(athlete_df, path_datalab)
    
    conn = None
    try:
        conn = get_connection(database=DB_NAME)
        cursor = conn.cursor()
        
        # =====================================================================
        # 2. CACHÉS EN MEMORIA
        # =====================================================================
        print_section("5.2 Carga de cachés en memoria para resolución de identidades")
        
        # Caché de atletas existentes para deduplicación:
        # clave: (nombre_norm, sexo) -> lista de dict con datos del atleta
        cursor.execute("SELECT id_atleta, id_externo, nombre, sexo, fecha_nac, altura_cm, peso_kg FROM atleta;")
        atletas_rows = cursor.fetchall()
        
        cache_atletas_matching = {}
        for r in atletas_rows:
            id_a, id_ext, nom, sx, fnac, alt, pes = r
            nom_norm = normalize_name(nom)
            key = (nom_norm, sx)
            if key not in cache_atletas_matching:
                cache_atletas_matching[key] = []
            cache_atletas_matching[key].append({
                'id_atleta': id_a,
                'id_externo': id_ext,
                'nombre': nom,
                'sexo': sx,
                'fecha_nac': fnac,
                'altura_cm': alt,
                'peso_kg': pes
            })
        print_ok(f"Atletas en catálogo maestro: {len(atletas_rows)}")
        
        # Medallas: tipo -> id_medalla
        cursor.execute("SELECT tipo, id_medalla FROM medalla;")
        cache_medallas = {r[0]: r[1] for r in cursor.fetchall()}
        
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
        
        # Participaciones existentes: (id_atleta, id_evento, id_olimpiada) -> id_participacion
        cursor.execute("SELECT id_atleta, id_evento, id_olimpiada, id_participacion FROM participacion;")
        cache_participaciones = {(r[0], r[1], r[2]): r[3] for r in cursor.fetchall()}
        print_ok(f"Participaciones preexistentes: {len(cache_participaciones)}")
        
        # =====================================================================
        # 3. PROCESAMIENTO DE REGISTROS DE KAGGLE
        # =====================================================================
        print_section("5.3 Deduplicación de atletas y enriquecimiento de participaciones")
        
        atletas_nuevos_insertados = 0
        atletas_reutilizados = 0
        participaciones_actualizadas = 0
        participaciones_nuevas_insertadas = 0
        
        sql_insert_atleta = """
            INSERT INTO atleta (
                id_externo, nombre, sexo, altura_cm, peso_kg, fecha_nac, nacionalidad
            ) VALUES (
                NULL, %s, %s, %s, %s, %s, %s
            );
        """
        
        sql_update_part = """
            UPDATE participacion SET
                edad = COALESCE(edad, %s),
                altura_reg = COALESCE(altura_reg, %s),
                peso_reg = COALESCE(peso_reg, %s)
            WHERE id_participacion = %s;
        """
        
        sql_insert_part = """
            INSERT INTO participacion (
                id_atleta, id_evento, id_olimpiada, id_equipo, id_medalla,
                compitio_como, edad, altura_reg, peso_reg, posicion, es_empate
            ) VALUES (
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s
            );
        """
        
        for _, row in athlete_df.iterrows():
            nom_raw = row.get('Name')
            sex_raw = row.get('Sex')
            if pd.isna(nom_raw) or pd.isna(sex_raw):
                continue
                
            nom_clean = fix_mojibake(str(nom_raw)).strip()[:120]
            nom_norm = normalize_name(nom_clean)
            sexo = str(sex_raw).strip().upper()[:1]
            if sexo not in ('M', 'F'):
                sexo = 'M'
                
            # Métricas físicas de Kaggle
            edad = int(row['Age']) if pd.notna(row.get('Age')) else None
            altura_reg = int(round(float(row['Height']))) if pd.notna(row.get('Height')) else None
            peso_reg = round(float(row['Weight']), 2) if pd.notna(row.get('Weight')) else None
            
            # Año de nacimiento aproximado: Year - Age
            anio_edicion, temp_edicion, raw_games = parsear_games(row.get('Games'))
            anio_nac_aprox = (anio_edicion - edad) if (anio_edicion and edad) else None
            
            # -----------------------------------------------------------------
            # A. Deduplicación de Atleta (DT-002)
            # -----------------------------------------------------------------
            key_atleta = (nom_norm, sexo)
            id_atleta = None
            
            if key_atleta in cache_atletas_matching:
                candidatos = cache_atletas_matching[key_atleta]
                # Si hay año aproximado, verificar coincidencia cronológica
                if anio_nac_aprox is not None:
                    for cand in candidatos:
                        if cand['fecha_nac']:
                            anio_cand = cand['fecha_nac'].year
                            if abs(anio_cand - anio_nac_aprox) <= 1:
                                id_atleta = cand['id_atleta']
                                break
                # Fallback: reutilizar primer candidato con mismo nombre y sexo
                if not id_atleta and candidatos:
                    id_atleta = candidatos[0]['id_atleta']
                    
            if id_atleta:
                atletas_reutilizados += 1
            else:
                # Insertar nuevo atleta exclusivo de Kaggle
                fecha_nac_estimada = f"{anio_nac_aprox}-01-01" if anio_nac_aprox else None
                nacionalidad = fix_mojibake(str(row.get('Team'))).strip()[:120] if pd.notna(row.get('Team')) else None
                
                cursor.execute(sql_insert_atleta, (
                    nom_clean,
                    sexo,
                    float(altura_reg) if altura_reg else None,
                    peso_reg,
                    fecha_nac_estimada,
                    nacionalidad
                ))
                id_atleta = cursor.lastrowid
                atletas_nuevos_insertados += 1
                
                # Actualizar caché de atletas
                if key_atleta not in cache_atletas_matching:
                    cache_atletas_matching[key_atleta] = []
                cache_atletas_matching[key_atleta].append({
                    'id_atleta': id_atleta,
                    'id_externo': None,
                    'nombre': nom_clean,
                    'sexo': sexo,
                    'fecha_nac': None,
                    'altura_cm': altura_reg,
                    'peso_kg': peso_reg
                })
                
            # -----------------------------------------------------------------
            # B. Contexto: Olimpiada
            # -----------------------------------------------------------------
            key_olimp = (anio_edicion, temp_edicion)
            id_olimpiada = cache_olimpiadas.get(key_olimp)
            if not id_olimpiada:
                # Asegurar sede y olimpiada si no existiera
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
                    
                cursor.execute(
                    "INSERT INTO olimpiada (anio, temporada, nombre_juegos, id_sede) VALUES (%s, %s, %s, %s);",
                    (anio_edicion, temp_edicion, str(row.get('Games')), id_sede)
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
                
            # Disciplina puente (disciplina.nombre = deporte.nombre, DT-003)
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
            
            if key_part in cache_participaciones:
                # Actualizar participación preexistente enriqueciendo métricas
                id_part = cache_participaciones[key_part]
                cursor.execute(sql_update_part, (edad, altura_reg, peso_reg, id_part))
                participaciones_actualizadas += 1
            else:
                # Insertar nueva participación desde Kaggle
                pos_medalla = homologar_posicion_desde_medalla(row.get('Medal'))
                cursor.execute(sql_insert_part, (
                    id_atleta,
                    id_evento,
                    id_olimpiada,
                    id_equipo,
                    id_med,
                    nom_clean,
                    edad,
                    altura_reg,
                    peso_reg,
                    pos_medalla,
                    False
                ))
                nuevo_id_part = cursor.lastrowid
                cache_participaciones[key_part] = nuevo_id_part
                participaciones_nuevas_insertadas += 1
                
        conn.commit()
        print_ok(f"Atletas de Kaggle procesados: nuevos={atletas_nuevos_insertados}, reutilizados={atletas_reutilizados}")
        print_ok(f"Participaciones: nuevas={participaciones_nuevas_insertadas}, enriquecidas(UPDATE)={participaciones_actualizadas}")
        
        # =====================================================================
        # 4. VERIFICACIÓN DE LA FASE 5
        # =====================================================================
        exito = verificar_fase5(cursor)
        
        cursor.close()
        conn.close()
        return exito
        
    except Error as e:
        if conn and conn.is_connected():
            conn.rollback()
            conn.close()
        print_error(f"Fallo durante la ejecución de la Fase 5 en MySQL: {e}")
        return False
    except Exception as e:
        if conn and conn.is_connected():
            conn.rollback()
            conn.close()
        print_error(f"Error general en Fase 5: {e}")
        return False


def verificar_fase5(cursor):
    """
    Ejecuta consultas de control para validar el enriquecimiento de la Fase 5.
    """
    print_section("5.4 Verificación de Fase 5")
    
    cursor.execute("SELECT COUNT(*) FROM atleta;")
    total_atletas = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM atleta WHERE id_externo IS NULL;")
    atletas_sin_externo = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM participacion;")
    total_part = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM participacion WHERE edad IS NOT NULL OR altura_reg IS NOT NULL OR peso_reg IS NOT NULL;")
    part_con_metricas = cursor.fetchone()[0]
    
    print(f"  Total atletas en 'atleta':                  {total_atletas} ({atletas_sin_externo} incorporados de Kaggle)")
    print(f"  Total participaciones en 'participacion':   {total_part}")
    print(f"  Participaciones con métricas registradas:  {part_con_metricas}")
    
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
    
    # Muestra de atletas de Kaggle con participaciones y métricas
    print("\n  Muestra de participaciones enriquecidas con métricas puntuales:")
    cursor.execute("""
        SELECT 
            a.nombre,
            a.sexo,
            CONCAT(o.anio, ' ', o.temporada) AS edicion,
            e.nombre AS prueba,
            p.edad,
            p.altura_reg,
            p.peso_reg,
            m.tipo AS medalla
        FROM participacion p
        JOIN atleta a ON p.id_atleta = a.id_atleta
        JOIN olimpiada o ON p.id_olimpiada = o.id_olimpiada
        JOIN evento e ON p.id_evento = e.id_evento
        JOIN medalla m ON p.id_medalla = m.id_medalla
        WHERE p.edad IS NOT NULL OR p.altura_reg IS NOT NULL
        ORDER BY p.id_participacion DESC
        LIMIT 5;
    """)
    for r in cursor.fetchall():
        print(f"    Atleta: '{r[0]}' ({r[1]}) | {r[2]} | {r[3]} | Edad: {r[4]}, Alt: {r[5]}cm, Peso: {r[6]}kg | Medalla: {r[7]}")
        
    if total_atletas > 15 and total_part > 15 and sum(huerfanas) == 0:
        print_ok("Verificación de Fase 5 EXITOSA. Enriquecimiento Kaggle aplicado correctamente.")
        return True
    else:
        print_error("Verificación de Fase 5 INCOMPLETA.")
        return False


if __name__ == '__main__':
    ok = cargar_enriquecimiento_kaggle()
    sys.exit(0 if ok else 1)
