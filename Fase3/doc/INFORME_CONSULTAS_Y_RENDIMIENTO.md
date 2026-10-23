# Informe Técnico — Consultas y Rendimiento (Integrante 3)

**Autora:** Yulianne Nicole López Elias — 202300659 (Integrante 3)
**Curso:** Sistemas de Bases de Datos 2, USAC
**Grupo:** 18
**Fecha:** octubre 2026

---

## 1. Objetivo

Diseñar e implementar las dos consultas analíticas requeridas por el enunciado
de la Fase 3 (incisos c y d), aprovechando el modelo documental desnormalizado
cargado por los Integrantes 1 y 2 en MongoDB Atlas, y certificar que las
consultas responden en tiempos aceptables y producen resultados equivalentes
a los stored procedures de la Fase 1.

## 2. Scripts entregados

Los dos scripts obligatorios (incisos c y d del enunciado) y los dos scripts
complementarios de rendimiento residen en el repositorio en:

```
Fase3/consultas/
├── consulta_atleta.py   (inciso c)
└── consulta_pais.py     (inciso d)

Fase3/pruebas/
├── casos_prueba.py       (medición de tiempos — complementario)
└── prueba_paridad.py     (paridad MySQL vs MongoDB — complementario)
```

## 3. Diseño de la consulta por atleta

El script `consulta_atleta.py` reproduce la firma del stored procedure
`sp_consultar_atleta(p_nombre, p_anio, p_deporte, p_pais)` de la Fase 1,
manteniendo el nombre como parámetro obligatorio y los filtros de año,
deporte y país como opcionales.

**Flujo de la consulta:**

1. Búsqueda de la ficha en la colección `atletas` por `$regex` sobre tres
   campos (`nombre`, `nombre_completo`, `nombre_norm`) para capturar las
   variantes de nombres y nombres completos. Se recuperan hasta 100
   coincidencias para no perder al atleta buscado cuando el apellido es
   común (ej. hay 14 atletas con apellido "Phelps").
2. Extracción del `id_atleta` (campo `_id`) de las fichas coincidentes.
3. Consulta a la colección `resultados` con el filtro
   `atleta.id ∈ [ids]` + los filtros opcionales, aprovechando el índice
   `idx_resultados_atleta_anio`.
4. Proyección mínima (solo los campos que se muestran al usuario) para
   reducir el tráfico de red.

El filtro por país distingue entre código NOC de 3 letras (coincidencia
exacta en `pais.codigo` o `noc.codigo`) y nombre (coincidencia por `$regex`
en `pais.nombre`), tal como lo hace el stored procedure original.

## 4. Diseño de la consulta por país

El script `consulta_pais.py` reproduce la firma de `sp_consultar_pais(p_pais,
p_anio_inicio, p_anio_fin, p_solo_medallas)`.

**Flujo de la consulta:**

1. Resolución del país: si el parámetro tiene 3 caracteres se busca por
   `codigo` (coincidencia exacta); si no, por `nombre` y `nombre_norm` con
   `$regex` insensible a mayúsculas.
2. Historial de sedes: viene embebido en el documento del país
   (`sedes_historicas`), por lo que no requiere una consulta adicional. Se
   devuelve completo sin filtrar por año, siguiendo el comportamiento del SP
   de MySQL.
3. Medallero histórico acumulado: `aggregate` sobre `resultados` filtrando
   por `pais.codigo` o `noc.codigo` y aplicando los rangos de año y el
   filtro de medallas si fueron pasados. Usa `$cond` para contar por tipo
   de medalla en una sola pasada.
4. Desglose por edición y disciplina: segundo `aggregate` que agrupa por
   `(anio, temporada, deporte, disciplina)` y acumula los conteos.

## 5. Rendimiento

Cada script registra el tiempo total de la consulta y lo imprime como
`tiempo_ms` al final de la salida. Se midió el rendimiento con una suite de
11 casos representativos (6 de atleta, 5 de país), con los resultados
siguientes:

