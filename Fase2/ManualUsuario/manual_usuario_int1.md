# Manual de usuario — respaldos (Integrante 1)

## Requisitos

- Windows con Docker Desktop instalado y el motor iniciado.
- Docker Compose v2.
- PowerShell.
- Espacio libre para el volumen MySQL y los respaldos en `Fase2/backup/archivos/`.

## Preparación inicial

Ejecutar desde la raíz del repositorio:

```powershell
Copy-Item Fase2/.env.example Fase2/.env
Copy-Item Fase2/backup/xtrabackup.cnf.example Fase2/backup/xtrabackup.cnf
```

Editar ambos archivos y asignar **la misma contraseña local**. No compartir ni versionar los archivos reales. En `Fase2/.env` se puede cambiar `MYSQL_PORT` si el puerto 3307 ya está ocupado; conservar el puerto de contenedor 3306.

Iniciar la instancia de Fase 2:

```powershell
docker compose --project-directory Fase2 --env-file Fase2/.env -f Fase2/docker-compose.yml up -d mysql
docker compose --project-directory Fase2 --env-file Fase2/.env -f Fase2/docker-compose.yml ps
```

El DDL se ejecuta automáticamente solo la primera vez que se crea el volumen vacío. Para conectarse desde un cliente MySQL, usar host `127.0.0.1`, puerto `3307` (o el definido en `.env`), usuario `root` y la contraseña local.

## Ejecutar respaldos

Si PowerShell bloquea la ejecución de scripts, permitirlos solo en la sesión actual:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

Ejecutar desde la raíz del repositorio, después de la carga correspondiente:

```powershell
# Después de 00_catalogos.sql (c0), una vez por cada ciclo
.\Fase2\backup\scripts\backup-full.ps1

# Después de cada ronda c1, c2 y c3, en cada ciclo
.\Fase2\backup\scripts\backup-differential.ps1
```

El flujo acordado con Integrante 2 tiene tres ciclos independientes: deportista, deporte y año. En cada ciclo se ejecuta primero `00_catalogos.sql` y después sus rondas `01`, `02` y `03`. Tras los catálogos (`c0`), ejecuta `backup-full.ps1`; después de cada ronda (`c1`, `c2`, `c3`), ejecuta `backup-differential.ps1`. Repite el ciclo en una instancia vacía según `Fase2/evidencias/PASOS.md`. En total se esperan 3 completos y 9 diferenciales.

El flujo vigente usa solo completos y diferenciales. En el manifiesto puede aparecer un registro incremental histórico de una prueba anterior; no lo uses como parte de la cadena diferencial.

## Archivos generados y verificación

- Backups del plan vigente: `Fase2/backup/archivos/full_*` y `diff_*`.
- Se conserva una carpeta `inc_*` de una prueba histórica previa; no forma parte del plan vigente.
- Log de cada ejecución: `Fase2/logs/backup_<nombre>.log`.
- Registro acumulado de fecha, estrategia, base y tamaño: `Fase2/logs/backup_manifest.csv`.

Verificar que cada ejecución finalice con código cero, que exista `xtrabackup_checkpoints` dentro del directorio generado y que el manifiesto tenga una fila con resultado `OK`. Registrar también fecha/hora visible y el tamaño del respaldo para la evidencia solicitada.

## Apagar sin perder datos

```powershell
docker compose --project-directory Fase2 --env-file Fase2/.env -f Fase2/docker-compose.yml down
```

Este comando conserva el volumen y los backups. Eliminar el volumen solo para reiniciar el laboratorio desde cero y con autorización del equipo:

```powershell
docker compose --project-directory Fase2 --env-file Fase2/.env -f Fase2/docker-compose.yml down -v
```

`down -v` elimina los datos de MySQL del laboratorio. No usarlo durante la validación de restauraciones ni si hay datos que deban conservarse. Los pasos y scripts de restauración se documentan por separado por Integrante 3.
