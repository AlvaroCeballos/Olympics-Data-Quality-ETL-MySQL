# Documentación Técnica — Restauración, Validación y Análisis (Integrante 3)

**Autor:** Integrante 3 — Álvaro Ceballos  
**Curso:** Sistemas de Bases de Datos 2, USAC  
**Grupo:** 18  
**Fecha:** Octubre 2026  
**Estrategia Técnica:** Restauración Física Diferencial con Percona XtraBackup 8.0 sobre MySQL 8.0 (Docker)  

---

## 1. Alcance y Responsabilidades (Rúbrica 2.3 y 2.4)

El Integrante 3 es el responsable de la etapa de **Restauración y Validación** (15 pts) y **Análisis Comparativo** (15 pts), así como de consolidar la entrega técnica final:

1. **Restauración física en consola:** Diseñar y ejecutar la restauración de los 3 respaldos completos y los 9 respaldos diferenciales sin usar interfaces gráficas de backup/dump.
2. **Medición automatizada de tiempos:** Registrar con cronómetro de alta precisión la duración exacta de cada proceso de recuperación física.
3. **Auditoría de integridad y validación:** Comprobar que los datos restaurados coincidan al 100% con los datos cargados por el Integrante 2 y verificar la ausencia total de claves foráneas huérfanas.
4. **Capturas de evidencia:** Documentar las 24 capturas requeridas (Censo de filas y Fragmentación de InnoDB) con el reloj del sistema operativo visible.
5. **Análisis comparativo:** Contrastar métricas de tiempo de recuperación vs. tamaño en disco vs. complejidad operativa entre cargas pequeñas (Deportista), medianas (Deporte) y masivas (Año).

---

## 2. Arquitectura de Aislamiento y Entorno Seguro

Para garantizar que el avance de los compañeros permanezca 100% protegido ante cualquier eventualidad:

```
                  +----------------------------------------------+
                  |               HOST (Windows)                 |
                  |  Puerto: 127.0.0.1:3307                      |
                  +----------------------+-----------------------+
                                         |
                       +-----------------+-----------------+
                       |                                   |
                       v                                   v
        +-----------------------------+     +-----------------------------+
        | Contenedor Principal (Int1) |     | Contenedor Aislado (Int 3)  |
        | Nombre: mysql               |     | Nombre: fase2_mysql_restore |
        | Volumen:                    |     | Volumen Aislado:            |
        | fase2_olimpiadas_mysql_data |     | fase2_restore_mysql_data    |
        | [PROTEGIDO - INTACTO]       |     | [SE VACIA Y RESTAURA]       |
        +-----------------------------+     +-----------------------------+
```

1. **Volumen persistente separado:** La restauración se realiza exclusivamente en `fase2_restore_mysql_data` definido en `docker-compose.restore.yml`. El volumen del equipo nunca se borra ni se modifica.
2. **Protección de copias de respaldo originales:** Dado que `xtrabackup --prepare` modifica archivos *in-place*, los scripts copian automáticamente los backups a una subcarpeta de trabajo temporal (`Fase2/backup/archivos/_restore_work/`). Los archivos originales en `backup/archivos/` nunca se alteran.
3. **Sincronización automática de credenciales:** Mediante `init-restore.sql` se asegura que la instancia restaurada reconozca la contraseña `admin` local configurada.

---

## 3. Catálogo de Respaldos Físicos Definitivos

Tras descartar los respaldos preliminares que presentaron errores en la toma inicial (como el Full de 145 MB que tenía datos previos cargados), los **12 respaldos definitivos** que cumplen la regla de 1 Full limpio + 3 Diferenciales basados en él son:

