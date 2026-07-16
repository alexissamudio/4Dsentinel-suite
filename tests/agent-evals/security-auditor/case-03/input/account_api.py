"""Endpoints de la API de cuentas (extracto). 'request' es el request HTTP entrante."""

import hmac

import requests

ALLOWED_HOST = "api.internal.example.com"


def db_get(sql, params):
    """Capa de datos parametrizada (stub). Usa placeholders, nunca interpola."""
    ...


def redirect(location):
    """Devuelve una respuesta HTTP 302 hacia location (stub)."""
    ...


def hmac_sha256(secret, payload):
    """Calcula el HMAC-SHA256 de payload con secret y lo devuelve en hex (stub)."""
    ...


def fetch_avatar(url):
    """Descarga el avatar remoto del usuario desde el host interno permitido."""
    # VULN SSRF (CWE-918): el allowlist se valida con substring 'in'. Una URL como
    # http://api.internal.example.com.attacker.com/ o http://evil/?x=api.internal.example.com
    # pasa el check y permite pegarle a hosts internos (169.254.169.254, etc.).
    if ALLOWED_HOST in url:
        return requests.get(url, timeout=3).content
    raise ValueError("host no permitido")


def get_invoice(request, invoice_id):
    """Devuelve la factura pedida por el usuario autenticado."""
    # VULN IDOR / Broken Access Control (CWE-639): usa invoice_id crudo y NUNCA verifica
    # que la factura pertenezca a request.user_id -> cualquiera lee facturas ajenas
    # iterando ids. La query esta parametrizada: el hueco es de autorizacion, no de SQLi.
    return db_get("SELECT * FROM invoices WHERE id = ?", (invoice_id,))


def login_redirect(request):
    """Redirige al usuario a la pagina 'next' luego de loguear."""
    target = request.args.get("next", "/dashboard")
    # VULN Open Redirect (CWE-601): 'next' viene del usuario y se usa como destino sin
    # validar que sea una ruta interna; ?next=https://evil.com se lleva al usuario afuera.
    return redirect(target)


def verify_webhook(signature, payload, secret):
    """Valida la firma HMAC de un webhook entrante."""
    expected = hmac_sha256(secret, payload)
    # VULN timing (CWE-208): '==' sobre strings corta en el primer byte distinto; el
    # tiempo filtra cuantos bytes acertaste y permite forjar la firma byte a byte.
    if signature == expected:
        return True
    return False


def safe_redirect(request):
    """Redirige solo a rutas internas conocidas."""
    target = request.args.get("next", "/dashboard")
    # DECOY: valida contra un allowlist EXACTO de rutas relativas; ?next=https://evil.com
    # no matchea y cae al default. No es open redirect.
    if target in {"/dashboard", "/settings", "/billing"}:
        return redirect(target)
    return redirect("/dashboard")


def verify_token(token, expected):
    """Compara un token contra el esperado."""
    # DECOY: hmac.compare_digest es comparacion en tiempo constante -> no filtra timing,
    # no es CWE-208.
    return hmac.compare_digest(token, expected)
