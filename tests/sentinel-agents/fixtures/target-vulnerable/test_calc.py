"""Test que FALLA por el bug plantado en calc.promedio (para el validator)."""

from calc import descuento, promedio


def test_promedio_correcto():
    # Espera el promedio real: (2+4+6)/3 = 4.0. Falla porque promedio divide por len-1.
    assert promedio([2, 4, 6]) == 4.0


def test_descuento_ok():
    assert descuento(100, 10) == 90.0
