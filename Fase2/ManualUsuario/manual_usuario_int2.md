# Manual de usuario — Carga y validación (Integrante 2)

**Autora:** Yulianne Nicole López Elias — 202300659 (Integrante 2)  
**Curso:** Sistemas de Bases de Datos 2, USAC  
**Grupo:** 18  

> Sección a cargo del Integrante 2. Explica cómo cargar los datos en la instancia de
> Fase 2 y cómo validar cada carga. Se integra al manual de usuario del grupo.

## 1. Requisitos previos

- La instancia MySQL de Fase 2 levantada (ver sección del Integrante 1: `Fase2/Start.bat`).
- MySQL Workbench conectado a la instancia:
  - Host `127.0.0.1`, Puerto `3307`, Usuario `root`, contraseña definida en `Fase2/.env`.
  - **Importante:** usar el puerto **3307** (contenedor de Fase 2), nunca el 3306 local.
- Base de datos de destino: `olimpiadas` (la crea el contenedor automáticamente desde
  `Fase2/ddl/olimpiada2s.sql` al levantarse con el volumen vacío).

## 2. Orden de ejecución de las cargas

Las cargas se ejecutan abriendo cada archivo en Workbench (`File > Open SQL Script...`) y
corriéndolo completo con el botón **"Execute SQL Script"** (el del rayo con hojitas,
`Ctrl+Shift+Enter`). Los scripts de carga **no muestran resultado**: solo insertan datos.

Para cada tipo de carga, el orden es:

1. `Fase2/carga/00_catalogos.sql` — carga inicial de catálogos (10 dimensiones).
2. `Fase2/carga/<tipo>/01_ronda1_*.sql` — primera ronda.
3. `Fase2/carga/<tipo>/02_ronda2_*.sql` — segunda ronda.
4. `Fase2/carga/<tipo>/03_ronda3_*.sql` — tercera ronda.

Donde `<tipo>` es `anio`, `deporte` o `deportista`.

> No ejecutar dos veces el mismo archivo de carga: produce el error
> `Error Code: 1062. Duplicate entry` (el dato ya estaba cargado).

Para empezar un tipo de carga en una instancia nueva (vacía), se reinicia el contenedor:

```powershell
docker compose --project-directory Fase2 --env-file Fase2/.env -f Fase2/docker-compose.yml down -v
.\Fase2\Start.bat
```

## 3. Validación después de cada carga

Después de cada carga, abrir `Fase2/validacion.sql` y ejecutarlo. Produce dos grillas:

- **Censo** (columnas `tabla | total`): el `COUNT(*)` exacto de las 12 tablas. Es la
  evidencia principal de que la carga se realizó.
- **Fragmentación** (columnas `tabla`, `filas_aprox`, `datos_kb`, `indices_kb`,
  `espacio_libre_kb`, `pct_fragmentacion`).

Para que la fragmentación muestre valores actualizados, ejecutar primero, en una pestaña
de consulta:

```sql
ANALYZE TABLE olimpiadas.atleta, olimpiadas.participacion, olimpiadas.pais,
  olimpiadas.equipo, olimpiadas.evento, olimpiadas.poblacion_pais;
```

> El censo (`COUNT(*)`) es exacto siempre. La columna `filas_aprox` de la fragmentación es
> un estimado de InnoDB y puede mostrar 0 hasta correr `ANALYZE TABLE`.

## 4. Registro de evidencias (capturas)

Después de cada carga se toman capturas de pantalla con **`Win + Impr Pant`** (para que
aparezca el reloj del sistema operativo). Se guardan en `Fase2/evidencias/<tipo>/` con el
nombre `<tipo>_c<N>_<etapa>_<resultado>.png`, por ejemplo:

```
deportista_c0_catalogos_censo.png
deportista_c1_atenas2004_censo.png
deportista_c1_atenas2004_frag.png
```

Donde `c0` = catálogos, `c1/c2/c3` = rondas, y `<resultado>` = `censo` o `frag`.

La convención completa está en `Fase2/evidencias/README.md` y la secuencia paso a paso en
`Fase2/evidencias/PASOS.md`.

## 5. Validación posterior a la restauración

Después de que el Integrante 3 restaure cada respaldo, se vuelve a correr `validacion.sql`
y se capturan las mismas grillas. Los conteos del censo restaurado deben **coincidir** con
los de la carga correspondiente; si coinciden, la restauración fue íntegra y sin pérdida de
datos.
