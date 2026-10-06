# Guía de Estudio — Calificación Proyecto Fase 1
### Sistemas de Bases de Datos 2 · Basado en la clase magistral del catedrático

> **Contexto:** La calificación es **oral y en vivo**. El ingeniero pregunta cara a cara, pide consultas en el momento, y hace modificaciones sobre la marcha. **No se puede usar IA durante la calificación** — él lo diseñó "a prueba de IA" a propósito. Lo que importa es que **conozcas tu proyecto**.

---

## 1. La filosofía de calificación (lo más importante que dijo)

**La regla de oro: conocé tu proyecto.**

El ingeniero fue explícito: no busca perfección, busca que **entiendas lo que hiciste y por qué**. Sus frases clave:

- *"No busques la perfección, porque nunca la vas a encontrar."*
- *"Si algo se te escapó y no me explicás → sacás 0. Con la explicación → sacás 8 o 9."*
- *"Conocé bien tu proyecto, entonces vas a poder resolver."*

**Traducción práctica:** si el día de la calificación aparece un dato que no cargaste o un error, **NO es 0 automático**. Si puedes ir a tus **tablas crudas** y mostrar *"mire, aquí está el dato, no lo cargué por esta razón"* → sacás 99 en vez de 100. Lo que mata es no saber responder.

### Por eso la regla de "no descartar ningún dato"
Él insiste: **nunca deseches datos**. Mantené las tablas crudas. ¿Por qué? Porque en la calificación te puede decir *"¿por qué no cargaste este dato?"* y tú necesitas poder rebatir con la fuente cruda en mano: *"permítame... sí está, aquí, no lo cargué por X razón"*. Esa capacidad de rebatir con evidencia es lo que te salva la nota.

---

## 2. El tema de la limpieza de datos (el caso Messi)

Un compañero preguntó **qué tan minucioso** hay que limpiar. La respuesta: **"lo suficiente como para que la lógica te dé."**

### El ejemplo de Messi (clave para entender el nivel esperado)
- Existe "Lionel Andrés Messi", "Lionel Messi Cuccittini", "Leo Messi" → **son la misma persona**.
- El truco: **basarse en el apellido que todos conocen** (Messi) para reconciliar variantes.
- Problema real que encontró el compañero: un registro decía "Messi" y otro "Mssi" (mal escrito, sin la 'e') → el sistema los tomaba como **dos personas distintas**, e inflaba el conteo de medallas.

### El nivel de minuciosidad esperado
- **SÍ tenés que resolver:** los casos comunes y famosos (Messi, Ronaldo, Barrondo, Neymar, Usain Bolt). Que el apellido esté bien para poder encontrarlos.
- **NO tenés que resolver:** casos rebuscados y oscuros (un ruso desconocido de 1990 con el nombre transliterado raro). Eso está fuera del criterio razonable.
- **La prueba de fuego:** *"que las cuentas salgan cabales"*. Si Argentina tiene 10 oros oficiales pero tu consulta da 11 por un Messi duplicado → tenés un error que corregir.

### Cómo se valida
Las dudas se validan contra el **sitio oficial (olympics.com)**. Si tu cuenta no cuadra con la oficial, hay un duplicado o un dato sucio que arreglar.

### Un caso que NO te va a preguntar
Mencionó que hay un atleta que compitió como hombre (sin medallas) y luego como mujer (con medallas). Dijo que **eso no lo va a preguntar** — no le interesa al "negocio". Al negocio le interesa **la élite**: quién se esforzó, quién es puntero (tipo Usain Bolt).

---

## 3. LAS CONSULTAS QUE VA A PEDIR (lo que más tenés que practicar)

Él mismo las enumeró como "tips". Estas son **las consultas concretas** que hay que tener dominadas. Las agrupo por tipo.

### Grupo A — Consultas de PAÍS (usan tu Stored Procedure de país)
El SP de país es reutilizable: le cambiás el filtro y sale todo.

1. **¿Quiénes han ganado alguna medalla para Guatemala?**
2. **¿Quiénes ganaron medalla de oro para Guatemala?** (mismo SP, filtro por tipo de medalla)
3. **¿Quién ganó medalla de oro para Estados Unidos en tal año?** (filtro país + año)
4. **¿Quién ganó medalla con dos países distintos?** (curiosa, la mencionó explícitamente)

