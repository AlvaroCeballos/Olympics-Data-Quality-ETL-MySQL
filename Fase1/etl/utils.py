# -*- coding: utf-8 -*-
"""
utils.py — Módulo de utilidades comunes para el pipeline ETL Olimpiadas G18.

Contiene:
  - Conexión a MySQL (get_connection)
  - Reparación de mojibake (fix_mojibake)
  - Normalización de nombres para deduplicación (normalize_name)
  - Inserción segura con manejo de duplicados (safe_insert)
  - Rutas centralizadas a los archivos de datos

Decisiones técnicas aplicadas: DT-005, DT-006, DT-002
"""

import os
import sys
import io
import re
import unicodedata
import mysql.connector
from mysql.connector import Error

if sys.platform == 'win32':
    try:
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        if hasattr(sys.stderr, 'reconfigure'):
            sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

# =====================================================================
# CONFIGURACIÓN DE CONEXIÓN MySQL
# =====================================================================
DB_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'user': 'root',
    'password': 'admin',
    'charset': 'utf8mb4',
    'collation': 'utf8mb4_unicode_ci',
    'use_unicode': True,
}

DB_NAME = 'olimpiadas'

# =====================================================================
# RUTAS A ARCHIVOS DE DATOS (data_samples/)
# =====================================================================
# Todas las rutas son relativas al directorio raíz del proyecto.
# Los archivos en data_samples son muestras de 5 filas; los scripts
# están diseñados para funcionar igualmente con los CSVs completos.

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DATA_DIR = os.path.join(_PROJECT_ROOT, 'data_samples')

# Fuente 1: Keith Galli / Olympedia (data cruda)
BIOS_RAW         = os.path.join(_DATA_DIR, 'bios_sample.csv')
RESULTS_RAW      = os.path.join(_DATA_DIR, 'results.csv_sample.csv')

# Fuente 1: Archivos de referencia / auxiliares (clean-data)
BIOS_LOCS        = os.path.join(_DATA_DIR, 'bios_locs_sample.csv')
BIOS_CLEAN_REF   = os.path.join(_DATA_DIR, 'bios_clean_sample.csv')
RESULTS_CLEAN_REF = os.path.join(_DATA_DIR, 'results_clean_sample.csv')
NOC_REGIONS      = os.path.join(_DATA_DIR, 'noc_regions_sample.csv')
POPULATIONS      = os.path.join(_DATA_DIR, 'populations_sample.csv')

# Fuente 2: Kaggle 120 Years (1896–2016)
ATHLETE_EVENTS   = os.path.join(_DATA_DIR, 'athlete_events_sample.csv')

# Fuente 3: Kaggle Summer Olympics (1896–2024)
OLYMPICS_DATASET = os.path.join(_DATA_DIR, 'olympics_dataset.csv')

# Fuente 4: DataCamp Datalab (idéntica a Fuente 2, solo validación)
ATHLETE_EVENTS_DATALAB = os.path.join(_DATA_DIR, 'athlete_events_datalab_sample.csv')

# Ruta al script DDL
DDL_SCRIPT = os.path.join(_PROJECT_ROOT, 'olimpiada2s.sql')


def resolve_data_file(filename_or_base):
    """
    Resuelve la ruta a un archivo de datos buscando en multiples ubicaciones.
    Prioriza archivos completos sobre muestras (_sample.csv).
    
    Args:
        filename_or_base: Nombre del archivo (ej: 'noc_regions.csv', 'bios.csv')
                          o base sin extension (ej: 'noc_regions')
    
    Returns:
        Ruta absoluta al archivo existente, o None si no se encuentra.
    """
    base = filename_or_base
    if base.endswith('.csv'):
        base = base[:-4]
    if base.endswith('_sample'):
        base = base[:-7]
    
    candidates = [
        # 1. Archivo completo en directorio raiz
        os.path.join(_PROJECT_ROOT, f"{base}.csv"),
        # 2. Archivo completo en Olympics-Dataset/clean-data/
        os.path.join(_PROJECT_ROOT, 'Olympics-Dataset', 'clean-data', f"{base}.csv"),
        # 3. Archivo completo en Olympics-Dataset/
        os.path.join(_PROJECT_ROOT, 'Olympics-Dataset', f"{base}.csv"),
        # 4. Archivo completo en data_samples/
        os.path.join(_DATA_DIR, f"{base}.csv"),
        # 5. Archivo muestra en data_samples/
        os.path.join(_DATA_DIR, f"{base}_sample.csv"),
        # 6. Variantes con extensiones dobles (ej: results.csv_sample.csv)
        os.path.join(_DATA_DIR, f"{base}.csv_sample.csv"),
        # 7. Exactamente como se paso
        os.path.join(_DATA_DIR, filename_or_base),
        os.path.join(_PROJECT_ROOT, filename_or_base),
    ]
    
    for path in candidates:
        if os.path.isfile(path):
            return os.path.abspath(path)
    
    return None


