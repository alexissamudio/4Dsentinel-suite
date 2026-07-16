"""Servicio de agregacion de metricas, dedup y paginacion de resultados."""

import threading


class MetricBucket:
    """Acumula muestras. Cada instancia deberia tener su PROPIO buffer."""

    # BUG (aliasing): 'samples' es atributo de CLASE, no de instancia. La lista mutable
    # se comparte entre TODAS las instancias; add() en una contamina a las demas.
    samples = []

    def __init__(self, name):
        self.name = name

    def add(self, value):
        self.samples.append(value)

    def total(self):
        return sum(self.samples)


def crossed_threshold(prev_balance, delta, threshold=0.3):
    """True si el balance cruza EXACTO o supera el umbral tras aplicar delta."""
    new_balance = prev_balance + delta
    # BUG (precision float): con prev=0.1, delta=0.2 -> new_balance == 0.30000000000000004,
    # nunca igual a 0.3; el cruce exacto se pierde y toma la rama equivocada.
    if new_balance == threshold:
        return True
    return new_balance > threshold


def paginate(items, page, per_page):
    """Devuelve la porcion de items para la pagina dada (1-indexed)."""
    start = (page - 1) * per_page
    # BUG (off-by-one enmascarado): end suma un +1 de mas, la porcion incluye el primer
    # item de la pagina siguiente; los bordes entre paginas se solapan.
    end = start + per_page + 1
    return items[start:end]


_seen_lock = threading.Lock()
_seen = set()


def register_once(key, sink):
    """Registra key una sola vez; si ya se vio, no reenvia a sink."""
    # BUG (race / check-then-act): el 'not in' y el add() NO estan bajo el lock; dos
    # threads pueden pasar el chequeo a la vez y llamar sink(key) dos veces.
    if key not in _seen:
        _seen.add(key)
        sink(key)


def register_locked(key, sink):
    """Variante con lock tomado durante todo el check-and-act."""
    # DECOY: parece el mismo patron check-then-act sobre estado compartido, pero aca es
    # atomico (todo dentro del 'with lock') -> no hay race real.
    with _seen_lock:
        if key in _seen:
            return
        _seen.add(key)
    sink(key)


def last_page_items(items, per_page):
    """Devuelve los items de la ultima pagina."""
    # DECOY: parece off-by-one, pero -(len % per_page) con el guard del 0 devuelve
    # exactamente el resto final; el slice es correcto.
    rem = len(items) % per_page
    if rem == 0:
        return items[-per_page:]
    return items[-rem:]
