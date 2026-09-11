# -*- coding: utf-8 -*-
"""
fase0_ddl.py — Fase 0: Ejecución del DDL y verificación de la base de datos.

Este script:
  1. Conecta a MySQL sin seleccionar base de datos
  2. Ejecuta el script olimpiada2s.sql completo (DROP + CREATE DATABASE + tablas + índices + semilla)
  3. Verifica que las 12 tablas existan
  4. Verifica que la semilla de medallas esté insertada (4 registros)

Ingeniería inversa: No aplica en esta fase (DDL puro).
Decisiones técnicas: DT-008 (orden de inserción), DT-010 (semilla medalla)
"""

import sys
import os
import re

# Agregar el directorio padre al path para importar utils
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from etl.utils import get_connection, DDL_SCRIPT, DB_NAME, print_section, print_ok, print_error, print_warn


# Tablas esperadas en el orden de creación (DT-008)
TABLAS_ESPERADAS = [
    'pais',
    'noc',
    'sede',
    'olimpiada',
    'atleta',
    'deporte',
    'disciplina',
    'evento',
    'equipo',
    'medalla',
    'participacion',
    'poblacion_pais',
]


def parse_sql_statements(sql_text):
    """
    Parsea un script SQL en sentencias individuales.
    Maneja correctamente:
      - Comentarios de línea (--)
      - Sentencias multilínea
      - Cadenas con punto y coma dentro de comillas
    """
    statements = []
    current = []
    
    for line in sql_text.split('\n'):
        stripped = line.strip()
        
        # Ignorar líneas vacías y comentarios puros
        if not stripped or stripped.startswith('--'):
            continue
        
        # Quitar comentarios al final de la línea (fuera de comillas)
        # Simplificado: quitar todo después de -- que no esté dentro de comillas
        comment_pos = stripped.find('--')
        if comment_pos > 0:
            # Verificar que no esté dentro de comillas (simplificación)
            before = stripped[:comment_pos]
            if before.count("'") % 2 == 0:
                stripped = before.rstrip()
        
        current.append(stripped)
        
        # Si la línea termina con ';', es el final de una sentencia
        if stripped.endswith(';'):
            stmt = ' '.join(current).rstrip(';').strip()
            if stmt:
                statements.append(stmt)
            current = []
    
    # Agregar sentencia final si no terminó con ';'
    if current:
        stmt = ' '.join(current).strip()
        if stmt:
            statements.append(stmt)
    
    return statements


def ejecutar_ddl():
    """
    Lee y ejecuta el script DDL completo contra MySQL.
    """
    print_section("FASE 0: Ejecucion del DDL")
    
    # 1. Leer el script DDL
    print(f"  Leyendo DDL desde: {DDL_SCRIPT}")
    if not os.path.exists(DDL_SCRIPT):
        print_error(f"No se encontro el archivo DDL: {DDL_SCRIPT}")
        return False
    
    with open(DDL_SCRIPT, 'r', encoding='utf-8') as f:
        ddl_content = f.read()
    
    print_ok(f"DDL leido: {len(ddl_content)} bytes")
    
    # 2. Conectar SIN base de datos (para poder DROP/CREATE DATABASE)
    print("\n  Conectando a MySQL (sin base de datos)...")
    conn = get_connection(database=None)
    cursor = conn.cursor()
    
    # 3. Parsear y ejecutar sentencias una por una
    print("  Ejecutando script DDL...")
    statements = parse_sql_statements(ddl_content)
    
    try:
        executed = 0
        for i, stmt in enumerate(statements):
            try:
                cursor.execute(stmt)
                executed += 1
            except Exception as e:
                print_error(f"Sentencia {i+1}: {e}")
                print(f"    SQL: {stmt[:120]}...")
                conn.rollback()
                cursor.close()
                conn.close()
                return False
        conn.commit()
        print_ok(f"Script DDL ejecutado exitosamente ({executed} sentencias)")
    except Exception as e:
        print_error(f"Error general ejecutando DDL: {e}")
        conn.rollback()
        cursor.close()
        conn.close()
        return False
    
    cursor.close()
    conn.close()
    return True