# =====================================================================
# CONEXIÓN A MYSQL
# =====================================================================
def get_connection(database=None):
    """
    Obtiene una conexión a MySQL.
    
    Args:
        database: Nombre de la base de datos. Si es None, conecta sin
                  seleccionar base de datos (útil para CREATE DATABASE).
    
    Returns:
        mysql.connector.connection.MySQLConnection
    """
    config = DB_CONFIG.copy()
    if database:
        config['database'] = database
    try:
        conn = mysql.connector.connect(**config)
        return conn
    except Error as e:
        print(f"[ERROR] No se pudo conectar a MySQL: {e}")
        raise


# =====================================================================
# REPARACIÓN DE MOJIBAKE (DT-005)
# =====================================================================
def fix_mojibake(text):
    """
    Repara texto con doble codificación (UTF-8 interpretado como CP1252).
    
    Ejemplos:
      'Jean-FranÃ§ois'        → 'Jean-François'
      'PyrÃ©nÃ©es-Atlantiques' → 'Pyrénées-Atlantiques'
      'â€¢'                     → ' ' (bullet reemplazado por espacio)
    
    También reemplaza el carácter bullet (•) por espacio.
    
    Decisión técnica: DT-005
    """
    if text is None or not isinstance(text, str):
        return text
    
    # Paso 1: Intentar reparar mojibake (encode cp1252 → decode utf-8)
    try:
        repaired = text.encode('cp1252').decode('utf-8')
    except (UnicodeEncodeError, UnicodeDecodeError):
        # Si falla la recodificación, mantener el texto original
        repaired = text
    
    # Paso 2: Reemplazar bullet (•) y su versión mojibake (â€¢) por espacio
    repaired = repaired.replace('•', ' ')
    repaired = repaired.replace('â€¢', ' ')
    
    # Paso 3: Limpiar espacios múltiples resultantes
    repaired = re.sub(r'\s+', ' ', repaired).strip()
    
    return repaired


def fix_mojibake_series(series):
    """
    Aplica fix_mojibake a una Serie de pandas completa.
    Solo procesa valores de tipo string; ignora NaN.
    """
    return series.map(lambda x: fix_mojibake(x) if isinstance(x, str) else x)


# =====================================================================
# NORMALIZACIÓN DE NOMBRES PARA DEDUPLICACIÓN (DT-002)
_CORRUPTED_TOKEN_MAP = {
    'garca': 'garcia',
    'lpez': 'lopez',
    'rodrguez': 'rodriguez',
    'martnez': 'martinez',
    'hernndez': 'hernandez',
    'snchez': 'sanchez',
    'prez': 'perez',
    'gonzlez': 'gonzalez',
    'gmez': 'gomez',
    'daz': 'diaz',
    'jos': 'jose',
    'ngel': 'angel',
    'mara': 'maria',
    'vtor': 'vitor',
    'bernab': 'bernabe',
}

def normalize_name(name):
    """
    Normaliza un nombre para construir la matching key de deduplicación.
    
    Proceso:
      1. Convertir a minúsculas
      2. Quitar bullet (•)
      3. Normalización Unicode NFKD (descomponer caracteres acentuados)
      4. Quitar marcas diacríticas (acentos)
      5. Reemplazar puntuación por espacios (ej: 'Jean-Pierre' -> 'jean pierre')
      6. Restaurar tokens comunes con vocales eliminadas por raspadores defectuosos (ej: 'garca' -> 'garcia')
      7. Colapsar espacios múltiples y trim
    
    Decisión técnica: DT-002
    """
    if name is None or not isinstance(name, str):
        return ''
    
    # Minúsculas
    result = name.lower()
    
    # Quitar bullet primero
    result = result.replace('•', ' ').replace('â€¢', ' ')
    
    # NFKD → quitar marcas diacríticas
    result = unicodedata.normalize('NFKD', result)
    result = ''.join(c for c in result if not unicodedata.combining(c))
    
    # Reemplazar puntuación por espacio para que nombres con guión no se peguen
    result = re.sub(r'[^\w\s]', ' ', result)
    
    # Colapsar espacios
    tokens = result.split()
    tokens = [_CORRUPTED_TOKEN_MAP.get(t, t) for t in tokens]
    
    return ' '.join(tokens).strip()


