# -*- coding: utf-8 -*-
"""
fase1_dimensionales.py — Pipeline ETL Fase 1: Carga de Tablas Dimensionales Base.

Tablas procesadas:
  1. pais            — Entidades geograficas y politicas (ISO 3166-1 alpha-3 + NOCs)
  2. noc             — Comites Olimpicos Nacionales y delegaciones historicas
  3. poblacion_pais  — Serie demografica 1960–2023 (pivoteada con pandas.melt)

Archivos de entrada:
  - noc_regions_sample.csv (o noc_regions.csv completo)
  - populations_sample.csv (o populations.csv completo)

Decisiones tecnicas aplicadas:
  - DT-004: Vinculo populations -> pais via codigo_pais
  - DT-005: Saneamiento universal de mojibake
  - DT-006: Entrada via resolve_data_file()
  - DT-008: Secuencia FK estricta: pais -> noc, pais -> poblacion_pais
  - DT-016: Estrategia de homologacion pais-noc
  - DT-017: Conservacion de agregados regionales en pais
  - DT-018: Desnormalizacion con pandas.melt() omitiendo NaN
"""

import os
import sys
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
# PALABRAS CLAVE PARA DETECTAR AGREGADOS REGIONALES (DT-017)
# =====================================================================
_AGGREGATE_KEYWORDS = [
    'world', 'total', 'eastern and southern', 'western and central',
    'euro area', 'latin america', 'caribbean', 'middle east',
    'north africa', 'sub-saharan', 'oecd', 'ibrd', 'ida',
    'income', 'dividend', 'fragile', 'small states', 'union',
    'south asia', 'east asia', 'pacific', 'europe & central asia'
]


def _es_agregado_regional(nombre):
    """Determina si un nombre de pais corresponde a un agregado regional."""
    if not nombre:
        return False
    nombre_lower = nombre.lower()
    return any(kw in nombre_lower for kw in _AGGREGATE_KEYWORDS)


# =====================================================================
# 1. CARGA DE PAISES DESDE POPULATIONS (Banco Mundial)
# =====================================================================
def cargar_paises_desde_poblaciones(cursor, pop_df):
    """
    Inserta o actualiza registros en 'pais' a partir de populations.csv.
    Utiliza Country Code (ISO 3166-1 alpha-3) y Country Name.
    """
    print_section("1.1 Carga de PAIS desde populations.csv")
    
    # Extraer pares unicos de (Country Code, Country Name)
    df_unique = pop_df[['Country Code', 'Country Name']].drop_duplicates().dropna()
    print(f"  Paises/Territorios unicos en populations: {len(df_unique)}")
    
    sql = """
        INSERT INTO pais (codigo_pais, nombre, region)
        VALUES (%s, %s, %s)
        ON DUPLICATE KEY UPDATE
            nombre = COALESCE(VALUES(nombre), nombre),
            region = COALESCE(VALUES(region), region);
    """
    
    insertados = 0
    for _, row in df_unique.iterrows():
        code = str(row['Country Code']).strip().upper()[:3]
        name = fix_mojibake(str(row['Country Name'])).strip()[:120]
        region = 'Agregado Regional' if _es_agregado_regional(name) else None
        
        cursor.execute(sql, (code, name, region))
        insertados += cursor.rowcount
    
    print_ok(f"Registros procesados en 'pais' desde populations: {len(df_unique)} (afectados: {insertados})")


# =====================================================================
# 2. CARGA/COMPLEMENTO DE PAISES DESDE NOC_REGIONS
# =====================================================================
def cargar_paises_desde_noc(cursor, noc_df):
    """
    Complementa 'pais' con registros de noc_regions.csv.
    Si el codigo NOC no existe en 'pais', lo inserta como pais.
    Si ya existe, complementa region y nombre_alt (notes).
    """
    print_section("1.2 Complemento de PAIS desde noc_regions.csv")
    
    sql = """
        INSERT INTO pais (codigo_pais, nombre, nombre_alt, region)
        VALUES (%s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            nombre = COALESCE(pais.nombre, VALUES(nombre)),
            nombre_alt = COALESCE(pais.nombre_alt, VALUES(nombre_alt)),
            region = COALESCE(pais.region, VALUES(region));
    """
    
    procesados = 0
    for _, row in noc_df.iterrows():
        noc_code = str(row['NOC']).strip().upper()[:3] if pd.notna(row.get('NOC')) else None
        if not noc_code:
            continue
        
        reg_name = fix_mojibake(str(row['region'])).strip()[:120] if pd.notna(row.get('region')) else noc_code
        notes = fix_mojibake(str(row['notes'])).strip()[:120] if pd.notna(row.get('notes')) else None
        
        cursor.execute(sql, (noc_code, reg_name, notes, reg_name))
        procesados += 1
    
    print_ok(f"Registros de noc_regions procesados en 'pais': {procesados}")


