"""Cache en memoria muy simple. NO hay backend Redis en este repo."""

_store = {}


def get(key):
    return _store.get(key)


def set(key, value):
    _store[key] = value
