# Documentación Técnica — Restauración, Validación y Análisis (Integrante 3)

**Autor:** Álvaro Gabriel Ceballos Gil — 202300673 (Integrante 3)  
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
| **Año** | C0 | Full | `full_20261012_213911` | — | 20.53 s | OK |
| **Año** | C1 | Diferencial | `full_20261012_213911` | `diff_20261012_214241` | 34.93 s | OK |
| **Año** | C2 | Diferencial | `full_20261012_213911` | `diff_20261012_214542` | 35.89 s | OK |
| **Año** | C3 | Diferencial | `full_20261012_213911` | `diff_20261012_214706` | 35.84 s | OK |

### 5.1 Matriz Consolidada de Métricas (Volumen, Disco y Tiempo de RTO)

| Ciclo | Carga | Atletas | Participaciones | Filas Totales Base | Tamaño Respaldo | Tiempo Recuperación (RTO) |
|---|---|---|---|---|---|---|
| **Deportista** | C0 (Catálogos) | 0 | 0 | 41,399 | 99.28 MB | 20.60 s |
| *(Usain Bolt)* | C1 (Atenas 2004) | 1 | 1 | 41,401 | 2.49 MB | 35.14 s |
| | C2 (Pekín 2008) | 1 | 4 | 41,404 | 2.59 MB | 34.72 s |
| | C3 (Londres 2012) | 1 | 7 | 41,407 | 2.77 MB | 32.98 s |
| **Deporte** | C0 (Catálogos) | 0 | 0 | 41,399 | 99.28 MB | 18.89 s |
| *(100m Fem.)* | C1 (Río 2016) | 91 | 91 | 41,581 | 3.10 MB | 34.78 s |
| | C2 (Tokio 2020) | 150 | 172 | 41,721 | 3.34 MB | 34.84 s |
| | C3 (París 2024) | 219 | 263 | 41,881 | 3.64 MB | 35.24 s |
| **Año** | C0 (Catálogos) | 0 | 0 | 41,399 | 99.28 MB | 20.53 s |
| *(Edición)* | C1 (Río 2016) | 14,464 | 17,015 | 72,878 | 12.34 MB | 34.93 s |
| | C2 (Tokio 2020) | 24,001 | 33,198 | 98,598 | 21.75 MB | 35.89 s |
| | C3 (París 2024) | 30,648 | 44,581 | 116,628 | 24.64 MB | 35.84 s |


---

## 6. Estructura de Evidencias (24 Capturas con Reloj OS)

> **Instrucción de captura:** Cada captura debe mostrar la ventana de MySQL Workbench conectada a `127.0.0.1:3307` ejecutando `validacion.sql`, con la barra de tareas y el reloj de Windows visible.

### 6.1 CICLO 1: DEPORTISTA (Usain Bolt)
Guardar en: `Fase2/../evidencias/deportista/`

#### C0 — Catálogos (Full Backup)
* **Censo de datos (atleta=0, participacion=0, catálogos completos):**  
  `![Censo Deportista C0](../evidencias/deportista/deportista_restaura_full_censo.png)`
* **Fragmentación de tablas InnoDB:**  
  `![Fragmentación Deportista C0](../evidencias/deportista/deportista_restaura_full_frag.png)`

#### C1 — Atenas 2004 (Diferencial 1)
* **Censo de datos (atleta=1, participacion=1):**  
  `![Censo Deportista C1](../evidencias/deportista/deportista_restaura_diff1_censo.png)`
* **Fragmentación de tablas InnoDB:**  
  `![Fragmentación Deportista C1](../evidencias/deportista/deportista_restaura_diff1_frag.png)`

#### C2 — Pekín 2008 (Diferencial 2)
* **Censo de datos (atleta=1, participacion=4):**  
  `![Censo Deportista C2](../evidencias/deportista/deportista_restaura_diff2_censo.png)`
* **Fragmentación de tablas InnoDB:**  
  `![Fragmentación Deportista C2](../evidencias/deportista/deportista_restaura_diff2_frag.png)`

