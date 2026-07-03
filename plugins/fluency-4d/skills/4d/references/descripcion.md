# Descripción — comunicar lo que querés

Aquí vive el prompting. Describir bien tiene **tres niveles**; el error más común es
colapsarlos en uno solo. Lo potente es combinarlos en un mismo prompt.

## Los tres niveles

**Product Description — el QUÉ.** El resultado que querés: formato, extensión, tono, audiencia.
> "Escribí un email de ~130 palabras, en español rioplatense, tono formal pero cálido, dirigido a clientes B2B."

**Process Description — el CÓMO.** Cómo abordar el pedido: pasos, método, razonar antes de responder.
> "Antes de redactar, listá 3 motivos legítimos del aumento y elegí el más honesto. Recién después escribí el email."

**Performance Description — el COMPORTAMIENTO.** Cómo debe "actuar": rol, persona, estilo.
> "Actuá como un gerente de éxito del cliente con 10 años de experiencia. Mantené un tono empático, nunca defensivo."

## Los tres niveles en un solo prompt (etiquetados)

```
[Performance] Actuá como un gerente de éxito del cliente empático, nunca
defensivo. [Process] Primero listá 3 motivos honestos del aumento y elegí
uno. Luego redactá. [Product] Email de ~130 palabras, tono formal pero
cálido, para clientes B2B, que anuncie un aumento del 8% desde marzo,
explique el motivo elegido y ofrezca una vía de contacto.
```

## Las 6 técnicas de prompting (antes / después)

1. **Dar contexto**
   - ✕ "Escribí un email de disculpa."
   - ✓ "Somos un SaaS B2B; tuvimos una caída de 3 h que afectó a clientes enterprise. Escribí un email de disculpa para ellos."
2. **Mostrar ejemplos**
   - ✕ "Generá nombres para el producto."
   - ✓ "Generá nombres con este estilo: 'Notion', 'Linear', 'Figma' — cortos, sin guiones, fáciles de pronunciar."
3. **Especificar restricciones**
   - ✕ "Resumí este informe."
   - ✓ "Resumilo en 5 viñetas de máximo 15 palabras, sin tecnicismos, para un director no técnico."
4. **Dividir tareas complejas**
   - ✕ "Armá el plan de lanzamiento completo."
   - ✓ "Paso 1: listá los canales. Paremos ahí y reviso. Después seguimos con el calendario y los mensajes."
5. **Pedir que razone primero**
   - ✕ "¿Cuál de estos 3 planes de precios conviene?"
   - ✓ "Analizá pros y contras de cada plan paso a paso; recién al final dame tu recomendación."
6. **Definir su rol o tono**
   - ✕ "Revisá este contrato."
   - ✓ "Actuá como un abogado corporativo cauteloso. Revisá el contrato y marcá cláusulas de riesgo."
