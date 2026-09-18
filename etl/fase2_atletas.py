# -*- coding: utf-8 -*-
"""
fase2_atletas.py — Pipeline ETL Fase 2: Limpieza de bios1.csv y Carga de 'atleta'.

Tabla procesada:
  - atleta: Catalogo maestro de atletas (entidad unica con 21 atributos limpios).

Archivos de entrada:
  - bios_sample.csv (o bios1.csv / bios.csv crudo) — Fuente maestra biografica (16 columnas)
  - bios_locs_sample.csv (o bios_locs.csv) — Enriquecimiento lat/long (WGS84)
  - bios_clean_sample.csv — Archivo de referencia para validacion comparativa

Ingenieria inversa aplicada (referencia Keith Galli clean_data.ipynb):
  - Celda 6:  df['name'] = df['Used name'].str.replace("•", " ")
  - Celda 8-9: Measurements.str.split('/') -> height_cm, weight_kg
  - Celda 11: Born/Died regex date_pattern r'(\d+ \w+ \d{4}|\d{4})'
  - Celda 12-13: Born regex location_pattern r'in ([\w\s().-]+), ([\w\s.-]+) \((\w+)\)'
  - DIFERENCIA CLAVE (Reglas 4, 7 y 12 del catedratico): NO se descartan columnas.
    Se conservan Full name, Other names, Original name, Name order, Nick/petnames,
    Title(s), Affiliations, Roles, Nationality.

Decisiones tecnicas aplicadas:
  - DT-001: bios1.csv es fuente maestra (atleta.id_externo = athlete_id)
  - DT-002: Matching key normalizada para deduplicacion cross-source
  - DT-005: Saneamiento universal de mojibake (fix_mojibake)
  - DT-006: Entrada via resolve_data_file()
  - DT-008: Orden FK respetando dependencias
  - DT-009: Sexo 'Male' -> 'M', 'Female' -> 'F'
  - DT-019: Desglose semantico de ubicacion de nacimiento
  - DT-020: Enriquecimiento georreferenciado (bios_locs merge)
  - DT-021: Conversion robusta de fechas historicas a MySQL DATE
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
# EXPRESIONES REGULARES PARA EXTRACCION BIOGRAFICA
# =====================================================================
# Patron de fecha: "12 December 1886" o solo anio "1886"
_DATE_PATTERN = re.compile(r'(\d{1,2}\s+[A-Za-z]+\s+\d{4}|\d{4})')

# Mapeo de meses en ingles a numero
_MONTHS = {
    'january': 1, 'february': 2, 'march': 3, 'april': 4,
    'may': 5, 'june': 6, 'july': 7, 'august': 8,
    'september': 9, 'october': 10, 'november': 11, 'december': 12
}


def parsear_fecha_a_mysql(texto_fecha):
    """
    Convierte una fecha en texto libre (ej: '12 December 1886', '1886', '1969-04-01')
    a formato de fecha ISO-8601 'YYYY-MM-DD' valido para MySQL DATE.
    Si solo trae anio ('1886'), se normaliza a '1886-01-01'.
    Retorna None si no se puede determinar la fecha.
    """
    if not texto_fecha or pd.isna(texto_fecha):
        return None
    
    texto = str(texto_fecha).strip()
    match = _DATE_PATTERN.search(texto)
    if not match:
        # Intentar parseo directo con pandas
        try:
            ts = pd.to_datetime(texto, format='mixed', errors='coerce')
            if pd.notna(ts):
                return ts.strftime('%Y-%m-%d')
        except Exception:
            pass
        return None
    
    fecha_str = match.group(1).strip()
    
    # Caso 1: Solo anio (4 digitos)
    if re.match(r'^\d{4}$', fecha_str):
        return f"{fecha_str}-01-01"
    
    # Caso 2: "DD Month YYYY" o "Month DD YYYY"
    partes = fecha_str.split()
    if len(partes) == 3:
        # Formato: dia mes anio
        if partes[0].isdigit() and partes[1].lower() in _MONTHS and partes[2].isdigit():
            dia = int(partes[0])
            mes = _MONTHS[partes[1].lower()]
            anio = int(partes[2])
            return f"{anio:04d}-{mes:02d}-{dia:02d}"
        # Formato: mes dia anio
        elif partes[0].lower() in _MONTHS and partes[1].isdigit() and partes[2].isdigit():
            mes = _MONTHS[partes[0].lower()]
            dia = int(partes[1])
            anio = int(partes[2])
            return f"{anio:04d}-{mes:02d}-{dia:02d}"
    
    # Fallback con pandas
    try:
        ts = pd.to_datetime(fecha_str, format='mixed', errors='coerce')
        if pd.notna(ts):
            return ts.strftime('%Y-%m-%d')
    except Exception:
        pass
    
    return None


def parsear_ubicacion(texto_born):
    """
    Extrae (ciudad, region, codigo_pais) del campo 'Born'.
    Formatos soportados:
      - '... in Bordeaux, Gironde (FRA)' -> ('Bordeaux', 'Gironde', 'FRA')
      - '... in Paris (FRA)'             -> ('Paris', None, 'FRA')
      - '... in Monaco, Monaco (MON)'    -> ('Monaco', 'Monaco', 'MON')
    """
    if not texto_born or pd.isna(texto_born):
        return None, None, None
    
    texto = str(texto_born).strip()
    
    # 3 partes: in Ciudad, Region (PAIS)
    m3 = re.search(r'in\s+([^,()]+),\s*([^()]+)\s*\((\w+)\)', texto)
    if m3:
        ciudad = fix_mojibake(m3.group(1)).strip()[:120]
        region = fix_mojibake(m3.group(2)).strip()[:120]
        pais_cod = m3.group(3).strip().upper()[:3]
        return ciudad, region, pais_cod
    
    # 2 partes: in Ciudad (PAIS)
    m2 = re.search(r'in\s+([^()]+)\s*\((\w+)\)', texto)
    if m2:
        ciudad = fix_mojibake(m2.group(1)).strip()[:120]
        pais_cod = m2.group(2).strip().upper()[:3]
        return ciudad, None, pais_cod
    
    # 1 parte: in Ciudad/Pais sin parentesis
    m1 = re.search(r'in\s+(.+)', texto)
    if m1:
        ciudad = fix_mojibake(m1.group(1)).strip()[:120]
        return ciudad, None, None
    
    return None, None, None


def parsear_medidas(texto_medidas):
    """
    Extrae (altura_cm, peso_kg) del campo 'Measurements' (ej: '183 cm / 76 kg').
    """
    if not texto_medidas or pd.isna(texto_medidas):
        return None, None
    
    texto = str(texto_medidas).strip()
    partes = texto.split('/')
    
    altura = None
    peso = None
    
    if len(partes) >= 1:
        m_alt = re.search(r'(\d+(?:\.\d+)?)\s*cm', partes[0])
        if m_alt:
            try:
                altura = float(m_alt.group(1))
            except ValueError:
                pass
    
    if len(partes) >= 2:
        m_peso = re.search(r'(\d+(?:\.\d+)?)\s*kg', partes[1])
        if m_peso:
            try:
                peso = float(m_peso.group(1))
            except ValueError:
                pass
    
    return altura, peso


def homologar_sexo(sexo_raw):
    """
    Homologa 'Male' -> 'M', 'Female' -> 'F'.
    """
    if not sexo_raw or pd.isna(sexo_raw):
        return None
    s = str(sexo_raw).strip().upper()
    if s.startswith('M'):
        return 'M'
    elif s.startswith('F'):
        return 'F'
    return None


# =====================================================================
# CARGA DE LA TABLA ATLETA
# =====================================================================
def cargar_atletas(cursor, conn):
    """
    Procesa bios1.csv crudo + bios_locs.csv y carga la tabla atleta.
    """
    print_section("2.1 Carga de datos de bios y coordenadas")
    
    path_bios = resolve_data_file('bios')
    path_locs = resolve_data_file('bios_locs')
    
    if not path_bios or not os.path.isfile(path_bios):
        print_error(f"No se encontro archivo bios: {path_bios}")
        return False
    
    print(f"  Archivo bios: {path_bios}")
    bios_df = pd.read_csv(path_bios)
    print_ok(f"bios leido: {len(bios_df)} registros, {len(bios_df.columns)} columnas")
    
    # Leer bios_locs si existe
    locs_dict = {}
    if path_locs and os.path.isfile(path_locs):
        print(f"  Archivo bios_locs: {path_locs}")
        locs_df = pd.read_csv(path_locs)
        for _, row in locs_df.iterrows():
            aid = row.get('athlete_id')
            if pd.notna(aid):
                lat = float(row['lat']) if pd.notna(row.get('lat')) else None
                lon = float(row['long']) if pd.notna(row.get('long')) else None
                locs_dict[int(aid)] = (lat, lon)
        print_ok(f"bios_locs en memoria: {len(locs_dict)} coordenadas georreferenciadas")
    else:
        print_warn("bios_locs no disponible, lat/long quedaran en NULL")
    
    # Pre-cargar cache de paises existentes
    print_section("2.2 Cache de paises para resolucion de nacimiento")
    cursor.execute("SELECT id_pais, codigo_pais, nombre FROM pais;")
    pais_por_codigo = {}
    pais_por_nombre = {}
    for pid, pcode, pnom in cursor.fetchall():
        if pcode:
            pais_por_codigo[pcode.strip().upper()] = pid
        if pnom:
            pais_por_nombre[normalize_name(pnom)] = pid
    
    print_ok(f"Paises en cache: {len(pais_por_codigo)} codigos, {len(pais_por_nombre)} nombres")
    
    # Mapeo de auxilio para nombres de codigos olimpicos comunes
    _COMMON_COUNTRY_NAMES = {
        'FRA': 'France', 'GBR': 'Great Britain', 'USA': 'United States',
        'GER': 'Germany', 'ITA': 'Italy', 'ESP': 'Spain', 'SWE': 'Sweden',
        'NOR': 'Norway', 'FIN': 'Finland', 'DEN': 'Denmark', 'SUI': 'Switzerland',
        'AUT': 'Austria', 'BEL': 'Belgium', 'NED': 'Netherlands', 'GRE': 'Greece',
        'CAN': 'Canada', 'AUS': 'Australia', 'JPN': 'Japan', 'CHN': 'China',
        'GUA': 'Guatemala', 'MEX': 'Mexico', 'BRA': 'Brazil', 'ARG': 'Argentina',
    }

    # Helper para buscar o crear pais de nacimiento
    def resolver_pais_nac(codigo, nombre_sugerido=None):
        if codigo:
            cod = codigo.strip().upper()[:3]
            if cod in pais_por_codigo:
                return pais_por_codigo[cod]
            
            # Nombre para el nuevo pais (usar mapeo o sugerido si coincide o fallback a codigo)
            nom_insert = _COMMON_COUNTRY_NAMES.get(cod)
            if not nom_insert and nombre_sugerido and cod == nombre_sugerido[:3].upper():
                nom_insert = nombre_sugerido
            if not nom_insert:
                nom_insert = cod
            
            # Insertar nuevo pais para preservar integridad referencial
            cursor.execute(
                "INSERT INTO pais (codigo_pais, nombre, region) VALUES (%s, %s, %s) "
                "ON DUPLICATE KEY UPDATE nombre = COALESCE(pais.nombre, VALUES(nombre));",
                (cod, nom_insert, nom_insert)
            )
            conn.commit()
            nuevo_id = cursor.lastrowid
            if not nuevo_id or nuevo_id == 0:
                cursor.execute("SELECT id_pais FROM pais WHERE codigo_pais = %s;", (cod,))
                nuevo_id = cursor.fetchone()[0]
            
            pais_por_codigo[cod] = nuevo_id
            pais_por_nombre[normalize_name(nom_insert)] = nuevo_id
            print(f"    [PAIS CREADO ON-THE-FLY] {cod} - {nom_insert} (id={nuevo_id})")
            return nuevo_id
        
        # Si no hubo codigo, buscar por nombre sugerido
        if nombre_sugerido:
            nom_norm = normalize_name(nombre_sugerido)
            if nom_norm in pais_por_nombre:
                return pais_por_nombre[nom_norm]
        
        return None

    # Pre-cargar atletas existentes por id_externo para idempotencia
    cursor.execute("SELECT id_externo, id_atleta FROM atleta WHERE id_externo IS NOT NULL;")
    atletas_existentes = {row[0]: row[1] for row in cursor.fetchall()}
    print(f"  Atletas previamente registrados en BD: {len(atletas_existentes)}")
    
    # Procesar e insertar atletas
    print_section("2.3 Procesamiento e insercion de atletas")
    
    sql_insert = """
        INSERT INTO atleta (
            id_externo, nombre, nombre_completo, otros_nombres, nombre_original,
            orden_nombre, apodo, titulo, afiliacion, sexo,
            fecha_nac, ciudad_nac, region_nac, id_pais_nac, fecha_muerte,
            altura_cm, peso_kg, roles, nacionalidad, latitud, longitud
        ) VALUES (
            %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s, %s
        );
    """
    
    sql_update = """
        UPDATE atleta SET
            nombre = %s,
            nombre_completo = %s,
            otros_nombres = %s,
            nombre_original = %s,
            orden_nombre = %s,
            apodo = %s,
            titulo = %s,
            afiliacion = %s,
            sexo = %s,
            fecha_nac = %s,
            ciudad_nac = %s,
            region_nac = %s,
            id_pais_nac = %s,
            fecha_muerte = %s,
            altura_cm = %s,
            peso_kg = %s,
            roles = %s,
            nacionalidad = %s,
            latitud = %s,
            longitud = %s
        WHERE id_atleta = %s;
    """
    
    insertados = 0
    actualizados = 0
    
    for idx, (_, row) in enumerate(bios_df.iterrows()):
        athlete_id = int(row['athlete_id']) if pd.notna(row.get('athlete_id')) else None
        
        # Nombres
        nombre = fix_mojibake(str(row['Used name'])).strip()[:120] if pd.notna(row.get('Used name')) else None
        nombre_completo = fix_mojibake(str(row['Full name'])).strip()[:150] if pd.notna(row.get('Full name')) else None
        otros_nombres = fix_mojibake(str(row['Other names'])).strip()[:255] if pd.notna(row.get('Other names')) else None
        nombre_original = fix_mojibake(str(row['Original name'])).strip()[:150] if pd.notna(row.get('Original name')) else None
        orden_nombre = fix_mojibake(str(row['Name order'])).strip()[:50] if pd.notna(row.get('Name order')) else None
        apodo = fix_mojibake(str(row['Nick/petnames'])).strip()[:150] if pd.notna(row.get('Nick/petnames')) else None
        titulo = fix_mojibake(str(row['Title(s)'])).strip()[:100] if pd.notna(row.get('Title(s)')) else None
        afiliacion = fix_mojibake(str(row['Affiliations'])).strip()[:255] if pd.notna(row.get('Affiliations')) else None
        roles = fix_mojibake(str(row['Roles'])).strip()[:150] if pd.notna(row.get('Roles')) else None
        nacionalidad = fix_mojibake(str(row['Nationality'])).strip()[:120] if pd.notna(row.get('Nationality')) else None
        
        # Sexo
        sexo = homologar_sexo(row.get('Sex'))
        
        # Nacimiento
        born_raw = fix_mojibake(str(row['Born'])) if pd.notna(row.get('Born')) else None
        fecha_nac = parsear_fecha_a_mysql(born_raw)
        ciudad_nac, region_nac, pais_nac_cod = parsear_ubicacion(born_raw)
        
        # Pais de nacimiento: resolver FK
        # Sugerir pais desde columna NOC de bios si aplica
        pais_sugerido = str(row.get('NOC')).strip() if pd.notna(row.get('NOC')) else None
        id_pais_nac = resolver_pais_nac(pais_nac_cod, pais_sugerido)
        
        # Muerte
        died_raw = fix_mojibake(str(row['Died'])) if pd.notna(row.get('Died')) else None
        fecha_muerte = parsear_fecha_a_mysql(died_raw)
        
        # Medidas
        altura_cm, peso_kg = parsear_medidas(row.get('Measurements'))
        
        # Coordenadas georreferenciadas
        coords = locs_dict.get(athlete_id, (None, None)) if athlete_id else (None, None)
        latitud, longitud = coords
        
        # Verificar si el atleta ya existe por athlete_id
        if athlete_id and athlete_id in atletas_existentes:
            id_atleta = atletas_existentes[athlete_id]
            cursor.execute(sql_update, (
                nombre, nombre_completo, otros_nombres, nombre_original,
                orden_nombre, apodo, titulo, afiliacion, sexo,
                fecha_nac, ciudad_nac, region_nac, id_pais_nac, fecha_muerte,
                altura_cm, peso_kg, roles, nacionalidad, latitud, longitud,
                id_atleta
            ))
            actualizados += 1
        else:
            cursor.execute(sql_insert, (
                athlete_id, nombre, nombre_completo, otros_nombres, nombre_original,
                orden_nombre, apodo, titulo, afiliacion, sexo,
                fecha_nac, ciudad_nac, region_nac, id_pais_nac, fecha_muerte,
                altura_cm, peso_kg, roles, nacionalidad, latitud, longitud
            ))
            nuevo_id = cursor.lastrowid
            if athlete_id:
                atletas_existentes[athlete_id] = nuevo_id
            insertados += 1

        if (idx + 1) % 25000 == 0:
            conn.commit()
            print(f"  -> Progreso: {idx + 1}/{len(bios_df)} atletas ({((idx + 1)/len(bios_df)*100):.1f}%)...")
    
    conn.commit()
    print_ok(f"Atletas procesados: {len(bios_df)} (nuevos insertados: {insertados}, actualizados: {actualizados})")
    return True


# =====================================================================
# VERIFICACION DE LA FASE 2
# =====================================================================
def verificar_fase2(cursor):
    """
    Ejecuta consultas de control para validar el estado de la tabla atleta.
    """
    print_section("2.4 Verificacion de Fase 2")
    
    cursor.execute("SELECT COUNT(*) FROM atleta;")
    total_atletas = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM atleta WHERE id_externo IS NOT NULL;")
    con_externo = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM atleta WHERE fecha_nac IS NOT NULL;")
    con_nac = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM atleta WHERE fecha_muerte IS NOT NULL;")
    con_muerte = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM atleta WHERE altura_cm IS NOT NULL;")
    con_altura = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM atleta WHERE latitud IS NOT NULL;")
    con_lat = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM atleta WHERE id_pais_nac IS NOT NULL;")
    con_pais_nac = cursor.fetchone()[0]
    
    print(f"  Total atletas en 'atleta':            {total_atletas}")
    print(f"  Atletas con id_externo (Olympedia):   {con_externo}")
    print(f"  Atletas con fecha_nac:                {con_nac}")
    print(f"  Atletas con fecha_muerte:             {con_muerte}")
    print(f"  Atletas con altura/peso:              {con_altura}")
    print(f"  Atletas con coordenadas lat/long:     {con_lat}")
    print(f"  Atletas con id_pais_nac resuelto:     {con_pais_nac}")
    
    print("\n  Muestra de atletas cargados en la base de datos:")
    cursor.execute("""
        SELECT a.id_atleta, a.id_externo, a.nombre, a.sexo, a.fecha_nac, 
               a.ciudad_nac, a.region_nac, p.codigo_pais, a.altura_cm, a.peso_kg,
               a.latitud, a.longitud
        FROM atleta a
        LEFT JOIN pais p ON a.id_pais_nac = p.id_pais
        ORDER BY a.id_atleta
        LIMIT 5;
    """)
    for r in cursor.fetchall():
        print(f"    [{r[0]}] ext_id={r[1]}, nombre='{r[2]}', sexo={r[3]}, "
              f"nac={r[4]}, ciudad='{r[5]}', reg='{r[6]}', pais={r[7]}, "
              f"medidas={r[8]}cm/{r[9]}kg, coords=({r[10]}, {r[11]})")
    
    if total_atletas > 0 and con_externo > 0 and con_nac > 0:
        print_ok("Verificacion de Fase 2 EXITOSA.")
        return True
    else:
        print_error("Verificacion de Fase 2 INCOMPLETA: datos insuficientes.")
        return False


# =====================================================================
# EJECUTOR PRINCIPAL DE FASE 2
# =====================================================================
def ejecutar_fase2():
    """Ejecuta el pipeline completo de la Fase 2."""
    print_section("INICIO DE EJECUCION: FASE 2 (Limpieza de bios y carga de atleta)")
    
    conn = None
    try:
        conn = get_connection(database=DB_NAME)
        cursor = conn.cursor()
        
        # 1. Cargar atletas
        if not cargar_atletas(cursor, conn):
            return False
        
        # 2. Verificacion
        exito = verificar_fase2(cursor)
        
        cursor.close()
        conn.close()
        return exito
        
    except Error as e:
        if conn and conn.is_connected():
            conn.rollback()
            conn.close()
        print_error(f"Fallo durante la ejecucion de la Fase 2 en MySQL: {e}")
        return False
    except Exception as e:
        if conn and conn.is_connected():
            conn.rollback()
            conn.close()
        print_error(f"Error general en Fase 2: {e}")
        return False


if __name__ == '__main__':
    ok = ejecutar_fase2()
    sys.exit(0 if ok else 1)