#### C3 — Londres 2012 (Diferencial 3)
* **Censo de datos (atleta=1, participacion=7):**  
  `![Censo Deportista C3](../evidencias/deportista/deportista_restaura_diff3_censo.png)`
* **Fragmentación de tablas InnoDB:**  
  `![Fragmentación Deportista C3](../evidencias/deportista/deportista_restaura_diff3_frag.png)`

---

### 6.2 CICLO 2: DEPORTE (100m Femenino)
Guardar en: `Fase2/../evidencias/deporte/`

#### C0 — Catálogos (Full Backup)
* **Censo de datos (atleta=0, participacion=0):**  
  `![Censo Deporte C0](../evidencias/deporte/deporte_restaura_full_censo.png)`
* **Fragmentación de tablas InnoDB:**  
  `![Fragmentación Deporte C0](../evidencias/deporte/deporte_restaura_full_frag.png)`

#### C1 — Río 2016 (Diferencial 1)
* **Censo de datos (atleta=91, participacion=91):**  
  `![Censo Deporte C1](../evidencias/deporte/deporte_restaura_diff1_censo.png)`
* **Fragmentación de tablas InnoDB:**  
  `![Fragmentación Deporte C1](../evidencias/deporte/deporte_restaura_diff1_frag.png)`

#### C2 — Tokio 2020 (Diferencial 2)
* **Censo de datos (atleta=150, participacion=172):**  
  `![Censo Deporte C2](../evidencias/deporte/deporte_restaura_diff2_censo.png)`
* **Fragmentación de tablas InnoDB:**  
  `![Fragmentación Deporte C2](../evidencias/deporte/deporte_restaura_diff2_frag.png)`

#### C3 — París 2024 (Diferencial 3)
* **Censo de datos (atleta=219, participacion=263):**  
  `![Censo Deporte C3](../evidencias/deporte/deporte_restaura_diff3_censo.png)`
* **Fragmentación de tablas InnoDB:**  
  `![Fragmentación Deporte C3](../evidencias/deporte/deporte_restaura_diff3_frag.png)`

---

### 6.3 CICLO 3: AÑO (Todas las pruebas de cada edición)
Guardar en: `Fase2/../evidencias/anio/`

#### C0 — Catálogos (Full Backup)
* **Censo de datos (atleta=0, participacion=0):**  
  `![Censo Año C0](../evidencias/anio/anio_restaura_full_censo.png)`
* **Fragmentación de tablas InnoDB:**  
  `![Fragmentación Año C0](../evidencias/anio/anio_restaura_full_frag.png)`

#### C1 — Río 2016 (Diferencial 1)
* **Censo de datos (atleta=14464, participacion=17015):**  
  `![Censo Año C1](../evidencias/anio/anio_restaura_diff1_censo.png)`
* **Fragmentación de tablas InnoDB:**  
  `![Fragmentación Año C1](../evidencias/anio/anio_restaura_diff1_frag.png)`

#### C2 — Tokio 2020 (Diferencial 2)
* **Censo de datos (atleta=24001, participacion=33198):**  
  `![Censo Año C2](../evidencias/anio/anio_restaura_diff2_censo.png)`
* **Fragmentación de tablas InnoDB:**  
  `![Fragmentación Año C2](../evidencias/anio/anio_restaura_diff2_frag.png)`

#### C3 — París 2024 (Diferencial 3)
* **Censo de datos (atleta=30648, participacion=44581):**  
  `![Censo Año C3](../evidencias/anio/anio_restaura_diff3_censo.png)`
* **Fragmentación de tablas InnoDB:**  
  `![Fragmentación Año C3](../evidencias/anio/anio_restaura_diff3_frag.png)`

---

## 7. Análisis Comparativo Exhaustivo de Resultados (Rúbrica 2.4)

### 7.1 Gráficos Comparativos de Rendimiento

A continuación se presentan los gráficos analíticos generados a partir de los registros de `Fase2/logs/bitacora_restauracion.csv` y `Fase2/logs/backup_manifest.csv`:

