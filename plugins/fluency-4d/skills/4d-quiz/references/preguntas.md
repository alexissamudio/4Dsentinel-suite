# Banco de preguntas — Certificación AI Fluency

24 preguntas en 6 secciones. Cada una: enunciado, opciones A-D, correcta,
explicación y qué reference releer si se falla.

## S1 — Las 4D y sus preguntas clave

**P1.** ¿Qué pregunta responde la competencia de Delegación?
- A) ¿Cómo le explico lo que quiero?
- B) ¿Qué hago yo y qué hace la IA?
- C) ¿Puedo confiar en lo que me dio?
- D) ¿Quién es responsable del resultado?
- **Correcta: B.** Delegación = decidir el reparto del trabajo humano–IA. A es Descripción, C es Discernimiento, D es Diligencia.
- Releer: `4d/references/delegacion.md`

**P2.** ¿En qué orden se recorren las 4D para aprenderlas?
- A) Descripción → Delegación → Diligencia → Discernimiento
- B) Delegación → Descripción → Discernimiento → Diligencia
- C) Diligencia → Discernimiento → Descripción → Delegación
- D) El orden es indistinto porque son independientes
- **Correcta: B.** Se aprenden en ese orden, aunque no son pasos rígidos: forman un ciclo. D es la trampa: no son independientes, se retroalimentan.
- Releer: `4d/references/delegacion.md`

**P3.** "La mayoría de los fallos con IA no vienen de un mal prompt, sino de..."
- A) ...un modelo desactualizado
- B) ...una ventana de contexto chica
- C) ...un mal reparto del trabajo
- D) ...falta de ejemplos en el prompt
- **Correcta: C.** Idea que cae en el examen: arreglá primero la Delegación (el reparto); después la Descripción (el prompt).
- Releer: `4d/references/delegacion.md`

**P4.** ¿Cuál de estas afirmaciones sobre las 4D es correcta?
- A) Son pasos rígidos que nunca se repiten
- B) Solo aplican a tareas de programación
- C) Forman un ciclo iterativo
- D) Descripción y Discernimiento son la misma competencia
- **Correcta: C.** No son pasos rígidos: describís, evaluás, corregís y volvés a describir. D confunde: comparten los 3 niveles pero una comunica y la otra evalúa.
- Releer: `4d/references/discernimiento.md`

## S2 — Delegación y sus sub-competencias

**P5.** ¿Cuáles son las tres sub-competencias de la Delegación?
- A) Product, Process y Performance Awareness
- B) Goal/Problem, Platform y Task Awareness
- C) Creation, Transparency y Deployment Awareness
- D) Context, Prompt y Output Awareness
- **Correcta: B.** Conciencia del objetivo, de la herramienta y del reparto de la tarea. A son los niveles de Descripción/Discernimiento; C son los aspectos de Diligencia.
- Releer: `4d/references/delegacion.md`

**P6.** Según Goal/Problem Awareness, ¿cuándo estás listo para delegar?
- A) Cuando conocés el modelo que vas a usar
- B) Cuando podés completar "Quiero [entregable] para [audiencia], que cumpla [criterio]"
- C) Cuando tenés el prompt escrito en tres niveles
- D) Cuando la tarea es repetitiva
- **Correcta: B.** Si no podés completar la frase-objetivo, el objetivo es difuso y la respuesta será difusa. C llega después (Descripción); D es criterio de reparto, no de preparación.
- Releer: `4d/references/delegacion.md`

**P7.** El principio práctico del Task Awareness es:
- A) Delegá todo lo que la IA pueda hacer más rápido
- B) Delegá lo repetitivo, quedate con el criterio y la relación
- C) Delegá solo tareas creativas
- D) Nunca delegues la redacción de borradores
- **Correcta: B.** El reparto no es por velocidad sino por fortalezas: la IA toma lo repetitivo; el humano conserva las decisiones, las cifras reales y el trato con terceros.
- Releer: `4d/references/delegacion.md`

**P8.** En el caso guía del email del aumento del 8%, ¿qué sub-tarea corresponde a "Yo" (el humano)?
- A) Redactar el primer borrador del email
- B) Ajustar el tono para que sea empático
- C) Decidir el % real y el motivo honesto del aumento
- D) Generar tres variantes del asunto
- **Correcta: C.** Las cifras y el motivo real son criterio del humano; el borrador es de la IA; el tono es de Ambos.
- Releer: `4d/references/delegacion.md`