| Consulta | Tiempo medido |
|---|---:|
| `consulta_atleta` — Phelps | 1194 ms |
| `consulta_atleta` — Phelps + año 2008 | 406 ms |
| `consulta_atleta` — Bolt + deporte Athletics | 473 ms |
| `consulta_atleta` — Barrondo + país GUA | 403 ms |
| `consulta_atleta` — Ruano | 421 ms |
| `consulta_atleta` — Jean Borotra | 405 ms |
| `consulta_pais` — GUA | 302 ms |
| `consulta_pais` — GUA solo medallas | 178 ms |
| `consulta_pais` — FRA | 555 ms |
| `consulta_pais` — USA 2016–2024 | 272 ms |
| `consulta_pais` — Guatemala (por nombre) | 180 ms |

La captura de la suite registra resultados de aproximadamente 169 ms a
1.24 s. Otra captura de `consulta_atleta.py "Phelps"` registra 1.84 s, por lo
que el tiempo depende del caso y de la ejecución; no debe garantizarse un
máximo menor a 1.3 s.

**Evidencia:** `imgs/casos_prueba_suite.png` y
`imgs/consulta_atleta_phelps.png`.

## 6. Prueba de paridad MySQL vs MongoDB

Para verificar que la migración preservó la semántica de las consultas, se
ejecutaron los stored procedures de la Fase 1 (`sp_consultar_atleta` y
`sp_consultar_pais`) y los scripts equivalentes de la Fase 3 con los mismos
parámetros, y se compararon los conteos. Resultados:

| Caso | Fichas / participaciones / sedes / medallero | Observación |
|---|---|---|
| `atleta` Phelps | 10 fichas, 69 participaciones | Los conteos visibles coinciden. |
| `atleta` Bolt + Athletics | 10 fichas, 19 participaciones | Los conteos visibles coinciden. |
| `atleta` Barrondo + GUA | 4 fichas, 8 participaciones | Los conteos visibles coinciden. |
| `pais` GUA | 0 sedes, 1-1-1 | Los conteos visibles coinciden. |
| `pais` FRA | 6 sedes, medallas 834-996-1027; MySQL registra 1,028 bronces | Difiere en un bronce. |
| `pais` USA 2016–2024 | 8 sedes, medallas 411-308-275; MySQL registra 276 bronces | Difiere en un bronce. |

La captura presenta dos diferencias unitarias en el total de bronces. En
informes anteriores se sugirió que podrían relacionarse con `es_empate`, pero
la prueba no inspecciona las participaciones discrepantes y no confirma esa
causa. El script compara algunos conteos, no la igualdad de todas las filas,
y no marca el proceso como fallido automáticamente al hallar diferencias.
Por ello, la paridad exacta de la consulta por país queda pendiente de
aclaración.

**Evidencia:** `imgs/paridad_mysql_mongo.png`.

## 7. Verificación visual de la infraestructura

Antes de ejecutar las consultas se verificó visualmente en MongoDB Atlas la
disponibilidad de los datos y los índices que soportan las consultas:

- `imgs/atlas_colecciones.png` — Vista Browse Collections con los conteos
  oficiales (`atletas` 190,471; `ediciones` 63; `paises` 487;
  `resultados` 380,548).
- `imgs/atlas_indices.png` — Vista de índices de la colección `resultados`,
  mostrando los índices compuestos definidos por el Integrante 1
  (`idx_resultados_atleta_anio`, `idx_resultados_pais_anio_deporte`,
  `idx_resultados_noc_anio`).

## 8. Capturas de ejecución

- `imgs/consulta_atleta_phelps.png` — Ejecución de
  `consulta_atleta.py "Phelps"` con el resultado y el tiempo.
- `imgs/consulta_pais_gua.png` — Ejecución de
  `consulta_pais.py GUA --solo-medallas` mostrando los tres medallistas
  históricos de Guatemala y el tiempo.

## 9. Conclusiones

- Los dos scripts obligatorios (incisos c y d) están implementados en Python
  con `pymongo`, usan los parámetros equivalentes a los stored procedures de
  la Fase 1 y aprovechan los índices compuestos definidos sobre las
  colecciones.
- Los tiempos documentados varían entre ejecuciones; una captura registra
  1.84 s para Phelps. Deben comprobarse desde la red y el clúster de la
  evaluación.
- La muestra presenta diferencias unitarias de bronce para Francia y
  Estados Unidos. Su causa aún no está demostrada y la prueba no realiza
  comparación fila por fila; no corresponde afirmar una paridad funcional
  total.