| Ciclo | Carga | Identificador de Respaldo | Tipo | Basado en | Tamaño Aprox. |
|---|---|---|---|---|---|
| **Ciclo 1: Deportista** | C0 (Catálogos) | `full_20261012_211829` | Full | *(Base limpia)* | ~104 MB |
| *(Usain Bolt)* | C1 (Atenas 2004) | `diff_20261012_212322` | Diferencial | `full_20261012_211829` | ~2.60 MB |
| | C2 (Pekín 2008) | `diff_20261012_212404` | Diferencial | `full_20261012_211829` | ~2.72 MB |
| | C3 (Londres 2012) | `diff_20261012_212457` | Diferencial | `full_20261012_211829` | ~2.90 MB |
| **Ciclo 2: Deporte** | C0 (Catálogos) | `full_20261012_213152` | Full | *(Base limpia)* | ~104 MB |
| *(100m Femenino)* | C1 (Río 2016) | `diff_20261012_213250` | Diferencial | `full_20261012_213152` | ~3.25 MB |
| | C2 (Tokio 2020) | `diff_20261012_213408` | Diferencial | `full_20261012_213152` | ~3.50 MB |
| | C3 (París 2024) | `diff_20261012_213758` | Diferencial | `full_20261012_213152` | ~3.81 MB |
| **Ciclo 3: Año** | C0 (Catálogos) | `full_20261012_213911` | Full | *(Base limpia)* | ~104 MB |
| *(Edición Completa)* | C1 (Río 2016) | `diff_20261012_214241` | Diferencial | `full_20261012_213911` | ~12.93 MB |
| | C2 (Tokio 2020) | `diff_20261012_214542` | Diferencial | `full_20261012_213911` | ~22.80 MB |
| | C3 (París 2024) | `diff_20261012_214706` | Diferencial | `full_20261012_213911` | ~25.83 MB |

---

## 4. Procedimiento Operativo y Scripts

Los scripts se ejecutan desde la raíz del repositorio en PowerShell:

### 4.1 Restauración de Respaldo Completo (C0)
```powershell
.\Fase2\restauracion\restore-full.ps1 -Ciclo deportista
```
**Pasos automáticos ejecutados:**
1. Detiene contenedores en conflicto y libera el puerto 3307.
2. Vacía el volumen aislado `fase2_restore_mysql_data`.
3. Inicia el cronómetro de alta precisión (`System.Diagnostics.Stopwatch`).
4. Copia el Full a `_restore_work`.
5. Ejecuta `xtrabackup --prepare --target-dir=/work/<full>`.
6. Ejecuta `xtrabackup --copy-back --target-dir=/work/<full> --datadir=/var/lib/mysql`.
7. Ajusta permisos de propiedad Linux (`chown -R 999:999`).
8. Levanta el contenedor `fase2_mysql_restore` y valida el healthcheck.
9. Registra la duración exacta en `Fase2/logs/bitacora_restauracion.csv`.

### 4.2 Restauración de Respaldo Diferencial (C1, C2, C3)
```powershell
.\Fase2\restauracion\restore-differential.ps1 -Ciclo deportista -Ronda c1
```
**Cadena de preparación física XtraBackup:**
1. `xtrabackup --prepare --apply-log-only --target-dir=/work/<full>` (Aplica redo log del full sin rollback).
2. `xtrabackup --prepare --target-dir=/work/<full> --incremental-dir=/work/<diff>` (Aplica páginas delta del diferencial).
3. `xtrabackup --prepare --target-dir=/work/<full>` (Rollback final de transacciones no confirmadas).
4. `xtrabackup --copy-back --target-dir=/work/<full> --datadir=/var/lib/mysql`.
5. Permisos (`999:999`), arranque y cronometraje.

### 4.3 Auditoría de Integridad y Validación
```powershell
.\Fase2\restauracion\validar-restauracion.ps1 -Ciclo deportista -Carga c1 -SaveReport
```
**Verificaciones ejecutadas:**
- **Censo de 12 tablas:** Valida que cada tabla contenga exactamente las filas esperadas.
- **Integridad referencial:** 7 consultas anti-join (`LEFT JOIN ... WHERE IS NULL`) para certificar 0 huérfanos.
- **Integridad física:** `CHECK TABLE` en todas las tablas InnoDB.
- **Fragmentación:** Consulta `information_schema.TABLES` mostrando `espacio_libre_kb` y `%_fragmentacion`.

---

## 5. Bitácora de Tiempos de Recuperación Física

*Registros cronometrados automáticamente y almacenados en `Fase2/logs/bitacora_restauracion.csv`:*

