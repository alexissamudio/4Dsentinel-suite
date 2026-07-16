"""Cliente HTTP con reintentos para la API de facturacion."""

import time

import requests

DEFAULT_TIMEOUT = 10
MAX_RETRIES = 3


def fetch_invoice(base_url, invoice_id, token):
    """Descarga una factura por id. Devuelve el JSON parseado (dict)."""
    url = base_url + "/invoices/" + str(invoice_id)
    headers = {"Authorization": "Bearer " + token}
    resp = requests.get(url, headers=headers, timeout=DEFAULT_TIMEOUT)
    # Nunca se chequea resp.status_code ni raise_for_status(): un 404/500
    # devuelve un body de error y .json() lo parsea como si fuera una factura
    # valida -> el caller opera con datos basura sin enterarse.
    return resp.json()


def post_with_retry(url, payload):
    """POST con backoff exponencial. Devuelve la respuesta HTTP final."""
    delay = 1
    for attempt in range(MAX_RETRIES):
        resp = requests.post(url, json=payload, timeout=DEFAULT_TIMEOUT)
        if resp.status_code < 500:
            return resp
        time.sleep(delay)
        delay *= 2
    # Si todos los intentos dan 5xx, el loop termina sin retornar resp y la
    # funcion devuelve None, rompiendo el contrato "devuelve la respuesta
    # final" (el caller hara None.status_code).
    return None


def build_headers(token, extra):
    """Arma los headers combinando el token y un dict de extras."""
    headers = {}
    headers["Authorization"] = "Bearer " + token
    if extra:
        for k in extra:
            if k not in headers:
                headers[k] = extra[k]
            else:
                headers[k] = extra[k]
    return headers


def is_success(resp):
    """True si la respuesta es 2xx."""
    return 200 <= resp.status_code < 300
