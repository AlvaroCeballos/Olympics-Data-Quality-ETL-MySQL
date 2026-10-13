

## 3. Resumen Ejecutivo

Este proyecto está diseñado para que los estudiantes apliquen de manera integral sus competencias en administración de bases de datos, específicamente en la gestión de respaldos y restauración de información. El desafío central consiste en gestionar el ciclo completo de copia de seguridad y recuperación de datos.

Los estudiantes trabajarán con la base de datos de fase previa. A través de este proyecto, aprenderán la diferencia fundamental entre las estrategias de respaldo: completos (*full backup*), incrementales (*incremental backup*) y diferenciales (*differential backup*).

El proceso requerirá que los estudiantes realicen carga masiva de datos desde archivos Excel o que se generen los datos a través de script, ejecutan respaldos diarios utilizando comandos en consola (no herramientas visuales), y posteriormente restauren la base de datos desde estos respaldos para validar su integridad. Este ciclo de creación y restauración permitirá a los estudiantes comprender las ventajas y limitaciones de cada estrategia de respaldo, y desarrollar la capacidad de tomar decisiones informadas sobre cuál utilizar en diferentes escenarios.

---

## 4. Enunciado del Proyecto

### 4.1 Descripción del problema o necesidad a resolver
Se les ha solicitado cargar la información relacionada con los datos de las Olimpiadas (Juegos Olímpicos). Para ello, se utilizará una estrategia dividida en 3 rondas de carga de datos:
* **Carga 1:** Cargas por año
* **Carga 2:** Cargas por deporte (por año / evento)
* **Carga 3:** Cargas por deportista (por año / por evento)

El desafío principal consiste en:
* Cargar información hacia una base de datos relacional (SQLServer, MySQL, Oracle, PostgreSQL) normalizada.
* Ejecutar respaldos utilizando las siguientes estrategias: respaldo completo y respaldos incremental o diferencial.
* Medir y comparar el rendimiento de las estrategias en términos de tiempo de restauración.
* Analizar resultados para determinar cuál estrategia es más apropiada para el volumen de datos manejado.
* Garantizar recuperabilidad validando que los respaldos puedan restaurarse completamente y sin pérdida de datos.

El estudiante debe demostrar competencia en la administración de bases de datos desde línea de comandos, comprendiendo que, en ambientes empresariales, los DBAs (*Database Administrators*) deben dominar estas herramientas para garantizar la seguridad y disponibilidad de la información.

### 4.2 Alcance del proyecto

#### Alcance obligatorio:
Para cada tipo de carga (por año, por deporte, por deportista):
* En una instancia de base de datos nueva realizar una carga inicial.
* Ejecutar backup completo (*full backup*) luego de la carga inicial.
* Ejecutar backup incremental (o diferencial) luego de cada carga por año o evento siguiente (hasta 3 cargas de datos).
* Registrar mediante capturas de pantalla: `SELECT *` y `SELECT COUNT(*)` de cada tabla después de cada carga.
* Eliminar la base de datos completa.
* Restaurar respaldo completo registrando tiempo de restauración.
* Restaurar respaldo incremental registrando tiempo de restauración.
* Validar integridad mediante capturas de `SELECT *` y `SELECT COUNT(*)` después de cada restauración.
* Realizar análisis comparativo de tiempos de restauración entre ambas estrategias.
* Presentar conclusiones sobre qué tipo de backup es más recomendado.

#### Alcance opcional:
* Implementar compresión en los archivos de backup para optimizar espacio en disco.
* Realizar programación de backups automáticos mediante scripts cron.
* Implementar cifrado en los archivos de backup.
* Crear alertas de validación de integridad posterior a la restauración.

### 4.3 Recursos y herramientas a utilizar

| Tipo (Obligatorio / Opcional) | Categoría (Software / Hardware / Plataforma / Etc.) | Descripción |
| :--- | :--- | :--- |
| **Obligatorio** | Software | Motor de base de datos relacional: PostgreSQL, MySQL, entre otros. |
| **Obligatorio** | Software | Herramienta para respaldos físicos (no dumps), MS SQL Server Management, Xtrabackup, entre otros. |
| **Opcional** | Software | Manejador gráfico de bases de datos: MS SQL Server Management, MySQL Workbench, entre otros. |

### 4.4 Entregables
A continuación se detalla cada uno de los elementos que deberá presentar el estudiante:

