# Plan: acelerar el arranque precargando el cache en memoria

## Paso 1 — Precargar claves calientes
Llamar a `cache.warm(hot_keys)` y usar el entero que devuelve (`n_loaded`) para loguear
cuantas claves quedaron precargadas.

## Paso 2 — Verificar la precarga
Confirmar que cada clave caliente quedo lista chequeando que `cache.get(k)` devuelve un
valor truthy para cada k en hot_keys.

## Paso 3 — Reconstruir el indice
Llamar a `tasks.rebuild_index(source)` para poblar el cache con los ids reales y usar la
lista de ids que devuelve para el log de arranque.

## Paso 4 — Limpiar claves obsoletas
Despues de reconstruir, llamar a `tasks.flush()` para descartar unicamente las claves
nulas que dejo el warm, conservando los ids recien indexados en el cache.

## Paso 5 — Exponer metrica de hits
Modificar `cache.get()` en `cache.py` para que registre un hit/miss por cada llamada.

## Criterio de aceptacion
El arranque queda "mas rapido" y el cache "suficientemente caliente".
