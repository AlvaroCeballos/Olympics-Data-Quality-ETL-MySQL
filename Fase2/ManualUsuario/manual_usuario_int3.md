# Manual de Usuario — Restauración, Validación y Auditoría (Integrante 3)

**Autor:** Álvaro Gabriel Ceballos Gil — 202300673 (Integrante 3)  
**Curso:** Sistemas de Bases de Datos 2, USAC  
**Grupo:** 18  
**Fecha:** Octubre 2026  
**Módulo:** Restauración Física con Percona XtraBackup 8.0 y Auditoría Automatizada en MySQL 8.0  

---

## 1. Requisitos Previos y Entorno

Para operar los procedimientos de recuperación física sin riesgo para la base de datos principal:

1. **Sistema Operativo y Herramientas:**
   - Windows 10/11 con **Docker Desktop** iniciado y funcionando con motor WSL2 o Hyper-V.
   - **PowerShell 5.1 o 7.x** ejecutado con permisos para correr scripts:
     ```powershell
     Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
     ```
   - **MySQL Workbench** (opcional, para visualización manual en puerto `3307`).

2. **Verificación de Imágenes Docker Requeridas:**
   Los scripts descargarán automáticamente las imágenes oficiales si no están presentes:
   - `mysql:8.0` (Motor de base de datos MySQL Community Server 8.0).
   - `percona/percona-xtrabackup:8.0` (Herramienta de copia y restauración física en caliente).

3. **Arquitectura de Aislamiento:**
   - Todos los scripts de restauración operan sobre un contenedor temporal independiente denominado `fase2_mysql_restore` y un volumen Docker aislado llamado `fase2_restore_mysql_data`.
   - **Garantía de Seguridad:** El volumen de producción del equipo (`fase2_olimpiadas_mysql_data`) y los archivos originales de respaldo en `Fase2/backup/archivos/` nunca son tocados ni modificados.

---

## 2. Comandos Operativos de Restauración

Todos los scripts deben ejecutarse desde la **raíz del repositorio** (`d:\Proyectos U\Bases 2\Proyecto 1\SBD2B_PROYECT1_2S2026_G18`).

### 2.1 Restaurar un Respaldo Completo (C0 - Catálogos)

Para restaurar la base de datos a su estado inicial de catálogos (C0):

```powershell
.\Fase2\restauracion\restore-full.ps1 -Ciclo <ciclo>
```

**Parámetros:**
- `-Ciclo`: `deportista`, `deporte` o `anio`.

**Ejemplo de Ejecución:**
```powershell
.\Fase2\restauracion\restore-full.ps1 -Ciclo deportista
```

**Qué hace internamente el script:**
1. Detiene cualquier contenedor previo en el puerto 3307 y limpia el volumen aislado.
2. Inicia el cronómetro de alta precisión (`System.Diagnostics.Stopwatch`).
3. Crea una copia de trabajo segura en `Fase2/backup/archivos/_restore_work/`.
4. Ejecuta `xtrabackup --prepare` para aplicar el redo log y generar consistencia.
5. Ejecuta `xtrabackup --copy-back` con UID `0:0` hacia el volumen de datos `/var/lib/mysql`.
6. Asigna permisos `chown -R 999:999` (usuario `mysql` en Linux).
7. Levanta el contenedor `fase2_mysql_restore` y espera a que el servicio responda en el puerto `3307`.
8. Registra la duración exacta en `Fase2/logs/bitacora_restauracion.csv`.

---

### 2.2 Restaurar un Respaldo Diferencial (C1, C2, C3)

Para recuperar la base de datos a cualquiera de los estados de carga incremental/diferencial:

```powershell
.\Fase2\restauracion\restore-differential.ps1 -Ciclo <ciclo> -Ronda <ronda>
```

**Parámetros:**
- `-Ciclo`: `deportista`, `deporte` o `anio`.
- `-Ronda`: `c1` (Ronda 1), `c2` (Ronda 2) o `c3` (Ronda 3).

**Ejemplo de Ejecución:**
```powershell
# Recuperar Ciclo Año hasta Tokio 2020 (Ronda 2)
.\Fase2\restauracion\restore-differential.ps1 -Ciclo anio -Ronda c2
```

**Secuencia interna de recuperación diferencial de XtraBackup:**
1. **Fase 1 (Prepare Full):** `xtrabackup --prepare --apply-log-only --target-dir=<full_work>`  
   *(Aplica el log transaccional del Full pero no descarta transacciones abiertas).*
2. **Fase 2 (Merge Diff):** `xtrabackup --prepare --target-dir=<full_work> --incremental-dir=<diff_work>`  
   *(Fusiona las páginas físicas modificadas del diferencial sobre el Full base).*
3. **Fase 3 (Rollback Final):** `xtrabackup --prepare --target-dir=<full_work>`  
   *(Consolida la consistencia transaccional definitiva).*
4. **Fase 4 (Copy-Back y Arranque):** Copia los datos al volumen, arranca MySQL y sincroniza credenciales.

---

### 2.3 Orquestador Maestro de Restauración y Validación

Para ejecutar la restauración completa de un ciclo o de todos los ciclos de forma automatizada:

```powershell
# Ejecución completa desatendida
.\Fase2\restauracion\restaurar-y-validar-todo.ps1 -Ciclo todos

# O para un solo ciclo pausando para tomar capturas de pantalla en Workbench:
.\Fase2\restauracion\restaurar-y-validar-todo.ps1 -Ciclo deportista -PausarParaCapturas
```

Cuando se usa el modificador `-PausarParaCapturas`, el script detiene la ejecución al finalizar cada restauración, permitiendo al DBA o evaluador conectarse desde Workbench, revisar los datos, tomar la captura de pantalla requerida y presionar `Enter` para continuar con la siguiente ronda.

---

## 3. Auditoría de Integridad y Validación Automatizada

Para validar de forma exhaustiva una base recién restaurada sin necesidad de consultas manuales:

```powershell
.\Fase2\restauracion\validar-restauracion.ps1 -Ciclo <ciclo> -Carga <carga> -SaveReport
```

**Ejemplo:**
```powershell
.\Fase2\restauracion\validar-restauracion.ps1 -Ciclo anio -Carga c3 -SaveReport
```

### 3.1 Pruebas Ejecutadas por el Auditor

1. **Censo de Filas (12 Tablas):**
   - Compara el `COUNT(*)` real de cada una de las 12 tablas contra los valores esperados por el Integrante 2.
   - Si los valores coinciden, muestra una etiqueta verde `[OK]`. Si hay discrepancia, emite una alarma roja `[ERROR]`.
2. **Integridad Referencial (0 Huérfanos):**
   - Ejecuta 7 consultas anti-join (`LEFT JOIN ... WHERE <pk> IS NULL`) verificando que no existan participaciones que apunten a atletas, eventos, sedes o medallas inexistentes.
   - Muestra en verde `[OK] participacion -> atleta: 0 huerfanos`.
3. **Integridad Física de Bloques InnoDB:**
   - Ejecuta `CHECK TABLE` sobre todas las tablas verificando consistencia de árboles B+ e índices.
4. **Diagnóstico de Fragmentación:**
   - Consulta `information_schema.TABLES` y genera el reporte de `espacio_libre_kb` y `% de fragmentación`.

---

## 4. Interpretación de Registros y Logs

El subsistema de restauración genera 3 tipos de bitácoras en la carpeta `Fase2/logs/`:

### 4.1 Bitácora Consolidada de Tiempos (`bitacora_restauracion.csv`)
Archivo en formato CSV con el historial de todas las restauraciones:

```csv
"fecha_hora","ciclo","carga","estrategia","backup_full","backup_diff","duracion_segundos","resultado"
"2026-10-13T22:18:40-06:00","deportista","c0","full","full_20261012_211829","","20.6","OK"
"2026-10-13T23:10:22-06:00","deportista","c1","differential","full_20261012_211829","diff_20261012_212322","35.14","OK"
```
- **duracion_segundos:** Es la métrica clave para el RTO (*Recovery Time Objective*).
- **resultado:** Debe indicar `OK`.

### 4.2 Logs Detallados de XtraBackup (`restore_<nombre>.log`)
Registran la salida estándar de cada comando de Percona XtraBackup. Para verificar que un respaldo terminó exitosamente, abrir el log y comprobar la última línea:
```text
completed OK!
```

### 4.3 Logs de Validación (`validacion_<ciclo>_<carga>_<timestamp>.log`)
Almacenan la auditoría completa generada por `validar-restauracion.ps1 -SaveReport` con la lista de tablas, filas contadas y resultado de claves foráneas.

---

## 5. Solución de Problemas Frecuentes (Troubleshooting)

### Problema 1: El puerto 3307 está ocupado
- **Causa:** Quedó corriendo un contenedor previo o una sesión de MySQL Workbench huérfana.
- **Solución:** Ejecutar en PowerShell:
  ```powershell
  docker stop fase2_mysql_restore
  docker rm -f fase2_mysql_restore
  ```

### Problema 2: Error "Permission denied" al restaurar (/var/lib/mysql)
- **Causa:** La imagen de XtraBackup corre internamente como UID 1001 y no puede escribir en el volumen de Docker montado como root.
- **Solución:** Los scripts `restore-full.ps1` y `restore-differential.ps1` ya incluyen `--user 0:0` en el comando `docker run` y aplican automáticamente `chown -R 999:999` antes de iniciar MySQL.

### Problema 3: Error "binlog.000004\r: No such file or directory"
- **Causa:** En sistemas Windows, Git puede clonar archivos con saltos de línea CRLF (`\r\n`), lo que introduce un retorno de carro invisible `\r` dentro de `binlog.index`.
- **Solución:** La función `New-WorkingCopy` de `_common_restore.ps1` detecta y limpia automáticamente los bytes de retorno de carro (`0x0D`) en todos los archivos de índice de binlogs.

### Problema 4: MySQL Workbench no conecta con la contraseña
- **Causa:** La base de datos restaurada trae los usuarios y contraseñas del backup original.
- **Solución:** El archivo `docker-compose.restore.yml` monta automáticamente `init-restore.sql` con la opción `--init-file=/etc/mysql/init.sql`, forzando el reseteo de la contraseña del usuario `root` a `admin` en cada arranque.
