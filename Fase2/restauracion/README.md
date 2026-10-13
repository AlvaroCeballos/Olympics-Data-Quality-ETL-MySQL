# Módulo de Restauración y Validación — Integrante 3

Este módulo contiene la infraestructura y scripts de automatización para la restauración física de respaldos de MySQL 8.0 utilizando **Percona XtraBackup 8.0**, así como el sistema de **alertas de integridad y validación de datos**.

---

## 1. Arquitectura de Aislamiento

Para garantizar que el avance y los datos de los demás integrantes permanezcan completamente protegidos:

1. **Volumen de Datos Aislado:**
   - La restauración opera exclusivamente sobre el volumen `fase2_restore_mysql_data` definido en `docker-compose.restore.yml`.
   - El volumen del equipo (`fase2_olimpiadas_mysql_data`) **nunca se modifica ni se borra**.
2. **Protección de Archivos de Respaldo Originales:**
   - XtraBackup `--prepare` modifica los archivos en el lugar (*in-place*).
   - Por ello, los scripts copian automáticamente los respaldos necesarios a una carpeta de trabajo temporal (`Fase2/backup/archivos/_restore_work/`).
   - Los respaldos originales en `Fase2/backup/archivos/` permanecen 100% intactos y reutilizables.
3. **Mismo Puerto de Acceso (3307):**
   - Antes de iniciar la restauración, se apaga temporalmente el contenedor principal (sin borrar su volumen) para liberar el puerto `3307`.
   - El contenedor restaurado (`fase2_mysql_restore`) se expone en `127.0.0.1:3307`. Esto permite que MySQL Workbench y los scripts de validación se conecten directamente sin cambiar configuraciones.

---

## 2. Mapa de Respaldos Definitivos

De acuerdo con el análisis del manifiesto (`backup_manifest.csv`) y las indicaciones del Integrante 1 (donde los ciclos fallidos fueron reiniciados desde cero), los conjuntos definitivos son:

| Ciclo | Carga | Respaldo Físico | Tipo | Tamaño Aprox. |
|---|---|---|---|---|
| **Deportista** | C0 (Catálogos) | `full_20261012_210023` | Full | ~145 MB |
| | C1 (Atenas 2004) | `diff_20261012_210255` | Diferencial | ~3.68 MB |
| | C2 (Pekín 2008) | `diff_20261012_210352` | Diferencial | ~3.68 MB |
| | C3 (Londres 2012) | `diff_20261012_210508` | Diferencial | ~3.68 MB |
| **Deporte** | C0 (Catálogos) | `full_20261012_213152` | Full | ~104 MB |
| | C1 (Río 2016) | `diff_20261012_213250` | Diferencial | ~3.25 MB |
| | C2 (Tokio 2020) | `diff_20261012_213408` | Diferencial | ~3.50 MB |
| | C3 (París 2024) | `diff_20261012_213758` | Diferencial | ~3.81 MB |
| **Año** | C0 (Catálogos) | `full_20261012_213911` | Full | ~104 MB |
| | C1 (Río 2016) | `diff_20261012_214241` | Diferencial | ~12.93 MB |
| | C2 (Tokio 2020) | `diff_20261012_214542` | Diferencial | ~22.80 MB |
| | C3 (París 2024) | `diff_20261012_214706` | Diferencial | ~25.83 MB |

---

## 3. Scripts Disponibles

Todos los scripts se ejecutan desde PowerShell:

### A. Restauración Completa (Full - C0)
Restaura el estado inicial con catálogos:
```powershell
.\Fase2\restauracion\restore-full.ps1 -Ciclo deportista
# Opciones para -Ciclo: deportista | deporte | anio
```

### B. Restauración Diferencial (Diff - C1, C2, C3)
Aplica la cadena diferencial sobre la base completa correspondiente:
```powershell
.\Fase2\restauracion\restore-differential.ps1 -Ciclo deportista -Ronda c1
.\Fase2\restauracion\restore-differential.ps1 -Ciclo deporte    -Ronda c2
.\Fase2\restauracion\restore-differential.ps1 -Ciclo anio       -Ronda c3
```

### C. Alertas de Validación e Integridad
Comprueba inmediatamente después de restaurar:
```powershell
.\Fase2\restauracion\validar-restauracion.ps1 -Ciclo deportista -Carga c1
```
**Alertas verificadas:**
1. **Discrepancia en Conteos:** Compara tabla por tabla (10 catálogos + atleta + participacion) contra los valores documentados por el Integrante 2. Alerta en rojo si hay cualquier desviación.
2. **Integridad Referencial (Huérfanos):** Ejecuta 7 consultas `LEFT JOIN ... WHERE IS NULL` en `participacion` y otras tablas clave. Alerta si existe aunque sea 1 registro huérfano.
3. **Integridad Física (CHECK TABLE):** Ejecuta `CHECK TABLE` en las 12 tablas InnoDB para descartar corrupción.
4. **Fragmentación:** Muestra la grilla de fragmentación (`DATA_FREE`, `%_FRAG`) para las capturas de evidencia.

### D. Orquestador Maestro
Permite ejecutar un ciclo completo o todos secuencialmente:
```powershell
# Ejecutar un ciclo completo pausando para tomar capturas:
.\Fase2\restauracion\restaurar-y-validar-todo.ps1 -Ciclo deportista -PausarParaCapturas
```

---

## 4. Bitácora de Tiempos

Cada ejecución registra automáticamente en `Fase2/logs/bitacora_restauracion.csv`:
- `fecha_hora`: Marca temporal ISO 8601.
- `ciclo`: deportista, deporte o anio.
- `carga`: c0, c1, c2 o c3.
- `estrategia`: full o differential.
- `backup_full`: Nombre de la carpeta base.
- `backup_diff`: Nombre de la carpeta diferencial aplicada.
- `duracion_segundos`: Tiempo exacto de recuperación en segundos.
- `resultado`: OK o mensaje de error.