# =====================================================================
# 3. CONSTRUCCION DE CACHE EN MEMORIA DE PAISES
# =====================================================================
def obtener_cache_paises(cursor):
    """
    Carga todos los paises de la BD en memoria para resolver claves foraneas rapidamente.
    Retorna:
      - por_codigo: { 'GUA': id_pais, ... }
      - por_nombre: { 'guatemala': id_pais, ... }
      - por_alt:    { 'antillas holandesas': id_pais, ... }
    """
    cursor.execute("SELECT id_pais, codigo_pais, nombre, region, nombre_alt FROM pais")
    rows = cursor.fetchall()
    
    por_codigo = {}
    por_nombre = {}
    por_alt = {}
    
    for id_p, cod, nom, reg, alt in rows:
        if cod:
            por_codigo[cod.strip().upper()] = id_p
        if nom:
            por_nombre[normalize_name(nom)] = id_p
        if reg:
            por_nombre[normalize_name(reg)] = id_p
        if alt:
            por_alt[normalize_name(alt)] = id_p
    
    print_ok(f"Cache de paises cargado: {len(rows)} paises en memoria")
    return por_codigo, por_nombre, por_alt


# =====================================================================
# 4. CARGA DE LA TABLA NOC
# =====================================================================
def cargar_noc(cursor, noc_df, por_codigo, por_nombre, por_alt):
    """
    Inserta registros en 'noc' vinculando con 'id_pais' segun corresponda.
    Delegaciones especiales (ROT, EUN, etc.) quedan con id_pais = NULL.
    """
    print_section("1.3 Carga de la tabla NOC")
    
    sql = """
        INSERT INTO noc (codigo_noc, nombre_noc, id_pais, notas)
        VALUES (%s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            nombre_noc = VALUES(nombre_noc),
            id_pais = VALUES(id_pais),
            notas = VALUES(notas);
    """
    
    total = 0
    vinculados = 0
    sin_pais = 0
    
    for _, row in noc_df.iterrows():
        noc_code = str(row['NOC']).strip().upper()[:3] if pd.notna(row.get('NOC')) else None
        if not noc_code:
            continue
        
        nom_noc = fix_mojibake(str(row['region'])).strip()[:150] if pd.notna(row.get('region')) else noc_code
        notas = fix_mojibake(str(row['notes'])).strip()[:255] if pd.notna(row.get('notes')) else None
        
        # Resolucion jerarquica de id_pais
        id_pais = por_codigo.get(noc_code)
        if not id_pais and nom_noc:
            id_pais = por_nombre.get(normalize_name(nom_noc))
        if not id_pais and notas:
            id_pais = por_alt.get(normalize_name(notas))
        
        if id_pais:
            vinculados += 1
        else:
            sin_pais += 1
        
        cursor.execute(sql, (noc_code, nom_noc, id_pais, notas))
        total += 1
    
    print_ok(f"NOCs cargados: {total} (vinculados a pais: {vinculados}, sin pais/delegacion especial: {sin_pais})")


# =====================================================================
# 5. CARGA DE LA TABLA POBLACION_PAIS (pandas.melt)
# =====================================================================
def cargar_poblacion_pais(cursor, pop_df, por_codigo):
    """
    Pivotea populations.csv de formato ancho (1960–2023) a formato largo
    usando pandas.melt() e inserta en la tabla poblacion_pais.
    """
    print_section("1.4 Carga de POBLACION_PAIS (pandas.melt)")
    
    # Identificar columnas de anios (ej: '1960' ... '2023')
    year_cols = [c for c in pop_df.columns if str(c).strip().isdigit()]
    print(f"  Columnas de anio detectadas: {len(year_cols)} ({year_cols[0]} a {year_cols[-1]})")
    
    # Aplicar pandas.melt
    melted = pd.melt(
        pop_df,
        id_vars=['Country Name', 'Country Code'],
        value_vars=year_cols,
        var_name='anio',
        value_name='poblacion'
    )
    
    # Descartar valores NaN / nulos
    melted = melted[melted['poblacion'].notna()].copy()
    print(f"  Filas desnormalizadas con poblacion valida: {len(melted)}")
    
    sql = """
        INSERT INTO poblacion_pais (id_pais, anio, poblacion)
        VALUES (%s, %s, %s)
        ON DUPLICATE KEY UPDATE
            poblacion = VALUES(poblacion);
    """
    
    batch = []
    batch_size = 1000
    insertados = 0
    omitidos_sin_pais = 0
    
    for _, row in melted.iterrows():
        code = str(row['Country Code']).strip().upper()[:3]
        id_pais = por_codigo.get(code)
        
        if not id_pais:
            omitidos_sin_pais += 1
            continue
        
        try:
            anio = int(row['anio'])
            pob = int(float(row['poblacion']))
            batch.append((id_pais, anio, pob))
        except (ValueError, TypeError):
            continue
        
        if len(batch) >= batch_size:
            cursor.executemany(sql, batch)
            insertados += len(batch)
            batch = []
    
    if batch:
        cursor.executemany(sql, batch)
        insertados += len(batch)
    
    print_ok(f"Registros insertados en poblacion_pais: {insertados}")
    if omitidos_sin_pais > 0:
        print_warn(f"Registros omitidos por codigo de pais no encontrado: {omitidos_sin_pais}")


