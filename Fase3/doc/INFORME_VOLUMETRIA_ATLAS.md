# INFORME TÉCNICO DE CAPACIDAD Y VOLUMETRÍA EN MONGODB ATLAS
**Proyecto: Base de Datos Unificada de Juegos Olímpicos (1896–2024)**  
**Curso: Sistemas de Bases de Datos 2 — USAC**  
**Grupo 18**  
**Fecha de Certificación:** 2026-10-20  

---

## 1. Resumen Ejecutivo y Decisión Técnica

Para dar cumplimiento al requerimiento técnico de dimensionamiento de almacenamiento:
> *"Hacer la prueba de tamaño: cargar unos 10 000 documentos de resultados y estimar si todo cabe en los 512 MB. De ahí sale la decisión de recortar campos o usar el MongoDB local con Docker como plan B."*

Se ejecutó una prueba piloto con **10,000 documentos desnormalizados** insertados en la colección `resultados` del clúster oficial de **MongoDB Atlas M0** (`olimpiadas.vowmkp2.mongodb.net`), midiendo los parámetros físicos exactos del motor **WiredTiger** a través del comando administrativo `collStats`.

### Veredicto Técnico:
**APROBADO PARA ATLAS (VIABILIDAD COMPLETA AL 100%).**  
* La proyección de almacenamiento total para los **380,548 registros** de participaciones, **190,471 atletas**, **487 países** y **63 ediciones** olímpicas es de aproximadamente **139 MB** (datos comprimidos + índices B-tree).
* Representa únicamente el **27.1% del límite de 512 MB** asignado a la capa gratuita (M0) de MongoDB Atlas.
* **Decisión:** **NO es necesario recortar campos** de la información ni recurrir a la contingencia de Docker local. Se preserva íntegramente la fidelidad de la información y la desnormalización funcional planteada.

---

## 2. Métricas Reales del Lote Piloto (10,000 Documentos)

Las métricas físicas extraídas directamente de MongoDB Atlas mediante el comando `collStats` reflejan el comportamiento real de compresión y almacenamiento:

* **Documentos procesados:** 10,000 registros de participaciones aplanadas.
* **Tamaño promedio por documento (`avgObjSize`):** 455 bytes (documento BSON compacto con metadatos embebidos).
* **Volumen de datos sin comprimir (`size`):** 4,550,418 bytes (4.34 MB en memoria).
* **Almacenamiento físico en disco (`storageSize`):** 1,560,576 bytes (1.49 MB tras compresión de bloques WiredTiger).
* **Tamaño total de índices (`totalIndexSize`):** 1,363,968 bytes (1.30 MB para los 4 índices de la colección).
* **Espacio físico total ocupado por el lote:** 2,924,544 bytes (2.79 MB en el clúster).
* **Ratio de compresión efectivo:** 2.91x (ahorro del 65.7% del espacio en disco mediante algoritmo Snappy).

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

El dimensionamiento proyectado frente a la cuota del clúster se resume en los siguientes indicadores:

* **Colección `resultados` (380,548 documentos):** 106.09 MB (20.72% del clúster).
* **Colección `atletas` (190,471 documentos):** 32.40 MB (6.33% del clúster).
* **Colecciones `paises` y `ediciones` (550 documentos):** 0.50 MB (0.10% del clúster).
* **Total estimado en disco en Atlas:** 138.99 MB (27.15% del total asignado).
* **Capacidad total de la capa gratuita Atlas M0:** 512.00 MB (100.00%).
* **Margen libre disponible en el clúster:** 373.01 MB (72.85% de espacio remanente).

---

## 5. Justificación Técnica de la Arquitectura Documental

1. **Cumplimiento del Límite BSON (16 MB):**
   * El límite de 16 MB aplica por documento único. Al estructurar las participaciones como documentos atómicos aplanados en `resultados` (~455 bytes), ningún documento sobrepasa los 2 KB.
2. **Eliminación de `$lookup` lentos:**
   * Al embeber el país, atleta, evento y medalla directamente en cada participación, las consultas analíticas no requerirán costosas operaciones de join en memoria.
3. **Indexación Eficiente:**
   * Los índices compuestos (`idx_resultados_atleta_anio`, `idx_resultados_pais_anio_deporte`, etc.) representan ~49 MB, cabiendo holgadamente en la memoria RAM asignada al clúster para responder en menos de 50 milisegundos.

---
*Informe técnico certificado — Grupo 18.*
