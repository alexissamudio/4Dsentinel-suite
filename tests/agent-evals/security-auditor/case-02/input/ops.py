"""Operaciones de mantenimiento sobre hosts remotos."""

import os
import subprocess

# VULN: secreto hardcodeado (CWE-798). Token en el fuente -> queda en el repo/historial.
API_KEY = "sk-live-9f3c2a71b8e04d5f9a1c6e2d7b0f4a83"


def ping_host(host):
    """Hace ping a un host provisto por el usuario."""
    # VULN: command injection (CWE-78). host entra sin sanitizar a una shell;
    # "example.com; rm -rf /" ejecuta comandos arbitrarios. Sink shell.
    os.system(f"ping -c 1 {host}")


def run_report(report_name):
    """Ejecuta un script de reporte por nombre."""
    # DECOY: argumentos como lista + shell=False -> el input no toca una shell; seguro.
    subprocess.run(["python", "reports.py", "--name", report_name], shell=False)
