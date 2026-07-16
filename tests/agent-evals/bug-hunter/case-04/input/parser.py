"""Parseo de registros y despacho de trabajos."""

import json


def parse_record(raw):
    """Parsea un registro JSON; devuelve dict o None si es invalido."""
    try:
        return json.loads(raw)
    except Exception:
        # BUG: excepcion tragada sin log ni senal -> un JSON invalido se vuelve None
        # silenciosamente y el caller no distingue "vacio" de "error de parseo".
        pass


def enqueue_all(records, queue):
    """Encola cada registro parseado; devuelve la cantidad encolada."""
    count = 0
    for raw in records:
        rec = parse_record(raw)
        # BUG: no se chequea rec is None -> rec["id"] sobre None lanza TypeError
        # cuando parse_record devolvio None (registro invalido).
        queue.put(rec["id"])
        count += 1
    return count


def safe_divide(a, b):
    """Division protegida; devuelve None si el divisor es cero."""
    # DECOY: este SI maneja el edge case (b == 0 -> None). No es un bug.
    if b == 0:
        return None
    return a / b
