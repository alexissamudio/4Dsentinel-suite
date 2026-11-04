# Fundamentos — cómo funciona por dentro

Esta capa no es una de las 4D: es el **"cómo funciona por dentro"** que hace que las
cuatro competencias tengan sentido.

## IA generativa vs. IA tradicional

- **IA tradicional** — clasifica y predice sobre datos definidos. Ej: un filtro de spam.
- **IA generativa** — crea contenido nuevo. Ej: redacta el email del aumento desde cero.

## Los tres pilares

| Pilar | Qué es | Por qué te importa |
|---|---|---|
| Datos masivos | Enormes volúmenes de texto de los que aprende patrones | Explica por qué "sabe" de casi todo… pero también repite sesgos |
| Poder de cómputo | La potencia de cálculo para entrenar a gran escala | Explica por qué los modelos mejoran con el tiempo |
| Redes neuronales (transformers) | La arquitectura que modela el lenguaje | **Predice "la siguiente palabra probable": por eso a veces suena seguro y se equivoca** |

La consecuencia práctica: la fluidez del texto **no garantiza** su exactitud.

## Cómo se construye un LLM

1. **Pre-training** — aprende patrones del lenguaje prediciendo la siguiente palabra.
2. **Fine-tuning** — se ajusta para ser útil, seguro y alineado (RLHF).

## La ventana de contexto — la "mesa de trabajo"

Es **todo lo que el modelo puede tener en cuenta a la vez**: tu pedido + su respuesta.
Es limitada. En chats muy largos, la info del principio puede "caerse" de la mesa.
Si notás que se olvidó de algo importante, volvé a pegarlo en el mensaje actual.