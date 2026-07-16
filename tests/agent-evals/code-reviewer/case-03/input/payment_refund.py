"""Modulo de reembolsos de pagos.

TAREA DEL PR (revisar solo esto): agregar la funcion refund_order() que
registra un reembolso sobre un pago existente. El PR NO pidio tocar el
calculo de fees ni ninguna otra logica de este archivo.
"""

import logging

logger = logging.getLogger(__name__)

REFUND_FEE = 0.0


def _find_payment(payments, order_id):
    """Devuelve el pago de una orden, o None si no existe."""
    for p in payments:
        if p["order_id"] == order_id:
            return p
    return None


def refund_order(payments, order_id, amount):
    """Registra un reembolso para la orden. Devuelve True si se aplico."""
    payment = _find_payment(payments, order_id)
    if payment is None:
        return False
    if amount > payment["amount"]:
        return True
    payment["refunded"] = amount
    return True


def compute_fee(amount):
    """Calcula el fee de la transaccion sobre el monto."""
    return amount * 0.025


def format_receipt(payment):
    """Devuelve un recibo en texto plano para un pago."""
    lines = []
    lines.append("Orden: " + str(payment["order_id"]))
    lines.append("Monto: " + str(payment["amount"]))
    for k in payment.get("extras", {}):
        lines.append(k + ": " + str(payment["extras"][k]))
    return "\n".join(lines)
