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

Tomar un punto recuperable después de cada carga acordada con Integrante 2. Para tres cargas, la cadena propuesta es:

1. Después de la primera carga: un respaldo completo (`full_*`).
2. Después de la segunda: un incremental (`inc_*`) basado en el último backup válido.
3. Después de la tercera: otro incremental basado en el incremental anterior.

El script diferencial también está disponible para la comparación: cada diferencial se basa en el último completo, no en el diferencial anterior. No mezclar cadenas al documentar la restauración. Un incremental exige el full y todos los incrementales previos de la cadena; para recuperar con un diferencial se usa el full y el diferencial más reciente que se quiera restaurar.

XtraBackup registra LSN y checkpoints. El nombre de carpeta incluye fecha/hora `yyyyMMdd_HHmmss`; los logs individuales y `logs/backup_manifest.csv` guardan la fecha, estrategia, backup base, tamaño en bytes y resultado. Después de cada carga, el equipo debe conservar las capturas de conteos/validaciones correspondientes y anotar qué backup representa ese estado.

## Credenciales y seguridad

Crear `Fase2/.env` a partir de `.env.example` y `Fase2/backup/xtrabackup.cnf` a partir de `backup/xtrabackup.cnf.example`; usar la misma contraseña en ambos. Los archivos reales están excluidos de Git. Esta configuración usa `root` solo para el entorno local de laboratorio: no exponer el puerto fuera de `127.0.0.1` ni reutilizar esta configuración en producción.

## Restauración e integración

La restauración física se coordina con Integrante 3. El backup contiene el directorio de datos de la instancia MySQL, no un archivo SQL individual de `olimpiadas`. Para restaurar, detener MySQL, preparar/combinar la cadena en orden y copiar el backup preparado a un directorio de datos vacío usando una versión compatible de MySQL/XtraBackup. Integrante 3 debe registrar comandos, tiempos y validaciones en sus scripts y evidencias.

Para una cadena incremental, XtraBackup prepara el full con `--apply-log-only`, aplica cada incremental en orden con `--incremental-dir` y finaliza la preparación del último paso sin `--apply-log-only`. Para diferencial se aplica solo el diferencial elegido al full. No ejecutar `--copy-back` sobre un directorio de datos activo ni borrar el volumen compartido sin coordinar la prueba.
