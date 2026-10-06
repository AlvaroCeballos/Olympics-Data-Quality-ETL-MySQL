# Fase 2 — Respaldos físicos y restauración

Esta carpeta contiene la infraestructura aislada de Fase 2. No modifica Fase 1. El esquema usado es una copia de `Fase1/olimpiada2s.sql` en `ddl/olimpiada2s.sql`; los scripts de carga de Fase 2 deben conectarse a esta instancia, no a la instancia local de Fase 1.

## Componentes

- `docker-compose.yml`: MySQL 8.0 con volumen persistente y XtraBackup 8.0.
- `ddl/olimpiada2s.sql`: copia del DDL de Fase 1; se ejecuta solo al inicializar un volumen vacío.
- `backup/scripts/`: scripts PowerShell para respaldos completos, incrementales y diferenciales.
- `backup/archivos/`: destino de los respaldos físicos; los archivos generados se excluyen de Git.
- `logs/`: logs por ejecución y `backup_manifest.csv` con fecha, estrategia, base, tamaño y resultado.
- `documentacion_tecnica.md` y `manual_usuario.md`: documentación correspondiente a infraestructura/respaldos.
- `guia_ejecucion.md`: flujo de ejecución paso a paso en PowerShell.

## Inicio rápido (PowerShell, desde la raíz del repositorio)

1. Instala Docker Desktop con Docker Compose y asegúrate de que el motor esté iniciado.
2. Crea los archivos locales de configuración:

   ```powershell
   Copy-Item Fase2/.env.example Fase2/.env
   Copy-Item Fase2/backup/xtrabackup.cnf.example Fase2/backup/xtrabackup.cnf
   ```

3. Cambia la contraseña en ambos archivos locales por el mismo valor. No agregues esos archivos a Git.
4. Inicia la instancia:

   ```powershell
   docker compose --project-directory Fase2 --env-file Fase2/.env -f Fase2/docker-compose.yml up -d mysql
   ```

   El primer inicio crea `olimpiadas` y las tablas desde el DDL copiado. La instancia se publica en `127.0.0.1:3307`, para no interferir con MySQL de Fase 1 en el puerto 3306.
5. Ejecuta las cargas definidas por el equipo y toma los respaldos después de cada carga según el plan de `documentacion_tecnica.md`.

El flujo completo y los comandos están en `guia_ejecucion.md`; los comandos resumidos también están en `manual_usuario.md`. `docker compose down` detiene la instancia sin borrar los datos. **No uses `docker compose down -v` para pruebas normales**: elimina el volumen persistente.
