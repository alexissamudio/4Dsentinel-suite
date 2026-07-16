"""frontmatter_utils.py - Parseo compartido de frontmatter YAML de los .md.

Helper unico para los checks que leen el frontmatter de agentes/skills/comandos
(check_agents.py, sentinel_check_skills.py, check_commands.py). Antes cada uno
tenia su propia copia de `frontmatter()` (identica en 3 sitios) y el fix de
`parse_tools` (F1) no se propagaba; centralizarlo mata esa clase de bug
(cf. auditoria 2026-07-15, F9).

Este modulo NO es un script ejecutable: lo importan los checks.

El regex de apertura tolera trailing whitespace (`^---\\s*\\n`) por defensa ante
CRLF/espacios (cf. F5); `.gitattributes` ya fuerza LF en los .md del repo, asi
que en la practica no cambia el resultado, pero endurece parsers de terceros.
"""

from __future__ import annotations

import re

_FRONTMATTER = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
_TOOLS_KEY = re.compile(r"^tools\s*:\s*(.*)$")
_LIST_ITEM = re.compile(r"^\s*-\s+(.+?)\s*$")


def frontmatter_body(text: str) -> str | None:
    """Devuelve el cuerpo (entre los `---`) del frontmatter, o None si no hay."""
    m = _FRONTMATTER.match(text)
    return m.group(1) if m else None


def strip_quotes(value: str) -> str:
    """Quita comillas simples o dobles envolventes de un valor escalar."""
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        return value[1:-1]
    return value


def frontmatter(text: str) -> dict[str, str]:
    """Parsea el frontmatter como pares escalar `clave: valor` (sin listas)."""
    body = frontmatter_body(text)
    if body is None:
        return {}
    fm: dict[str, str] = {}
    for line in body.splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            fm[k.strip()] = v.strip()
    return fm


def parse_tools(text: str) -> set[str]:
    """Extrae el set de tools del frontmatter en AMBOS formatos:

    - inline con comas:   ``tools: Read, Grep, Glob``  (o ``[Read, Grep]``)
    - bloque lista YAML:  ``tools:\\n  - Read\\n  - Bash``

    Reune todas las herramientas en un set sin importar el formato. Sin esto,
    un ``tools:`` en formato lista dejaba el campo vacio (el parser scalar solo
    veia ``tools`` -> "") y un agente con Write/Bash PASABA el check (falso OK),
    rompiendo la garantia read-only que el guard protege (cf. F1).
    """
    body = frontmatter_body(text)
    if body is None:
        return set()
    lines = body.splitlines()
    tools: set[str] = set()
    for i, line in enumerate(lines):
        m = _TOOLS_KEY.match(line)
        if not m:
            continue
        inline = m.group(1).strip().strip("[]").strip()
        if inline:
            # Formato inline con comas. (.strip("'\"") como el original: quita
            # cualquier comilla en los extremos; NO se cambia por strip_quotes
            # para no alterar la semantica de un guard de seguridad.)
            tools |= {t.strip().strip("'\"") for t in inline.split(",") if t.strip()}
        else:
            # Formato bloque lista: lineas siguientes '- X' (con indentacion 0 o
            # mas: YAML acepta el item a la misma columna que la clave), hasta la
            # proxima clave (primera linea no vacia que no sea un item de lista).
            for nxt in lines[i + 1 :]:
                if not nxt.strip():
                    continue
                item = _LIST_ITEM.match(nxt)
                if not item:
                    break
                tools.add(item.group(1).strip().strip("'\""))
        break
    return tools
