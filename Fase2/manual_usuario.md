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
# Respaldo completo: crear una nueva base de la cadena
.\Fase2\backup\scripts\backup-full.ps1

# Incremental: usa el full/incremental válido más reciente como base
.\Fase2\backup\scripts\backup-incremental.ps1

# Diferencial: siempre usa el respaldo full válido más reciente
.\Fase2\backup\scripts\backup-differential.ps1
```

Estrategia propuesta para tres cargas: ejecutar `backup-full.ps1` tras la primera, y `backup-incremental.ps1` tras cada carga siguiente. Para ensayar diferencial, partir de un full y ejecutar `backup-differential.ps1` tras la carga que se quiera comparar. No se deben ejecutar incremental y diferencial como si fueran una misma cadena.

## Archivos generados y verificación

- Backups físicos: `Fase2/backup/archivos/full_*`, `inc_*` o `diff_*`.
- Log de cada ejecución: `Fase2/logs/backup_<nombre>.log`.
- Registro acumulado de fecha, estrategia, base y tamaño: `Fase2/logs/backup_manifest.csv`.

Verificar que cada ejecución finalice con código cero, que exista `.xtrabackup_checkpoints` dentro del directorio generado y que el manifiesto tenga una fila con resultado `OK`. Registrar también fecha/hora visible y el tamaño del respaldo para la evidencia solicitada.

## Apagar sin perder datos

```powershell
docker compose --project-directory Fase2 --env-file Fase2/.env -f Fase2/docker-compose.yml down
```

Este comando conserva el volumen y los backups. Eliminar el volumen solo para reiniciar el laboratorio desde cero y con autorización del equipo:

```powershell
docker compose --project-directory Fase2 --env-file Fase2/.env -f Fase2/docker-compose.yml down -v
```

`down -v` elimina los datos de MySQL del laboratorio. No usarlo durante la validación de restauraciones ni si hay datos que deban conservarse. Los pasos y scripts de restauración se documentan por separado por Integrante 3.
