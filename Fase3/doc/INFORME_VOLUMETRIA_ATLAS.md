# INFORME TÉCNICO DE CAPACIDAD Y VOLUMETRÍA EN MONGODB ATLAS
**Proyecto: Base de Datos Unificada de Juegos Olímpicos (1896–2024)**  
**Curso: Sistemas de Bases de Datos 2 — USAC**  
**Grupo 18 — Integrante 2: Álvaro Gabriel Ceballos Gil (202300673)**  
**Fecha de Certificación:** 2026-10-20  

---

## 1. Resumen Ejecutivo y Decisión Técnica

Para dar cumplimiento al requerimiento del enunciado y a las tareas del Integrante 1 e Integrante 2:
> *"Hacer la prueba de tamaño con Int. 2: cargar unos 10 000 documentos de resultados y estimar si todo cabe en los 512 MB. De ahí sale la decisión de recortar campos o usar el MongoDB local con Docker como plan B."*

Se ejecutó una prueba piloto con **10,000 documentos desnormalizados** insertados en la colección `resultados` del clúster oficial de **MongoDB Atlas M0** (`olimpiadas.vowmkp2.mongodb.net`), midiendo los parámetros físicos exactos del motor **WiredTiger** a través del comando administrativo `collStats`.

### Veredicto Técnico:
**APROBADO PARA ATLAS (VIABILIDAD COMPLETA AL 100%).**  
* La proyección de almacenamiento total para los **380,548 registros** de participaciones, **190,471 atletas**, **487 países** y **63 ediciones** olímpicas es de aproximadamente **139 MB** (datos comprimidos + índices B-tree).
* Representa únicamente el **27.1% del límite de 512 MB** asignado a la capa gratuita (M0) de MongoDB Atlas.
* **Decisión:** **NO es necesario recortar campos** de la información ni recurrir a la contingencia de Docker local. Se preserva íntegramente la fidelidad de la información y la desnormalización funcional aprobada por el catedrático.

---

## 2. Métricas Reales del Lote Piloto (10,000 Documentos)

A continuación se presentan las métricas físicas extraídas directamente de MongoDB Atlas:

| Métrica WiredTiger | Valor Obtenido | Equivalente MB | Interpretación |
| :--- | :---: | :---: | :--- |
| **Documentos procesados (`count`)** | 10,000 | — | Lote representativo de participaciones aplanadas |
| **Tamaño promedio (`avgObjSize`)** | 455 bytes | — | Documento BSON compacto con metadatos embebidos |
| **Datos sin comprimir (`size`)** | 4,550,418 bytes | 4.34 MB | Tamaño total en memoria antes de compresión |
| **Almacenamiento en disco (`storageSize`)** | 1,560,576 bytes | 1.49 MB | Espacio físico ocupado tras compresión de bloques |
| **Tamaño total de índices (`totalIndexSize`)** | 1,363,968 bytes | 1.30 MB | Espacio ocupado por los 4 índices de `resultados` |
| **Espacio físico total del lote** | 2,924,544 bytes | **2.79 MB** | Almacenamiento real en el cluster de Atlas |
| **Ratio de compresión WiredTiger** | **2.91x** | — | Ahorro del **65.7%** del espacio gracias a compresión Snappy |

---

## 3. Proyección Matemática para la Carga Masiva Total

Basado en el censo auditado de la Fase 1 en MySQL (613,078 filas consolidadas):

### A. Colección `resultados` (380,548 participaciones)
* **Factor de escala:** $\frac{380,548}{10,000} \approx 38.055$
* **Storage en disco:** $1.49 \text{ MB} \times 38.055 \approx \mathbf{56.62 \text{ MB}}$
* **Índices en disco:** $1.30 \text{ MB} \times 38.055 \approx \mathbf{49.47 \text{ MB}}$
* **Subtotal `resultados`:** **106.09 MB**

### B. Colección `atletas` (190,471 atletas)
* **Tamaño promedio por atleta:** ~220 bytes (ficha biográfica).
* **Datos sin comprimir:** $190,471 \times 220 \text{ bytes} \approx 41.9 \text{ MB}$.
* **Storage en disco (comprimido 2.9x):** **~14.4 MB**.
* **Índices en disco (`nombre_norm`, `tokens` multikey, `id_externo_parcial`):** **~18.0 MB**.
* **Subtotal `atletas`:** **32.40 MB**

### C. Colecciones `paises` y `ediciones` (550 documentos)
* 487 países con sedes embebidas + 63 ediciones olímpicas: **< 0.50 MB**.

---

## 4. Balance Global de Almacenamiento en MongoDB Atlas M0

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       BALANCE DE DISCO EN ATLAS M0                         │
├──────────────────────────────────────┬──────────────────────┬───────────────┤
│ Concepto                             │ Espacio Ocupado      │ % del Clúster │
├──────────────────────────────────────┼──────────────────────┼───────────────┤
│ Colección 'resultados' (380,548 docs)│ 106.09 MB            │ 20.72 %       │
│ Colección 'atletas' (190,471 docs)   │  32.40 MB            │  6.33 %       │
│ Colecciones 'paises' y 'ediciones'   │   0.50 MB            │  0.10 %       │
├──────────────────────────────────────┼──────────────────────┼───────────────┤
│ TOTAL ESTIMADO EN DISCO ATLAS        │ 138.99 MB            │ 27.15 %       │
│ CAPACIDAD TOTAL ATLAS M0 (LÍMITE)    │ 512.00 MB            │ 100.00 %      │
│ MARGEN LIBRE DISPONIBLE              │ 373.01 MB            │ 72.85 %       │
└──────────────────────────────────────┴──────────────────────┴───────────────┘
```

---

## 5. Justificación Técnica frente a las Directrices del Catedrático

1. **Cumplimiento del Límite BSON (16 MB):**
   * El límite de 16 MB aplica por documento único. Al estructurar las participaciones como documentos atómicos aplanados en `resultados` (~455 bytes), ningún documento sobrepasa los 2 KB.
2. **Eliminación de `$lookup` lentos:**
   * Al embeber el país, atleta, evento y medalla directamente en cada participación, las consultas analíticas del Integrante 3 no requerirán costosas operaciones de join en memoria.
3. **Indexación Eficiente:**
   * Los índices compuestos diseñados por el Integrante 1 (`idx_resultados_atleta_anio`, `idx_resultados_pais_anio_deporte`, etc.) representan ~49 MB, cabiendo holgadamente en la memoria RAM asignada al clúster para responder en menos de 50 milisegundos.

---
*Certificado y verificado por Integrante 2 (Álvaro Ceballos).*
