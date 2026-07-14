# Delegación — decidir el reparto humano–IA

Es la competencia más ignorada y la que más errores previene. La regla: respondé
**QUÉ y POR QUÉ antes que QUIÉN y CÓMO**. Tiene tres sub-competencias.

## 1. Goal / Problem Awareness — conciencia del objetivo

Tener claro el objetivo real, el entregable y el criterio de éxito ANTES de involucrar
a la IA. Si el objetivo es difuso, la respuesta será difusa.

**Cómo aplicarlo:** completá la frase
> "Quiero [entregable concreto] para [audiencia/objetivo], que cumpla [criterio de éxito]."

Si no podés completarla, todavía no estás listo para delegar.

| ✕ Objetivo difuso | ✓ Objetivo claro |
|---|---|
| "Ayudame con el email del aumento." | "Un email de ~130 palabras para avisar a clientes B2B de un aumento del 8% desde marzo; tono empático y transparente; meta: reducir cancelaciones." |

## 2. Platform Awareness — conciencia de la herramienta

Conocer qué puede y qué no puede la herramienta: ventana de contexto, tendencia a
alucinar, fecha de corte de conocimiento. No todas las herramientas son intercambiables.

**Cómo aplicarlo:** antes de delegar, preguntate "¿esta tarea choca con algún límite
conocido?" — datos recientes, cálculos exactos, información privada, textos larguísimos.

| Limitación | Qué significa | Qué hago |
|---|---|---|
| Knowledge cutoff | Solo conoce datos hasta su fecha de corte | Doy el dato reciente en el prompt o uso búsqueda web |
| Alucinaciones | Puede inventar datos convincentes | Verifico toda cifra, cita o fuente antes de usarla |
| No determinista | El mismo prompt puede dar respuestas distintas | Fijo el formato con ejemplos; no espero copias idénticas |

**Ejemplo (caso guía):** le pido que **redacte** el email del aumento (lo hace muy
bien), pero **no** le pido que "confirme" la normativa fiscal vigente sin verificar:
puede estar desactualizada o inventada. Las cifras —el 8%— las pongo y las verifico yo,
no ella.

Para entender **por qué** la IA tiene estos límites —cómo funciona por dentro:
transformers que predicen la siguiente palabra, cómo se entrena, la ventana de contexto
como "mesa de trabajo"— leé `references/fundamentos.md`.

## 3. Task Awareness — reparto de la tarea

Dividir el trabajo en sub-tareas y repartirlas según las fortalezas de cada uno.
**Principio práctico: delegá lo repetitivo, quedate con el criterio y la relación.**

**Cómo aplicarlo:** tabla de sub-tareas etiquetadas IA / Yo / Ambos. Ejemplo (caso guía
del email de aumento de precios):

| Sub-tarea | ¿Quién? |
|---|---|
| Decidir el % real y el motivo honesto del aumento | Yo |
| Redactar el primer borrador del email | IA |
| Ajustar el tono para que sea empático | Ambos |
| Verificar cifras y aprobar el envío | Yo |

**Idea clave:** la mayoría de los fallos con IA no vienen de un mal prompt, sino de un
mal reparto. Arreglá primero la Delegación; después, la Descripción.

## No la confundas con Discernimiento (trampa del examen)

Diseñar el reparto **por adelantado** (quién hace qué) es Delegación; evaluar el
resultado **después** (¿esto que me dio sirve?) es Discernimiento
(`references/discernimiento.md`). Es la confusión más habitual del examen: no mezcles el
*antes* con el *después*.
