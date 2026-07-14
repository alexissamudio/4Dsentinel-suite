"""Regresion: los comandos de hooks.json deben quotear ${CLAUDE_PLUGIN_ROOT}.

Bug (reportado por un usuario en Windows): con un espacio en el path del usuario
(ej. C:\\Users\\Nombre Apellido), un ${CLAUDE_PLUGIN_ROOT} SIN comillas parte el argumento
y `uv run --script` recibe medio path -> todos los hooks fallan. El fix es envolver el
path del script en comillas dobles. Este test lo vuelve un contrato: pasa con el fix,
falla sin el.
"""
import json
from pathlib import Path

HOOKS_JSON = (
    Path(__file__).resolve().parents[3]
    / "plugins" / "fluency-4d" / "hooks" / "hooks.json"
)


def _iter_commands(data):
    for evento in data.get("hooks", {}).values():
        for grupo in evento:
            for h in grupo.get("hooks", []):
                cmd = h.get("command")
                if cmd:
                    yield cmd


def test_plugin_root_esta_quoteado():
    data = json.loads(HOOKS_JSON.read_text(encoding="utf-8"))
    cmds = list(_iter_commands(data))
    assert cmds, "no se encontraron comandos en hooks.json"
    # Todo comando que use ${CLAUDE_PLUGIN_ROOT} debe abrirlo con comilla doble y
    # cerrar con comilla doble tras el .py (si no, se rompe en paths con espacios).
    malos = [
        c
        for c in cmds
        if "${CLAUDE_PLUGIN_ROOT}" in c
        and not ('"${CLAUDE_PLUGIN_ROOT}' in c and '.py"' in c)
    ]
    assert not malos, (
        "Comandos con ${CLAUDE_PLUGIN_ROOT} sin comillas (rompen en Windows con espacio "
        f"en el path del usuario): {malos}"
    )
