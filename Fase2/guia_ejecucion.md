# Guía de ejecución de Fase 2

Guía para levantar la instancia MySQL de Fase 2, ejecutar las cargas del equipo y tomar respaldos físicos con XtraBackup. Los comandos están escritos para **PowerShell en Windows** y se ejecutan desde la raíz del repositorio.

> Esta guía usa exclusivamente la infraestructura de `Fase2/`. No ejecutes las cargas de Fase 1 contra el puerto `3306`: la instancia de Fase 2 se publica en `127.0.0.1:3307`.

## 1. Requisitos

- Docker Desktop instalado y en ejecución.
- Docker Compose v2 disponible (`docker compose version`).
- PowerShell abierto en la raíz del repositorio.
- Espacio disponible para la base de datos y respaldos.
- Conocer los scripts y el orden de las tres cargas definidos por Integrante 2.

Verifica las herramientas:

```powershell
docker --version
docker compose version
```

La primera ejecución puede descargar las imágenes de MySQL y XtraBackup; se necesita conexión a Internet para ese paso.

## 2. Crear la configuración local

Crear los archivos privados a partir de sus plantillas:

```powershell
Copy-Item Fase2/.env.example Fase2/.env
Copy-Item Fase2/backup/xtrabackup.cnf.example Fase2/backup/xtrabackup.cnf
```

Editar ambos archivos:

```powershell
notepad Fase2/.env
notepad Fase2/backup/xtrabackup.cnf
```

Configura la misma contraseña en ambos archivos. El archivo `.env` define la contraseña inicial de MySQL y el `.cnf` permite que XtraBackup se autentique. No subas los archivos reales al repositorio; están excluidos por `Fase2/.gitignore`.

Si el puerto `3307` ya está ocupado, cambia `MYSQL_PORT` en `Fase2/.env`. Para una contraseña fácil de interpretar por Compose y el archivo CNF, usa un valor local sin espacios ni comillas.

## 3. Validar e iniciar MySQL

Valida la configuración de Compose:

```powershell
docker compose --project-directory Fase2 --env-file Fase2/.env -f Fase2/docker-compose.yml config --quiet
```

Levanta la instancia de una de estas dos formas:

- Doble clic en `Fase2/Start.bat`.
- O ejecuta desde PowerShell, en la raíz del repositorio:

```powershell
docker compose --project-directory Fase2 --env-file Fase2/.env -f Fase2/docker-compose.yml up -d mysql
```

El archivo `.bat` verifica que Docker y `.env` estén disponibles. XtraBackup no queda levantado como servicio permanente: los scripts PowerShell lo ejecutan cuando solicitas un respaldo.

Consulta su estado y, si no está listo, revisa los logs:

```powershell
docker compose --project-directory Fase2 --env-file Fase2/.env -f Fase2/docker-compose.yml ps
docker compose --project-directory Fase2 --env-file Fase2/.env -f Fase2/docker-compose.yml logs mysql
```

La primera vez que se crea el volumen vacío, Docker ejecuta `Fase2/ddl/olimpiada2s.sql` y crea el esquema. Puedes comprobarlo con:

```powershell
docker compose --project-directory Fase2 --env-file Fase2/.env -f Fase2/docker-compose.yml exec mysql mysql -uroot -p -e "USE olimpiadas; SHOW TABLES;"
```

Escribe la contraseña local cuando MySQL la solicite. Desde los scripts de carga o un cliente instalado en Windows, usa estos parámetros:

| Parámetro | Valor |
|---|---|
| Host | `127.0.0.1` |
| Puerto | `3307` o el valor configurado en `MYSQL_PORT` |
| Usuario | `root` |
| Contraseña | La definida en `Fase2/.env` |
| Base de datos | `olimpiadas` |

El DDL de Fase 1 tiene una copia en Fase 2, pero los scripts de Fase 1 no se copian ni se ejecutan automáticamente. Integrante 2 debe ejecutar sus cargas de Fase 2 apuntando a la conexión anterior.

## 4. Ejecutar las cargas y respaldar cada estado

