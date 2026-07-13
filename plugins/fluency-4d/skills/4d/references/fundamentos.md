# Fundamentos — cómo funciona por dentro

Esta capa no es una de las 4D: es el **"cómo funciona por dentro"** que hace que las
cuatro competencias tengan sentido. Saber por qué la IA a veces suena segura y se
equivoca es lo que te vuelve capaz de delegar y discernir con criterio.

## IA generativa vs. IA tradicional

- **IA tradicional** — clasifica y predice sobre datos definidos. Ej: un filtro que
  marca un email como "spam / no spam".
- **IA generativa** — crea contenido nuevo. Ej: redacta el email del aumento desde
  cero, con un texto que no existía antes.

## Los tres pilares (y por qué te importan al usarla)

| Pilar | Qué es | Por qué te importa |
|---|---|---|
| Datos masivos | Enormes volúmenes de texto de los que aprende patrones | Explica por qué "sabe" de casi todo… pero también repite los sesgos de esos datos |
| Poder de cómputo | La potencia de cálculo para entrenar a gran escala | Explica por qué los modelos mejoran con el tiempo (más escala) |
| Redes neuronales (transformers) | La arquitectura que modela el lenguaje | **Predice "la siguiente palabra probable": por eso a veces suena seguro y se equivoca** |

La consecuencia práctica del tercer pilar: la fluidez del texto **no garantiza** su
exactitud. Un modelo puede encadenar palabras muy convincentes y estar inventando.

## Cómo se construye un LLM

1. **Pre-training** — aprende patrones del lenguaje prediciendo la siguiente palabra
   sobre cantidades enormes de texto.
2. **Fine-tuning** — se ajusta para ser útil, seguro y alineado, incluyendo aprendizaje
   a partir de feedback humano (RLHF).

## La ventana de contexto — la "mesa de trabajo" del modelo

Es **todo lo que el modelo puede tener en cuenta a la vez**: tu pedido + su respuesta.
Es limitada.

**Cómo aplicarlo:** en chats muy largos, la info del principio puede "caerse" de la
mesa. Si notás que se olvidó de algo importante, volvé a pegarlo en el mensaje actual
en vez de asumir que lo recuerda. (Esto es una técnica de Descripción: ver
`references/descripcion.md`.)

## Las limitaciones que se derivan de esto

Los tres límites operativos —knowledge cutoff, alucinaciones y no determinismo— y qué
hacer con cada uno viven en la tabla de **Platform Awareness** de
`references/delegacion.md`: ahí es donde se usan al decidir el reparto. No se duplican
acá; este archivo explica el *porqué*, aquella tabla el *qué hago*.
