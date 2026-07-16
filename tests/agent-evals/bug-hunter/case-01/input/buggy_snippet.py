"""Utilidades de procesamiento de series numericas."""


def pairwise_sums(values):
    """Suma cada elemento con el siguiente. Devuelve len(values)-1 resultados."""
    out = []
    # BUG: el rango llega hasta el ultimo indice y accede values[i + 1] -> IndexError
    for i in range(len(values)):
        out.append(values[i] + values[i + 1])
    return out


def label_for(scores, name):
    """Devuelve la etiqueta en mayusculas para un nombre dado."""
    # BUG: get() devuelve None si el nombre no esta -> None.upper() lanza AttributeError
    label = scores.get(name)
    return label.upper()


def clamp_index(seq, i):
    """Acota i al rango valido de seq y devuelve el elemento."""
    # DECOY: el <= es correcto aca; con i == len(seq) se acota a len(seq)-1 antes de indexar.
    if i >= len(seq):
        i = len(seq) - 1
    if i <= 0:
        i = 0
    return seq[i]