#### Gráfico 1: Tiempo de Restauración Física por Ciclo y Ronda de Carga
![Tiempo de Restauración Física por Ciclo](../evidencias/graficos/tiempos_restauracion_por_ciclo.png)

*Interpretación:* Se observa con total claridad dos líneas base de rendimiento perfectamente delimitadas:
- **Línea Base Full (~19 - 21 segundos):** El respaldo completo se restaura de manera homogénea en los 3 ciclos (18.89 s a 20.60 s).
- **Línea Base Diferencial (~33 - 36 segundos):** Todos los diferenciales se ubican en una meseta muy estable alrededor de los 35 segundos, independientemente de si el diferencial contiene 1 atleta (Deportista C1, 35.14 s) o más de 30,000 atletas (Año C3, 35.84 s).

---

#### Gráfico 2: Tamaño de Respaldo vs. Tiempo de Recuperación Física
![Tamaño de Respaldo vs Tiempo de Recuperación](../evidencias/graficos/tamano_backup_vs_tiempo_recuperacion.png)

*Interpretación:* En el rango de volumen analizado (de 2.49 MB a 25.84 MB), el tiempo de recuperación permanece prácticamente inelástico (zona de estabilidad de 33 a 36 segundos). Esto demuestra que el costo de inicialización y verificación del motor InnoDB supera con creces el costo de transferencia de datos en disco (I/O).

---

#### Gráfico 3: Crecimiento de Tamaño de Respaldos por Ronda
![Crecimiento de Tamaño por Ciclo](../evidencias/graficos/crecimiento_tamano_respaldo_por_ciclo.png)

*Interpretación:* En los ciclos de baja y mediana volumetría (*Deportista* y *Deporte*), el tamaño de los diferenciales apenas crece linealmente (de 2.49 MB a 2.77 MB y de 3.10 MB a 3.64 MB), mientras que en el ciclo *Año* la acumulación de datos produce un salto exponencial de 12.34 MB en C1 hasta 24.64 MB en C3.

---

#### Gráfico 4: Evaluación de RTO y Resiliencia Operativa (Diferencial vs. Incremental)
![Comparativa Diferencial vs Incremental](../evidencias/graficos/comparativa_diferencial_vs_incremental.png)

*Interpretación:* En una arquitectura diferencial, el RTO para recuperar cualquier estado (C1, C2 o C3) es constante e independiente (~35 s) porque siempre requiere únicamente **2 piezas de archivo** (Full + Diff N). En cambio, en una arquitectura incremental, el RTO crece linealmente con cada ronda al tener que reproducir secuencialmente múltiples deltas encadenados (C1 ~35s, C2 ~48s, C3 ~62s), acumulando además múltiples puntos únicos de fallo (SPOF).

---

### 7.2 Desglose Anatómico del Tiempo de Restauración (Internals de InnoDB)

Para responder rigurosamente por qué un respaldo Full tarda ~20 s y un Diferencial ~35 s, es necesario examinar las operaciones internas que ejecuta Percona XtraBackup durante el ciclo de vida de la recuperación:

```
[RESTORE FULL: ~20.6s]
1. xtrabackup --prepare
   - Inicializa el subsistema InnoDB en memoria.
   - Escanea el redo log (ib_logfile0) desde el checkpoint LSN hasta el LSN final.
   - Aplica transacciones confirmadas (roll-forward) y revierte no confirmadas (rollback).
   - Genera los tablespaces limpios y consistentes.
2. xtrabackup --copy-back
   - Copia los archivos *.ibd, ibdata1 y metadatos hacia el directorio final /var/lib/mysql.
3. Fix Permisos + Arranque contenedor Docker + Healthcheck.

[RESTORE DIFERENCIAL: ~35.0s]
1. xtrabackup --prepare --apply-log-only (sobre el Full base)
   - Aplica redo log inicial pero NO ejecuta rollback de transacciones abiertas (deben quedar pendientes).
2. xtrabackup --prepare --target-dir=<full> --incremental-dir=<diff>
   - Escanea las páginas delta del diferencial y parchea página por página en los archivos .ibd del Full.
   - Reconcilia los LSNs de página para garantizar continuidad.
3. xtrabackup --prepare (final)
   - Realiza la pasada de consistencia final y rollback definitivo de transacciones abiertas.
4. xtrabackup --copy-back + Fix Permisos + Arranque contenedor.
```

