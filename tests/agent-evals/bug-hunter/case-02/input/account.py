"""Modelo simple de cuenta con transferencias."""


class Account:
    def __init__(self, balance):
        self.balance = balance

    def withdraw(self, amount):
        # BUG: condicional invertido -> permite retirar cuando NO hay fondos y
        # rechaza cuando SI hay. El signo de la comparacion esta al reves.
        if self.balance < amount:
            self.balance -= amount
            return True
        return False


def load_config(path):
    """Lee un archivo de config y devuelve sus lineas no vacias."""
    # BUG: fuga de recurso -> el archivo se abre pero solo se cierra si no hay excepcion;
    # si una linea falla el .strip() (None) el close nunca corre. Falta 'with'.
    f = open(path)
    lines = [ln.strip() for ln in f if ln.strip()]
    f.close()
    return lines


def total_price(items, tax_rate=0.21):
    """Suma precios y aplica impuesto."""
    # DECOY: default mutable? No: tax_rate es float inmutable, no hay aliasing. Correcto.
    subtotal = sum(it["price"] for it in items)
    return subtotal * (1 + tax_rate)
