#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""build_harness.py - Generador multi-harness: Claude Code suite -> Codex / OpenCode.

Toma la FUENTE canonica de la suite (plugins/*, read-only) y emite bundles
regenerables bajo dist/: dist/codex/ (Codex CLI) y dist/opencode/ (OpenCode).

Alcance del PoC (lo demas queda como TODO comentado en el bundle):
  Codex (dist/codex/):
    - skill  : handoff
    - hooks  : hooks.json (mismo schema de Claude Code) con rutas absolutas.
               Codex descubre los hooks via $CODEX_HOME/hooks.json o
               <proyecto>/.codex/hooks.json -- NO via config.toml [hooks].
    - agente : critic ([agents.critic] en config.toml)
  OpenCode (dist/opencode/, OpenCode 1.19.x y 2.2.5 -- TODO el bundle sale de aca):
    - command   : un command por skill portable (cuerpo + references
                  INCRUSTADOS y traducidos; ver M.SKILLS_UNSUPPORTED) y por
                  cada command de memory (command/*.md).
    - agentes   : todos los de sentinel-agents (agent/*.md, mode: subagent,
                  permisos del allowlist + external_directory sobre references/).
    - references: agent-contract.md (sec. 7 reescrita) + KB ISO (byte-a-byte).
    - hooks     : plugin shim JS (plugin/fluency-hooks.js) que puentea los hooks
                  Python de UserPromptSubmit (v1: chat.message; v2: hook context).
    - config    : opencode.json (solo documenta el MCP).

Idempotente: correrlo N veces produce el mismo arbol de salida.

ASCII puro (regla de CLAUDE.md): sin acentos en los strings de codigo. Los
archivos de CONTENIDO que emite (SKILL.md, config.toml, AGENTS.md...) SI llevan
acentos, porque su texto proviene de leer los archivos fuente en UTF-8.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

# tools/multiharness/build_harness.py -> parents[2] = raiz del repo.
REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(REPO_ROOT / "scripts"))
import mappings as M  # noqa: E402
from frontmatter_utils import parse_tools  # noqa: E402

# ---------------------------------------------------------------------------
# Rutas ancla (absolutas, resueltas desde la ubicacion de este script)
# ---------------------------------------------------------------------------
PLUGINS = REPO_ROOT / "plugins"
FLUENCY_ROOT = PLUGINS / "fluency-4d"          # resuelve ${CLAUDE_PLUGIN_ROOT}
SENTINEL_ROOT = PLUGINS / "sentinel-agents"
MEMORY_ROOT = PLUGINS / "memory"
DEFAULT_DIST = REPO_ROOT / "dist" / "codex"
DEFAULT_OPENCODE_DIST = REPO_ROOT / "dist" / "opencode"
DEFAULT_HERMES_DIST = REPO_ROOT / "dist" / "hermes"

# ---------------------------------------------------------------------------
# Exclusion "solo Claude Code"
# ---------------------------------------------------------------------------
# Piezas de fluency-4d que dependen del engine de mods de Claude Code (Panel 4D,
# hooks module TSX) o de su status line / temas. NO se emiten a Codex ni a
# OpenCode. Rutas relativas a plugins/fluency-4d (se nombran aunque todavia no
# existan: la lista es el contrato, no un reflejo del arbol actual). Las skills
# salen de M.SKILLS_UNSUPPORTED: las que no soporta ningun harness.
CLAUDE_CODE_ONLY: tuple[str, ...] = (
    "hooks/register.tsx",      # hooks module del Panel 4D
    "tests",                   # tests del panel (claude plugin test)
    "types",                   # contrato $.state del panel
    "tsconfig.json",           # typecheck del panel
    ".claude-plugin/types",    # tipos que escribe el engine
    "statusline",              # status line (Node)
    "themes",                  # temas de Claude Code
) + tuple(
    "skills/" + skill
    for skill, (harnesses, _) in M.SKILLS_UNSUPPORTED.items()
    if set(M.HARNESSES) <= set(harnesses)
)
# Claves de hooks/hooks.json que solo entiende Claude Code (`modules` = hooks
# modules del engine de mods). Se quitan antes de transpilar.
CLAUDE_CODE_ONLY_HOOK_KEYS: tuple[str, ...] = ("modules",)


def is_claude_code_only(path: Path) -> bool:
    """True si `path` (abs o relativo a fluency-4d) cae bajo CLAUDE_CODE_ONLY."""
    p = Path(path)
    if p.is_absolute():
        try:
            p = p.relative_to(FLUENCY_ROOT)
        except ValueError:
            return False
    rel = p.as_posix()
    return any(rel == x or rel.startswith(x + "/") for x in CLAUDE_CODE_ONLY)


def strip_claude_only_keys(hooks: dict) -> dict:
    """Copia de hooks.json sin las claves CLAUDE_CODE_ONLY_HOOK_KEYS."""
    return {k: v for k, v in hooks.items() if k not in CLAUDE_CODE_ONLY_HOOK_KEYS}


def unsupported_skills(harness: str) -> dict[str, str]:
    """{skill: razon} de las skills que `harness` no soporta (M.SKILLS_UNSUPPORTED)."""
    return {skill: why for skill, (harnesses, why) in M.SKILLS_UNSUPPORTED.items()
            if harness in harnesses}


# ---------------------------------------------------------------------------
# Descubrimiento
# ---------------------------------------------------------------------------
def discover_skills() -> list[Path]:
    """Globea plugins/*/skills/*/SKILL.md (NO lee el campo skills de plugin.json).

    Excluye las skills CLAUDE_CODE_ONLY de fluency-4d (barra, statusline).
    """
    return sorted(p for p in PLUGINS.glob("*/skills/*/SKILL.md")
                  if not is_claude_code_only(p.parent))


def parse_frontmatter(text: str) -> dict[str, str]:
    """Parser minimo de frontmatter YAML plano (key: value entre --- ---)."""
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end == -1:
        return {}
    block = text[3:end]
    out: dict[str, str] = {}
    for line in block.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, _, val = line.partition(":")
        key = key.strip()
        val = val.strip()
        if len(val) >= 2 and val[0] == val[-1] and val[0] in "\"'":
            val = val[1:-1]
        out[key] = val
    return out


def discover_agents() -> dict[str, dict[str, str]]:
    """Parsea el frontmatter de plugins/sentinel-agents/agents/*.md.

    El texto completo queda en meta["_text"] (los builders no releen el .md).
    """
    agents: dict[str, dict[str, str]] = {}
    for md in sorted(SENTINEL_ROOT.glob("agents/*.md")):
        text = md.read_text(encoding="utf-8")
        meta = parse_frontmatter(text)
        meta["_path"] = str(md)
        meta["_text"] = text
        agents[meta.get("name", md.stem)] = meta
    return agents


def load_hooks() -> dict:
    """Lee plugins/fluency-4d/hooks/hooks.json sin las claves solo-Claude-Code."""
    raw = json.loads((FLUENCY_ROOT / "hooks" / "hooks.json").read_text(encoding="utf-8"))
    return strip_claude_only_keys(raw)


def hook_script_names(hooks: dict, event: str) -> list[str]:
    """Nombres (`x.py`) de los hooks de `event` bajo ${CLAUDE_PLUGIN_ROOT}/hooks/, en orden."""
    marker = M.PLUGIN_ROOT_VAR + "/hooks/"
    out: list[str] = []
    for group in hooks.get("hooks", {}).get(event, []):
        for hk in group.get("hooks", []):
            cmd = hk.get("command", "")
            idx = cmd.find(marker)
            if idx != -1:
                out.append(cmd[idx + len(marker):].split('"')[0].split(" ")[0])
    return out


def hook_list(hooks: dict, event: str) -> str:
    """'a, b, c' con los nombres sin `.py` de los hooks de `event` (para READMEs)."""
    return ", ".join(Path(n).stem for n in hook_script_names(hooks, event))


# ---------------------------------------------------------------------------
# Helpers de emision
# ---------------------------------------------------------------------------
def quote_dq(s: str) -> str:
    """String entre comillas dobles con \\ y " escapados.

    Mismo escape para un basic string TOML y un escalar YAML double-quoted.
    """
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def resolve_plugin_root(obj):
    """Reemplaza ${CLAUDE_PLUGIN_ROOT} por la ruta abs de fluency-4d (recursivo).

    Camina dicts/lists/strings de la estructura de hooks.json y sustituye la
    variable de plugin de Claude por la ruta absoluta de plugins/fluency-4d en
    esta maquina. Los backslashes se escapan solos al pasar por json.dumps.
    """
    root = str(FLUENCY_ROOT)
    if isinstance(obj, dict):
        return {k: resolve_plugin_root(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [resolve_plugin_root(v) for v in obj]
    if isinstance(obj, str):
        return obj.replace(M.PLUGIN_ROOT_VAR, root)
    return obj


def write(path: Path, content: str) -> Path:
    """Escribe UTF-8 (con \\n) creando padres. Devuelve la ruta."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")
    return path


# ---------------------------------------------------------------------------
# Transpiladores
# ---------------------------------------------------------------------------
def build_hooks_json(hooks: dict) -> str:
    """Transpila fluency-4d/hooks/hooks.json al hooks.json del bundle Codex.

    Formato IDENTICO al de Claude Code (Codex adopto ese contrato): mismos
    eventos y schema, solo se resuelve ${CLAUDE_PLUGIN_ROOT} a la ruta absoluta
    de plugins/fluency-4d. Codex descubre este archivo en $CODEX_HOME/hooks.json
    o en <proyecto>/.codex/hooks.json (mecanismo verificado por E2E) -- NO por
    config.toml [hooks]. Incluye todos los eventos (UserPromptSubmit,
    PostToolUse, Stop) tal cual la fuente. Sin
    `modules` (hooks module del Panel 4D, solo Claude Code).
    """
    resolved = resolve_plugin_root(strip_claude_only_keys(hooks))
    return json.dumps(resolved, indent=2, ensure_ascii=False) + "\n"


def build_config_toml(agents: dict[str, dict[str, str]]) -> str:
    critic = agents.get("critic", {})
    desc = critic.get("description", "")
    parts = [
        "# config.toml - bundle Codex generado por tools/multiharness/build_harness.py",
        "# NO editar a mano: regenerar con `uv run --script tools/multiharness/build_harness.py`.",
        "",
        M.HOOK_FEATURE_FLAG,
        "",
        "# --- Hooks ---",
        "# El mecanismo REAL de ejecucion de hooks en Codex es `hooks.json` (mismo",
        "# schema que Claude Code), descubierto en $CODEX_HOME/hooks.json o en",
        "# <proyecto>/.codex/hooks.json. Este bundle lo emite como `hooks.json`",
        "# (junto a este archivo). NO se declaran hooks en config.toml: la seccion",
        "# [hooks] parsea pero NO dispara nada (mecanismo equivocado).",
        "# Nota: los hooks corren en la sesion interactiva (TUI); `codex exec`",
        "# headless NO los dispara (ref issue openai/codex#17532).",
        "",
        "# --- Subagentes ---",
        "[agents]",
        "# Subagentes portados de plugins/sentinel-agents/agents/*.md",
        "",
        "[agents.critic]",
        "description = " + quote_dq(desc),
        'config_file = "critic.config.toml"',
        "",
        "# TODO(PoC): resto de sentinel-agents (advisor, bug-hunter, code-reviewer, ...)",
        "# mismo patron: [agents.<name>] con config_file dedicado.",
        "",
        "# --- MCP: DIFERIDO ---",
        "# El binario codebase-memory (cbm) no esta instalado -> sin [mcp_servers].",
        "",
    ]
    return "\n".join(parts)


def build_critic_config(agents: dict[str, dict[str, str]]) -> str:
    critic = agents.get("critic", {})
    model = critic.get("model", "inherit")
    max_turns = critic.get("maxTurns", "")
    tools = critic.get("tools", "")
    out = [
        "# critic.config.toml - config del subagente critic para Codex CLI.",
        "# Portado de plugins/sentinel-agents/agents/critic.md (fuente Claude).",
        "# El cuerpo/instrucciones del agente vive en agents/critic.md.",
        "",
        "# model (Claude): %s" % model,
    ]
    if model.strip().lower() == "inherit":
        out.append("#   -> 'inherit' en Claude: en Codex se hereda el modelo de la sesion")
        out.append("#      (sin override). Descomentar para forzar uno:")
        out.append('# model = "o4-mini"')
    else:
        out.append("model = " + quote_dq(model))
    out += [
        "",
        "# maxTurns (Claude) = %s" % (max_turns or "n/d"),
        "# TODO(verificar-schema): confirmar el nombre exacto del campo en el",
        "# schema [agents] de Codex 0.130 antes de activarlo.",
    ]
    if max_turns:
        out.append("# max_turns = %s" % max_turns)
    out += [
        "",
        "# tools (Claude): %s" % (tools or "n/d"),
        "# Read/Grep/Glob = solo-lectura -> mapear a las tools read-only de Codex.",
        "",
    ]
    return "\n".join(out)


def strip_frontmatter(text: str) -> str:
    if not text.startswith("---"):
        return text
    end = text.find("\n---", 3)
    if end == -1:
        return text
    nl = text.find("\n", end + 1)
    return text[nl + 1:] if nl != -1 else ""


def build_critic_body(agents: dict[str, dict[str, str]]) -> str:
    body = strip_frontmatter(agents["critic"]["_text"]).lstrip("\n")
    header = (
        "<!-- Portado de plugins/sentinel-agents/agents/critic.md por "
        "tools/multiharness/build_harness.py. NO editar a mano. -->\n"
        "<!-- NOTA(PoC): la referencia a references/agent-contract.md NO esta "
        "incluida en este bundle; portarla es un TODO. -->\n\n"
    )
    return header + body


def build_handoff_skill() -> str:
    src = (FLUENCY_ROOT / "skills" / "handoff" / "SKILL.md").read_text(encoding="utf-8")
    # 1) reescribir el home del harness (~/.claude -> ~/.codex, y las variantes
    #    $CLAUDE_HOME/${CLAUDE_HOME}) usando la tabla-fuente mappings.HOME_MAP en
    #    vez de un literal hardcodeado. El SKILL.md fuente hoy solo contiene
    #    "~/.claude"; las otras claves no aparecen -> salida identica (sin drift),
    #    pero la traduccion queda gobernada por la tabla documentada.
    out = src
    for src_home, dst_home in M.HOME_MAP.items():
        out = out.replace(src_home, dst_home)
    # 2) insertar la nota de degradacion en el paso del plan activo.
    #    (la nota no contiene '~/.claude' para no re-mangear en re-generaciones).
    marker = "en `~/.codex/plans/` (por mtime), o el de la tarea."
    # tolerar acento en 'mas' del fuente (no afecta este marcador):
    marker_acc = marker
    note = (
        " **NOTA (Codex): Codex no hereda el directorio de planes de Claude; "
        "si `~/.codex/plans/` no esta poblado, este paso degrada a 'sin plan' "
        "y usas solo el estado/tarea.**"
    )
    if marker_acc in out:
        out = out.replace(marker_acc, marker_acc + note, 1)
    elif marker in out:
        out = out.replace(marker, marker + note, 1)
    banner = (
        "<!-- Portado de plugins/fluency-4d/skills/handoff/SKILL.md por "
        "tools/multiharness/build_harness.py. Rutas ~/.claude reescritas a "
        "~/.codex. La seccion de clipboard NO se toco. NO editar a mano. -->\n"
    )
    # insertar el banner despues del frontmatter
    if out.startswith("---"):
        end = out.find("\n---", 3)
        nl = out.find("\n", end + 1)
        out = out[: nl + 1] + banner + out[nl + 1:]
    else:
        out = banner + out
    return out


def build_handoff_prompt() -> str:
    return (
        "# /handoff\n\n"
        "Wrapper de slash command para Codex CLI. Dispara el skill `handoff`\n"
        "(instalado en `.agents/skills/handoff/SKILL.md`).\n\n"
        "Segui el skill `handoff` al pie de la letra: recolecta el contexto de\n"
        "git y el estado de sesion, actualiza `.claude/docs/estado-sesion.md`\n"
        "(o su equivalente del proyecto), sugeri el commit (NO lo ejecutes) y\n"
        "copia el handoff al portapapeles.\n\n"
        "NOTA (Codex): el paso del \"plan activo\" en `~/.codex/plans/` degrada a\n"
        "\"sin plan\" si ese directorio no existe (Codex no hereda los planes de\n"
        "Claude). El resto del skill es cross-harness.\n"
    )


def extract_hard_rules(claude_md: str) -> tuple[list[str], list[str]]:
    """Extrae las 'Reglas del proyecto (siempre)' y la tabla de puentes de CLAUDE.md."""
    lines = claude_md.splitlines()
    rules: list[str] = []
    bridges: list[str] = []
    in_rules = False
    in_bridges = False
    for ln in lines:
        s = ln.strip()
        if s.startswith("## Reglas del proyecto"):
            in_rules, in_bridges = True, False
            continue
        if s.startswith("## Puentes"):
            in_rules, in_bridges = False, True
            continue
        if s.startswith("## ") or s.startswith("<!-- END"):
            in_rules = in_bridges = False
            continue
        if in_rules and s.startswith("- "):
            rules.append(s)
        if in_bridges and s.startswith("|"):
            bridges.append(s)
    return rules, bridges


def build_contract_md(head: list[str], no_rules: str, bridges_note: list[str],
                      no_bridges: str, tail: list[str],
                      bridge_rewrite: tuple[str, str] | None = None) -> str:
    """Contrato del proyecto (reglas duras + puentes de CLAUDE.md) para otro harness.

    head/tail rodean las secciones fijas; bridges_note va antes de la tabla de
    puentes; bridge_rewrite = (old, new) aplicado a cada fila de la tabla.
    """
    rules, bridges = extract_hard_rules((REPO_ROOT / "CLAUDE.md").read_text(encoding="utf-8"))
    if bridge_rewrite:
        bridges = [b.replace(*bridge_rewrite) for b in bridges]
    parts = [*head, "## Reglas del proyecto (siempre)", ""]
    parts += rules or [no_rules]
    parts += ["", "## Puentes de documentacion", "", *bridges_note]
    parts += bridges or [no_bridges]
    parts += tail
    return "\n".join(parts)


def build_agents_md() -> str:
    return build_contract_md(
        head=[
            "# AGENTS.md - contrato del proyecto (bundle Codex)",
            "",
            "> Generado por `tools/multiharness/build_harness.py` desde los "
            "innegociables de `CLAUDE.md`. Equivalente en Codex de las reglas duras "
            "de Claude Code.",
            "",
        ],
        no_rules="- (sin reglas detectadas en CLAUDE.md)",
        bridges_note=[
            "> NOTA (Codex): los puentes apuntan a `.claude/docs/*` del proyecto. "
            "Codex no ejecuta el hook `bridge_router` automaticamente para leerlos; "
            "leelos a mano si la tarea toca ese tema.",
            "",
        ],
        no_bridges="(sin tabla de puentes)",
        tail=[
            "",
            "## Notas de portabilidad",
            "",
            "- Hooks: emitidos como `hooks.json` (schema de Claude Code), descubierto "
            "en `$CODEX_HOME/hooks.json` o `<proyecto>/.codex/hooks.json`. `config.toml` "
            "solo activa `[features] hooks = true`; su bloque `[hooks]` NO dispara nada.",
            "- Subagentes: `[agents.<name>]` + `<name>.config.toml`.",
            "- MCP (codebase-memory): DIFERIDO (binario `cbm` no instalado).",
            "",
        ],
    )


def build_readme(hooks: dict) -> str:
    hook_lists = tuple(hook_list(hooks, ev) for ev in ("UserPromptSubmit", "PostToolUse", "Stop"))
    return (
        "# Bundle Codex de la suite 4Dsentinel (PoC)\n"
        "\n"
        "Bundle regenerable que porta parte de la suite de plugins de Claude "
        "Code a **Codex CLI 0.130** (que adopto el contrato de hooks de Claude "
        "Code). Generado por `tools/multiharness/build_harness.py` desde la "
        "fuente canonica en `plugins/*` (read-only).\n"
        "\n"
        "## Que incluye este PoC\n"
        "\n"
        "- **Skill** `handoff` -> `.agents/skills/handoff/SKILL.md` (rutas "
        "`~/.claude` reescritas a `~/.codex`).\n"
        "- **Slash command** `handoff` -> `prompts/handoff.md`.\n"
        "- **Hooks** -> `hooks.json` (formato Claude Code): `UserPromptSubmit` "
        "(%s), `PostToolUse` (%s) y `Stop` (%s), con rutas absolutas a esta "
        "maquina.\n"
        "- **Subagente** `critic` -> `[agents.critic]` en `config.toml` + "
        "`critic.config.toml` + `agents/critic.md`.\n"
        "- **AGENTS.md** con las reglas duras del proyecto.\n"
        "\n"
        "## Como descubre Codex los hooks\n"
        "\n"
        "Codex ejecuta los hooks a partir de un `hooks.json` con el **mismo "
        "formato JSON que Claude Code**, buscado en `$CODEX_HOME/hooks.json` o "
        "en `<proyecto>/.codex/hooks.json`. Este es el mecanismo real "
        "(verificado por E2E). El bloque `[hooks]` de `config.toml` **parsea "
        "pero NO ejecuta** nada: por eso el bundle NO declara hooks ahi, solo "
        "deja `[features] hooks = true` y emite el `hooks.json`.\n"
        "\n"
        "> **Los hooks de Codex son de la sesion interactiva (TUI).** `codex "
        "exec` (headless) **NO** los dispara -- es una limitacion conocida de "
        "Codex (ref issue [openai/codex#17532]"
        "(https://github.com/openai/codex/issues/17532)), no un defecto de este "
        "bundle.\n"
        "\n"
        "## Instalacion\n"
        "\n"
        "Codex usa `CODEX_HOME` (default `~/.codex`). Copia el contenido de "
        "este bundle ahi (incluido `hooks.json`):\n"
        "\n"
        "```bash\n"
        "# Linux/macOS\n"
        "cp -r dist/codex/. \"${CODEX_HOME:-$HOME/.codex}\"/\n"
        "```\n"
        "\n"
        "```powershell\n"
        "# Windows PowerShell\n"
        "$dst = if ($env:CODEX_HOME) { $env:CODEX_HOME } else { \"$HOME\\.codex\" }\n"
        "Copy-Item -Recurse -Force dist\\codex\\* $dst\n"
        "```\n"
        "\n"
        "Alternativa por proyecto: copia `hooks.json` a `<proyecto>/.codex/"
        "hooks.json`. Verifica ademas que `config.toml` tenga `[features] "
        "hooks = true`.\n"
        "\n"
        "## Que se verifico\n"
        "\n"
        "- El generador corre sin error y es idempotente (`check_harness.py` no "
        "reporta drift).\n"
        "- `hooks.json` parsea como JSON y `config.toml` con `tomllib`.\n"
        "- Las rutas de los hooks son absolutas y apuntan a `.py` existentes.\n"
        "\n"
        "## Pendiente / no verificado\n"
        "\n"
        "- **E2E con Codex**: NO ejecutado aca (lo valida el humano). Recordar "
        "que los hooks solo corren en la TUI interactiva, no en `codex exec`.\n"
        "- **MCP** (codebase-memory / `cbm`): DIFERIDO, binario no instalado.\n"
        "- **Resto de subagentes** y `references/agent-contract.md`: TODO.\n"
        "- `~/.claude/plans/`: sin equivalente en Codex -> el paso del plan en "
        "`handoff` degrada a \"sin plan\".\n"
    ) % hook_lists


# ---------------------------------------------------------------------------
# OpenCode (dist/opencode/)
# ---------------------------------------------------------------------------
# Instalacion GLOBAL del bundle (OpenCode usa XDG: ~/.config/opencode). Los
# agentes y los commands referencian archivos del bundle por ruta ABSOLUTA de
# instalacion (references/ vive fuera del proyecto -> permiso external_directory).
OPENCODE_HOME = Path.home() / ".config" / "opencode"
OC_REFS_DIR = OPENCODE_HOME / "references"
PLUGIN_ROOTS: dict[str, Path] = {
    "fluency-4d": FLUENCY_ROOT,
    "sentinel-agents": SENTINEL_ROOT,
    "memory": MEMORY_ROOT,
}
# Subagentes nativos de OpenCode (mode: subagent) -- fallback del shim si el
# client del plugin no responde.
OPENCODE_NATIVE_SUBAGENTS: tuple[str, ...] = ("general", "explore")

BACKTICK_REF = re.compile(r"`references/([^`]*)`")
# `sentinel-agents:<agente>` -> `<agente>`. SENTINEL_NS/AGENT_NAME_RE tambien
# generan la regla equivalente del shim JS y la guarda de check_harness.
SENTINEL_NS = "sentinel-agents:"
AGENT_NAME_RE = r"[a-z][a-z-]*"
SENTINEL_PREFIX = re.compile(SENTINEL_NS + "(" + AGENT_NAME_RE + ")")
OC_TOOL_RENAMES = tuple((re.compile(r"\b%s\b" % re.escape(old)), new)
                        for old, new in M.OPENCODE_TOOL_RENAMES)


def oc_replace(text: str, rules, origin: str) -> str:
    """Aplica (old, new) en orden. `old` str -> literal; re.Pattern -> regex.

    Cada regla DEBE matchear al menos una vez: si la fuente cambio y el marcador
    ya no existe, el build falla en vez de emitir una traduccion a medias.
    Despues resuelve {OC_REFS} (ruta absoluta de references/ instalado).
    """
    for old, new in rules:
        if isinstance(old, re.Pattern):
            text, n = old.subn(new, text)
        else:
            n = text.count(old)
            text = text.replace(old, new)
        if n == 0:
            raise SystemExit("ERROR(%s): marcador de traduccion no encontrado: %r"
                             % (origin, getattr(old, "pattern", old)))
    return text.replace("{OC_REFS}", OC_REFS_DIR.as_posix())


def oc_translate_common(text: str, plugin_root: Path) -> str:
    """Traduccion Claude Code -> OpenCode comun a commands y agentes.

    - `sentinel-agents:X`  -> `X` (subagente OpenCode, tool task / subagent en 2.x).
    - ${CLAUDE_PLUGIN_ROOT} -> ruta abs del plugin en este repo (igual que el shim).
    - tools exclusivas de Claude Code -> equivalente OpenCode (M.OPENCODE_TOOL_MAP
      y los identificadores de M.OPENCODE_TOOL_RENAMES).
    - ~/.claude/plans/      -> directorios de planes de OpenCode.
    Los flags/estado en ~/.claude/fluency4d/ NO se traducen: los leen/escriben
    los hooks Python, que en OpenCode corren via el shim con esa misma ruta.
    """
    text = SENTINEL_PREFIX.sub(r"\1", text)
    text = text.replace(M.PLUGIN_ROOT_VAR, plugin_root.as_posix())
    for old, new in (*M.OPENCODE_TOOL_MAP, *M.OPENCODE_HOME_MAP):
        text = text.replace(old, new)
    for pattern, new in OC_TOOL_RENAMES:
        text = pattern.sub(new, text)
    return text


def oc_rewrite_refs(text: str, skill_dir: Path | None, plugin_root: Path) -> str:
    """Reescribe `references/<x>` backtickeado.

    - si <x> existe en <skill>/references/ -> el texto apunta a la copia
      INCRUSTADA al final del command;
    - si existe en <plugin>/references/ -> ruta ABSOLUTA de instalacion del
      bundle (~/.config/opencode/references/<x>).
    """
    def sub(m: re.Match) -> str:
        rel = m.group(1)
        if skill_dir is not None and (skill_dir / "references" / rel).is_file():
            return "`%s` (referencia incrustada al final de este comando)" % rel
        if (plugin_root / "references" / rel.rstrip("/")).exists():
            dst = (OC_REFS_DIR / rel.rstrip("/")).as_posix()
            return "`%s%s`" % (dst, "/" if rel.endswith("/") else "")
        raise SystemExit("ERROR: referencia no resoluble: references/%s" % rel)
    return BACKTICK_REF.sub(sub, text)


def opencode_userprompt_scripts(hooks: dict) -> list[str]:
    """Rutas absolutas de los .py de UserPromptSubmit (para el shim JS)."""
    return [str(FLUENCY_ROOT / "hooks" / name)
            for name in hook_script_names(hooks, "UserPromptSubmit")]


# --- Commands (skills + commands de memory) ---------------------------------
def opencode_skills(skills: list[Path]) -> list[Path]:
    """Skills portables que se emiten como command (sin las que OpenCode no soporta)."""
    skipped = unsupported_skills("opencode")
    return [p for p in skills if p.parent.name not in skipped]


def oc_command_header(desc: str, origin: str) -> str:
    return (
        "---\n"
        "description: " + quote_dq(desc) + "\n"
        "agent: build\n"
        "---\n\n"
        "<!-- Generado por tools/multiharness/build_harness.py desde %s "
        "(cuerpo incrustado y traducido a OpenCode). NO editar a mano. -->\n\n" % origin
    )


def build_opencode_skill_command(skill_md: Path, agent_names: list[str]) -> str:
    name = skill_md.parent.name
    plugin = skill_md.parents[2].name
    plugin_root = PLUGIN_ROOTS[plugin]
    origin = "plugins/%s/skills/%s" % (plugin, name)
    raw = skill_md.read_text(encoding="utf-8")
    # Reglas por-skill sobre el fuente COMPLETO (frontmatter incluido: la
    # description tambien puede nombrar mecanismos de Claude Code).
    src = oc_replace(raw, M.OPENCODE_SKILL_RULES.get(name, ()), origin)
    meta = parse_frontmatter(src)
    meta["description"] = oc_translate_common(meta.get("description", name), plugin_root)
    body = oc_translate_common(strip_frontmatter(src).lstrip("\n"), plugin_root)
    body = oc_rewrite_refs(body, skill_md.parent, plugin_root)

    notes = [
        "> **OpenCode (bundle 4Dsentinel, OpenCode %s).** Este comando INCRUSTA "
        "el skill `%s` completo: segui las instrucciones de abajo tal cual. NO "
        "busques un archivo de skill ni rutas de instalacion de Claude Code. Los "
        "subagentes de la suite (advisor, critic, librarian, ...) se invocan con "
        "la tool `task` (`subagent_type: <nombre>`) en OpenCode 1.x, o con la "
        "tool `subagent` (`agent: <nombre>`) en 2.x." % (M.OPENCODE_VERSION, name),
    ]
    extra = M.OPENCODE_SKILL_NOTES.get(name)
    if extra:
        if "{SKILL_AGENTS}" in extra:
            named = dict.fromkeys(a for a in SENTINEL_PREFIX.findall(raw) if a in agent_names)
            if not named:
                raise SystemExit("ERROR(%s): {SKILL_AGENTS} sin subagentes conocidos" % origin)
            extra = extra.replace("{SKILL_AGENTS}", ", ".join("`%s`" % a for a in named))
        notes.append("> " + extra)
    out = oc_command_header(meta.get("description", name), origin)
    out += "\n>\n".join(notes) + "\n\n" + body.rstrip("\n") + "\n"

    ref_dir = skill_md.parent / "references"
    if ref_dir.is_dir():
        # Se incrustan TODAS las references del skill (no solo las citadas):
        # el command debe ser autocontenido (fuera del proyecto, la lectura de
        # archivos pide external_directory y `opencode run` la auto-rechaza).
        refs = sorted(p for p in ref_dir.rglob("*") if p.is_file())
        out += "\n---\n\n## Referencias incrustadas\n"
        for ref in refs:
            rel = ref.relative_to(ref_dir).as_posix()
            text = oc_translate_common(ref.read_text(encoding="utf-8"), plugin_root)
            out += "\n### `%s`\n\n" % rel + text.rstrip("\n") + "\n"
    out += "\nArgumentos del usuario: `$ARGUMENTS`\n"
    return out


def build_opencode_memory_command(cmd_md: Path) -> str:
    name = cmd_md.stem
    src = cmd_md.read_text(encoding="utf-8")
    meta = parse_frontmatter(src)
    body = oc_translate_common(strip_frontmatter(src).strip("\n"), MEMORY_ROOT)
    origin = "plugins/memory/commands/%s.md" % name
    out = oc_command_header(meta.get("description", name), origin)
    out += "# /%s\n\n" % name
    hint = meta.get("argument-hint", "")
    if "$ARGUMENTS" not in body:
        out += "Argumentos: `$ARGUMENTS`" + (" -- %s" % hint if hint else "") + "\n\n"
    elif hint:
        out += "Argumentos (`$ARGUMENTS`): %s\n\n" % hint
    out += "## Instrucciones\n\n" + body + "\n\n"
    out += "## NOTA (OpenCode / MCP)\n\n" + M.OPENCODE_MCP_NOTE + "\n"
    return out


# --- Agentes -----------------------------------------------------------------
def opencode_permission(tools: set[str]) -> str:
    """Bloque `permission` (YAML) de un agente OpenCode.

    Deriva los deny del allowlist `tools` fuente (set de
    frontmatter_utils.parse_tools: inline o lista YAML; read-only Read/Grep/Glob ->
    edit/bash/webfetch: deny) y concede external_directory SOLO sobre el dir de
    references instalado (~/.config/opencode/references), que esta fuera del
    proyecto: sin esto OpenCode pide permiso y `opencode run` lo auto-rechaza.
    """
    allowed = {t.lower() for t in tools}
    lines = ["permission:"]
    if allowed and "*" not in allowed:
        if not (allowed & {"write", "edit", "multiedit", "notebookedit"}):
            lines.append("  edit: deny")
        if "bash" not in allowed:
            lines.append("  bash: deny")
        if "webfetch" not in allowed:
            lines.append("  webfetch: deny")
    lines.append("  external_directory:")
    lines.append("    " + quote_dq(OC_REFS_DIR.as_posix() + "/*") + ": allow")
    return "\n".join(lines) + "\n"


def oc_translate_agent_body(text: str, origin: str) -> str:
    text = oc_replace(text, M.OPENCODE_AGENT_RULES.get(Path(origin).stem, ()), origin)
    text = oc_translate_common(text, SENTINEL_ROOT)
    return oc_rewrite_refs(text, None, SENTINEL_ROOT)


def build_opencode_agent(agents: dict[str, dict[str, str]], name: str) -> str:
    meta = agents.get(name, {})
    if not meta:
        raise SystemExit("ERROR: no se encontro el agente '%s'" % name)
    src = meta["_text"]
    origin = "plugins/sentinel-agents/agents/%s.md" % name
    body = oc_translate_agent_body(strip_frontmatter(src).lstrip("\n"), origin)
    banner = (
        "<!-- Portado de %s por tools/multiharness/build_harness.py. Frontmatter "
        "reescrito al schema de OpenCode %s. NO editar a mano. -->\n\n"
        "> **OpenCode:** el contrato de agentes esta instalado en `%s` (ruta "
        "absoluta; leelo con la tool read, ya tenes permiso external_directory "
        "sobre ese directorio).\n\n"
        % (origin, M.OPENCODE_VERSION, (OC_REFS_DIR / "agent-contract.md").as_posix())
    )
    return (
        "---\n"
        "description: " + quote_dq(meta.get("description", "")) + "\n"
        "mode: subagent\n"
        + opencode_permission(parse_tools(src))
        + "---\n\n"
        + banner + body
    )


def build_opencode_agent_contract() -> str:
    src = (SENTINEL_ROOT / "references" / "agent-contract.md").read_text(encoding="utf-8")
    origin = "plugins/sentinel-agents/references/agent-contract.md"
    body = oc_translate_agent_body(src, origin)
    return ("<!-- Portado de %s por tools/multiharness/build_harness.py (seccion 7 "
            "reescrita a la KB instalada por el bundle OpenCode). NO editar a mano. "
            "-->\n\n" % origin) + body


# --- Shim de hooks -----------------------------------------------------------
# Plantilla JS del plugin (UN archivo para OpenCode v1 y v2). Placeholders:
# @@HOOKS@@ (rutas abs de los .py), @@REWRITES@@ (CONTEXT_REWRITES),
# @@SUBAGENTS@@, @@V1@@ y @@V2@@ (versiones).
OPENCODE_SHIM_TEMPLATE = r"""// fluency-hooks.js - shim de plugin OpenCode para la suite fluency-4d.
// Generado por tools/multiharness/build_harness.py. NO editar a mano.
//
// Proposito: PUENTEAR (no reescribir) los hooks Python de fluency-4d al ciclo
// de vida de OpenCode. En el equivalente a UserPromptSubmit de Claude Code
// invoca cada hook Python por subprocess (uv run --script <ruta_abs>), le pasa
// el input por stdin (JSON, contrato de Claude) y reinyecta el
// `additionalContext` que emite por stdout.
//
// UN archivo, DOS contratos de plugin (verificados en runtime real):
// - OpenCode @@V1@@ (v1): lee `default.server` (fn) y usa el hook
//   `chat.message`, que corre al crear el mensaje del usuario ANTES de
//   persistirlo: input = {sessionID, agent, model, messageID, variant},
//   output = {message, parts}. La parte inyectada va con `synthetic: true` (el
//   modelo la ve; la TUI no la muestra como texto del usuario) y con id
//   ascendente mayor que el de las partes del usuario -> queda DESPUES del
//   prompt. Si `default` es un objeto, los exports nombrados se ignoran.
// - OpenCode @@V2@@ (v2): valida `default` contra {id, setup: fn} y llama
//   setup(api). No existe `chat.message`: se usa api.session.hook("context"),
//   que corre en CADA llamada al modelo (tambien en cada paso de tools) con
//   {sessionID, agent, model, system, messages, tools}. Se inserta un mensaje
//   user SIN persistir (no api.session.synthetic) justo despues del mensaje
//   del usuario; el resultado de los hooks se cachea por id de ese mensaje, asi
//   los hooks corren una vez por prompt y no en cada paso de tool.
// - Subagentes (sesion hija con parentID / agente mode subagent): NO se
//   inyecta nada (los hooks tambien lo saltean por agent_type).
// Los hooks corren en paralelo y sin bloquear el event loop (spawn async).
// Ante cualquier fallo el shim degrada a NO-OP: nunca rompe la sesion.

import { spawn } from "node:child_process";
import { randomBytes } from "node:crypto";

// Rutas absolutas a los hooks Python de fluency-4d (resueltas al generar).
const USER_PROMPT_HOOKS = [
@@HOOKS@@
];

// Fallback de deteccion de subagentes (agentes del bundle + nativos de
// OpenCode) si la API del plugin no responde.
const KNOWN_SUBAGENTS = new Set([@@SUBAGENTS@@]);

// Python en Windows lee stdin con la codepage ANSI (cp1252) salvo que se
// fuerce UTF-8: sin esto los prompts con acentos rompen los keywords.
const HOOK_ENV = { ...process.env, PYTHONUTF8: "1", PYTHONIOENCODING: "utf-8" };
const HOOK_TIMEOUT_MS = 5000; // por hook (corren en paralelo)
const API_TIMEOUT_MS = 3000; // consultas a la API de OpenCode
const CACHE_MAX = 500; // entradas por cache (prompts v2, sesiones, cwd)
// Topes de tamano (en caracteres JS). Los hooks reales emiten ~1-2 KB por
// prompt; los topes solo frenan un hook roto o malicioso que vuelque MB al
// contexto (en v2 se reinyecta en cada paso de tool):
// - HOOK_STDOUT_MAX: stdout acumulado por hook (JSON incluido). Si se pasa, se
//   mata el arbol del hook y ese hook aporta "".
// - CONTEXT_MAX: contexto concatenado de todos los hooks; se trunca con marca.
const HOOK_STDOUT_MAX = 64 * 1024;
const CONTEXT_MAX = 32 * 1024;
const TRUNCATED_MARK = "\n\n[fluency-4d: contexto truncado]";
// Hooks (procesos uv+python) vivos a la vez entre todos los prompts.
const MAX_CONCURRENT_HOOKS = 8;

// Traduccion minima del texto que emiten los hooks (escritos para Claude
// Code) a los nombres de OpenCode.
const CONTEXT_REWRITES = [
@@REWRITES@@
];

// --- ids ascendentes v1 (formato OpenCode: prefijo_ + 12 hex de
// (ms*0x1000+contador) truncado a 48 bits + 14 base62) ---
const B62 = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz";
const MASK48 = (1n << 48n) - 1n;
function idTime(id) {
  const m = /^[a-z]+_([0-9a-f]{12})/.exec(String(id || ""));
  return m ? BigInt("0x" + m[1]) : -1n;
}
function partIDAfter(parts) {
  // Ultimo slot del ms actual, o el siguiente a la mayor parte existente.
  let t = (BigInt(Date.now()) * 0x1000n + 0xfffn) & MASK48;
  for (const p of parts) {
    const v = idTime(p && p.id);
    if (v >= t) t = (v + 1n) & MASK48;
  }
  const rnd = Array.from(randomBytes(14), (b) => B62[b % 62]).join("");
  return "prt_" + t.toString(16).padStart(12, "0") + rnd;
}

// Semaforo de spawns: como mucho MAX_CONCURRENT_HOOKS hooks vivos a la vez.
let activeHooks = 0;
const hookQueue = [];
function acquireHookSlot() {
  if (activeHooks < MAX_CONCURRENT_HOOKS) {
    activeHooks += 1;
    return Promise.resolve();
  }
  return new Promise((resolve) => hookQueue.push(resolve));
}
function releaseHookSlot() {
  const next = hookQueue.shift();
  if (next) next(); // el slot pasa directo al siguiente
  else activeHooks -= 1;
}

const IS_WIN = process.platform === "win32";

// Mata el ARBOL del hook. child.kill() solo mata uv: python queda huerfano,
// retiene el pipe de stdout y Node no termina hasta que sale. En Windows,
// taskkill /T /F; en POSIX el hook arranca en su propio grupo (detached) y se
// mata el grupo entero. Nunca lanza.
function killTree(child) {
  if (!child || !child.pid || child.exitCode !== null || child.signalCode !== null) return;
  try {
    if (IS_WIN) {
      const k = spawn("taskkill", ["/pid", String(child.pid), "/T", "/F"], {
        windowsHide: true,
        stdio: "ignore",
      });
      k.on("error", () => {
        try {
          child.kill();
        } catch (_e) {
          // ya termino
        }
      });
    } else {
      process.kill(-child.pid, "SIGKILL");
    }
  } catch (_e) {
    try {
      child.kill("SIGKILL");
    } catch (_e2) {
      // ya termino
    }
  }
}

// Invoca un hook Python SIN bloquear el event loop y resuelve con su
// additionalContext ('' si no aplica, falla, vence el timeout o se pasa de
// HOOK_STDOUT_MAX).
async function runPythonHook(scriptPath, payload) {
  await acquireHookSlot();
  return new Promise((resolve) => {
    let child = null;
    let out = "";
    let done = false;
    let timer = null;
    const finish = (value) => {
      if (done) return;
      done = true;
      clearTimeout(timer);
      releaseHookSlot();
      resolve(value);
    };
    const abort = () => {
      killTree(child);
      try {
        // Suelta los pipes ya: Node no espera al arbol para seguir/terminar.
        if (child) {
          child.stdout.destroy();
          child.stdin.destroy();
        }
      } catch (_e) {
        // sin pipes
      }
      finish("");
    };
    timer = setTimeout(abort, HOOK_TIMEOUT_MS);
    try {
      child = spawn("uv", ["run", "--script", scriptPath], {
        env: HOOK_ENV,
        windowsHide: true,
        detached: !IS_WIN, // POSIX: grupo propio para matar el arbol
        stdio: ["pipe", "pipe", "ignore"],
      });
      child.on("error", () => finish(""));
      child.stdout.setEncoding("utf8");
      child.stdout.on("data", (chunk) => {
        if (done) return;
        out += chunk;
        if (out.length > HOOK_STDOUT_MAX) abort();
      });
      child.on("close", (code) => {
        if (code !== 0 || !out) return finish("");
        try {
          const spec = JSON.parse(out).hookSpecificOutput;
          finish(spec && spec.additionalContext ? String(spec.additionalContext) : "");
        } catch (_e) {
          finish("");
        }
      });
      child.stdin.on("error", () => {}); // el hook cerro stdin: sin dato
      child.stdin.end(JSON.stringify(payload || {}));
    } catch (_e) {
      finish(""); // fail-degraded: un hook que falla nunca rompe la sesion.
    }
  });
}

// Corre los hooks en paralelo; los chunks conservan el orden de USER_PROMPT_HOOKS.
async function collectContext(payload) {
  const results = await Promise.all(USER_PROMPT_HOOKS.map((s) => runPythonHook(s, payload)));
  const chunks = [];
  for (let ctx of results) {
    if (!ctx) continue;
    for (const [re, rep] of CONTEXT_REWRITES) ctx = ctx.replace(re, rep);
    chunks.push(ctx);
  }
  return capContext(chunks.join("\n\n"));
}

// Trunca a CONTEXT_MAX (marca incluida) sin partir un par surrogate.
function capContext(text) {
  if (text.length <= CONTEXT_MAX) return text;
  let cut = CONTEXT_MAX - TRUNCATED_MARK.length;
  const c = text.charCodeAt(cut - 1);
  if (c >= 0xd800 && c <= 0xdbff) cut -= 1;
  return text.slice(0, cut) + TRUNCATED_MARK;
}

// Map acotado: al pasar de CACHE_MAX se descarta la entrada mas vieja.
function boundedSet(map, key, value) {
  map.delete(key); // re-insercion = mas reciente
  map.set(key, value);
  while (map.size > CACHE_MAX) map.delete(map.keys().next().value);
}

// Resuelve con fn() o con undefined si falla o tarda mas de ms. El timer se
// limpia apenas hay resultado (no quedan timers vivos por llamada).
function withTimeout(fn, ms) {
  let timer = null;
  const call = new Promise((resolve) => resolve(fn())).catch(() => undefined);
  const expire = new Promise((resolve) => {
    timer = setTimeout(() => resolve(undefined), ms);
  });
  return Promise.race([call, expire]).finally(() => clearTimeout(timer));
}

function unwrap(r) {
  return r && typeof r === "object" && "data" in r ? r.data : r;
}

// Subagente = sesion hija (la tool task/subagent crea la sesion con parentID)
// o agente con mode "subagent". El mode de la API manda; la lista estatica del
// bundle es solo el fallback si la API no lo da (asi un primario llamado como
// un subagente nativo, p. ej. `general` con mode primary, sigue recibiendo
// contexto). Las dos consultas van en paralelo; los modos se cachean una vez.
// Solo se cachea por sesion un resultado DETERMINADO: si session.get vence o
// falla, no se sabe si es hija -> se responde sin cachear y se reintenta en la
// proxima llamada (antes quedaba `false` para siempre e inyectaba en la hija).
function makeSubagentDetector(getSession, getAgentModes) {
  const bySession = new Map(); // sessionID -> boolean (solo determinados)
  let modes = null; // Promise<{agente: mode}>
  const loadModes = () => {
    if (!modes) {
      modes = withTimeout(getAgentModes, API_TIMEOUT_MS).then((m) => {
        if (!m || !Object.keys(m).length) modes = null; // reintentar luego
        return m || {};
      });
    }
    return modes;
  };
  return async function isSubagent(sessionID, agent) {
    if (sessionID && bySession.has(sessionID)) return bySession.get(sessionID);
    const [session, agentModes] = await Promise.all([
      sessionID ? withTimeout(() => getSession(sessionID), API_TIMEOUT_MS) : undefined,
      agent ? loadModes() : {},
    ]);
    const sessionKnown = Boolean(session && typeof session === "object");
    const mode = agent && agentModes ? agentModes[agent] : undefined;
    let sub;
    let known;
    if (sessionKnown && session.parentID) {
      sub = true;
      known = true;
    } else if (mode) {
      sub = mode === "subagent";
      known = sub || sessionKnown;
    } else if (agent && KNOWN_SUBAGENTS.has(agent)) {
      sub = true;
      known = true; // match en la lista del bundle
    } else {
      sub = false;
      known = sessionKnown;
    }
    if (sessionID && known) boundedSet(bySession, sessionID, sub);
    return sub;
  };
}

function modesFrom(list, keys) {
  const out = {};
  if (!Array.isArray(list)) return out;
  for (const a of list) {
    if (!a) continue;
    for (const k of keys) if (a[k]) out[a[k]] = a.mode;
  }
  return out;
}

function hookPayload(sessionID, prompt, cwd, agent) {
  return {
    session_id: sessionID || "",
    hook_event_name: "UserPromptSubmit",
    prompt,
    cwd,
    permission_mode: agent === "plan" ? "plan" : "default",
  };
}

// --- v1: default.server -> chat.message (parte synthetic persistida) -------
export const FluencyHooks = async ({ client, directory, worktree } = {}) => {
  const isSubagent = makeSubagentDetector(
    async (id) => unwrap(await client.session.get({ path: { id } })),
    async () => modesFrom(unwrap(await client.app.agents()), ["name"]),
  );

  return {
    // chat.message = equivalente a UserPromptSubmit.
    "chat.message": async (input, output) => {
      try {
        if (!output || !Array.isArray(output.parts)) return;
        const parts = output.parts;
        // Ids ANTES del payload: sin input.sessionID se toma el de las partes
        // (si no, el hook recibia session_id "" y compartia estado de dedup).
        const ref = parts.find((p) => p && p.sessionID && p.messageID);
        const sid = (input && input.sessionID) || (ref && ref.sessionID);
        const messageID = (output.message && output.message.id)
          || (ref && ref.messageID) || (input && input.messageID);
        if (!messageID || !sid) return; // sin ids reales no se inventan
        const agent = input && input.agent;
        if (await isSubagent(sid, agent)) return; // subagentes: no inyectar
        const userText = parts
          .filter((p) => p && p.type === "text" && !p.synthetic && typeof p.text === "string")
          .map((p) => p.text)
          .join("\n");
        const cwd = directory || worktree || process.cwd();
        const extra = await collectContext(hookPayload(sid, userText, cwd, agent));
        if (!extra) return;
        output.parts.push({
          id: partIDAfter(parts),
          sessionID: sid,
          messageID,
          type: "text",
          synthetic: true,
          text: extra,
        });
      } catch (_e) {
        // NO-OP seguro.
      }
    },
  };
};

// --- v2: default.setup -> api.session.hook("context") (sin persistir) --------
const INJECTED = "fluency4d"; // marca en metadata del mensaje inyectado

function messageText(m) {
  const content = m && Array.isArray(m.content) ? m.content : [];
  return content
    .filter((c) => c && c.type === "text" && typeof c.text === "string")
    .map((c) => c.text)
    .join("\n");
}

function isInjected(m) {
  return Boolean(m && m.metadata && m.metadata[INJECTED]);
}

export async function setupV2(api) {
  const isSubagent = makeSubagentDetector(
    async (sessionID) => unwrap(await api.session.get({ sessionID })),
    async () => modesFrom(unwrap(await api.agent.list()), ["id", "name"]),
  );
  const pending = new Map(); // "sesion:mensaje" -> Promise<string>
  const resolved = new Map(); // "sesion:mensaje" -> string (para el historial)
  const cwdBySession = new Map();

  async function sessionCwd(sessionID) {
    if (cwdBySession.has(sessionID)) return cwdBySession.get(sessionID);
    const s = await withTimeout(
      async () => unwrap(await api.session.get({ sessionID })),
      API_TIMEOUT_MS,
    );
    const dir = s && ((s.location && s.location.directory) || s.directory);
    if (!dir) return process.cwd(); // respaldo NO cacheado: se reintenta
    boundedSet(cwdBySession, sessionID, dir);
    return dir;
  }

  function remember(key, promise) {
    pending.set(key, promise);
    // Solo si la clave sigue viva: una entrada desalojada mientras corria no
    // debe reaparecer en `resolved` (fuga + contexto viejo en el historial).
    promise.then((text) => {
      if (pending.get(key) === promise) resolved.set(key, text);
    });
    while (pending.size > CACHE_MAX) {
      const oldest = pending.keys().next().value;
      pending.delete(oldest);
      resolved.delete(oldest);
    }
  }

  async function onContext(r) {
    if (!r || !Array.isArray(r.messages) || !r.sessionID) return;
    if (await isSubagent(r.sessionID, r.agent)) return; // subagentes: no inyectar
    const msgs = r.messages;
    // TODO(estres): un mensaje user AJENO al final (recordatorio de plan mode u
    // otro plugin, despues de un paso de tool) se toma como "el prompt": corre
    // los hooks con ese texto y no con el del usuario. No se filtra todavia
    // porque la forma de esos mensajes en v2 no esta validada en runtime real.
    let last = -1;
    for (let i = msgs.length - 1; i >= 0; i--) {
      if (msgs[i] && msgs[i].role === "user" && !isInjected(msgs[i])) {
        last = i;
        break;
      }
    }
    if (last === -1) return;
    const keyOf = (m) => r.sessionID + ":" + (m.id || messageText(m));
    const lastKey = keyOf(msgs[last]);
    if (!pending.has(lastKey)) {
      const prompt = messageText(msgs[last]);
      const agent = r.agent;
      remember(
        lastKey,
        sessionCwd(r.sessionID)
          .then((cwd) => collectContext(hookPayload(r.sessionID, prompt, cwd, agent)))
          .catch(() => ""),
      );
    }
    // El prompt actual usa su propio resultado (aunque lo hayan desalojado
    // del cache mientras corria); el historial, lo que quede en `resolved`.
    const lastText = await pending.get(lastKey);
    // Reinserta (de atras hacia adelante) el contexto de CADA prompt del
    // historial, como en v1 donde la parte synthetic queda en su mensaje.
    for (let i = msgs.length - 1; i >= 0; i--) {
      const m = msgs[i];
      if (!m || m.role !== "user" || isInjected(m)) continue;
      const text = i === last ? lastText : resolved.get(keyOf(m));
      if (!text || isInjected(msgs[i + 1])) continue;
      msgs.splice(i + 1, 0, {
        role: "user",
        content: [{ type: "text", text }],
        metadata: { [INJECTED]: true },
      });
    }
  }

  const handle = await api.session.hook("context", async (r) => {
    try {
      await onContext(r);
    } catch (_e) {
      // NO-OP seguro.
    }
  });
  return () => {
    try {
      if (handle && handle.dispose) return handle.dispose();
    } catch (_e) {
      // ya cerrado
    }
  };
}

// v1 (1.19.x) lee `server`; v2 (2.x) exige `id` y lee `setup`.
export default {
  id: "4dsentinel.fluency-hooks",
  server: FluencyHooks,
  setup: setupV2,
};
"""


def opencode_context_rewrites() -> list[tuple[str, str]]:
    """(regex JS, reemplazo) del shim: la misma traduccion que oc_translate_common
    hace con SENTINEL_PREFIX y M.OPENCODE_TOOL_RENAMES. El `:` va como `[:]` para
    que el shim no contenga el literal `sentinel-agents:` (guarda de check_harness).
    """
    sentinel = r"/\b%s[:](%s)/g" % (SENTINEL_NS.rstrip(":"), AGENT_NAME_RE)
    return [(sentinel, "$1")] + [(r"/\b%s\b/g" % re.escape(old), new)
                                 for old, new in M.OPENCODE_TOOL_RENAMES]


def build_opencode_plugin(hooks: dict, agent_names: list[str]) -> str:
    scripts = opencode_userprompt_scripts(hooks)
    js_list = ",\n".join('  "' + s.replace("\\", "\\\\") + '"' for s in scripts)
    js_rewrites = "\n".join("  [%s, %s]," % (rx, json.dumps(new))
                            for rx, new in opencode_context_rewrites())
    subagents = sorted(set(agent_names) | set(OPENCODE_NATIVE_SUBAGENTS))
    js_sub = ", ".join('"%s"' % a for a in subagents)
    return (
        OPENCODE_SHIM_TEMPLATE.replace("@@HOOKS@@", js_list)
        .replace("@@REWRITES@@", js_rewrites)
        .replace("@@SUBAGENTS@@", js_sub)
        .replace("@@V1@@", M.OPENCODE_V1_VERSION)
        .replace("@@V2@@", M.OPENCODE_V2_VERSION)
    )


def build_opencode_json() -> str:
    data = {
        "$schema": "https://opencode.ai/config.json",
        "//": (
            "opencode.json - bundle OpenCode generado por "
            "tools/multiharness/build_harness.py. NO editar a mano. NO copiar "
            "encima de un opencode.json existente: solo documenta el MCP."
        ),
        "//mcp": (
            "MCP codebase-memory: registralo en TU opencode.json con ruta "
            "absoluta al exe verificado (ver /suite-setup): \"mcp\": { "
            "\"codebase-memory-mcp\": { \"type\": \"local\", \"command\": "
            "[\"<ruta-abs>/codebase-memory-mcp.exe\"], \"enabled\": true } }"
        ),
    }
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


def build_opencode_readme(cmd_names: list[str], agent_names: list[str], hooks: dict) -> str:
    cmd_names = sorted(cmd_names)
    skipped = "".join("- `%s`: %s\n" % kv for kv in unsupported_skills("opencode").items())
    return (
        "# Bundle OpenCode de la suite 4Dsentinel\n"
        "\n"
        "Bundle regenerable que porta la suite de plugins de Claude Code a "
        "**OpenCode %s**. Generado por `tools/multiharness/build_harness.py` "
        "desde la fuente canonica en `plugins/*` (read-only). NO editar a mano: "
        "`check_harness.py` falla si el bundle no coincide con el generador.\n"
        "\n"
        "## Que incluye\n"
        "\n"
        "- **Commands** (`command/*.md`, %d): %s. Cada command INCRUSTA el cuerpo "
        "real del skill/command fuente (y sus `references/`), traducido a OpenCode: "
        "nombres de agente calificados con el plugin sentinel-agents -> subagente "
        "`X` via la tool `task` (`subagent` en 2.x); la variable de raiz de plugin "
        "de Claude Code -> "
        "ruta absoluta del plugin en el repo; "
        "`AskUserQuestion` -> tool `question`; planes -> `.opencode/plans/` / "
        "`~/.local/share/opencode/plans/`.\n"
        "- **Agentes** (`agent/*.md`, %d, `mode: subagent`): permisos derivados del "
        "allowlist `tools` fuente (read-only -> `edit/bash/webfetch: deny`) + "
        "`external_directory` permitido SOLO sobre `%s/*` (el contrato y la KB "
        "viven fuera del proyecto; sin ese permiso `opencode run` lo auto-rechaza).\n"
        "- **References** (`references/`): `agent-contract.md` (seccion 7 "
        "reescrita a la KB instalada) + KB ISO 27000 (`iso-27000/`, copia "
        "byte-a-byte, incluido `.manifest.sha256`).\n"
        "- **Hooks** -> `plugin/fluency-hooks.js`: shim que puentea los hooks "
        "Python de `UserPromptSubmit` (%s). UN archivo con los dos "
        "contratos de plugin: `export default { id, server, setup }`. **v1 "
        "(1.x)** lee `server` y usa `chat.message`: inyecta una parte "
        "`synthetic: true` (el modelo la ve; la TUI no la muestra como texto del "
        "usuario) con id ascendente posterior al prompt. **v2 (2.x)** lee "
        "`setup(api)` y usa `api.session.hook(\"context\")`: inserta un mensaje "
        "user SIN persistir despues del prompt, cacheado por id de mensaje (los "
        "hooks corren una vez por prompt, no en cada paso de tool). Payload: "
        "`session_id`, `hook_event_name`, `prompt`, `cwd`, `permission_mode` "
        "(`plan` si el agente es `plan`). Hooks en paralelo y sin bloquear el "
        "event loop. No inyecta en subagentes. Fuerza `PYTHONUTF8=1` para que "
        "los acentos lleguen bien.\n"
        "- **Config** -> `opencode.json`: solo documenta el MCP; NO lo copies "
        "encima de tu config.\n"
        "\n"
        "## Skills que NO se emiten (y por que)\n"
        "\n"
        "%s"
        "\n"
        "## Notas de portabilidad\n"
        "\n"
        "- `caveman` / `adhd` escriben su flag en `~/.claude/fluency4d/` A "
        "PROPOSITO: es la ruta que leen `caveman_injector.py` / `adhd_injector.py`, "
        "que en OpenCode corren via el shim. Lo mismo `stats.json` (`/4d-status`).\n"
        "- Los puentes siguen en `.claude/docs/` del proyecto (los lee "
        "`bridge_router.py`). OpenCode usa `AGENTS.md`; si no existe, cae a "
        "`CLAUDE.md`.\n"
        "- Hooks `PostToolUse` (%s) y `Stop` (%s) NO se puentean: solo "
        "`UserPromptSubmit`.\n"
        "- Rutas absolutas de ESTA maquina (repo y `~/.config/opencode`): "
        "regenerar si cambian.\n"
        "\n"
        "## Instalacion (global)\n"
        "\n"
        "Los agentes apuntan a `%s` por ruta absoluta: instala en el dir global "
        "de OpenCode. Copia `command/`, `agent/`, `plugin/` y `references/` (NO "
        "`opencode.json`):\n"
        "\n"
        "```bash\n"
        "cp -r dist/opencode/command dist/opencode/agent dist/opencode/plugin "
        "dist/opencode/references ~/.config/opencode/\n"
        "```\n"
        "\n"
        "```powershell\n"
        "Copy-Item -Recurse -Force dist/opencode/command,dist/opencode/agent,"
        "dist/opencode/plugin,dist/opencode/references \"$HOME/.config/opencode/\"\n"
        "```\n"
        "\n"
        "Al actualizar, borra en destino los archivos que instalo un bundle "
        "anterior y ya no se generan (p. ej. `command/verify-diff.md`).\n"
        "\n"
        "## Verificacion\n"
        "\n"
        "- `check_harness.py`: sin drift, JSON/TOML validos, hooks `.py` "
        "existentes, y guardas OpenCode (default `{ id, server, setup }`, parte "
        "`synthetic` en v1, hook `context` en v2, `session_id` y `PYTHONUTF8` en "
        "el shim, sin nombres calificados de sentinel-agents ni la variable de "
        "raiz de plugin de Claude, commands autocontenidos).\n"
        "- `tests/scripts/opencode_shim_contract.mjs`: importa el plugin en Node y "
        "ejercita ambos contratos con mocks (lo corre `test_build_harness.py`).\n"
        "- E2E en runtime real de `opencode %s` (v1: `opencode run` + `opencode "
        "export`; v2: `opencode run --standalone` + `opencode session export`).\n"
        "- OpenCode 2.x carga `command/` (o `commands/`), `agent/` y `plugin/` "
        "del dir global; `opencode run` de 2.x no tiene `--command`: los commands "
        "se usan desde la TUI (`/nombre`) o la API `session.command`.\n"
        "- MCP (codebase-memory): fuera del bundle; se registra en el "
        "`opencode.json` del usuario.\n"
    ) % (
        M.OPENCODE_VERSION, len(cmd_names), ", ".join("`/%s`" % c for c in cmd_names),
        len(agent_names), OC_REFS_DIR.as_posix(), hook_list(hooks, "UserPromptSubmit"),
        skipped, hook_list(hooks, "PostToolUse"), hook_list(hooks, "Stop"),
        OC_REFS_DIR.as_posix(), M.OPENCODE_VERSION,
    )


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------
def build(dist_dir: Path, skills: list[Path] | None = None,
          agents: dict[str, dict[str, str]] | None = None) -> list[Path]:
    """Genera el bundle completo bajo dist_dir. Devuelve las rutas escritas.

    skills/agents: resultado de discover_skills()/discover_agents() si el
    llamador ya los tiene (si no, se descubren aca).
    """
    skills = discover_skills() if skills is None else skills
    agents = discover_agents() if agents is None else agents
    hooks = load_hooks()

    if "critic" not in agents:
        raise SystemExit("ERROR: no se encontro el agente 'critic' en sentinel-agents")
    if not any(p.parent.name == "handoff" for p in skills):
        raise SystemExit("ERROR: no se encontro el skill 'handoff'")

    written: list[Path] = []
    written.append(write(dist_dir / ".agents" / "skills" / "handoff" / "SKILL.md",
                          build_handoff_skill()))
    written.append(write(dist_dir / "prompts" / "handoff.md", build_handoff_prompt()))
    written.append(write(dist_dir / "hooks.json", build_hooks_json(hooks)))
    written.append(write(dist_dir / "config.toml", build_config_toml(agents)))
    written.append(write(dist_dir / "critic.config.toml", build_critic_config(agents)))
    written.append(write(dist_dir / "agents" / "critic.md", build_critic_body(agents)))
    written.append(write(dist_dir / "AGENTS.md", build_agents_md()))
    written.append(write(dist_dir / "README.md", build_readme(hooks)))
    return written


def build_opencode(dist_dir: Path, skills: list[Path] | None = None,
                   agents: dict[str, dict[str, str]] | None = None) -> list[Path]:
    """Genera el bundle OpenCode bajo dist_dir. Devuelve las rutas escritas.

    Todo lo que hay en dist/opencode sale de aca (check_harness falla si sobra
    o falta algo): commands (skills portables + commands de memory), agentes
    (todos los de sentinel-agents), references (contrato + KB ISO), shim de
    hooks, opencode.json y README.
    """
    agents = discover_agents() if agents is None else agents
    hooks = load_hooks()
    skills = opencode_skills(discover_skills() if skills is None else skills)
    memory_cmds = sorted(MEMORY_ROOT.glob("commands/*.md"))
    names = sorted(agents)
    if not names:
        raise SystemExit("ERROR: no se encontraron agentes en sentinel-agents")
    cmd_names = [p.parent.name for p in skills] + [p.stem for p in memory_cmds]
    if len(set(cmd_names)) != len(cmd_names):
        raise SystemExit("ERROR: nombres de command OpenCode duplicados: %s" % cmd_names)

    written: list[Path] = []
    for skill_md in skills:
        written.append(write(dist_dir / "command" / (skill_md.parent.name + ".md"),
                             build_opencode_skill_command(skill_md, names)))
    for cmd_md in memory_cmds:
        written.append(write(dist_dir / "command" / cmd_md.name,
                             build_opencode_memory_command(cmd_md)))
    for name in names:
        written.append(write(dist_dir / "agent" / (name + ".md"),
                             build_opencode_agent(agents, name)))
    written.append(write(dist_dir / "references" / "agent-contract.md",
                         build_opencode_agent_contract()))
    # KB ISO 27000: copia byte-a-byte (el .manifest.sha256 depende de los bytes).
    refs_root = SENTINEL_ROOT / "references"
    for src in sorted(p for p in (refs_root / "iso-27000").rglob("*") if p.is_file()):
        dst = dist_dir / "references" / src.relative_to(refs_root)
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(src.read_bytes())
        written.append(dst)
    written.append(write(dist_dir / "plugin" / "fluency-hooks.js",
                         build_opencode_plugin(hooks, names)))
    written.append(write(dist_dir / "opencode.json", build_opencode_json()))
    written.append(write(dist_dir / "README.md",
                         build_opencode_readme(cmd_names, names, hooks)))
    return written


def build_hermes_md() -> str:
    """Genera .hermes.md desde CLAUDE.md (puentes .claude/ -> .hermes/)."""
    return build_contract_md(
        head=[
            "# .hermes.md — Contrato del proyecto (bundle Hermes)",
            "",
            "> Generado por `tools/multiharness/build_harness.py` desde `CLAUDE.md`.",
            "> Adaptado para Hermes Agent: skills bajo demanda en vez de hooks automaticos.",
            "",
            "<!-- BEGIN 4D-BRIDGES -->",
        ],
        no_rules="- (sin reglas detectadas)",
        bridges_note=[],
        no_bridges="(sin puentes)",
        tail=[
            "",
            "Si la pregunta o tarea toca un tema de la tabla, LEE ese archivo ANTES de responder.",
            "Al escribir codigo, respeta `.hermes/docs/convenciones.md`.",
            "<!-- END 4D-BRIDGES -->",
            "",
            "## Skills instalados (suite 4Dsentinel para Hermes)",
            "",
            "Carga los skills desde `~/.hermes/skills/productivity/`. Mira el README en",
            "`dist/hermes/` para la lista completa de comandos.",
        ],
        bridge_rewrite=(".claude/", ".hermes/"),
    )


def build_hermes(dist_dir: Path) -> list[Path]:
    """Genera el bundle Hermes bajo dist_dir. Devuelve las rutas escritas."""
    written: list[Path] = []
    written.append(write(dist_dir / ".hermes.md", build_hermes_md()))
    return written


def main() -> int:
    skills = discover_skills()
    agents = discover_agents()
    written = build(DEFAULT_DIST, skills, agents)
    written_oc = build_opencode(DEFAULT_OPENCODE_DIST, skills, agents)
    written_hm = build_hermes(DEFAULT_HERMES_DIST)
    print("Repo root : %s" % REPO_ROOT)
    print("Bundle    : %s" % DEFAULT_DIST)
    print("Bundle OC : %s" % DEFAULT_OPENCODE_DIST)
    print("Bundle HM : %s" % DEFAULT_HERMES_DIST)
    print("Skills    : %d descubiertos" % len(skills))
    print("Agentes   : %d descubiertos" % len(agents))
    print("Archivos escritos (codex):")
    for p in written:
        print("  - %s" % p.relative_to(REPO_ROOT))
    print("Archivos escritos (opencode):")
    for p in written_oc:
        print("  - %s" % p.relative_to(REPO_ROOT))
    print("Archivos escritos (hermes):")
    for p in written_hm:
        print("  - %s" % p.relative_to(REPO_ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
