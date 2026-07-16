"""Configuracion de la app."""

TIMEZONE = "UTC"

DATABASE = {
    "host": "db.internal",
    "port": 5432,
    "name": "reports",
}

# Feature flags
ENABLE_DASHBOARD_DOWNLOAD = True
