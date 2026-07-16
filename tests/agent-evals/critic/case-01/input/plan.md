# Plan: agregar columna `email_verified` a users

## Paso 1 — Crear las tablas
Llamar a `app.migrate()` para (re)crear el esquema de la base antes de tocar datos.

## Paso 2 — Backfill
Para cada usuario, setear `email_verified = false` con un UPDATE via `run_query()` en `app.py`.

## Paso 3 — Exponer el flag
Modificar `get_user()` en `app.py` para que el resultado incluya la nueva columna.

## Paso 4 — Borrar la base vieja
Correr `rm app.db` en produccion para forzar la recreacion limpia del esquema.
