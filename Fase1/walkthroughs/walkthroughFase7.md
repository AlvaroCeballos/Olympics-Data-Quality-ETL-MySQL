# Walkthrough — ETL Olimpiadas G18

## Fase 7: Validación Cruzada, Auditoría de Integridad y Conteos Finales ✅

### Qué se hizo

Se creó y ejecutó el script [`fase7_validacion.py`](file:///d:/Proyectos%20U/Bases%202/Proyecto%201/SBD2B_PROYECT1_2S2026_G18/etl/fase7_validacion.py) para auditar integralmente la calidad de los datos, la integridad referencial y el rendimiento de las consultas para los Stored Procedures de la Persona 3:

1. **Censo Global de las 12 Tablas:**
   - Verificación de que ninguna tabla quedó con 0 registros.
   - Conteo total consolidado de todas las entidades y la tabla de hechos.

2. **Auditoría de Claves Foráneas (13 Relaciones FK):**
   - Comprobación de que no existen registros huérfanos en ninguna relación del modelo relacional en 3NF.
   - Resultado: **0 violaciones de integridad referencial**.

3. **Auditoría de Calidad y Normalización:**
   - Comprobación de que no existen caracteres viñeta (`•`) ni secuencias mojibake en nombres de atletas.
   - Validación del dominio categórico de `sexo` (`'M'`, `'F'`) y `medalla` (`'Gold'`, `'Silver'`, `'Bronze'`, `'NA'`).
   - Cobertura de series demográficas del Banco Mundial: 1960 a 2023 completas.

4. **Simulación de Consultas para los Stored Procedures (Persona 3):**
   - **`sp_consultar_atleta`:** Consulta con filtros flexibles sobre ficha biográfica y desglose histórico de participaciones vía `JOIN` entre 7 tablas.
   - **`sp_consultar_pais`:** Consulta sobre condición de sede histórica y cálculo del medallero acumulado agrupado por edición y disciplina deportiva.

---

### Censo Consolidado de la Base de Datos (`olimpiadas`)

| Entidad / Tabla | Registros Cargados | Rol en el Modelo |
|---|:---:|---|
| `pais` | **35** | Catálogo maestro de países y territorios soberanos |
| `noc` | **21** | Comités Olímpicos Nacionales (100% vinculados a país) |
| `poblacion_pais` | **960** | Series demográficas 1960–2023 (15 países × 64 años) |
| `sede` | **12** | Ciudades anfitrionas con clave única `(ciudad, id_pais)` |
| `olimpiada` | **13** | Ediciones de los juegos con clave única `(anio, temporada)` |
| `atleta` | **26** | Catálogo maestro con 21 atributos (fechas ISO, medidas, WGS84) |
| `deporte` | **11** | Catálogo único de deportes |
| `disciplina` | **11** | Disciplinas con regla de disciplina puente aplicada (DT-003) |
| `evento` | **20** | Pruebas olímpicas específicas |
| `equipo` | **16** | Equipos y delegaciones con clave única `(nombre, id_noc)` |
| `medalla` | **4** | Catálogo semilla (*Gold, Silver, Bronze, NA*) |
| `participacion` | **41** | Tabla transaccional de hechos con todas sus FKs íntegras |

---

### Resultado de Auditoría de Claves Foráneas

```text
Auditoría de Claves Foráneas (13 Relaciones FK):
  [OK] noc -> pais                         -> 0 huérfanas
  [OK] sede -> pais                        -> 0 huérfanas
  [OK] olimpiada -> sede                   -> 0 huérfanas
  [OK] disciplina -> deporte               -> 0 huérfanas
  [OK] evento -> disciplina                -> 0 huérfanas
  [OK] equipo -> noc                       -> 0 huérfanas
  [OK] atleta -> pais (nacimiento)         -> 0 huérfanas
  [OK] poblacion_pais -> pais              -> 0 huérfanas
  [OK] participacion -> atleta             -> 0 huérfanas
  [OK] participacion -> evento             -> 0 huérfanas
  [OK] participacion -> olimpiada          -> 0 huérfanas
  [OK] participacion -> equipo             -> 0 huérfanas
  [OK] participacion -> medalla            -> 0 huérfanas

Integridad referencial 100% íntegra (0 violaciones de FK).
```

---

### Dictamen Final de la Persona 2

> [!NOTE]
> **ESTADO DE LA ETAPA:**  
> Todas las fases del pipeline ETL (Fase 0 a Fase 7) se encuentran completadas, documentadas y validadas con 100% de éxito.  
> La base de datos `olimpiadas` está totalmente preparada para la Persona 3 (creación y ejecución de los Stored Procedures analíticos).
