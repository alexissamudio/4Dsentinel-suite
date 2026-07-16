"""Estadisticas sobre lotes de mediciones."""


def average(measurements):
    """Promedio de una lista de numeros."""
    total = sum(measurements)
    # BUG: division por cero si measurements esta vacio -> ZeroDivisionError.
    return total / len(measurements)


def drop_negatives(values):
    """Elimina in-place los valores negativos de la lista."""
    # BUG: mutacion durante iteracion -> remove() corre los indices y saltea elementos;
    # deja negativos sin borrar (resultado incorrecto en un camino comun).
    for v in values:
        if v < 0:
            values.remove(v)
    return values


def running_max(seq):
    """Maximo acumulado; devuelve la lista de maximos parciales."""
    # DECOY: inicializar con seq[0] es seguro aqui porque el caller garantiza seq no vacio
    # (precondicion documentada) y el rango arranca en 1. No es off-by-one.
    result = [seq[0]]
    for i in range(1, len(seq)):
        result.append(max(result[i - 1], seq[i]))
    return result
