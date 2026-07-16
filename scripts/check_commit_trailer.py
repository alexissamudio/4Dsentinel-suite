#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""check_commit_trailer.py - Ningun commit debe atribuir autoria a la IA.

La convencion del repo (CLAUDE.md) prohibe el trailer 'Co-Authored-By: Claude'
y cualquier atribucion a Claude Code / Anthropic en los mensajes de commit. Vivia
solo como regla escrita (F15); aca se vuelve un check ejecutable sobre los commits
que un push/PR agrega.

Uso:
  uv run scripts/check_commit_trailer.py <base>   # revisa <base>..HEAD
  uv run scripts/check_commit_trailer.py          # revisa solo HEAD

Si <base> no es un commit valido (p.ej. el 000...0 de un branch nuevo, o vacio),
cae a revisar solo HEAD -> nunca revienta por un rango inexistente.
"""

from __future__ import annotations

import re
import subprocess
import sys

# Trailer de co-autoria de IA prohibido. Anclado a INICIO de linea (un trailer
# git siempre lo esta) para NO marcar un commit que solo MENCIONE la regla en
# prosa (p.ej. este mismo repo describe el patron en docs y mensajes). Requiere
# claude/anthropic en el valor del trailer.
AI_ATTRIBUTION = re.compile(
    r"^co-authored-by:[^\n]*\b(?:claude|anthropic)\b",
    re.IGNORECASE | re.MULTILINE,
)


def _is_valid_commit(ref: str) -> bool:
    if not ref or set(ref) == {"0"}:
        return False
    result = subprocess.run(
        ["git", "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}"],
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def _log_range(base: str | None) -> str:
    """Devuelve el rango de `git log` a revisar: base..HEAD si base es valido,
    si no solo el ultimo commit (HEAD -1)."""
    if base and _is_valid_commit(base):
        return f"{base}..HEAD"
    return "-1"


def offending_commits(base: str | None) -> list[str]:
    rango = _log_range(base)
    args = ["git", "log", "--format=%H%n%B%n==END=="]
    args.extend(rango.split())
    out = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", check=True)
    offenders = []
    for bloque in out.stdout.split("==END==\n"):
        bloque = bloque.strip()
        if not bloque:
            continue
        sha, _, cuerpo = bloque.partition("\n")
        if AI_ATTRIBUTION.search(cuerpo):
            offenders.append(sha[:12])
    return offenders


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    base = args[0] if args else None
    offenders = offending_commits(base)
    if offenders:
        print(
            "ERROR - commits con atribucion de IA prohibida (CLAUDE.md): " + ", ".join(offenders),
            file=sys.stderr,
        )
        return 1
    print("OK - sin atribucion de IA en los commits revisados")
    return 0


if __name__ == "__main__":
    sys.exit(main())