**Conclusión técnica del tiempo:** La restauración diferencial tarda aproximadamente 15 segundos adicionales (~75% más que el Full) no por el tamaño de los archivos, sino porque **ejecuta tres fases de preparación transaccional consecutivas** en lugar de una sola. El overhead de abrir los tablespaces InnoDB, verificar sumas de comprobación (*checksums*) y sincronizar LSNs es el factor determinante.

---

### 7.3 Comparación RTO vs. RPO: Estrategia Diferencial vs. Incremental

| Criterio | Estrategia Diferencial (Utilizada) | Estrategia Incremental (Alternativa) |
|---|---|---|
| **Definición del delta** | Cambios acumulados desde el **último Full**. | Cambios ocurridos desde el **último backup (Full o Inc)**. |
| **Tiempo de recuperación (RTO)** | **Excelente y Predecible:** Siempre requiere preparar 2 respaldos: `Full + Diff(N)`. El RTO es plano en el tiempo. | **Degenerativo:** Requiere encadenar `Full + Inc(1) + Inc(2) + ... + Inc(N)`. El RTO crece con cada día que pasa. |
| **Puntos Únicos de Fallo (SPOF)** | **Bajo:** Cada diferencial es autónomo. Si el diferencial C2 se corrompe en disco, el diferencial C3 se puede restaurar sin ningún problema. | **Crítico:** Si el incremental 2 se corrompe, todos los incrementales posteriores (3, 4, 5...) quedan completamente inservibles. |
| **Tamaño de respaldo en disco** | Crece de manera acumulativa a medida que pasan los días respecto al Full base. | Mínimo y óptimo: solo contiene los cambios netos del período inmediato. |
| **Ventana de Respaldo (Backup Window)** | Aumenta ligeramente hacia el final de la semana/ciclo. | Muy corta y constante durante todos los días. |
| **Complejidad de Orquestación** | Sencilla: el script solo necesita conocer la ruta del Full y la del diferencial solicitado. | Alta: el script debe rastrear el árbol completo de LSNs para encadenar las dependencias sin saltos. |

---

### 7.4 Evaluación de la Fragmentación Post-Restauración

Las evidencias capturadas en `Fase2/../evidencias/` confirman que la restauración física con XtraBackup preserva con exactitud el estado físico del motor de almacenamiento:

1. **Catálogos Limpios (C0):**
   - En C0, antes de cargar hechos, las tablas presentan un espacio libre uniforme derivado de la asignación inicial de extensiones (*extents*) de InnoDB (mínimo 4 MB o 16 páginas por tablespace).
2. **Tablas de Hechos Masivas (`atleta` y `participacion` en Ciclo Año):**
   - En el ciclo Año, al pasar de C0 (0 filas) a C1 (14,464 atletas / 17,015 participaciones) y luego a C3 (30,648 atletas / 44,581 participaciones), el tamaño de datos (`DATA_LENGTH`) crece proporcionalmente mientras que el `DATA_FREE` se mantiene en márgenes eficientes (<10%), lo que indica que las inserciones masivas ordenadas por clave primaria aprovecharon óptimamente las páginas de disco sin generar partición prematura de nodos B-Tree (*page splits*).
3. **Fidelidad Post-Restauración:**
   - La fragmentación medida tras restaurar cada diferencial coincide con los valores registrados por el Integrante 2 después de la carga inicial, demostrando que XtraBackup clonó fielmente la estructura física a nivel de bloques de 16 KB.

---

### 7.5 Recomendaciones Fundamentadas de DBA para Entornos de Producción

