"""Tareas de mantenimiento del cache."""

import cache


def rebuild_index(source):
    """Reconstruye el indice desde source (iterable de filas con clave 'id').
    Devuelve la lista de ids indexados."""
    ids = [row["id"] for row in source]
    for i in ids:
        cache.set(i, True)
    return ids


def flush():
    """Vacia POR COMPLETO el cache: borra TODAS las claves. Devuelve None."""
    cache._store.clear()
