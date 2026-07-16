# Plan: migrar el cache a Redis con TTL

## Paso 1 — Usar el cliente Redis existente
Reutilizar el cliente Redis que ya vive en `cache.py` para no reconfigurar conexiones.

## Paso 2 — Agregar TTL configurable
Extender `cache.set()` para aceptar un parametro `ttl` y expirar las claves.

## Paso 3 — Instanciar el pool de conexiones
Crear el connection pool de Redis en `cache.py` e inyectarlo donde se use el cliente del Paso 1.

## Paso 4 — Ajustar los tests
Actualizar los tests del cache para el nuevo backend.
