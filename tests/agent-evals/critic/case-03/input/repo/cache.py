"""Cache en memoria de proceso. Sin dependencias externas."""

_store = {}


def get(key):
    """Devuelve el valor cacheado o None si la clave no existe."""
    return _store.get(key)


def set(key, value):
    """Guarda value bajo key. Muta _store in-place; no devuelve nada."""
    _store[key] = value


def warm(keys):
    """Reserva un slot para cada key con un sentinel None (el loader real lo llena
    despues). NO cuenta nada: la funcion termina sin return -> devuelve None."""
    for k in keys:
        _store[k] = None