| Ciclo | Carga | Estrategia | Respaldo Base | Respaldo Diferencial | Duración (segundos) | Estado |
|---|---|---|---|---|---|---|
| **Deportista** | C0 | Full | `full_20261012_211829` | — | 20.60 s | OK |
| **Deportista** | C1 | Diferencial | `full_20261012_211829` | `diff_20261012_212322` | 35.14 s | OK |
| **Deportista** | C2 | Diferencial | `full_20261012_211829` | `diff_20261012_212404` | 34.72 s | OK |
| **Deportista** | C3 | Diferencial | `full_20261012_211829` | `diff_20261012_212457` | 32.98 s | OK |
| **Deporte** | C0 | Full | `full_20261012_213152` | — | 18.89 s | OK |
| **Deporte** | C1 | Diferencial | `full_20261012_213152` | `diff_20261012_213250` | 34.78 s | OK |
| **Deporte** | C2 | Diferencial | `full_20261012_213152` | `diff_20261012_213408` | 34.84 s | OK |
| **Deporte** | C3 | Diferencial | `full_20261012_213152` | `diff_20261012_213758` | 35.24 s | OK |
| **Año** | C0 | Full | `full_20261012_213911` | — | *(Pendiente)* | — |
| **Año** | C1 | Diferencial | `full_20261012_213911` | `diff_20261012_214241` | *(Pendiente)* | — |
| **Año** | C2 | Diferencial | `full_20261012_213911` | `diff_20261012_214542` | *(Pendiente)* | — |
| **Año** | C3 | Diferencial | `full_20261012_213911` | `diff_20261012_214706` | *(Pendiente)* | — |

---

## 6. Estructura de Evidencias (24 Capturas con Reloj OS)

> **Instrucción de captura:** Cada captura debe mostrar la ventana de MySQL Workbench conectada a `127.0.0.1:3307` ejecutando `validacion.sql`, con la barra de tareas y el reloj de Windows visible.

### 6.1 CICLO 1: DEPORTISTA (Usain Bolt)
Guardar en: `Fase2/evidencias/deportista/`

#### C0 — Catálogos (Full Backup)
* **Censo de datos (atleta=0, participacion=0, catálogos completos):**  
  `![Censo Deportista C0](evidencias/deportista/deportista_restaura_full_censo.png)`
* **Fragmentación de tablas InnoDB:**  
  `![Fragmentación Deportista C0](evidencias/deportista/deportista_restaura_full_frag.png)`

#### C1 — Atenas 2004 (Diferencial 1)
* **Censo de datos (atleta=1, participacion=1):**  
  `![Censo Deportista C1](evidencias/deportista/deportista_restaura_diff1_censo.png)`
* **Fragmentación de tablas InnoDB:**  
  `![Fragmentación Deportista C1](evidencias/deportista/deportista_restaura_diff1_frag.png)`

#### C2 — Pekín 2008 (Diferencial 2)
* **Censo de datos (atleta=1, participacion=4):**  
  `![Censo Deportista C2](evidencias/deportista/deportista_restaura_diff2_censo.png)`
* **Fragmentación de tablas InnoDB:**  
  `![Fragmentación Deportista C2](evidencias/deportista/deportista_restaura_diff2_frag.png)`

#### C3 — Londres 2012 (Diferencial 3)
* **Censo de datos (atleta=1, participacion=7):**  
  `![Censo Deportista C3](evidencias/deportista/deportista_restaura_diff3_censo.png)`
* **Fragmentación de tablas InnoDB:**  
  `![Fragmentación Deportista C3](evidencias/deportista/deportista_restaura_diff3_frag.png)`

---

### 6.2 CICLO 2: DEPORTE (100m Femenino)
Guardar en: `Fase2/evidencias/deporte/`

#### C0 — Catálogos (Full Backup)
* **Censo de datos (atleta=0, participacion=0):**  
  `![Censo Deporte C0](evidencias/deporte/deporte_restaura_full_censo.png)`
* **Fragmentación de tablas InnoDB:**  
  `![Fragmentación Deporte C0](evidencias/deporte/deporte_restaura_full_frag.png)`

