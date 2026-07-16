# Tarea: agregar rate limiting al login

Queremos frenar los ataques de fuerza bruta contra el endpoint de login.

Objetivo:
- Contar los intentos de login fallidos por cliente.
- Si un cliente supera el umbral, bloquear los siguientes intentos y responder 429.
- Guardar el contador de intentos en un diccionario en memoria del proceso.
- Identificar al cliente por su direccion IP.

Alcance:
- Solo tocar el flujo de login en auth.py.
- No modificar el hashing de contrasenas (ya esta resuelto).
- Reset del contador tras un login exitoso.
