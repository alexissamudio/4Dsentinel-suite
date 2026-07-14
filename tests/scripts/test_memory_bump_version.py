"""memory_bump_version.py maneja SOLO los 2 lugares de 4dsentinel-memory
(entrada del marketplace por name + su plugin.json) y NO toca
`metadata.version` (version paraguas de la suite).

- test_check_*: --check da exit 0 sobre el estado actual del repo.
- test_set_*: un --set escribe la entrada del plugin y el plugin.json pero deja
  `metadata.version` intacto (contra copias temporales, sin tocar el repo real).
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "memory_bump_version.py"
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import memory_bump_version as mbv  # noqa: E402


def test_check_exit_cero_sobre_estado_actual():
    result = subprocess.run(
        ["uv", "run", str(SCRIPT), "--check"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=str(REPO_ROOT),
        timeout=120,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "OK - version sincronizada" in result.stdout


def test_set_no_toca_metadata_version(tmp_path, monkeypatch):
    market = tmp_path / "marketplace.json"
    plugin = tmp_path / "plugin.json"
    market.write_text(
        json.dumps(
            {
                "metadata": {"version": "9.9.9"},  # paraguas: NO se debe tocar
                "plugins": [
                    {"name": "4dsentinel-memory", "version": "0.1.0"},
                    {"name": "otro", "version": "1.2.3"},
                ],
            }
        ),
        encoding="utf-8",
    )
    plugin.write_text(json.dumps({"version": "0.1.0"}), encoding="utf-8")

    monkeypatch.setattr(mbv, "MARKETPLACE", market)
    monkeypatch.setattr(mbv, "PLUGIN", plugin)

    assert mbv.set_version("0.2.0") == 0

    m = json.loads(market.read_text(encoding="utf-8"))
    p = json.loads(plugin.read_text(encoding="utf-8"))
    assert m["metadata"]["version"] == "9.9.9"  # paraguas intacto
    assert mbv._market_entry(m)["version"] == "0.2.0"  # entrada del plugin actualizada
    assert p["version"] == "0.2.0"  # plugin.json actualizado
    # otras entradas del marketplace no se tocan
    assert next(e for e in m["plugins"] if e["name"] == "otro")["version"] == "1.2.3"


def test_set_rechaza_no_semver(tmp_path, monkeypatch):
    market = tmp_path / "marketplace.json"
    plugin = tmp_path / "plugin.json"
    market.write_text(
        json.dumps({"plugins": [{"name": "4dsentinel-memory", "version": "0.1.0"}]}),
        encoding="utf-8",
    )
    plugin.write_text(json.dumps({"version": "0.1.0"}), encoding="utf-8")
    monkeypatch.setattr(mbv, "MARKETPLACE", market)
    monkeypatch.setattr(mbv, "PLUGIN", plugin)
    assert mbv.set_version("v0.2") == 1  # no es X.Y.Z -> rechaza sin escribir
    assert json.loads(plugin.read_text(encoding="utf-8"))["version"] == "0.1.0"


if __name__ == "__main__":
    sys.exit(subprocess.call(["pytest", "-q", str(Path(__file__))]))