Si PowerShell impide ejecutar los `.ps1`, habilita scripts para esta sesión solamente:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

Coordina con Integrante 2 y sigue el orden de cargas acordado. **Después de que cada carga termine correctamente**, toma su respaldo:

| Momento | Respaldo | Comando |
|---|---|---|
| Después de la carga 1 | Completo, base de la cadena | `backup-full.ps1` |
| Después de la carga 2 | Incremental sobre el backup válido más reciente | `backup-incremental.ps1` |
| Después de la carga 3 | Incremental sobre el incremental anterior | `backup-incremental.ps1` |

Ejecuta los comandos individualmente desde la raíz del repositorio:

```powershell
.\Fase2\backup\scripts\backup-full.ps1
.\Fase2\backup\scripts\backup-incremental.ps1
.\Fase2\backup\scripts\backup-incremental.ps1
```

No ejecutes las tres líneas seguidas sin hacer las cargas entre ellas. El respaldo debe representar el estado posterior a la carga correspondiente.

Al ejecutar por primera vez, Docker puede mostrar `Extracting` y `Pull complete`: eso indica que está descargando la imagen, todavía no que hizo el backup. El respaldo se confirma cuando XtraBackup termina sin error, el script muestra `Respaldo completo terminado`, aparece el directorio `full_*` con `.xtrabackup_checkpoints` y el manifiesto registra `OK`. Si aparece `ERROR` o el script termina con código distinto de cero, no cuentes esa ejecución como respaldo exitoso.

### Ensayo de estrategia diferencial

Para comparar estrategias, conserva el full de referencia y, después de una carga elegida, ejecuta:

```powershell
.\Fase2\backup\scripts\backup-differential.ps1
```

El script diferencial toma como base el full más reciente. No es un eslabón de la cadena incremental: anota por separado en la bitácora qué full y qué carga representa cada diferencial.

## 5. Revisar y registrar los respaldos

Los scripts guardan los archivos en `Fase2/backup/archivos/`, con nombres que incluyen tipo y fecha/hora. Para listar carpetas de respaldo:

```powershell
Get-ChildItem Fase2/backup/archivos -Directory | Sort-Object LastWriteTime
```

Cada ejecución también produce:

- Un log individual `Fase2/logs/backup_<nombre>.log`.
- Una fila en `Fase2/logs/backup_manifest.csv` con fecha/hora, tipo, base usada, tamaño en bytes y resultado.

Consultar el manifiesto:

```powershell
Import-Csv Fase2/logs/backup_manifest.csv | Format-Table
```

Después de cada respaldo, verifica que el comando termine sin error, que el manifiesto indique `OK` y que exista `.xtrabackup_checkpoints` en la carpeta generada:

```powershell
Get-ChildItem Fase2/backup/archivos -Force -Recurse -Filter .xtrabackup_checkpoints
```

Guarda la captura o evidencia de fecha/hora, tamaño y resultado junto con la validación de datos posterior a esa carga. No subas los archivos físicos de backup a Git.

## 6. Apagar y volver a iniciar

Apaga sin eliminar la base de datos ni el volumen de una de estas dos formas:

- Doble clic en `Fase2/stop.bat`.
- O ejecuta desde PowerShell, en la raíz del repositorio:

```powershell
docker compose --project-directory Fase2 --env-file Fase2/.env -f Fase2/docker-compose.yml down
```

El archivo `.bat` ejecuta `docker compose down` sin `-v`; por eso conserva los datos.

Para continuar otro día, vuelve a ejecutar `up -d mysql` como en el paso 3. El volumen Docker conserva los datos.

> **Advertencia:** `docker compose down -v` elimina el volumen de MySQL. Úsalo solo para reiniciar el laboratorio desde cero, con autorización del equipo y después de conservar las evidencias necesarias. No lo uses durante las pruebas de restauración.

## 7. Alcance de la restauración

Esta guía cubre infraestructura y toma de respaldos. La preparación, restauración física, cronometraje y validación corresponden a Integrante 3 y se deben ejecutar en un entorno controlado, no sobre la instancia que contiene la carga original.
