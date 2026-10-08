# Paso a paso de capturas — Integrante 2

Guía ordenada para tomar TODAS las capturas. Son 3 ciclos (deportista, deporte, año).
Cada ciclo: 1 carga de catálogos + 3 rondas = 4 cargas. Después de cada carga: 2 capturas (censo + fragmentación).
**Total: 24 capturas** (3 ciclos × 4 cargas × 2).

## Reglas de oro

- **Captura con `Win + Impr Pant`** → se guarda en `C:\Users\Nicole\Pictures\Screenshots\` CON el reloj de Windows. Después la renombrás y la movés a la carpeta que se indica.
- Los scripts de **carga** (`00_catalogos`, rondas) **NO muestran resultado** — solo cargan. Es normal que no salga grilla.
- Los **resultados** salen solo al correr `validacion.sql` (2 grillas: censo y fragmentación).
- **Nunca corras dos veces el mismo archivo de carga** → da error "Duplicate entry" (ya estaba cargado).
- Ejecutar un script completo = botón del rayo con hojitas (`Ctrl+Shift+Enter`).
- Siempre conectada al puerto **3307** (Fase2 Docker), nunca al 3306.

## Preparación (una sola vez al empezar el día)

1. Abrir **Docker Desktop** y esperar a que la ballena quede fija.
2. En la terminal de VS Code (PowerShell), parada en la raíz del repo.
3. Tener MySQL Workbench abierto con la conexión **Fase2 Docker 3307**.

---

# CICLO 1 — DEPORTISTA (Usain Bolt)

### Reset a base vacía
En la terminal:
```powershell
docker compose --project-directory Fase2 --env-file Fase2/.env -f Fase2/docker-compose.yml down -v
.\Fase2\Start.bat
```
Esperar a que el contenedor quede `healthy`.

### Carga 0 — Catálogos
1. Workbench → abrir `Fase2/carga/00_catalogos.sql` → ejecutar (rayo hojitas). *(No muestra resultado: normal.)*
2. **[Integrante 1 toma el FULL backup aquí.]**
3. Abrir `Fase2/validacion.sql` → ejecutar.
4. Capturar el **censo** → `deportista_c0_catalogos_censo.png`
5. Capturar la **fragmentación** → `deportista_c0_catalogos_frag.png`
   - Esperado: atleta **0**, participacion **0**, pais 487, equipo 20845
   - Guardar en: `Fase2/evidencias/deportista/`

### Carga 1 — Atenas 2004
6. Abrir `Fase2/carga/deportista/01_ronda1_atenas2004.sql` → ejecutar.
7. **[Integrante 1: diferencial 1.]**
8. `validacion.sql` → ejecutar.
9. Censo → `deportista_c1_atenas2004_censo.png`
10. Fragmentación → `deportista_c1_atenas2004_frag.png`
    - Esperado: atleta **1**, participacion **1**

### Carga 2 — Pekín 2008
11. Abrir `Fase2/carga/deportista/02_ronda2_pekin2008.sql` → ejecutar.
12. **[Integrante 1: diferencial 2.]**
13. `validacion.sql` → ejecutar.
14. Censo → `deportista_c2_pekin2008_censo.png`
15. Fragmentación → `deportista_c2_pekin2008_frag.png`
    - Esperado: atleta **1**, participacion **4**

### Carga 3 — Londres 2012
16. Abrir `Fase2/carga/deportista/03_ronda3_londres2012.sql` → ejecutar.
17. **[Integrante 1: diferencial 3.]**
18. `validacion.sql` → ejecutar.
19. Censo → `deportista_c3_londres2012_censo.png`
20. Fragmentación → `deportista_c3_londres2012_frag.png`
    - Esperado: atleta **1**, participacion **7**

---

# CICLO 2 — DEPORTE (100m femenino)

### Reset a base vacía (igual que arriba: `down -v` + `Start.bat`)

### Carga 0 — Catálogos
- Correr `00_catalogos.sql` → **[FULL backup Int 1]** → `validacion.sql`
- `deporte_c0_catalogos_censo.png` / `deporte_c0_catalogos_frag.png`
- Esperado: atleta **0**, participacion **0**

### Carga 1 — Río 2016
- Correr `Fase2/carga/deporte/01_ronda1_rio2016.sql` → **[dif 1]** → `validacion.sql`
- `deporte_c1_rio2016_censo.png` / `deporte_c1_rio2016_frag.png`
- Esperado: atleta **91**, participacion **91**

### Carga 2 — Tokio 2020
- Correr `Fase2/carga/deporte/02_ronda2_tokio2020.sql` → **[dif 2]** → `validacion.sql`
- `deporte_c2_tokio2020_censo.png` / `deporte_c2_tokio2020_frag.png`
- Esperado: atleta **150**, participacion **172**

### Carga 3 — París 2024
- Correr `Fase2/carga/deporte/03_ronda3_paris2024.sql` → **[dif 3]** → `validacion.sql`
- `deporte_c3_paris2024_censo.png` / `deporte_c3_paris2024_frag.png`
- Esperado: atleta **219**, participacion **263**

Guardar todo en: `Fase2/evidencias/deporte/`

---

# CICLO 3 — AÑO (todas las pruebas de cada edición)

> Los archivos son grandes (hasta 4.7 MB); Workbench puede tardar en abrirlos. Es normal.

### Reset a base vacía (`down -v` + `Start.bat`)

### Carga 0 — Catálogos
- Correr `00_catalogos.sql` → **[FULL backup Int 1]** → `validacion.sql`
- `anio_c0_catalogos_censo.png` / `anio_c0_catalogos_frag.png`
- Esperado: atleta **0**, participacion **0**

### Carga 1 — Río 2016
- Correr `Fase2/carga/anio/01_ronda1_rio2016.sql` → **[dif 1]** → `validacion.sql`
- `anio_c1_rio2016_censo.png` / `anio_c1_rio2016_frag.png`
- Esperado: atleta **14464**, participacion **17015**

### Carga 2 — Tokio 2020
- Correr `Fase2/carga/anio/02_ronda2_tokio2020.sql` → **[dif 2]** → `validacion.sql`
- `anio_c2_tokio2020_censo.png` / `anio_c2_tokio2020_frag.png`
- Esperado: atleta **24001**, participacion **33198**

### Carga 3 — París 2024
- Correr `Fase2/carga/anio/03_ronda3_paris2024.sql` → **[dif 3]** → `validacion.sql`
- `anio_c3_paris2024_censo.png` / `anio_c3_paris2024_frag.png`
- Esperado: atleta **30648**, participacion **44581**

Guardar todo en: `Fase2/evidencias/anio/`

---

## Después (etapa de Integrante 3: restauración)

Cuando Int 3 restaure, tomar las mismas 2 capturas (censo + frag) después de cada
restauración, para comparar contra las de arriba. Nombre:
`<tipo>_restaura_<full|diff1|diff2|diff3>_censo.png`.
Los conteos restaurados deben COINCIDIR con los de la carga correspondiente.

## Nota sobre SELECT *
La rúbrica menciona `SELECT *` "de cada tabla". El censo (COUNT) ya prueba que todas
cargaron. Si el auxiliar exige también `SELECT *`, usar la sección D de `validacion.sql`.
Confirmar con el auxiliar si alcanza con el censo o quiere también el `SELECT *`.
