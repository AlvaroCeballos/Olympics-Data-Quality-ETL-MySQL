# Documentación técnica — infraestructura y respaldos (Integrante 1)

## Alcance

La infraestructura de Fase 2 vive en esta carpeta y mantiene intacta Fase 1. Se copia el esquema desde `Fase1/olimpiada2s.sql` a `Fase2/ddl/olimpiada2s.sql` para que la instancia de respaldo sea reproducible sin depender de ejecutar scripts desde otra carpeta. Las cargas de Fase 2 se deben conectar a la instancia Docker de esta fase.

## Motor y herramienta

- **Motor:** MySQL 8.0, con tablas InnoDB según el DDL del proyecto.
- **Herramienta:** Percona XtraBackup 8.0, respaldo físico en línea de InnoDB; no se generan dumps SQL.
- **Ejecución:** Docker Compose en Docker Desktop (Windows como anfitrión; contenedores Linux).
- **Persistencia de datos:** volumen Docker `fase2_olimpiadas_mysql_data`, montado en `/var/lib/mysql`.
- **Destino de backups:** `Fase2/backup/archivos/` en el anfitrión, montado como `/backups` en el contenedor de XtraBackup.
- **Puerto de desarrollo:** `127.0.0.1:3307` en el anfitrión hacia el puerto `3306` del contenedor, para evitar colisión con Fase 1.

La configuración usa las etiquetas de imagen `mysql:8.0` y `percona/percona-xtrabackup:8.0`. Antes de entregar las evidencias, registrar las versiones exactas resueltas en Docker (`docker compose images`) y comprobar que el respaldo/restauración funciona con esas versiones. No actualizar una imagen entre la toma del backup y su restauración.

## Especificaciones del servidor

El servidor de base de datos es el contenedor MySQL ejecutado por Docker Desktop. CPU, RAM y almacenamiento disponibles dependen del equipo anfitrión y de los límites asignados a Docker Desktop; no se fijan aquí valores que no se han medido. Completar esta tabla en el equipo donde se tomarán las evidencias:

| Recurso | Valor medido |
|---|---|
| Sistema operativo anfitrión | Windows (registrar edición y versión) |
| CPU asignada al motor Docker | Registrar salida de `docker info` |
| Memoria asignada al motor Docker | Registrar salida de `docker info` |
| Almacenamiento disponible para `Fase2/backup/archivos` | Registrar unidad y espacio libre |
| Imagen/versión MySQL resuelta | Registrar salida de `docker compose images` |
| Imagen/versión XtraBackup resuelta | Registrar salida de `docker compose images` |

Comandos de referencia en PowerShell:

```powershell
docker info
docker compose --project-directory Fase2 --env-file Fase2/.env -f Fase2/docker-compose.yml images
Get-PSDrive
```

## Plan de respaldo

El procedimiento de Integrante 2 define tres ciclos independientes: deportista, deporte y año. Cada ciclo empieza en una instancia vacía y tiene cuatro estados de carga: `c0` (catálogos), seguida de las rondas `c1`, `c2` y `c3`. El plan de Integrante 1 para cada ciclo es:

1. Después de `00_catalogos.sql` (`c0`): un respaldo completo (`full_*`).
2. Después de cada ronda (`c1`, `c2` y `c3`): un respaldo diferencial (`diff_*`) basado en el full de ese ciclo.

En total son 12 respaldos requeridos: 3 completos y 9 diferenciales. Se reinicia el volumen de la base entre los tres ciclos siguiendo el procedimiento de Integrante 2; los backups de `/backups` están en una carpeta del anfitrión y no se eliminan con el volumen MySQL. El script diferencial usa el full más reciente, por lo que se debe crear un full nuevo después de cada reinicio antes de ejecutar diferenciales.

El plan operativo de esta entrega utiliza solo respaldos completos y diferenciales. Para recuperar un estado, se usa el full del ciclo y el diferencial correspondiente a ese estado. El manifiesto conserva un registro histórico de una ejecución incremental de prueba anterior al cambio de estrategia; no forma parte de los respaldos requeridos.

XtraBackup registra LSN y checkpoints. Los respaldos nuevos se generan con compresión Zstandard (`--compress`, nivel 3) y cifrado AES-256; cada carpeta conserva los archivos comprimidos/cifrados de XtraBackup. El nombre de carpeta incluye fecha/hora `yyyyMMdd_HHmmss`; los logs individuales y `logs/backup_manifest.csv` guardan la fecha, estrategia, backup base, tamaño en bytes, compresión, cifrado y resultado. Al primer registro después de esta actualización, el manifiesto agrega las columnas de protección y conserva las filas históricas, marcándolas como `none (historico)`, porque esos respaldos anteriores no estaban protegidos.

## Credenciales, cifrado y seguridad

Crear `Fase2/.env` a partir de `.env.example` y `Fase2/backup/xtrabackup.cnf` a partir de `backup/xtrabackup.cnf.example`; usar la misma contraseña en ambos. Generar una clave AES-256 local con `Fase2/backup/scripts/generate-backup-encryption-key.ps1`. Los archivos reales (`.env`, CNF y clave) están excluidos de Git. Proteger la clave y compartirla con Integrante 3 por un canal privado distinto al de los archivos de backup: sin ella no se pueden restaurar los nuevos respaldos. Los archivos creados antes de activar cifrado siguen en texto claro y no se cifran retroactivamente.

Esta configuración usa `root` solo para el entorno local de laboratorio: no exponer el puerto fuera de `127.0.0.1` ni reutilizar esta configuración en producción.

## Programación automática

`backup/backup.crontab.example` ofrece una política de ejemplo para cron en Linux/WSL con PowerShell 7 (`pwsh`) y Docker Compose: full semanal el domingo a las 02:00 y diferenciales de lunes a sábado a las 02:00. Se debe reemplazar `FASE2_ROOT` por la ruta absoluta real e instalar el contenido con `crontab`. La programación no se instala ni activa automáticamente; requiere que cron, Docker Desktop, Docker Compose y `pwsh` estén disponibles en WSL. No habilitarla durante los tres ciclos `c0`-`c3`, porque generaría respaldos adicionales fuera de los estados coordinados con Integrante 2. En Windows nativo se puede usar el Programador de tareas con los mismos scripts PowerShell.

## Restauración e integración

La restauración física se coordina con Integrante 3. Los respaldos creados antes de esta actualización se preparan directamente; los nuevos requieren primero descifrado AES-256 y descompresión ZSTD. Copiar cada respaldo a un directorio de trabajo (no modificar el original), ejecutar XtraBackup con `--decrypt=AES256 --encrypt-key-file=/tmp/backup-encryption.key --target-dir=<copia>` y después `--decompress --target-dir=<copia>`. El entrypoint de Docker prepara la clave en `/tmp`; la ruta del keyfile solo aplica dentro del contenedor. Luego se prepara/combina la cadena y se copia el backup preparado a un datadir vacío con versiones compatibles de MySQL/XtraBackup. Integrante 3 debe registrar comandos, tiempos y validaciones en sus scripts y evidencias.

Para restaurar un diferencial, Integrante 3 debe preparar el full con `--apply-log-only`, aplicar el diferencial elegido con `--incremental-dir` y finalizar la preparación del full. Descifrar y descomprimir el full y el diferencial elegidos antes de prepararlos. No ejecutar `--copy-back` sobre un directorio de datos activo ni borrar el volumen compartido sin coordinar la prueba.