| Tipo | Descripción |
| :--- | :--- |
| **Documentación Técnica** | Documento PDF que incluye: descripción de la metodología, modelos entidad-relación utilizado, plan de respaldo, especificaciones técnicas del servidor, análisis detallado de resultados comparativos, y justificación de conclusiones. |
| **Código Fuente** | Scripts SQL para crear la base de datos, scripts de carga de datos desde archivos, scripts de respaldo (full e incremental), scripts de restauración, y logs de ejecución comentados. |
| **Manual de Usuario** | Guía práctica que explica paso a paso cómo realizar cada tipo de backup, cómo restaurar desde respaldos, interpretación de registros de respaldo, y procedimientos de validación post-restauración. |

---

## 5. Material de apoyo

| Categoría (Manual / Documentación oficial / Ejemplo / Etc.) | Link | Descripción |
| :--- | :--- | :--- |
| **Documentación oficial** | https://docs.percona.com/percona-xtrabackup/8.4/backup-overview.html | Herramienta de terceros para copias de seguridad de bases de datos. |
| **Documentación o tutorial** | https://labex.io/es/tutorials/docker-how-to-manage-docker-persistent-storage-493634 | Documentación para almacenamiento persistente en caso de usar Docker. |

*\*El link es opcional para una mejor guía del material de apoyo.*

---

## 6. Metodología

### Fase 1: Preparación y Diseño
Los estudiantes analizarán las estrategias para realizar las copias de seguridad y restauración; deben utilizar la copia de seguridad completa y elegir entre copia diferencial o incremental dependiendo de las limitaciones del sistema de bases de datos elegido. Realizarán esta planificación y prepararán el entorno de trabajo estableciendo rutas de almacenamiento para los respaldos.

Para cada tipo de carga los estudiantes deberán elegir, por ejemplo:
* **Carga por año:** París 2024, Tokio 2020, Río 2016.
* **Carga por deporte:** Por ejemplo 100 metros planos femeninos, de las ediciones París 2024, Tokio 2020, Río 2016.
* **Carga por deportista:** Usain Bolt en Atenas 2004 (Grecia), Pekín 2008 (China), Londres 2012 (Reino Unido).

### Fase 2: Carga de Datos
Se cargarán datos masivamente desde cualquier medio donde tengan los datos, inclusive su base de datos del Proyecto 1:
* **Día 1:** Cargas por año
* **Día 2:** Cargas por deporte
* **Día 3:** Cargas por deportista

Al final de cada tipo de carga (ejecución de full backup, backup incremental/diferencial): Deben realizar capturas de validación y obtener el nivel de fragmentación de las tablas.

### Fase 3: Restauración copias de seguridad
Para cada tipo de carga:
* Eliminar la base de datos y restaurar respaldo completo registrando tiempos de restauración.
* Restaurar cada uno de los 3 backups incrementales, registrando tiempo de restauración y al finalizar.

### Fase 4: Análisis y Conclusiones
Compararán resultados obtenidos, crearán tablas comparativas, analizarán ventajas/desventajas de cada estrategia, y elaborarán recomendaciones basadas en datos reales.

> **Nota:** Todas las capturas de pantalla deben mostrar fecha y hora del sistema operativo.

---

## 7. Cronograma

| Tipo | General | Carga Por Año | Carga por Deporte | Carga por Deportista |
| :--- | :--- | :--- | :--- | :--- |
| **Fase 1: Preparación y Diseño** | Día 1 | | | |
| **Fase 2: Carga de Datos** | | Día 2 | Día 3 | Día 4 |
| **Fase 3: Restauración de Full Backup** | | Día 2 | Día 3 | Día 4 |
| **Fase 4: Análisis y Conclusiones** | | Día 2 | Día 3 | Día 4 |

---

## 8. Rúbrica de Calificación

En esta sección se aborda todo lo relacionado a la calificación, lo que permite claridad para el estudiante y el tutor académico de los aspectos a evaluar y los mismos que conocen desde el inicio por lo que todo proyecto debe incluirlos desde el inicio.

### 8.1 Requisitos para optar a la calificación
Antes de la evaluación del proyecto, debe cumplir con los requisitos que se indiquen en esta sección; de no cumplir usted tendrá una nota con valor de cero puntos.

