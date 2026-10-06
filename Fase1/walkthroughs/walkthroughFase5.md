# Walkthrough — ETL Olimpiadas G18

## Fase 5: Enriquecimiento — Fuentes 2 y 4 (Kaggle `athlete_events.csv`) ✅

### Qué se hizo

Se creó y ejecutó el script [`fase5_enriquecimiento.py`](file:///d:/Proyectos%20U/Bases%202/Proyecto%201/SBD2B_PROYECT1_2S2026_G18/etl/fase5_enriquecimiento.py) para integrar los datos de Kaggle 120 Years of Olympic History:

1. **Validación Cruzada con Fuente 4 (DT-015):**
   - Comparación directa con `athlete_events_datalab_sample.csv` confirmando paridad del 100% en columnas y registros.

2. **Deduplicación Cross-Source de Atletas (DT-002 y DT-001):**
   - Consulta sobre el catálogo maestro mediante matching key `(nombre_normalizado, sexo, anio_nacimiento_aprox)`.
   - Reutilización de atletas coincidentes e inserción de **6 nuevos atletas exclusivos de Kaggle** (*A Dijiang, A Lamusi, Gunnar Nielsen Aaby, Edgar Lindenau Aabye, Christine Jacoba Aaftink, Per Knut Aaland*) asignándoles `id_externo = NULL`.
   - Total de atletas en la base de datos incrementó de 15 a **21 atletas**.

3. **Enriquecimiento de Participaciones:**
   - Inserción y enriquecimiento de participaciones con las métricas registradas en cada edición: **`edad`**, **`altura_reg`** y **`peso_reg`**.
   - Total de participaciones en la base de datos incrementó de 15 a **30 participaciones** (15 con métricas puntuales de edición).
   - Verificación de claves foráneas: **0 huérfanas** en todas las relaciones.

---

### Resultado de Ejecución

```text
============================================================
  INICIO DE EJECUCIÓN: FASE 5 (Enriquecimiento Kaggle)
============================================================
  Archivo athlete_events: data_samples\athlete_events_sample.csv (15 registros)

Validación Cruzada con Fuente 4:
  [OK] DT-015 Confirmada: Fuente 4 es idéntica a Fuente 2 (100% paridad).

Deduplicación e Inserción:
  [OK] Atletas de Kaggle procesados: nuevos=6, reutilizados=9
  [OK] Participaciones registradas: 15 nuevas con métricas

Verificación de Tablas:
  - Total atletas: 21 (6 incorporados de Kaggle con id_externo = NULL)
  - Total participaciones: 30 (15 con métricas de edad/altura/peso)
  - Claves foráneas huérfanas en 'participacion': 0

[OK] Verificación de Fase 5 EXITOSA. Enriquecimiento Kaggle aplicado correctamente.
```

---

### Muestra de Participaciones Enriquecidas

| Atleta | Sexo | Edición | Evento | Edad | Altura | Peso | Medalla |
|---|:---:|:---:|---|:---:|:---:|:---:|:---:|
| A Dijiang | M | 1992 Summer | Basketball Men's Basketball | 24 | 180 cm | 80 kg | NA |
| A Lamusi | M | 2012 Summer | Judo Men's Extra-Lightweight | 23 | 170 cm | 60 kg | NA |
| Edgar Lindenau Aabye | M | 1900 Summer | Tug-Of-War Men's Tug-Of-War | 34 | - | - | Gold |
| Christine Jacoba Aaftink | F | 1988 Winter | Speed Skating Women's 500 metres | 21 | 185 cm | 82 kg | NA |
| Per Knut Aaland | M | 1994 Winter | Cross Country Skiing Men's 10 kilometres | 33 | 188 cm | 75 kg | NA |

---

### Archivos Creados/Modificados

| Archivo | Acción |
|---|---|
| [`etl/fase5_enriquecimiento.py`](file:///d:/Proyectos%20U/Bases%202/Proyecto%201/SBD2B_PROYECT1_2S2026_G18/etl/fase5_enriquecimiento.py) | ✨ Creado y ejecutado exitosamente |
| [`walkthroughs/walkthroughFase5.md`](file:///d:/Proyectos%20U/Bases%202/Proyecto%201/SBD2B_PROYECT1_2S2026_G18/walkthroughs/walkthroughFase5.md) | ✨ Documentación generada |
| [`implementation_plan.md`](file:///d:/Proyectos%20U/Bases%202/Proyecto%201/SBD2B_PROYECT1_2S2026_G18/implementation_plan.md) | 🔧 Actualizado estado de Fase 5 a Completada |
