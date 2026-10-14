# Documentación técnica — infraestructura y respaldos (Integrante 1)

**Autor:** Ottoniel Fabricio Vásquez Pineda — 202307820 (Integrante 1)  
**Curso:** Sistemas de Bases de Datos 2, USAC  
**Grupo:** 18  

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
| Sistema operativo anfitrión | Microsoft Windows 11 Pro (NT Kernel 10.0.26200) |
| CPU asignada al motor Docker | 12 vCPUs (`docker info`) |
| Memoria asignada al motor Docker | 7.44 GB / 7,987,216,384 bytes (`docker info`) |
| Almacenamiento disponible para `Fase2/backup/archivos` | Unidad `D:` con 158.03 GB libres |
| Imagen/versión MySQL resuelta | `mysql:8.0` (Image ID: `7dcddc01f13b`, 1.10 GB) |
| Imagen/versión XtraBackup resuelta | `percona/percona-xtrabackup:8.0` (Image ID: `368c3429c4cc`, 2.02 GB) |

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

XtraBackup registra LSN y checkpoints. El nombre de carpeta incluye fecha/hora `yyyyMMdd_HHmmss`; los logs individuales y `logs/backup_manifest.csv` guardan la fecha, estrategia, backup base, tamaño en bytes y resultado. Después de cada estado de carga, conserva las capturas de conteos/validaciones correspondientes y anota qué backup representa ese estado.

## Credenciales y seguridad

Crear `Fase2/.env` a partir de `.env.example` y `Fase2/backup/xtrabackup.cnf` a partir de `backup/xtrabackup.cnf.example`; usar la misma contraseña en ambos. Los archivos reales están excluidos de Git. Esta configuración usa `root` solo para el entorno local de laboratorio: no exponer el puerto fuera de `127.0.0.1` ni reutilizar esta configuración en producción.

## Restauración e integración

La restauración física se coordina con Integrante 3. El backup contiene el directorio de datos de la instancia MySQL, no un archivo SQL individual de `olimpiadas`. Para restaurar, detener MySQL, preparar/combinar la cadena en orden y copiar el backup preparado a un directorio de datos vacío usando una versión compatible de MySQL/XtraBackup. Integrante 3 debe registrar comandos, tiempos y validaciones en sus scripts y evidencias.

Para restaurar un diferencial, Integrante 3 debe preparar el full con `--apply-log-only`, aplicar el diferencial elegido con `--incremental-dir` y finalizar la preparación del full. No ejecutar `--copy-back` sobre un directorio de datos activo ni borrar el volumen compartido sin coordinar la prueba.