_EVENT_STOP_WORDS = {
    'men', 'mens', 'women', 'womens', 'mixed', 'open',
    'olympic', 'nonolympic', 'intercalated', 'yog',
    'individual', 'team', 'pairs', 'doubles', 'singles',
    'summer', 'winter', 'games', 'the', 'and', 'for', 'with'
}

def extract_event_tokens(event_name):
    """
    Extrae los tokens esenciales de una prueba o evento olímpico
    omitiendo categorías de género y sufijos de formato.
    """
    if not event_name or not isinstance(event_name, str):
        return set()
    norm = normalize_name(event_name)
    # Reemplazar abreviaturas comunes
    norm = norm.replace('km', 'kilometres').replace('m ', 'metres ')
    return set(t for t in norm.split() if len(t) >= 2 and t not in _EVENT_STOP_WORDS)


# =====================================================================
# INSERCIÓN SEGURA
# =====================================================================
def safe_insert(cursor, sql, params, ignore_duplicates=True):
    """
    Ejecuta un INSERT manejando duplicados según la estrategia indicada.
    
    Args:
        cursor: Cursor MySQL activo
        sql: Sentencia INSERT (usar INSERT IGNORE o ON DUPLICATE KEY UPDATE)
        params: Tupla de parámetros
        ignore_duplicates: Si True, usa INSERT IGNORE. Si False, lanza excepción.
    
    Returns:
        lastrowid si insertó, None si fue duplicado ignorado
    """
    try:
        cursor.execute(sql, params)
        if cursor.lastrowid and cursor.lastrowid > 0:
            return cursor.lastrowid
        return None
    except mysql.connector.IntegrityError as e:
        if ignore_duplicates and e.errno == 1062:  # Duplicate entry
            return None
        raise


def get_or_create(cursor, table, unique_col, unique_val, extra_cols=None):
    """
    Busca un registro por columna única. Si no existe, lo inserta.
    
    Args:
        cursor: Cursor MySQL activo
        table: Nombre de la tabla
        unique_col: Nombre de la columna con UNIQUE KEY
        unique_val: Valor a buscar/insertar
        extra_cols: dict de columnas adicionales para el INSERT
                    Ej: {'id_pais': 5, 'notas': 'algo'}
    
    Returns:
        El ID (PK) del registro encontrado o insertado
    """
    # Buscar existente
    id_col = f'id_{table}'
    cursor.execute(f"SELECT {id_col} FROM {table} WHERE {unique_col} = %s", (unique_val,))
    row = cursor.fetchone()
    if row:
        return row[0]
    
    # Insertar nuevo
    cols = [unique_col]
    vals = [unique_val]
    if extra_cols:
        for k, v in extra_cols.items():
            cols.append(k)
            vals.append(v)
    
    placeholders = ', '.join(['%s'] * len(vals))
    col_names = ', '.join(cols)
    cursor.execute(
        f"INSERT IGNORE INTO {table} ({col_names}) VALUES ({placeholders})",
        tuple(vals)
    )
    
    if cursor.lastrowid and cursor.lastrowid > 0:
        return cursor.lastrowid
    
    # Si INSERT IGNORE no insertó (duplicado concurrent), buscar de nuevo
    cursor.execute(f"SELECT {id_col} FROM {table} WHERE {unique_col} = %s", (unique_val,))
    row = cursor.fetchone()
    return row[0] if row else None


def print_section(title):
    """Imprime un encabezado de sección formateado para la consola."""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def print_ok(msg):
    """Imprime un mensaje de éxito."""
    print(f"  [OK] {msg}")


def print_warn(msg):
    """Imprime un mensaje de advertencia."""
    print(f"  [WARN] {msg}")


def print_error(msg):
    """Imprime un mensaje de error."""
    print(f"  [ERROR] {msg}")
