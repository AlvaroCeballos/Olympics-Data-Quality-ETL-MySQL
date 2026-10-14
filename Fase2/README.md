# Proyecto Fase 2 — Respaldos Físicos, Carga y Restauración ante Desastres

**Universidad de San Carlos de Guatemala**  
**Facultad de Ingeniería — Escuela de Ciencias y Sistemas**  
**Sistemas de Bases de Datos 2 — 2do Semestre 2026**  
**Grupo 18**

| Integrante | Carnet | Rol Principal |
|---|---|---|
| **Ottoniel Fabricio Vásquez Pineda** | 202307820 | Integrante 1 (Infraestructura y Respaldos Físicos) |
| **Yulianne Nicole López Elias** | 202300659 | Integrante 2 (Modelado E-R, Cargas y Fragmentación) |
| **Álvaro Gabriel Ceballos Gil** | 202300673 | Integrante 3 (Restauración, Auditoría y Consolidación) |

---


## 1. Estructura Organizada del Repositorio

El directorio `Fase2/` ha sido estructurado de manera modular y profesional para facilitar la evaluación y la navegación:

```text
Fase2/
├── DOCUMENTACION_TECNICA_FINAL.md    <- DOCUMENTO TÉCNICO UNIFICADO DEL GRUPO (Rúbrica 1.1)
├── MANUAL_USUARIO_FINAL.md           <- MANUAL DE USUARIO UNIFICADO DEL GRUPO (Rúbrica 1.2)
├── README.md                         <- Guía rápida y paso a paso para la calificación en vivo
├── Start.bat / stop.bat              <- Accesos directos para iniciar/detener MySQL en Windows
├── docker-compose.yml                <- Definición del contenedor de producción (Int 1 y 2)
│
├── DocumentacionTecnica/             <- Evidencia individual de documentación técnica
│   ├── documentacion_tecnica_int1.md <- Infraestructura, servidor y respaldos (Int 1)
│   ├── documentacion_tecnica_int2.md <- Modelo E-R, cargas y fragmentación (Int 2)
│   └── documentacion_tecnica_int3.md <- Restauración, RTO y análisis comparativo (Int 3)
│
├── ManualUsuario/                    <- Evidencia individual de manuales de usuario
│   ├── manual_usuario_int1.md        <- Guía de respaldos físicos (Int 1)
│   ├── manual_usuario_int2.md        <- Guía de cargas masivas y validación (Int 2)
│   └── manual_usuario_int3.md        <- Guía de restauración y auditoría de integridad (Int 3)
│
├── ddl/                              <- Scripts DDL de base de datos
│   └── olimpiada2s.sql               <- Esquema relacional 3NF de 12 tablas en InnoDB
│
├── carga/                            <- Scripts de carga masiva de datos (Int 2)
│   ├── 00_catalogos.sql              <- Dimensiones fijas (C0 - 41,399 filas)
│   ├── deportista/                   <- Rondas C1, C2, C3 (Usain Bolt)
│   ├── deporte/                      <- Rondas C1, C2, C3 (100m Femenino)
│   └── anio/                         <- Rondas C1, C2, C3 (Ediciones completas)
│
├── backup/                           <- Infraestructura de respaldos físicos (Int 1)
│   ├── scripts/                      <- backup-full.ps1 y backup-differential.ps1
│   ├── archivos/                     <- Directorio de los 12 respaldos físicos XtraBackup
│   └── xtrabackup.cnf                <- Credenciales de XtraBackup para el contenedor
│
├── restauracion/                     <- Scripts de recuperación y auditoría (Int 3)
│   ├── docker-compose.restore.yml    <- Contenedor aislado (fase2_mysql_restore) en puerto 3307
│   ├── restore-full.ps1              <- Restauración física de backups completos
│   ├── restore-differential.ps1      <- Restauración física de backups diferenciales
│   ├── validar-restauracion.ps1      <- Auditor automatizado (censo, 0 huérfanos, fragmentación)
│   ├── restaurar-y-validar-todo.ps1  <- Orquestador maestro para demostración guiada
│   └── generar_graficas.py           <- Generador de gráficos analíticos de RTO (300 DPI)
│
├── logs/                             <- Bitácoras de ejecución y auditoría
│   ├── backup_manifest.csv           <- Registro oficial de los 12 respaldos físicos
│   ├── bitacora_restauracion.csv     <- Tiempos cronometrados de restauración física
│   └── *.log                         <- Salidas detalladas de XtraBackup y auditorías
│
└── evidencias/                       <- Capturas de pantalla con reloj visible del SO
    ├── deportista/                   <- 16 capturas (post-carga y post-restauración)
    ├── deporte/                      <- 16 capturas (post-carga y post-restauración)
    ├── anio/                         <- 16 capturas (post-carga y post-restauración)
    └── graficos/                     <- 4 gráficos analíticos de rendimiento comparativo
```

---

## 2. Guía Paso a Paso para Demostración de Calificación (Restauración en Vivo)

Esta sección describe el flujo exacto de comandos para **demostrar todo lo solicitado en la calificación de la etapa de restauración física y validación**.

### Paso 0: Preparación Rápida de la Consola
1. Asegurarse de que **Docker Desktop** esté iniciado.
2. Abrir **PowerShell** en la raíz del proyecto (`.../SBD2B_PROYECT1_2S2026_G18`) y habilitar ejecución de scripts:
   ```powershell
   Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
   ```