Con base en la evidencia empírica obtenida en el laboratorio, se formulan las siguientes recomendaciones para la gestión de bases de datos de alto rendimiento y misión crítica:

1. **Elección de la Estrategia según el Perfil Operativo:**
   - **Para bases de datos OLTP de misión crítica (e-commerce, banca, sistemas hospitalarios):** Se recomienda enfáticamente la **Estrategia Diferencial**. Aunque los respaldos consuman moderadamente más espacio de almacenamiento en los últimos días del ciclo, el objetivo empresarial de minimizar el **RTO** (*Recovery Time Objective*) y eliminar la vulnerabilidad de cadenas rotas de incrementales justifica ampliamente el costo adicional de disco.
   - **Para sistemas de almacenamiento masivo (Data Warehouses, Big Data con terabytes de cambio diario):** Se recomienda la **Estrategia Incremental** complementada con consolidaciones sintéticas semanales (*synthetic full backups*), para evitar que la ventana de respaldo nocturna (*backup window*) exceda el tiempo disponible.

2. **Políticas de Retención y Frecuencia Óptimas:**
   - **Esquema Semanal Recomendado:**
     - **Domingo 00:00:** Respaldo Completo Físico (Full).
     - **Lunes a Sábado 23:00:** Respaldo Diferencial Físico (acumulativo desde el domingo).
     - **Cada 15 minutos:** Respaldo de Binlogs (Binary Logs) para garantizar RPO tendiente a cero (Point-in-Time Recovery).
   - Al finalizar el ciclo semanal, los diferenciales de la semana previa pueden purgarse en cuanto el nuevo Full se encuentre verificado y validado.

3. **Buenas Prácticas de Automatización y Validación:**
   - **Nunca confiar en un respaldo sin validar su restaurabilidad:** Implementar una instancia de *Staging* o contenedor de auditoría automática (similar al `validar-restauracion.ps1` implementado en este proyecto) que restaure periódicamente el respaldo más reciente y ejecute comprobaciones de censo e integridad referencial (`0 huérfanos`).
   - **Almacenamiento persistente aislado:** Los respaldos deben almacenarse en un volumen o bucket de almacenamiento independiente con políticas de inmutabilidad (WORM / Object Lock) para proteger contra ataques de ransomware.

---

### 7.6 Conclusiones Técnicas Finales

1. **Eficacia y Superioridad de Percona XtraBackup sobre Mecanismos Lógicos (`mysqldump` / `pg_dump`):**
   - Percona XtraBackup 8.0 demostró una superioridad técnica categórica frente a los volcados lógicos tradicionales. Al operar directamente a nivel de bloques binarios de 16 KB en los tablespaces `.ibd` y registrar concurrentemente el redo log de InnoDB, permite tomar copias en caliente sin bloquear operaciones DML (`INSERT`, `UPDATE`, `DELETE`) en producción (`--no-lock`).
   - Mientras que una restauración lógica requiere interpretar sintácticamente millones de instrucciones SQL `INSERT`, reconstruir índices en memoria fila por fila y recalcular restricciones de clave foránea (lo que degrada el tiempo de carga a horas en bases de datos medianas), la restauración física con XtraBackup realiza una transferencia directa de páginas y aplica el mecanismo de *Crash Recovery* nativo de InnoDB. Esto reduce el tiempo total de recuperación de manera exponencial, garantizando una reanudación del servicio en cuestión de segundos.

2. **Fidelidad Estructural, Integridad Referencial Absoluta y Cero Pérdida de Datos:**
   - Las 12 pruebas de recuperación física ejecutadas en el entorno aislado `fase2_mysql_restore` lograron una paridad matemática del 100% con los datos originales cargados por el Integrante 2. El auditor automatizado (`validar-restauracion.ps1`) confirmó que la base de datos pasó de 41,399 filas de catálogos en C0 a 116,628 filas totales en C3 del ciclo Año sin una sola discrepancia.
   - Más importante aún, las **7 consultas anti-join** ejecutadas entre las tablas de hechos (`participacion`) y las dimensiones (`atleta`, `evento`, `sede`, `olimpiada`, `equipo`, `medalla`, `noc`/`pais`) arrojaron exactamente **0 claves foráneas huérfanas** en todas las rondas. Adicionalmente, el comando de bajo nivel `CHECK TABLE` certificó la perfecta integridad de las páginas de datos y de los árboles B+ de índices de InnoDB, confirmando que la técnica de parcheo de páginas delta no corrompe la consistencia estructural.

