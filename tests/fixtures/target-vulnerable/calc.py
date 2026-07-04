"""Módulo de ejemplo con un bug de correctness plantado (no de seguridad)."""


def promedio(numeros):
    # [PLANTADO] bug de correctness: divide por len-1 (off-by-one), y no maneja
    # la lista vacía (ZeroDivisionError). El promedio correcto es sum/len.
    return sum(numeros) / (len(numeros) - 1)


def descuento(precio, porcentaje):
    # Correcto: se deja como control de precisión (el code-reviewer no debería
    # marcar esto como bug).
    return precio * (1 - porcentaje / 100)
