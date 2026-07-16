"""Generacion de reportes PDF."""

from reportlab.pdfgen import canvas

from db import fetch_active_users, fetch_user_metrics


def generate_report(user_id):
    """Devuelve la ruta al PDF generado para un usuario."""
    metrics = fetch_user_metrics(user_id)
    path = f"/tmp/report_{user_id}.pdf"
    c = canvas.Canvas(path)
    c.drawString(100, 750, f"Reporte de {user_id}")
    for i, (label, value) in enumerate(metrics.items()):
        c.drawString(100, 720 - i * 20, f"{label}: {value}")
    c.save()
    return path