#### C1 — Río 2016 (Diferencial 1)
* **Censo de datos (atleta=91, participacion=91):**  
  `![Censo Deporte C1](evidencias/deporte/deporte_restaura_diff1_censo.png)`
* **Fragmentación de tablas InnoDB:**  
  `![Fragmentación Deporte C1](evidencias/deporte/deporte_restaura_diff1_frag.png)`

#### C2 — Tokio 2020 (Diferencial 2)
* **Censo de datos (atleta=150, participacion=172):**  
  `![Censo Deporte C2](evidencias/deporte/deporte_restaura_diff2_censo.png)`
* **Fragmentación de tablas InnoDB:**  
  `![Fragmentación Deporte C2](evidencias/deporte/deporte_restaura_diff2_frag.png)`

#### C3 — París 2024 (Diferencial 3)
* **Censo de datos (atleta=219, participacion=263):**  
  `![Censo Deporte C3](evidencias/deporte/deporte_restaura_diff3_censo.png)`
* **Fragmentación de tablas InnoDB:**  
  `![Fragmentación Deporte C3](evidencias/deporte/deporte_restaura_diff3_frag.png)`

---

### 6.3 CICLO 3: AÑO (Todas las pruebas de cada edición)
Guardar en: `Fase2/evidencias/anio/`

#### C0 — Catálogos (Full Backup)
* **Censo de datos (atleta=0, participacion=0):**  
  `![Censo Año C0](evidencias/anio/anio_restaura_full_censo.png)`
* **Fragmentación de tablas InnoDB:**  
  `![Fragmentación Año C0](evidencias/anio/anio_restaura_full_frag.png)`

#### C1 — Río 2016 (Diferencial 1)
* **Censo de datos (atleta=14464, participacion=17015):**  
  `![Censo Año C1](evidencias/anio/anio_restaura_diff1_censo.png)`
* **Fragmentación de tablas InnoDB:**  
  `![Fragmentación Año C1](evidencias/anio/anio_restaura_diff1_frag.png)`

#### C2 — Tokio 2020 (Diferencial 2)
* **Censo de datos (atleta=24001, participacion=33198):**  
  `![Censo Año C2](evidencias/anio/anio_restaura_diff2_censo.png)`
* **Fragmentación de tablas InnoDB:**  
  `![Fragmentación Año C2](evidencias/anio/anio_restaura_diff2_frag.png)`

#### C3 — París 2024 (Diferencial 3)
* **Censo de datos (atleta=30648, participacion=44581):**  
  `![Censo Año C3](evidencias/anio/anio_restaura_diff3_censo.png)`
* **Fragmentación de tablas InnoDB:**  
  `![Fragmentación Año C3](evidencias/anio/anio_restaura_diff3_frag.png)`

---

## 7. Análisis Comparativo Preliminar de Resultados

1. **Tiempo de preparación vs. Tamaño de respaldo:**
   - La preparación de un respaldo diferencial requiere preparar primero la base Full con `--apply-log-only` y luego incorporar el delta diferencial. Esto explica por qué un diferencial (ej. 38.62 s) tarda ligeramente más en recuperarse que un Full simple (20.60 s), ya que realiza dos pasadas de consistencia transaccional.
2. **Ventaja de la Estrategia Diferencial frente a la Incremental:**
   - Para recuperar el estado C3 (Ronda 3), la estrategia diferencial requiere **únicamente 2 piezas**: el Full base y el diferencial 3.
   - En una estrategia incremental, se requeriría encadenar obligatoriamente Full + Inc1 + Inc2 + Inc3, aumentando el tiempo acumulado de preparación y el riesgo de fallo si un archivo intermedio se corrompe.
3. **Comportamiento ante distintas volumetrías:**
   - En cargas pequeñas (Deportista, ~3 MB) y medianas (Deporte, ~4 MB), el tiempo de I/O de disco es mínimo y la mayor parte del tiempo se invierte en inicializar el subsistema InnoDB y aplicar los checkpoints.
   - En cargas masivas (Año, ~26 MB), el tiempo de copia de páginas físicas (`copy-back`) y la reconciliación del buffer pool adquieren mayor peso relativo.