# =====================================================================
# 6. VERIFICACION DE LA FASE 1
# =====================================================================
def verificar_fase1(cursor):
    """
    Ejecuta consultas de control para validar el estado de las tablas.
    """
    print_section("1.5 Verificacion de Fase 1")
    
    cursor.execute("SELECT COUNT(*) FROM pais;")
    total_pais = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM noc;")
    total_noc = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM noc WHERE id_pais IS NOT NULL;")
    noc_con_pais = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM poblacion_pais;")
    total_pob = cursor.fetchone()[0]
    
    cursor.execute("SELECT MIN(anio), MAX(anio), COUNT(DISTINCT id_pais) FROM poblacion_pais;")
    min_a, max_a, paises_con_pob = cursor.fetchone()
    
    print(f"  Total registros en 'pais':            {total_pais}")
    print(f"  Total registros en 'noc':             {total_noc} ({noc_con_pais} vinculados a pais)")
    print(f"  Total registros en 'poblacion_pais':  {total_pob}")
    print(f"  Rango de anios en poblacion_pais:     {min_a} - {max_a} ({paises_con_pob} paises)")
    
    print("\n  Muestra de 3 registros de 'pais':")
    cursor.execute("SELECT id_pais, codigo_pais, nombre, region FROM pais LIMIT 3;")
    for r in cursor.fetchall():
        print(f"    id={r[0]}, codigo={r[1]}, nombre={r[2]}, region={r[3]}")
    
    print("\n  Muestra de 3 registros de 'noc':")
    cursor.execute("SELECT id_noc, codigo_noc, nombre_noc, id_pais, notas FROM noc LIMIT 3;")
    for r in cursor.fetchall():
        print(f"    id={r[0]}, noc={r[1]}, nombre={r[2]}, id_pais={r[3]}, notas={r[4]}")
    
    print("\n  Muestra de 3 registros de 'poblacion_pais':")
    cursor.execute("SELECT p.nombre, pp.anio, pp.poblacion FROM poblacion_pais pp JOIN pais p ON pp.id_pais = p.id_pais LIMIT 3;")
    for r in cursor.fetchall():
        print(f"    pais={r[0]}, anio={r[1]}, poblacion={r[2]:,}")
    
    if total_pais > 0 and total_noc > 0 and total_pob > 0:
        print_ok("Verificacion de Fase 1 EXITOSA.")
        return True
    else:
        print_error("Verificacion de Fase 1 INCOMPLETA: tablas con 0 registros.")
        return False


# =====================================================================
# EJECUTOR PRINCIPAL DE FASE 1
# =====================================================================
def ejecutar_fase1():
    """Ejecuta el pipeline completo de la Fase 1."""
    print_section("INICIO DE EJECUCION: FASE 1 (Tablas Dimensionales)")
    
    # 1. Resolver rutas de archivos
    path_noc = resolve_data_file('noc_regions')
    path_pop = resolve_data_file('populations')
    
    if not path_noc or not os.path.isfile(path_noc):
        print_error(f"No se encontro el archivo de noc_regions: {path_noc}")
        return False
    if not path_pop or not os.path.isfile(path_pop):
        print_error(f"No se encontro el archivo de populations: {path_pop}")
        return False
    
    print(f"  Archivo noc_regions: {path_noc}")
    print(f"  Archivo populations: {path_pop}")
    
    # 2. Cargar DataFrames
    try:
        noc_df = pd.read_csv(path_noc)
        pop_df = pd.read_csv(path_pop)
        print_ok(f"CSVs leidos: noc_regions ({len(noc_df)} filas), populations ({len(pop_df)} filas)")
    except Exception as e:
        print_error(f"Error al leer archivos CSV: {e}")
        return False
    
    # 3. Conectar a MySQL y ejecutar pipeline
    conn = None
    try:
        conn = get_connection(database=DB_NAME)
        cursor = conn.cursor()
        
        # Cargas
        cargar_paises_desde_poblaciones(cursor, pop_df)
        cargar_paises_desde_noc(cursor, noc_df)
        conn.commit()
        
        # Cache de paises
        por_codigo, por_nombre, por_alt = obtener_cache_paises(cursor)
        
        # Carga NOC
        cargar_noc(cursor, noc_df, por_codigo, por_nombre, por_alt)
        conn.commit()
        
        # Carga Poblacion
        cargar_poblacion_pais(cursor, pop_df, por_codigo)
        conn.commit()
        
        # Verificacion
        exito = verificar_fase1(cursor)
        
        cursor.close()
        conn.close()
        return exito
        
    except Error as e:
        if conn and conn.is_connected():
            conn.rollback()
            conn.close()
        print_error(f"Fallo durante la ejecucion de la Fase 1 en MySQL: {e}")
        return False
    except Exception as e:
        if conn and conn.is_connected():
            conn.rollback()
            conn.close()
        print_error(f"Error general en Fase 1: {e}")
        return False


if __name__ == '__main__':
    ok = ejecutar_fase1()
    sys.exit(0 if ok else 1)
