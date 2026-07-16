"""Tests de check_bump_on_change.py (F17): la logica pura del gate de bump.

Requisito verificado: si cambian archivos SHIPPEADOS de un plugin (bajo su `source`)
sin bumpear su `version`, el gate FALLA; con bump, pasa; sin cambios, pasa; un plugin
nuevo (sin version previa) no exige bump. La I/O de git no se testea aca (es thin).
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import check_bump_on_change as cbc  # noqa: E402

PLUGINS = [
    ("fluency-4d", "plugins/fluency-4d"),
    ("sentinel-agents", "plugins/sentinel-agents"),
    ("memory", "plugins/memory"),
]


def test_cambio_sin_bump_falla():
    changed = ["plugins/fluency-4d/hooks/memory_checkpoint.py"]
    old = {"fluency-4d": "0.19.0", "sentinel-agents": "0.6.0", "memory": "0.5.1"}
    new = dict(old)  # sin bump
    fallas = cbc.evaluate(PLUGINS, changed, old, new)
    assert [f[0] for f in fallas] == ["fluency-4d"]
    assert fallas[0][2] == ["plugins/fluency-4d/hooks/memory_checkpoint.py"]


def test_cambio_con_bump_pasa():
    changed = ["plugins/fluency-4d/hooks/memory_checkpoint.py"]
    old = {"fluency-4d": "0.19.0", "sentinel-agents": "0.6.0", "memory": "0.5.1"}
    new = {"fluency-4d": "0.19.1", "sentinel-agents": "0.6.0", "memory": "0.5.1"}
    assert cbc.evaluate(PLUGINS, changed, old, new) == []


def test_sin_cambios_de_plugin_pasa():
    # Cambios solo en docs/CI/scripts (fuera de todo `source`): no exige bump.
    changed = [".github/workflows/validate.yml", "scripts/check_ascii.py", "README.md"]
    old = {"fluency-4d": "0.19.0", "sentinel-agents": "0.6.0", "memory": "0.5.1"}
    assert cbc.evaluate(PLUGINS, changed, old, dict(old)) == []


def test_plugin_nuevo_no_exige_bump():
    # Un plugin sin version previa (old None) es nuevo: no se le exige bump.
    changed = ["plugins/memory/scripts/nuevo.py"]
    old = {"fluency-4d": "0.19.0", "sentinel-agents": "0.6.0", "memory": None}
    new = {"fluency-4d": "0.19.0", "sentinel-agents": "0.6.0", "memory": "0.1.0"}
    assert cbc.evaluate(PLUGINS, changed, old, new) == []


def test_prefijo_no_matchea_hermano():
    # `plugins/fluency-4d-x/...` NO debe contar como cambio de `plugins/fluency-4d`.
    assert cbc.touched_source("plugins/fluency-4d", ["plugins/fluency-4d-x/a.py"]) == []
    assert cbc.touched_source("plugins/fluency-4d", ["plugins/fluency-4d/hooks/a.py"]) == [
        "plugins/fluency-4d/hooks/a.py"
    ]


def test_varios_plugins_a_la_vez():
    changed = [
        "plugins/fluency-4d/skills/4d/SKILL.md",
        "plugins/sentinel-agents/agents/critic.md",
    ]
    old = {"fluency-4d": "0.19.0", "sentinel-agents": "0.6.0", "memory": "0.5.1"}
    new = {"fluency-4d": "0.19.1", "sentinel-agents": "0.6.0", "memory": "0.5.1"}
    # fluency bumpeo -> ok; sentinel cambio sin bump -> falla.
    fallas = cbc.evaluate(PLUGINS, changed, old, new)
    assert [f[0] for f in fallas] == ["sentinel-agents"]
