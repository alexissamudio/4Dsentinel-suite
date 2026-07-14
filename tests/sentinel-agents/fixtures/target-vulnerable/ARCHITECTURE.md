# Arquitectura del proyecto de ejemplo

Documento PLANTADO para el librarian: prosa CORRECTA y bien formada, sin
hallazgos de calidad ni bugs. Existe solo para que el librarian lo lea y lo
RESUMA con fidelidad (evidencia-primero), sin inventar módulos que no están.

## Componentes

- `auth.js` — módulo de autenticación: expone `login(username, password)` y
  `findUser(username)`. Depende de `./db` para las consultas.
- `calc.py` — utilidades numéricas: `promedio(numeros)` y `descuento(precio, porcentaje)`.
- `test_calc.py` — pruebas de `calc.py` con `pytest`.

## Flujo de login

1. La UI llama a `login(username, password)`.
2. `login` busca el usuario con `findUser` y compara la contraseña.
3. Si coincide, `signToken` firma un JWT y lo devuelve.

## Persistencia

Toda consulta pasa por el módulo `./db`. No hay ORM ni caché en esta versión de
ejemplo. La base tiene dos tablas relevantes: `users` y `audit_log`.
