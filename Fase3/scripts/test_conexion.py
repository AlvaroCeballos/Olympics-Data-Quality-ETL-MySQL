# -*- coding: utf-8 -*-
"""
test_conexion.py — Script de verificación de handshake MySQL y MongoDB Atlas.
Parte de la Fase 0 del plan de Integrante 2 (Extracción y Carga).
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import mysql.connector
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, OperationFailure

# Cargar variables de entorno desde Fase3/.env
env_path = Path(__file__).resolve().parent.parent / '.env'
if not env_path.exists():
    print(f"[ERROR] No se encontró el archivo .env en: {env_path}")
    print("Crea el archivo Fase3/.env basándote en Fase3/.env.example")
    sys.exit(1)

load_dotenv(dotenv_path=env_path)

MYSQL_HOST = os.getenv('MYSQL_HOST', 'localhost')
MYSQL_PORT = int(os.getenv('MYSQL_PORT', 3306))
MYSQL_USER = os.getenv('MYSQL_USER', 'root')
MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD', 'admin')
MYSQL_DB = os.getenv('MYSQL_DB', 'olimpiadas')

MONGO_URI = os.getenv('MONGO_URI')
MONGO_DB = os.getenv('MONGO_DB', 'olimpiadas')

def test_mysql():
    print("\n--- 1. Probando conexión a MySQL (Origen) ---")
    try:
        conn = mysql.connector.connect(
            host=MYSQL_HOST,
            port=MYSQL_PORT,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            database=MYSQL_DB
        )
        cursor = conn.cursor()
        cursor.execute("SELECT DATABASE(), VERSION();")
        db_name, version = cursor.fetchone()
        print(f"[OK] Conectado exitosamente a MySQL: BD '{db_name}', Versión {version}")
        
        cursor.execute("SELECT COUNT(*) FROM atleta;")
        atletas = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM participacion;")
        part = cursor.fetchone()[0]
        print(f"[INFO] Censo Origen: {atletas:,} atletas, {part:,} participaciones registradas.")
        
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"[ERROR] Falló la conexión a MySQL: {e}")
        return False

def test_mongodb():
    print("\n--- 2. Probando conexión a MongoDB Atlas (Destino) ---")
    if not MONGO_URI or "USUARIO:PASSWORD" in MONGO_URI:
        print("[ALERTA] La variable MONGO_URI en Fase3/.env no ha sido configurada con valores reales.")
        return False
    
    try:
        # Timeout corto de 5 segundos para fail-fast
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        # Comando de ping obligatorio
        client.admin.command('ping')
        print("[OK] Handshake exitoso con MongoDB Atlas (Ping OK)")
        
        db = client[MONGO_DB]
        colls = db.list_collection_names()
        print(f"[OK] Conectado a la base de datos '{MONGO_DB}'. Colecciones existentes: {colls}")
        
        client.close()
        return True
    except ConnectionFailure as e:
        print(f"[ERROR] Error de conexión a MongoDB (timeout/red): {e}")
        return False
    except OperationFailure as e:
        print(f"[ERROR] Error de autenticación en MongoDB (usuario/contraseña incorrectos): {e}")
        return False
    except Exception as e:
        print(f"[ERROR] Error inesperado en MongoDB: {e}")
        return False

if __name__ == '__main__':
    print("===============================================================")
    print("           VERIFICACIÓN DE CONEXIONES (FASE 0)                 ")
    print("===============================================================")
    mysql_ok = test_mysql()
    mongo_ok = test_mongodb()
    
    print("\n---------------------------------------------------------------")
    if mysql_ok and mongo_ok:
        print(">>> RESULTADO: AMBOS SERVICIOS ESTÁN LISTOS PARA LA FASE 1 <<<")
    elif mysql_ok and not mongo_ok:
        print(">>> RESULTADO: MySQL está listo. Pendiente configurar MONGO_URI en .env <<<")
    else:
        print(">>> RESULTADO: Hay servicios pendientes de configurar. <<<")
    print("===============================================================")