## S3 — Descripción: los 3 niveles y las 6 técnicas

**P9.** "Actuá como un gerente de éxito del cliente con 10 años de experiencia; mantené un tono empático, nunca defensivo" es un ejemplo de:
- A) Product Description
- B) Process Description
- C) Performance Description
- D) Platform Awareness
- **Correcta: C.** Define el comportamiento/rol/persona de la IA durante la colaboración. Product sería el formato y extensión; Process, los pasos.
- Releer: `4d/references/descripcion.md`

**P10.** "Antes de redactar, listá 3 motivos legítimos del aumento y elegí el más honesto; recién después escribí el email" es:
- A) Product Description
- B) Process Description
- C) Performance Description
- D) Discernimiento de proceso
- **Correcta: B.** Describe el CÓMO: el método y los pasos antes de producir. D es la trampa: evaluar el razonamiento después es Discernimiento; pedirlo por adelantado es Descripción.
- Releer: `4d/references/descripcion.md`

**P11.** ¿Cuál es el error más común al describir?
- A) Usar los tres niveles en un mismo prompt
- B) Colapsar los tres niveles en uno solo
- C) Dar demasiado contexto
- D) Definir el rol de la IA
- **Correcta: B.** Los niveles se COMBINAN (eso es lo potente); el error es aplastarlos en un pedido único y difuso. A es exactamente lo recomendado.
- Releer: `4d/references/descripcion.md`

**P12.** Cambiar "Resumí este informe" por "Resumilo en 5 viñetas de máximo 15 palabras, sin tecnicismos, para un director no técnico" es la técnica de:
- A) Mostrar ejemplos
- B) Pedir que razone primero
- C) Especificar restricciones
- D) Dividir tareas complejas
- **Correcta: C.** Impone formato, longitud, registro y audiencia. Ejemplos sería dar muestras del estilo esperado; dividir sería frenar en pasos.
- Releer: `4d/references/descripcion.md`

## S4 — Discernimiento y el loop

**P13.** Las tres capas del Discernimiento son:
- A) Las mismas tres de la Descripción: Product, Process y Performance
- B) Datos, cómputo y redes neuronales
- C) Goal, Platform y Task
- D) Precisión, sesgo y formato
- **Correcta: A.** Describís en tres capas y evaluás en esas mismas tres capas: ¿el resultado sirve? ¿el camino tiene sentido? ¿mantuvo el rol?
- Releer: `4d/references/discernimiento.md`

**P14.** El borrador dice: "Según un estudio de Gartner, el 82% de los clientes acepta subas justificadas", pero no pediste datos externos ni hay fuente verificable. ¿Qué hacés?
- A) Lo dejo: suena creíble y da autoridad
- B) Lo elimino: es una alucinación típica
- C) Lo suavizo a "según estudios"
- D) Cambio de modelo de IA
- **Correcta: B.** Inventar cifras con aire de autoridad es la alucinación clásica; toda cifra o fuente no provista por vos se verifica o se elimina. C mantiene el dato inventado con peor disfraz.
- Releer: `4d/references/discernimiento.md`

**P15.** Pediste tono empático y a mitad del email aparece "si no está de acuerdo, puede cancelar". ¿Qué nivel de discernimiento falló?
- A) Product Discernment
- B) Process Discernment
- C) Performance Discernment
- D) Creation Diligence
- **Correcta: C.** La IA rompió el rol/comportamiento pedido: eso es Performance. Product sería un dato incorrecto; Process, un razonamiento que no se sostiene.
- Releer: `4d/references/discernimiento.md`

**P16.** ¿De qué depende el discernimiento, según el punto crítico del curso?
- A) De la calidad del modelo
- B) De tu propio conocimiento del dominio
- C) Del largo del prompt
- D) De la temperatura del modelo
- **Correcta: B.** No podés evaluar de forma fiable algo que no entendés. Si no sos experto: delegá solo lo verificable, sumá un revisor humano o diseñá una verificación independiente.
- Releer: `4d/references/discernimiento.md`