> **Dato del negocio que hay que saber:** Guatemala solo tiene **3 medallistas**: Ruano (plata, tiro), Barrondo (plata, marcha) y Brol (bronce, tiro). Oro, plata y bronce. Conocé esto de memoria — demuestra que "conocés el negocio".

### Grupo B — Consultas de ATLETA / medallero individual
5. **¿Quién es el atleta con más medallas de oro?**
6. **¿Quién es el atleta con más medallas de plata?** (importando o no el deporte)
7. **¿Quién es el atleta con más medallas de bronce?** ("el mayor tercer lugar del mundo")
8. **¿Quién es el máximo medallista absoluto** (oro + plata + bronce combinados)?
9. **¿Quién es la atleta MUJER con más medallas?** vs **¿el atleta HOMBRE?** vs **absoluto**
10. **¿Quién es el atleta con MENOS medallas?**

### Grupo C — Consultas de EVENTO específico
11. **¿Quién ganó medalla de oro en natación 100 metros** (en tal año)?
12. **¿Quién ganó medalla de oro en 100 metros planos (atletismo)** en tal año? → *sale Usain Bolt*

### Grupo D — Consultas de EDAD (usan fecha de nacimiento / edad)
13. **¿Quién ganó medalla de oro siendo el más joven?** ("normalmente en gimnasia aparecen")
14. La edad registrada **es la edad al ganar la medalla** — si tenés ese campo, ya te hicieron el trabajo.

### Grupo E — Consultas SIMPLES (no subestimar estas)
15. **`SELECT * FROM <tabla_de_medallas>`** — "quiero ver todo". 
    - **El riesgo real:** que te quedés en blanco pensando *"¿en qué tabla están las medallas?"*. **Tenés que saber de memoria en qué tabla está cada cosa.**

> **Regla técnica que impuso (importante):** que los Stored Procedures **NO devuelvan un millón de datos**. Usá parámetros y filtros. El truco que mencionó: sobre el SP que saca el atleta, *"le ponés el `COUNT`"*, o *"ordenás por el count, le das un `HAVING MAX` y ahí está"*.

---

## 4. Cómo respondés en vivo (la mecánica)

- Las consultas hay que sacarlas **en el momento**, no en 10 minutos. *"Ustedes saben SQL, conocen su diseño, ya tienen el SP que saca el atleta, entonces solo le ponen el count."*
- Va a "inundar" con varias consultas seguidas (dijo ~3-4, aunque amenazó con 10).
- **Llevá tus queries de prueba ya escritas y subidas** — te pueden ayudar de apoyo el día de la calificación.

---

## 5. Advertencias logísticas (no perder puntos tontos)

- **NO hagas la calificación con la solución solo en la nube** si tu conexión es mala. *"Las excusas no se pagan."*
- Que **2 o 3 integrantes lleven una copia** en su compu. *"En mi casa sí funcionaba" no es excusa válida.*
- Piensa en la **Ley de Murphy**: algo puede salir mal, tené respaldo.

---

## 6. Checklist de preparación personal

- [ ] Sé **de memoria en qué tabla está cada cosa** (sobre todo dónde están las medallas: tabla `participacion` unida a `medalla`).
- [ ] Puedo escribir de memoria el JOIN medallero país: `participacion → atleta`/`equipo → noc`/`pais` + `medalla`.
- [ ] Tengo el SP de país y sé cómo restringirlo por año y por tipo de medalla.
- [ ] Sé los 3 medallistas de Guatemala (Ruano, Barrondo, Brol).
- [ ] Puedo explicar por qué cada decisión de diseño (NOC separado, temporada VARCHAR, no descartar columnas).
- [ ] Tengo las tablas crudas a mano para rebatir "¿por qué no cargaste este dato?".
- [ ] Llevo respaldo local del proyecto (no solo nube).
- [ ] Tengo queries de prueba escritas y listas.

---

*Documento de estudio derivado de la transcripción de la clase magistral. Ordenado e interpretado para preparar la calificación oral.*
