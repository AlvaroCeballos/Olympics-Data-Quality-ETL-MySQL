# Walkthrough — ETL Olimpiadas G18

## Fase 3: Tablas de Contexto (`sede`, `olimpiada`, `deporte`, `disciplina`, `evento`, `equipo`) ✅

### Qué se hizo

Se creó el script [`fase3_contexto.py`](file:///d:/Proyectos%20U/Bases%202/Proyecto%201/SBD2B_PROYECT1_2S2026_G18/etl/fase3_contexto.py) para procesar los datos contextuales de `results.csv_sample.csv` (Olympedia) y `athlete_events_sample.csv` (Kaggle):

1. **Carga de `sede` y `olimpiada`:**
   - Parseo de la cadena `Games` hacia `(anio, temporada, nombre_juegos)`.
   - Resolución de la ciudad anfitriona consultando `athlete_events.csv` con respaldo en un **catálogo histórico oficial (DT-022)** para cubrir ediciones históricas como 1912 Summer (Stockholm) y 1924 Summer (Paris).
   - Vínculo automático de la ciudad con su entidad geográfica en `pais`.
   - Total resultante: **9 sedes** y **10 olimpiadas** (ediciones de 1900 a 2012, Summer y Winter).

2. **Carga de la Jerarquía Deportiva 3NF (`deporte`, `disciplina`, `evento`):**
   - **Deporte:** Ingesta de nombres únicos derivados de `Discipline` (Olympedia) y `Sport` (Kaggle). Total: **7 deportes**.
   - **Disciplina:** Creación de disciplinas hijas y aplicación de la regla de **disciplina puente (DT-003)** para fuentes Kaggle (`disciplina.nombre = deporte.nombre`). Total: **7 disciplinas** (100% con `id_deporte` asignado).
   - **Evento:** Ingesta de pruebas olímpicas específicas vinculadas a su respectiva disciplina (`Singles, Men`, `Doubles, Men`, `Basketball Men's Basketball`, etc.). Total: **13 eventos**.

3. **Carga de `equipo`:**
   - Resolución de comités olímpicos correspondientes en la tabla `noc` (aprovisionando delegaciones on-the-fly según **DT-024** si no existían).
   - Aplicación de **DT-023**: Para pruebas individuales donde `Team` es nulo o vacío en `results1.csv`, se asigna como nombre de equipo la delegación oficial (ej. `"France"` o `"FRA"`), preservando los nombres de parejas/clubes en eventos de dobles.
   - Total resultante: **15 equipos** (100% con `id_noc` asignado).

4. **Documentación:**
   - Registradas decisiones **DT-022**, **DT-023** y **DT-024** en [`decisiones_tecnicas.md`](file:///d:/Proyectos%20U/Bases%202/Proyecto%201/SBD2B_PROYECT1_2S2026_G18/decisiones_tecnicas.md).

---

### Resultado de Ejecución

```text
============================================================
  INICIO DE EJECUCION: FASE 3 (Carga de Contexto)
============================================================
  Archivo results: data_samples\results.csv_sample.csv (15 registros)
  Archivo athlete_events: data_samples\athlete_events_sample.csv (15 registros)

Tablas cargadas:
- sede: 9 registros (100% vinculadas a pais)
- olimpiada: 10 registros (100% vinculadas a sede)
- deporte: 7 registros
- disciplina: 7 registros (100% vinculadas a deporte)
- evento: 13 registros (100% vinculados a disciplina)
- equipo: 15 registros (100% vinculados a noc)

Comprobando integridad de claves foráneas:
  FK sede -> pais huérfanas: 0
  FK olimpiada -> sede huérfanas: 0
  FK disciplina -> deporte huérfanas: 0
  FK evento -> disciplina huérfanas: 0
  FK equipo -> noc huérfanas: 0

[OK] Verificación de Fase 3 EXITOSA. Todas las tablas y FKs están conformes.
```

---

### Archivos Creados/Modificados

| Archivo | Acción |
|---|---|
| [`etl/fase3_contexto.py`](file:///d:/Proyectos%20U/Bases%202/Proyecto%201/SBD2B_PROYECT1_2S2026_G18/etl/fase3_contexto.py) | ✨ Creado y ejecutado exitosamente |
| [`decisiones_tecnicas.md`](file:///d:/Proyectos%20U/Bases%202/Proyecto%201/SBD2B_PROYECT1_2S2026_G18/decisiones_tecnicas.md) | 🔧 Actualizado con DT-022, DT-023 y DT-024 |
| [`walkthroughs/walkthroughFase3.md`](file:///d:/Proyectos%20U/Bases%202/Proyecto%201/SBD2B_PROYECT1_2S2026_G18/walkthroughs/walkthroughFase3.md) | ✨ Documentación generada |