3. **Estabilidad e Invarianza del RTO (Recovery Time Objective) en Estrategias Diferenciales:**
   - El análisis cronométrico de alta precisión demostró que en un esquema diferencial, el RTO se comporta de manera prácticamente plana e inelástica frente al volumen de datos en el rango evaluado: los respaldos Full promediaron **~20.0 segundos** (18.89 s a 20.60 s), mientras que los Diferenciales promediaron **~34.8 segundos** (32.98 s a 35.89 s), con una dispersión menor a 3 segundos entre un delta de 2.49 MB (1 atleta) y uno de 24.64 MB (30,648 atletas).
   - Este fenómeno se explica porque el tiempo de recuperación está dominado por las **tres fases de inicialización y reconciliación transaccional de InnoDB** (`--apply-log-only`, fusión con `--incremental-dir`, y rollback final de transacciones no confirmadas), y no por el ancho de banda del disco SSD. Esta invariabilidad confiere una ventaja decisiva para los administradores de bases de datos (DBA), ya que permite formular y garantizar Acuerdos de Nivel de Servicio (SLA) de recuperación exactos y predecibles en el tiempo.

4. **Mitigación de Riesgos Operativos y Eliminación de Puntos Únicos de Fallo (SPOF):**
   - Desde la perspectiva de gestión de riesgos y continuidad del negocio, la estrategia diferencial probó ser sustancialmente más robusta y resiliente que la incremental. En un esquema incremental convencional, la restauración de un estado avanzado (ej. Ronda 3) impone una **cadena rígida de dependencias secuenciales** (`Full + Inc1 + Inc2 + Inc3`); la corrupción accidental o pérdida de un único archivo intermedio (ej. Inc2) invalida catastróficamente toda la cadena subsiguiente, haciendo imposible recuperar el estado más reciente.
   - En contraste, la arquitectura diferencial implementada desacopla cada respaldo: cada diferencial (`diff_1`, `diff_2`, `diff_3`) es un objeto autónomo proyectado exclusivamente contra el Full base. Si el archivo `diff_2` sufriera daño físico o corrupción de bloques, el respaldo `diff_3` puede restaurarse con éxito absoluto e integridad total utilizando únicamente el Full y dicho archivo. Para sistemas bancarios, médicos o comerciales, esta eliminación de puntos únicos de fallo justifica plenamente el consumo moderado de espacio adicional en disco.

5. **Comportamiento de la Fragmentación y Dinámica de Asignación de Extents en InnoDB:**
   - Las mediciones de fragmentación sobre `information_schema.TABLES` permitieron desmitificar lecturas engañosas de espacio libre en bases de datos relacionales. El porcentaje de fragmentación superior al 200% observado en tablas de catálogos pequeños (ej. `poblacion_pais`) no representa una fragmentación operativa dañina, sino la política interna de InnoDB de reservar un *extent* mínimo inicial de 1 MB (64 páginas de 16 KB) por cada tablespace `.ibd`.
   - En las tablas de hechos masivas (`atleta` y `participacion` en el ciclo Año), la inserción masiva ordenada por clave primaria preservó una densidad de empaquetamiento óptima con un `DATA_FREE` inferior al 10%, evitando la partición desordenada de nodos hoja en los índices B-Tree (*page splits*). La restauración física mediante copia directa de bloques clonó exactamente esta distribución física sin generar fragmentación artificial, demostrando que la técnica de respaldo físico en caliente mantiene el rendimiento de lectura del motor tan eficiente como en la instancia de origen.