def verificar_tablas():
    """
    Verifica que las 12 tablas existan en la base de datos.
    """
    print_section("Verificacion de tablas")
    
    conn = get_connection(database=DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute("SHOW TABLES")
    tablas_existentes = {row[0] for row in cursor.fetchall()}
    
    todas_ok = True
    for tabla in TABLAS_ESPERADAS:
        if tabla in tablas_existentes:
            print_ok(f"Tabla '{tabla}' existe")
        else:
            print_error(f"Tabla '{tabla}' NO encontrada")
            todas_ok = False
    
    # Reportar tablas extra (si las hay)
    extras = tablas_existentes - set(TABLAS_ESPERADAS)
    if extras:
        for t in extras:
            print_warn(f"Tabla extra encontrada: '{t}'")
    
    print(f"\n  Total tablas encontradas: {len(tablas_existentes)} / {len(TABLAS_ESPERADAS)} esperadas")
    
    cursor.close()
    conn.close()
    return todas_ok


def verificar_semilla_medallas():
    """
    Verifica que la tabla medalla tenga los 4 registros semilla.
    """
    print_section("Verificacion de semilla: medalla")
    
    conn = get_connection(database=DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute("SELECT id_medalla, tipo FROM medalla ORDER BY id_medalla")
    rows = cursor.fetchall()
    
    medallas_esperadas = {'Gold', 'Silver', 'Bronze', 'NA'}
    medallas_encontradas = {row[1] for row in rows}
    
    for row in rows:
        print_ok(f"id_medalla={row[0]}, tipo='{row[1]}'")
    
    if medallas_encontradas == medallas_esperadas:
        print(f"\n  Semilla de medallas completa ({len(rows)} registros)")
        ok = True
    else:
        faltantes = medallas_esperadas - medallas_encontradas
        print_error(f"Faltan tipos de medalla: {faltantes}")
        ok = False
    
    cursor.close()
    conn.close()
    return ok


def verificar_estructura_tablas():
    """
    Muestra un resumen de la estructura de cada tabla (columnas y tipos).
    """
    print_section("Estructura de tablas")
    
    conn = get_connection(database=DB_NAME)
    cursor = conn.cursor()
    
    for tabla in TABLAS_ESPERADAS:
        cursor.execute(f"DESCRIBE {tabla}")
        cols = cursor.fetchall()
        col_names = [c[0] for c in cols]
        print(f"\n  {tabla} ({len(cols)} columnas): {', '.join(col_names)}")
    
    cursor.close()
    conn.close()


def main():
    """Punto de entrada principal."""
    print("=" * 60)
    print("  PIPELINE ETL OLIMPIADAS G18 - FASE 0")
    print("  Ejecucion del DDL y verificacion de la base de datos")
    print("=" * 60)
    
    # Paso 1: Ejecutar DDL
    if not ejecutar_ddl():
        print("\n[ABORTADO] Error en la ejecucion del DDL.")
        sys.exit(1)
    
    # Paso 2: Verificar tablas
    if not verificar_tablas():
        print("\n[ABORTADO] No todas las tablas fueron creadas.")
        sys.exit(1)
    
    # Paso 3: Verificar semilla
    if not verificar_semilla_medallas():
        print("\n[ABORTADO] La semilla de medallas no esta completa.")
        sys.exit(1)
    
    # Paso 4: Mostrar estructura
    verificar_estructura_tablas()
    
    print_section("FASE 0 COMPLETADA EXITOSAMENTE")
    print("  Base de datos 'olimpiadas' creada con 12 tablas y semilla de medallas.")
    print("  Listo para Fase 1: Carga de tablas dimensionales.\n")


if __name__ == '__main__':
    main()