---

### Paso 1: Demostrar Restauración de un Respaldo Completo (Full — C0)

Para demostrar cómo se recupera la base limpia de catálogos:

```powershell
.\Fase2\restauracion\restore-full.ps1 -Ciclo deportista
```

**Puntos a explicar al evaluador:**
- El script no toca el volumen de producción del equipo; opera sobre el contenedor aislado `fase2_mysql_restore` y el volumen temporal `fase2_restore_mysql_data`.
- Trabaja sobre una copia temporal en `_restore_work`, protegiendo los backups originales de cualquier corrupción.
- Ejecuta `xtrabackup --prepare`, luego `--copy-back` con permisos Linux `chown 999:999` y levanta MySQL en el puerto `3307`.
- El tiempo se cronometró automáticamente con `Stopwatch` (~20.6 segundos).

**Validar inmediatamente la integridad en consola:**
```powershell
.\Fase2\restauracion\validar-restauracion.ps1 -Ciclo deportista -Carga c0
```
- **Resultado mostrado:** 0 atletas, 0 participaciones, 41,399 filas de catálogos y **0 claves foráneas huérfanas**.

---

### Paso 2: Demostrar Restauración de un Respaldo Diferencial (C1, C2 o C3)

Para demostrar la recuperación de un estado con alta volumetría (ejemplo: ciclo **Año**, ronda **C3 — París 2024** con más de 30,000 atletas):

```powershell
.\Fase2\restauracion\restore-differential.ps1 -Ciclo anio -Ronda c3
```

**Puntos a explicar al evaluador sobre la cadena XtraBackup:**
1. **Fase 1:** Prepara el Full base con `--apply-log-only` (aplica redo log sin rollback).
2. **Fase 2:** Aplica las páginas delta del diferencial con `--incremental-dir`.
3. **Fase 3:** Ejecuta la pasada final de consistencia y rollback de transacciones abiertas.
4. **Fase 4:** Realiza el `copy-back` hacia `/var/lib/mysql`.

**Auditar en consola con reporte guardado:**
```powershell
.\Fase2\restauracion\validar-restauracion.ps1 -Ciclo anio -Carga c3 -SaveReport
```
- **Resultado mostrado:**
  - `[OK] atleta: 30648 / 30648`
  - `[OK] participacion: 44581 / 44581`
  - Total de filas en base de datos: **116,628**.
  - **7 verificaciones de integridad referencial aprobadas con 0 huérfanos**.
  - Diagnóstico de fragmentación y salud de tablas InnoDB.

---

### Paso 3: Demostración Guiada e Interactiva con MySQL Workbench

Si el evaluador solicita ver la base restaurada en vivo dentro de **MySQL Workbench**:

1. Ejecutar el orquestador con pausa para capturas:
   ```powershell
   .\Fase2\restauracion\restaurar-y-validar-todo.ps1 -Ciclo deporte -PausarParaCapturas
   ```
2. Al terminar cada etapa, la consola pausará diciendo: `Presiona [ENTER] para continuar...`.
3. Abrir **MySQL Workbench** y conectarse a:
   - **Host:** `127.0.0.1`
   - **Puerto:** `3307`
   - **Usuario:** `root`
   - **Contraseña:** `admin` (la configurada en `.env`)
4. Abrir y ejecutar `Fase2/validacion.sql` para mostrar en pantalla las dos grillas:
   - **Censo de Filas** (coincidencia exacta).
   - **Fragmentación** (`DATA_FREE` y `% de fragmentación`).
5. Presionar `Enter` en PowerShell para avanzar a la siguiente ronda.

---

### Paso 4: Demostración de Bitácoras de Tiempo y RTO

Mostrar al evaluador que todos los tiempos fueron registrados automáticamente por código:

```powershell
Get-Content Fase2/logs/bitacora_restauracion.csv
```

**Valores medidos en laboratorio:**
* **Respaldos Full (C0):** `~18.9 s` a `20.6 s` (tiempo base de preparación InnoDB).
* **Respaldos Diferenciales (C1 - C3):** `~33.0 s` a `35.9 s` (debido a las 3 pasadas de preparación requeridas por XtraBackup).

---

### Paso 5: Demostración de los Gráficos Analíticos de Rendimiento

Para mostrar los gráficos generados en alta resolución:

```powershell
# Abrir la carpeta de gráficos en el explorador de Windows:
explorer.exe Fase2\evidencias\graficos
```

O volver a generarlos en cualquier momento ejecutando:
```powershell
python Fase2/restauracion/generar_graficas.py
```

Los 4 gráficos generados son:
1. `tiempos_restauracion_por_ciclo.png`: Tiempos de recuperación por ciclo y carga.
2. `tamano_backup_vs_tiempo_recuperacion.png`: Relación tamaño vs tiempo (meseta de InnoDB).
3. `crecimiento_tamano_respaldo_por_ciclo.png`: Crecimiento de MB en disco ronda por ronda.
4. `comparativa_diferencial_vs_incremental.png`: Evaluación de RTO y resiliencia ante SPOF.

---

### Paso 6: Detener el Contenedor de Restauración al Finalizar

Para liberar el puerto 3307 y apagar el entorno de restauración:

```powershell
docker compose -f Fase2/restauracion/docker-compose.restore.yml down
```

*(Si se desea conservar los datos restaurados para consultas posteriores, simplemente dejar el contenedor encendido).*
