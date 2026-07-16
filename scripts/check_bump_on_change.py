#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""check_bump_on_change.py - Exige bump de version cuando cambia un plugin (F17).

Todo cambio en el contenido SHIPPEADO de un plugin (cualquier archivo bajo su
`source` del marketplace: codigo, hooks, skills, agents, commands, plugin.json)
DEBE venir con un bump de la `version` de ese plugin. Sin eso, el usuario corre
codigo stale o una version distinta a la del catalogo, sin senal (F17 de la
auditoria 2026-07-15).

Compara el rango BASE..HEAD (BASE = argv[1], el mismo que usa check_commit_trailer):
por cada plugin con archivos cambiados bajo su `source`, la `version` de su plugin.json
debe DIFERIR entre BASE y HEAD. Los docs internos del repo (.claude/docs/, README,
auditoria) NO son contenido de plugin (no caen bajo ningun `source`) -> no cuentan.

Sin BASE valido (p.ej. un push sin historia previa) no se puede comparar: se saltea sin
bloquear. Un plugin NUEVO (sin plugin.json en BASE) tampoco exige bump.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
MARKETPLACE = REPO_ROOT / ".claude-plugin" / "marketplace.json"


def touched_source(source: str, changed: list[str]) -> list[str]:
    """Archivos de `changed` que caen bajo el `source` de un plugin."""
    prefix = source.rstrip("/") + "/"
    return [f for f in changed if f == source or f.startswith(prefix)]


def evaluate(
    plugins: list[tuple[str, str]],
    changed: list[str],
    old_versions: dict[str, str | None],
    new_versions: dict[str, str | None],
) -> list[tuple[str, str | None, list[str]]]:
    """Logica pura: plugins con cambios shippeados y version SIN bumpear.

    plugins: [(name, source)]. old/new_versions: name -> version|None.
    Un plugin nuevo (old is None) no exige bump. Devuelve [(name, version, touched)].
    """
    fallas: list[tuple[str, str | None, list[str]]] = []
    for name, source in plugins:
        touched = touched_source(source, changed)
        if not touched:
            continue
        old = old_versions.get(name)
        new = new_versions.get(name)
        if old is not None and old == new:
            fallas.append((name, old, touched))
    return fallas


def _base_valid(base: str) -> bool:
    return (
        subprocess.run(
            ["git", "rev-parse", "--verify", "--quiet", f"{base}^{{commit}}"],
            capture_output=True,
        ).returncode
        == 0
    )


def _changed_files(base: str) -> list[str]:
    out = subprocess.run(
        ["git", "diff", "--name-only", base, "HEAD"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    ).stdout
    return [ln.strip() for ln in out.splitlines() if ln.strip()]


def _version_at(ref: str, rel_path: str) -> str | None:
    """`version` del plugin.json en `ref`, o None si no existe / no parsea alli."""
    r = subprocess.run(
        ["git", "show", f"{ref}:{rel_path}"],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if r.returncode != 0:
        return None
    try:
        data = json.loads(r.stdout)
    except json.JSONDecodeError:
        return None
    ver = data.get("version") if isinstance(data, dict) else None
    return ver if isinstance(ver, str) else None


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    base = args[0] if args else ""
    if not base or not _base_valid(base):
        print("SKIP - sin BASE valido para comparar; no se evalua el bump")
        return 0

    market: dict[str, Any] = json.loads(MARKETPLACE.read_text(encoding="utf-8"))
    plugins: list[tuple[str, str]] = []
    for p in market.get("plugins", []):
        source = p.get("source")
        if isinstance(source, str):
            plugins.append((p.get("name", "<sin-name>"), source))

    changed = _changed_files(base)
    old_versions: dict[str, str | None] = {}
    new_versions: dict[str, str | None] = {}
    for name, source in plugins:
        pj = f"{source.rstrip('/')}/.claude-plugin/plugin.json"
        old_versions[name] = _version_at(base, pj)
        new_versions[name] = _version_at("HEAD", pj)

    fallas = evaluate(plugins, changed, old_versions, new_versions)
    if fallas:
        print(
            "ERROR - cambio shippeado de plugin sin bump de version (F17):",
            file=sys.stderr,
        )
        for name, ver, touched in fallas:
            print(
                f"  - {name}: version sigue en {ver!r}; cambiaron {len(touched)} "
                f"archivo(s), p.ej. {touched[0]}",
                file=sys.stderr,
            )
        print(
            "Corre `uv run scripts/<plugin>_bump_version.py --set X.Y.Z` "
            "(sincroniza plugin.json + marketplace).",
            file=sys.stderr,
        )
        return 1
    print("OK - todo plugin con cambios shippeados trae bump de version")
    return 0


if __name__ == "__main__":
    sys.exit(main())