| Tema | Descripción | Cumple (Si/No) |
| :--- | :--- | :---: |
| **Entrega formal** | Presenta todos los archivos y evidencias en el tiempo indicado. | |
| **Funcionamiento mínimo** | El sistema ejecuta correctamente las funciones obligatorias. | |
| **Originalidad** | El proyecto no presenta plagio ni copia directa no referenciada. | |
| **Documentación** | Incluye manual técnico y manual de usuario. | |
| **Repositorio** | Entrega código ordenado y funcional. | |
| **Entrega en UEDI** | Todos los integrantes entregan en UEDI. | |

### 8.2 Detalle de la Calificación

| No. | Criterio de evaluación | Punteo máximo | Satisfactorio (100% - 61%) | Necesita mejorar (60% - 0%) | Punteo Obtenido |
| :--- | :--- | :---: | :--- | :--- | :---: |
| **1** | **Habilidades** | **40** | | | |
| 1.1 | **Documentación Técnica** | 15 | **Descripción:** La documentación presenta el plan de respaldo, especificaciones técnicas, análisis detallado de resultados con gráficos comparativos, y conclusiones bien fundamentadas sobre qué tipo de backup es más apropiado.<br><br>**Rango:** 15 - 9 | **Descripción:** La documentación está incompleta, no muestra análisis comparativo claro, carece de gráficos o conclusiones débilmente justificadas.<br><br>**Rango:** 8 - 0 | |
| 1.2 | **Manual de Usuario** | 10 | **Descripción:** El manual explica claramente los procedimientos de respaldo y restauración, incluye comandos específicos, ejemplos de ejecución, interpretación de logs y validación de integridad.<br><br>**Rango:** 10 - 6 | **Descripción:** El manual es confuso, carece de comandos específicos, no explica adecuadamente cómo restaurar o validar integridad.<br><br>**Rango:** 5 - 0 | |
| 1.3 | **Código Fuente Organizado** | 15 | **Descripción:** Los scripts SQL y de respaldo están bien estructurados, comentados, incluyen nombres descriptivos, y están organizados por tipo (DDL, carga, backup, restauración).<br><br>**Rango:** 15 - 9 | **Descripción:** El código está desorganizado, sin comentarios, con nomenclatura inconsistente o difícil de entender.<br><br>**Rango:** 8 - 0 | |
| | **Sub-Total de Puntos** | **40** | | | |
| **2** | **Conocimientos** | **60** | | | |
| 2.1 | **Carga Masiva de Datos** | 15 | **Descripción:** Se cargan o generan correctamente todos los datos sin errores de integridad referencial. Se incluyen todas las capturas de validación requeridas.<br><br>**Rango:** 15 - 9 | **Descripción:** La carga presenta errores, faltan datos, no sigue el orden especificado, o faltan capturas de validación en múltiples ocasiones.<br><br>**Rango:** 8 - 0 | |
| 2.2 | **Ejecución de Respaldos** | 15 | **Descripción:** Se generan correctamente 3 respaldos completos y 3 respaldos incrementales/diferenciales utilizando comandos en consola, en los momentos adecuados. Se registran todos los archivos y se documenta la fecha/hora.<br><br>**Rango:** 15 - 9 | **Descripción:** Se generan respaldos incompletos, faltan respaldos o no están documentados adecuadamente.<br><br>**Rango:** 8 - 0 | |
| 2.3 | **Restauración y Validación** | 15 | **Descripción:** Se restauran correctamente todos los respaldos (full e incremental), se registran tiempos de restauración con precisión, y se valida integridad mediante capturas de SELECT mostrando datos completos.<br><br>**Rango:** 15 - 9 | **Descripción:** Falla en restaurar respaldos, los datos restaurados están incompletos, no se registran tiempos o faltan capturas de validación.<br><br>**Rango:** 8 - 0 | |
| 2.4 | **Análisis Comparativo** | 15 | **Descripción:** Se realiza análisis exhaustivo comparando tiempos de restauración, se crean tablas comparativas que muestran claramente las diferencias, se concluye recomendación fundamentada sobre qué tipo de backup es más apropiado.<br><br>**Rango:** 15 - 9 | **Descripción:** El análisis es superficial, falta información comparativa, no hay tabla comparativa o la conclusión no está sustentada en datos reales.<br><br>**Rango:** 8 - 0 | |
| | **Sub-Total de Puntos** | **60** | | | |
| | **TOTAL** | **100** | | | |

### 8.3 Comentarios Generales
* Si se utiliza Docker o similares para cargar las bases de datos se debe implementar almacenamiento persistente.
* **Entrega:** 17-octubre-2026