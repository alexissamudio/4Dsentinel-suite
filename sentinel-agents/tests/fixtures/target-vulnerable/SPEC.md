# Especificación: función de login

El login debe ser rápido y seguro. El usuario ingresa sus credenciales y el
sistema lo autentica.

## Requisitos

- R1: El sistema debe responder rápido.
- R2: Las contraseñas se guardan de forma segura.
- R3: El login debe soportar hasta 1000 usuarios y también muchos más.

## Criterios de aceptación

- El login funciona.

<!-- [PLANTADO] Spec con problemas de REDACCION a propósito, para el
     auditor-de-redaccion (NO son bugs de código; el código de auth.js es otro
     asunto). Ground-truth de la prosa:
       - "rápido" (titulo + R1) sin umbral -> [Ambiguedad] / Medibilidad.
       - R2 "de forma segura" sin definir algoritmo/estándar -> [Ambiguedad].
       - R3 "hasta 1000 usuarios y también muchos más" se contradice -> [Conflicto].
       - "El login funciona" no es verificable y no cubre R1/R2/R3 -> [Gap]/Cobertura.
       - Faltan casos de error (credenciales inválidas, bloqueo) y actores -> [Gap].
       - Da por sentado que ya existen usuarios/credenciales -> [Supuesto].
     El auditor-de-redaccion NO debe juzgar si el login del sistema funciona
     (eso es de code-reviewer/validator): solo la calidad del TEXTO. -->