**P17.** ¿Cuál es la habilidad que más distingue el uso fluido del superficial?
- A) Escribir prompts largos
- B) Iterar: el loop Descripción → Discernimiento con correcciones puntuales
- C) Conocer muchos modelos distintos
- D) Automatizar todo con agentes
- **Correcta: B.** Describir y discernir no ocurren una sola vez: corregís con cambios puntuales ("dos cambios: ...") en vez de re-describir todo, y repetís hasta que pase la checklist.
- Releer: `4d/references/discernimiento.md`

## S5 — Diligencia

**P18.** Los tres aspectos de la Diligencia son:
- A) Creation, Transparency y Deployment
- B) Product, Process y Performance
- C) Goal, Platform y Task
- D) Verificación, iteración y publicación
- **Correcta: A.** Con qué y cómo creás; honestidad sobre el uso de IA; y responsabilidad al publicar.
- Releer: `4d/references/diligencia.md`

**P19.** Tenés que pegar la lista real de clientes con sus contratos para que la IA la procese. ¿Qué dicta la Creation Diligence?
- A) Pegarla: la IA no guarda datos
- B) Anonimizarla primero o usar una herramienta con acuerdo de confidencialidad
- C) Pedirle a la IA que la trate como confidencial
- D) Usar un modelo más grande
- **Correcta: B.** La elección de sistema y forma de trabajo depende de la sensibilidad de los datos; a veces la decisión correcta es no usar IA. C es teatro: pedirlo no cambia el tratamiento de los datos.
- Releer: `4d/references/diligencia.md`

**P20.** La regla simple de la Transparency Diligence es:
- A) Declarar el modelo exacto y su versión en cada documento
- B) Si te incomodaría que te pregunten "¿esto lo escribió una IA?", falta diligencia
- C) Nunca revelar que usaste IA para proteger tu reputación
- D) Solo declarar el uso de IA en trabajos académicos
- **Correcta: B.** Es honestidad con quienes deban saberlo, calibrada por esa incomodidad — no un formulario fijo (A) ni ocultamiento (C).
- Releer: `4d/references/diligencia.md`

**P21.** Antes de enviar el email a 5.000 clientes, la Deployment Diligence exige:
- A) Correr el email por un segundo modelo de IA
- B) Leerlo entero, confirmar el "8% desde marzo" contra tu fuente y aprobar conscientemente
- C) Agregar un disclaimer de que fue generado por IA
- D) Guardar el prompt usado
- **Correcta: B.** Verificás y te hacés cargo del producto final como propio: si algo falla, es tu responsabilidad, no del modelo (la IA es como un martillo).
- Releer: `4d/references/diligencia.md`

## S6 — Fundamentos, limitaciones y trampas de examen

**P22.** ¿Por qué un LLM "a veces suena seguro y se equivoca"?
- A) Porque fue entrenado con datos privados
- B) Porque predice la siguiente palabra probable, no la verdad
- C) Porque su ventana de contexto es infinita
- D) Porque el fine-tuning lo hace más creativo
- **Correcta: B.** La arquitectura (transformers) modela "la palabra siguiente más probable": por eso la fluidez no garantiza exactitud.
- Releer: `4d/references/delegacion.md` (tabla de limitaciones)

**P23.** En un chat muy largo, notás que la IA "olvidó" un dato del principio. ¿Qué hacés?
- A) Regañarla para que recuerde
- B) Volver a pegar el dato en el mensaje actual
- C) Bajar la temperatura
- D) Empezar otro chat siempre
- **Correcta: B.** La ventana de contexto es la "mesa de trabajo" limitada: lo del principio puede caerse; se re-pega en vez de asumir que lo recuerda.
- Releer: `4d/references/delegacion.md`

**P24. (LA trampa del examen)** Armar la tabla de reparto IA/Yo/Ambos ANTES de empezar vs. revisar la checklist del email DESPUÉS de recibirlo. ¿Qué competencias son?
- A) Ambas son Discernimiento
- B) Ambas son Delegación
- C) Reparto = Delegación; checklist = Discernimiento
- D) Reparto = Descripción; checklist = Diligencia
- **Correcta: C.** La trampa más habitual del examen: diseñar el reparto POR ADELANTADO es Delegación; evaluar el resultado DESPUÉS es Discernimiento. No confundir el antes con el después.
- Releer: `4d/references/delegacion.md` y `discernimiento.md`
