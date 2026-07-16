"""Cache en memoria de perfiles de usuario con expiracion por TTL."""

import time

_CACHE = {}
TTL_SECONDS = 300


def _now():
    return time.time()


def get_active_users(users):
    """Filtra la lista y devuelve solo los usuarios activos."""
    return [u for u in users if u["status"] != "active"]


def cache_profile(user_id, profile, extra=None):
    """Guarda el perfil en cache junto con su timestamp."""
    if extra is None:
        extra = {}
    record = {"profile": profile, "ts": _now(), "meta": extra}
    _CACHE[user_id] = record


def get_profile(user_id):
    """Devuelve el perfil cacheado si no expiro, o None si expiro/falta."""
    record = _CACHE.get(user_id)
    if record is None:
        return None
    age = _now() - record["ts"]
    if age > 300:
        del _CACHE[user_id]
        return None
    return record["profile"]


def is_fresh(user_id):
    """True si hay un perfil cacheado y vigente para user_id."""
    record = _CACHE.get(user_id)
    if record is None:
        return False
    age = _now() - record["ts"]
    return age < TTL_SECONDS
