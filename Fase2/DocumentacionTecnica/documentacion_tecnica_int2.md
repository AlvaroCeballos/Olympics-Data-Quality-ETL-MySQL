# Documentación técnica — Datos y validación (Integrante 2)

**Autora:** Yulianne Nicole López Elias — 202300659 (Integrante 2)  
**Curso:** Sistemas de Bases de Datos 2, USAC  
**Grupo:** 18  

> Secciones a cargo del Integrante 2: modelo E-R, metodología de carga y fragmentación.
> Se integran al PDF de documentación técnica que consolida el Integrante 3.

## 1. Modelo Entidad-Relación

El modelo de datos de Fase 2 reutiliza el esquema diseñado en el Proyecto 1, por tratarse
de la misma base de datos olímpica. El diagrama se encuentra en
`Fase2/ddl/ERD-OLIMPIADAS-G18.pdf` y el script de creación en `Fase2/ddl/olimpiada2s.sql`.

Es un modelo en **Tercera Forma Normal (3NF)** de **12 tablas**, con las siguientes
decisiones de diseño relevantes:

- **`pais` y `noc` están separadas.** `pais` es la entidad geográfica (código ISO de 3
  letras); `noc` es el Comité Olímpico Nacional. Se separan porque hay comités que no
  corresponden a un país soberano actual (ej. `URS`, `GDR`, `EUN`, `ROT`); por eso
  `noc.id_pais` admite `NULL`.
- **`sede` es una entidad propia**, separada de `pais` y de `olimpiada`. La sede es una
  ciudad; `olimpiada` (año + temporada) referencia a `sede` por `id_sede`. `temporada`
  es `VARCHAR` porque los datos incluyen más que Verano/Invierno (Intercalados 1906,
  Juveniles, etc.).
- **Jerarquía deportiva de 3 niveles:** `deporte → disciplina → evento`. Cuando una fuente
  no trae el nivel intermedio se genera una "disciplina puente" para no dejar eventos
  huérfanos.
- **`medalla` es un catálogo fijo de 4 filas** (`Gold`, `Silver`, `Bronze`, `NA`).
  `participacion.id_medalla` es `NOT NULL` y apunta a `NA` cuando no hubo premio.
- **`participacion` es la tabla de hechos:** una fila = un atleta en un evento de una
  edición. Las medidas registradas en esa edición (`altura_reg`, `peso_reg`, `edad`) se
  distinguen de las medidas base del atleta en la tabla `atleta`.
- **`poblacion_pais`** guarda la población por `(id_pais, anio)` (clave primaria compuesta).

Todas las tablas usan el motor **InnoDB**, requisito para que XtraBackup pueda tomar
respaldos físicos incrementales/diferenciales basados en LSN.

## 2. Metodología de carga

### 2.1 Origen de los datos

Los datos provienen de la base de datos del **Proyecto 1** (`olimpiadas`). Se extrajeron
mediante scripts de Python (`Fase2/carga/_generadores/`) que generan archivos `.sql` de
carga masiva, **preservando las claves primarias originales** para mantener la integridad
referencial entre catálogos y hechos.

### 2.2 Estrategia de tres cargas

Según el enunciado, se definieron tres tipos de carga, cada uno en una **instancia nueva**
(contenedor Docker reseteado con `docker compose down -v`):

| Tipo | Casos (ediciones) |
|---|---|
| Por año | Río 2016, Tokio 2020, París 2024 (todas las pruebas) |
| Por deporte | 100 m planos femenino, en Río 2016 / Tokio 2020 / París 2024 |
| Por deportista | Usain Bolt en Atenas 2004 / Pekín 2008 / Londres 2012 |

Cada tipo se carga en **4 pasos**: primero una **carga inicial de catálogos** (las 10
tablas de dimensión) y luego **3 rondas** con los hechos (`atleta` + `participacion`) de
cada edición. En total: **12 cargas** (3 iniciales + 9 rondas). Esto produce, por tipo,
**1 respaldo completo** (tras los catálogos) y **3 diferenciales** (tras cada ronda).

### 2.3 Deduplicación de atletas

Como un mismo atleta puede competir en varias ediciones, al cargar las rondas se inserta
cada atleta **una sola vez** (en la primera ronda donde aparece). Las rondas siguientes solo
agregan sus participaciones. Por eso, por ejemplo, Usain Bolt se inserta en la ronda de
Atenas 2004 y en Pekín/Londres solo crecen las participaciones.

### 2.4 Conteos esperados por carga (evidencia de validación)

| Tipo | Carga | atleta | participacion |
|---|---|---|---|
| deportista | catálogos | 0 | 0 |
| deportista | Atenas 2004 | 1 | 1 |
| deportista | Pekín 2008 | 1 | 4 |
| deportista | Londres 2012 | 1 | 7 |
| deporte | catálogos | 0 | 0 |
| deporte | Río 2016 | 91 | 91 |
| deporte | Tokio 2020 | 150 | 172 |
| deporte | París 2024 | 219 | 263 |
| año | catálogos | 0 | 0 |
| año | Río 2016 | 14 464 | 17 015 |
| año | Tokio 2020 | 24 001 | 33 198 |
| año | París 2024 | 30 648 | 44 581 |

Los catálogos son idénticos en los tres tipos (pais 487, noc 236, sede 45, olimpiada 63,
deporte 148, disciplina 149, evento 3152, equipo 20845, medalla 4, poblacion_pais 16930).

La integridad referencial se verificó: cero claves foráneas huérfanas en `participacion`
en todos los casos.

## 3. Fragmentación

### 3.1 Cómo se mide

La fragmentación se consulta desde `information_schema.TABLES` (script
`Fase2/validacion.sql`, bloque C): `DATA_LENGTH` (datos), `INDEX_LENGTH` (índices) y
`DATA_FREE` (espacio reservado sin usar). El porcentaje se calcula como
`DATA_FREE / (DATA_LENGTH + INDEX_LENGTH) * 100`.

Antes de medir se ejecuta `ANALYZE TABLE` para refrescar las estadísticas de InnoDB, ya que
la columna `TABLE_ROWS` es un **estimado** que InnoDB no actualiza inmediatamente tras una
carga masiva (puede reportar 0 aunque los datos estén cargados; el conteo exacto siempre se
obtiene con `COUNT(*)`).

### 3.2 Interpretación

- En tablas pequeñas el porcentaje puede superar el 100 % (ej. `poblacion_pais` ~224 %)
  porque InnoDB reserva un mínimo de espacio por tablespace aunque la tabla sea chica; no es
  fragmentación problemática.
- En el caso **deportista** la fragmentación es **insignificante** por el bajísimo volumen
  (1 a 7 participaciones): el espacio libre apenas cambia entre rondas.
- En el caso **año** (decenas de miles de filas) la fragmentación es donde adquiere valor
  analítico: el `espacio_libre_kb` de `atleta` y `participacion` se mueve de forma
  apreciable al crecer los datos ronda a ronda.

La comparación relevante es la de una **misma tabla antes y después de restaurar**: los
valores deben ser coherentes, confirmando que la restauración reprodujo el estado físico.
