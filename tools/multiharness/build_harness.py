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
  OpenCode (dist/opencode/, OpenCode 1.19.1 -- TODO el bundle sale de aca):
    - command   : un command por skill portable (cuerpo + references
                  INCRUSTADOS y traducidos; ver M.OPENCODE_SKILLS_SKIPPED) y por
                  cada command de memory (command/*.md).
    - agentes   : todos los de sentinel-agents (agent/*.md, mode: subagent,
                  permisos del allowlist + external_directory sobre references/).
    - references: agent-contract.md (sec. 7 reescrita) + KB ISO (byte-a-byte).
    - hooks     : plugin shim JS (plugin/fluency-hooks.js) que puentea los hooks
                  Python de UserPromptSubmit via chat.message.
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

sys.path.insert(0, str(Path(__file__).resolve().parent))
import mappings as M  # noqa: E402

# ---------------------------------------------------------------------------
# Rutas ancla (absolutas, resueltas desde la ubicacion de este script)
# ---------------------------------------------------------------------------
# tools/multiharness/build_harness.py -> parents[2] = raiz del repo.
REPO_ROOT = Path(__file__).resolve().parents[2]
PLUGINS = REPO_ROOT / "plugins"
FLUENCY_ROOT = PLUGINS / "fluency-4d"          # resuelve ${CLAUDE_PLUGIN_ROOT}
SENTINEL_ROOT = PLUGINS / "sentinel-agents"
DEFAULT_DIST = REPO_ROOT / "dist" / "codex"
DEFAULT_OPENCODE_DIST = REPO_ROOT / "dist" / "opencode"

# ---------------------------------------------------------------------------
# Exclusion "solo Claude Code"
# ---------------------------------------------------------------------------
# Piezas de fluency-4d que dependen del engine de mods de Claude Code (Panel 4D,
# hooks module TSX) o de su status line / temas. NO se emiten a Codex ni a
# OpenCode. Rutas relativas a plugins/fluency-4d (se nombran aunque todavia no
# existan: la lista es el contrato, no un reflejo del arbol actual).
CLAUDE_CODE_ONLY: tuple[str, ...] = (
    "hooks/register.tsx",      # hooks module del Panel 4D
    "tests",                   # tests del panel (claude plugin test)
    "types",                   # contrato $.state del panel
    "tsconfig.json",           # typecheck del panel
    ".claude-plugin/types",    # tipos que escribe el engine
    "statusline",              # status line (Node)
    "themes",                  # temas de Claude Code
    "skills/barra",
    "skills/statusline",
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
    """Parsea el frontmatter de plugins/sentinel-agents/agents/*.md."""
    agents: dict[str, dict[str, str]] = {}
    for md in sorted(SENTINEL_ROOT.glob("agents/*.md")):
        meta = parse_frontmatter(md.read_text(encoding="utf-8"))
        meta["_path"] = str(md)
        agents[meta.get("name", md.stem)] = meta
    return agents


def load_hooks() -> dict:
    """Lee plugins/fluency-4d/hooks/hooks.json sin las claves solo-Claude-Code."""
    raw = json.loads((FLUENCY_ROOT / "hooks" / "hooks.json").read_text(encoding="utf-8"))
    return strip_claude_only_keys(raw)


# ---------------------------------------------------------------------------
# Helpers de emision
# ---------------------------------------------------------------------------
def toml_basic(s: str) -> str:
    """Escapa un string para un basic string TOML (comillas dobles)."""
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
    config.toml [hooks]. Incluye UserPromptSubmit (4), PostToolUse (doc_drift,
    memory_checkpoint) y Stop (discernment_gate), tal cual la fuente. Sin
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
        "description = " + toml_basic(desc),
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
        out.append("model = " + toml_basic(model))
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
    critic = agents.get("critic", {})
    src = Path(critic["_path"]).read_text(encoding="utf-8")
    body = strip_frontmatter(src).lstrip("\n")
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


def build_agents_md() -> str:
    claude_md = (REPO_ROOT / "CLAUDE.md").read_text(encoding="utf-8")
    rules, bridges = extract_hard_rules(claude_md)
    parts = [
        "# AGENTS.md - contrato del proyecto (bundle Codex)",
        "",
        "> Generado por `tools/multiharness/build_harness.py` desde los "
        "innegociables de `CLAUDE.md`. Equivalente en Codex de las reglas duras "
        "de Claude Code.",
        "",
        "## Reglas del proyecto (siempre)",
        "",
    ]
    parts += rules if rules else ["- (sin reglas detectadas en CLAUDE.md)"]
    parts += [
        "",
        "## Puentes de documentacion",
        "",
        "> NOTA (Codex): los puentes apuntan a `.claude/docs/*` del proyecto. "
        "Codex no ejecuta el hook `bridge_router` automaticamente para leerlos; "
        "leelos a mano si la tarea toca ese tema.",
        "",
    ]
    parts += bridges if bridges else ["(sin tabla de puentes)"]
    parts += [
        "",
        "## Notas de portabilidad",
        "",
        "- Hooks: emitidos como `hooks.json` (schema de Claude Code), descubierto "
        "en `$CODEX_HOME/hooks.json` o `<proyecto>/.codex/hooks.json`. `config.toml` "
        "solo activa `[features] hooks = true`; su bloque `[hooks]` NO dispara nada.",
        "- Subagentes: `[agents.<name>]` + `<name>.config.toml`.",
        "- MCP (codebase-memory): DIFERIDO (binario `cbm` no instalado).",
        "",
    ]
    return "\n".join(parts)


def build_readme() -> str:
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
        "(bridge_router, plan_calibrator, caveman_injector, suite_playbook), "
        "`PostToolUse` (doc_drift, memory_checkpoint) y `Stop` "
        "(discernment_gate), con rutas absolutas a esta maquina.\n"
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
    )


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
    "memory": PLUGINS / "memory",
}
MEMORY_ROOT = PLUGINS / "memory"
# Subagentes nativos de OpenCode (mode: subagent) -- fallback del shim si el
# client del plugin no responde.
OPENCODE_NATIVE_SUBAGENTS: tuple[str, ...] = ("general", "explore")

BACKTICK_REF = re.compile(r"`references/([^`]*)`")
SENTINEL_PREFIX = re.compile(r"sentinel-agents:([a-z][a-z-]*)")


def yaml_dq(s: str) -> str:
    """Escala YAML entre comillas dobles (escapa backslash y comilla doble)."""
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def oc_abs(p: Path) -> str:
    """Ruta absoluta con '/' (la tool read de OpenCode la acepta en Windows)."""
    return p.as_posix()


def oc_replace(text: str, rules, origin: str) -> str:
    """Aplica (old, new) en orden. `old` str -> literal; re.Pattern -> regex.

    Cada regla DEBE matchear al menos una vez: si la fuente cambio y el marcador
    ya no existe, el build falla en vez de emitir una traduccion a medias.
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
    return text


def oc_translate_common(text: str, plugin_root: Path) -> str:
    """Traduccion Claude Code -> OpenCode comun a commands y agentes.

    - `sentinel-agents:X`  -> `X` (subagente OpenCode, se invoca con la tool task).
    - ${CLAUDE_PLUGIN_ROOT} -> ruta abs del plugin en este repo (igual que el shim).
    - tools exclusivas de Claude Code -> equivalente OpenCode (M.OPENCODE_TOOL_MAP).
    - ~/.claude/plans/      -> directorios de planes de OpenCode.
    Los flags/estado en ~/.claude/fluency4d/ NO se traducen: los leen/escriben
    los hooks Python, que en OpenCode corren via el shim con esa misma ruta.
    """
    text = SENTINEL_PREFIX.sub(r"\1", text)
    text = text.replace(M.PLUGIN_ROOT_VAR, oc_abs(plugin_root))
    for old, new in M.OPENCODE_TOOL_MAP:
        text = text.replace(old, new)
    for old, new in M.OPENCODE_HOME_MAP:
        text = text.replace(old, new)
    return text


def oc_rewrite_refs(text: str, skill_dir: Path | None, plugin_root: Path,
                    embedded: set[str]) -> str:
    """Reescribe `references/<x>` backtickeado.

    - si <x> existe en <skill>/references/ -> se INCRUSTA al final del command
      (se anota en `embedded`) y el texto apunta a la copia incrustada;
    - si existe en <plugin>/references/ -> ruta ABSOLUTA de instalacion del
      bundle (~/.config/opencode/references/<x>).
    """
    def sub(m: re.Match) -> str:
        rel = m.group(1)
        if skill_dir is not None and (skill_dir / "references" / rel).is_file():
            embedded.add(rel)
            return "`%s` (referencia incrustada al final de este comando)" % rel
        if (plugin_root / "references" / rel.rstrip("/")).exists():
            dst = oc_abs(OC_REFS_DIR / rel.rstrip("/"))
            return "`%s%s`" % (dst, "/" if rel.endswith("/") else "")
        raise SystemExit("ERROR: referencia no resoluble: references/%s" % rel)
    return BACKTICK_REF.sub(sub, text)


def opencode_userprompt_scripts(hooks: dict) -> list[str]:
    """Rutas absolutas de los .py de UserPromptSubmit (para el shim JS)."""
    marker = M.PLUGIN_ROOT_VAR + "/hooks/"
    out: list[str] = []
    for group in hooks.get("hooks", {}).get("UserPromptSubmit", []):
        for hk in group.get("hooks", []):
            cmd = hk.get("command", "")
            idx = cmd.find(marker)
            if idx == -1:
                continue
            rest = cmd[idx + len(marker):]
            name = rest.split('"')[0].split(" ")[0]
            out.append(str(FLUENCY_ROOT / "hooks" / name))
    return out


# --- Commands (skills + commands de memory) ---------------------------------
def discover_opencode_skills() -> list[Path]:
    """Skills portables que se emiten como command (excluye M.OPENCODE_SKILLS_SKIPPED)."""
    return [p for p in discover_skills() if p.parent.name not in M.OPENCODE_SKILLS_SKIPPED]


def oc_command_header(desc: str, origin: str) -> str:
    return (
        "---\n"
        "description: " + yaml_dq(desc) + "\n"
        "agent: build\n"
        "---\n\n"
        "<!-- Generado por tools/multiharness/build_harness.py desde %s "
        "(cuerpo incrustado y traducido a OpenCode). NO editar a mano. -->\n\n" % origin
    )


def build_opencode_skill_command(skill_md: Path) -> str:
    name = skill_md.parent.name
    plugin = skill_md.parents[2].name
    plugin_root = PLUGIN_ROOTS[plugin]
    origin = "plugins/%s/skills/%s" % (plugin, name)
    # Reglas por-skill sobre el fuente COMPLETO (frontmatter incluido: la
    # description tambien puede nombrar mecanismos de Claude Code). {OC_REFS}
    # = ruta absoluta de references/ instalado.
    src = oc_replace(skill_md.read_text(encoding="utf-8"),
                     M.OPENCODE_SKILL_RULES.get(name, ()), origin)
    src = src.replace("{OC_REFS}", oc_abs(OC_REFS_DIR))
    meta = parse_frontmatter(src)
    meta["description"] = oc_translate_common(meta.get("description", name), plugin_root)
    body = oc_translate_common(strip_frontmatter(src).lstrip("\n"), plugin_root)
    embedded: set[str] = set()
    body = oc_rewrite_refs(body, skill_md.parent, plugin_root, embedded)

    notes = [
        "> **OpenCode (bundle 4Dsentinel, OpenCode %s).** Este comando INCRUSTA "
        "el skill `%s` completo: segui las instrucciones de abajo tal cual. NO "
        "busques un archivo de skill ni rutas de instalacion de Claude Code. Los "
        "subagentes de la suite (advisor, critic, librarian, ...) se invocan con "
        "la tool `task` (`subagent_type: <nombre>`)." % (M.OPENCODE_VERSION, name),
    ]
    extra = M.OPENCODE_SKILL_NOTES.get(name)
    if extra:
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
def opencode_permission(tools: str) -> str:
    """Bloque `permission` (YAML) de un agente OpenCode.

    Deriva los deny del allowlist `tools` fuente (read-only Read/Grep/Glob ->
    edit/bash/webfetch: deny) y concede external_directory SOLO sobre el dir de
    references instalado (~/.config/opencode/references), que esta fuera del
    proyecto: sin esto OpenCode pide permiso y `opencode run` lo auto-rechaza.
    """
    allowed = {t.strip().lower() for t in tools.split(",") if t.strip()}
    lines = ["permission:"]
    if allowed and "*" not in allowed:
        if not (allowed & {"write", "edit", "multiedit", "notebookedit"}):
            lines.append("  edit: deny")
        if "bash" not in allowed:
            lines.append("  bash: deny")
        if "webfetch" not in allowed:
            lines.append("  webfetch: deny")
    lines.append("  external_directory:")
    lines.append("    " + yaml_dq(oc_abs(OC_REFS_DIR) + "/*") + ": allow")
    return "\n".join(lines) + "\n"


def oc_translate_agent_body(text: str, origin: str) -> str:
    text = oc_replace(text, M.OPENCODE_AGENT_RULES.get(Path(origin).stem, ()), origin)
    text = text.replace("{OC_REFS}", oc_abs(OC_REFS_DIR))
    text = oc_translate_common(text, SENTINEL_ROOT)
    return oc_rewrite_refs(text, None, SENTINEL_ROOT, set())


def build_opencode_agent(agents: dict[str, dict[str, str]], name: str) -> str:
    meta = agents.get(name, {})
    if not meta:
        raise SystemExit("ERROR: no se encontro el agente '%s'" % name)
    src = Path(meta["_path"]).read_text(encoding="utf-8")
    origin = "plugins/sentinel-agents/agents/%s.md" % name
    body = oc_translate_agent_body(strip_frontmatter(src).lstrip("\n"), origin)
    banner = (
        "<!-- Portado de %s por tools/multiharness/build_harness.py. Frontmatter "
        "reescrito al schema de OpenCode %s. NO editar a mano. -->\n\n"
        "> **OpenCode:** el contrato de agentes esta instalado en `%s` (ruta "
        "absoluta; leelo con la tool read, ya tenes permiso external_directory "
        "sobre ese directorio).\n\n"
        % (origin, M.OPENCODE_VERSION, oc_abs(OC_REFS_DIR / "agent-contract.md"))
    )
    return (
        "---\n"
        "description: " + yaml_dq(meta.get("description", "")) + "\n"
        "mode: subagent\n"
        + opencode_permission(meta.get("tools", ""))
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


def opencode_kb_files() -> list[Path]:
    """KB ISO 27000 (copia byte-a-byte: el .manifest.sha256 depende de los bytes)."""
    root = SENTINEL_ROOT / "references" / "iso-27000"
    return sorted(p for p in root.rglob("*") if p.is_file())


# --- Shim de hooks -----------------------------------------------------------
def build_opencode_plugin(hooks: dict, agent_names: list[str]) -> str:
    scripts = opencode_userprompt_scripts(hooks)
    js_list = ",\n".join('  "' + s.replace("\\", "\\\\") + '"' for s in scripts)
    subagents = sorted(set(agent_names) | set(OPENCODE_NATIVE_SUBAGENTS))
    js_sub = ", ".join('"%s"' % a for a in subagents)
    return (
        "// fluency-hooks.js - shim de plugin OpenCode para la suite fluency-4d.\n"
        "// Generado por tools/multiharness/build_harness.py. NO editar a mano.\n"
        "//\n"
        "// Proposito: PUENTEAR (no reescribir) los hooks Python de fluency-4d\n"
        "// al ciclo de vida de OpenCode. En el evento equivalente a\n"
        "// UserPromptSubmit de Claude Code, invoca cada hook Python por\n"
        "// subprocess (uv run --script <ruta_abs>), le pasa el input por stdin\n"
        "// (JSON, contrato de Claude) y reinyecta el `additionalContext` que\n"
        "// emite por stdout.\n"
        "//\n"
        "// API OpenCode {VER} (verificada): el hook `chat.message` se dispara al\n"
        "// crear el mensaje del usuario, ANTES de persistirlo y de llamar al\n"
        "// modelo: input = {sessionID, agent, model, messageID, variant},\n"
        "// output = {message, parts}. El texto del usuario vive en output.parts.\n"
        "// - La parte inyectada va con `synthetic: true`: el modelo la recibe,\n"
        "//   pero la TUI no la muestra/copia/edita como texto del usuario.\n"
        "// - Su id es ascendente (mismo formato que los ids nativos) y mayor que\n"
        "//   el de las partes del usuario -> queda DESPUES del prompt.\n"
        "// - Subagentes (sesion hija de la tool task / agente mode subagent): NO\n"
        "//   se inyecta nada (los hooks tambien lo saltean por agent_type).\n"
        "// Ante cualquier fallo el shim degrada a NO-OP: nunca rompe la sesion.\n"
        "\n"
        'import { spawnSync } from "node:child_process";\n'
        'import { randomBytes } from "node:crypto";\n'
        "\n"
        "// Rutas absolutas a los hooks Python de fluency-4d (resueltas al generar).\n"
        "const USER_PROMPT_HOOKS = [\n"
        + js_list + "\n"
        "];\n"
        "\n"
        "// Fallback de deteccion de subagentes (agentes del bundle + nativos de\n"
        "// OpenCode) si el client del plugin no responde.\n"
        "const KNOWN_SUBAGENTS = new Set([" + js_sub + "]);\n"
        "\n"
        "// Python en Windows lee stdin con la codepage ANSI (cp1252) salvo que se\n"
        "// fuerce UTF-8: sin esto los prompts con acentos rompen los keywords.\n"
        "const HOOK_ENV = { ...process.env, PYTHONUTF8: \"1\", PYTHONIOENCODING: \"utf-8\" };\n"
        "\n"
        "// Traduccion minima del texto que emiten los hooks (escritos para Claude\n"
        "// Code) a los nombres de OpenCode.\n"
        "const CONTEXT_REWRITES = [\n"
        "  [/\\bsentinel-agents[:]([a-z][a-z-]*)/g, \"$1\"],\n"
        "  [/\\bExitPlanMode\\b/g, \"plan_exit\"],\n"
        "];\n"
        "\n"
        "// --- ids ascendentes (formato OpenCode: prefijo_ + 12 hex de\n"
        "// (ms*0x1000+contador) truncado a 48 bits + 14 base62) ---\n"
        'const B62 = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz";\n'
        "const MASK48 = (1n << 48n) - 1n;\n"
        "function idTime(id) {\n"
        "  const m = /^[a-z]+_([0-9a-f]{12})/.exec(String(id || \"\"));\n"
        "  return m ? BigInt(\"0x\" + m[1]) : -1n;\n"
        "}\n"
        "function partIDAfter(parts) {\n"
        "  // Ultimo slot del ms actual, o el siguiente a la mayor parte existente.\n"
        "  let t = (BigInt(Date.now()) * 0x1000n + 0xfffn) & MASK48;\n"
        "  for (const p of parts) {\n"
        "    const v = idTime(p && p.id);\n"
        "    if (v >= t) t = (v + 1n) & MASK48;\n"
        "  }\n"
        "  const rnd = Array.from(randomBytes(14), (b) => B62[b % 62]).join(\"\");\n"
        "  return \"prt_\" + t.toString(16).padStart(12, \"0\") + rnd;\n"
        "}\n"
        "\n"
        "// Invoca un hook Python y devuelve su additionalContext (o '' si no aplica).\n"
        "function runPythonHook(scriptPath, payload) {\n"
        "  try {\n"
        '    const res = spawnSync("uv", ["run", "--script", scriptPath], {\n'
        "      input: JSON.stringify(payload || {}),\n"
        '      encoding: "utf8",\n'
        "      env: HOOK_ENV,\n"
        "      timeout: 5000,\n"
        "      windowsHide: true,\n"
        "    });\n"
        '    if (res.status !== 0 || !res.stdout) return "";\n'
        "    const out = JSON.parse(res.stdout);\n"
        "    const spec = out && out.hookSpecificOutput;\n"
        '    return (spec && spec.additionalContext) ? String(spec.additionalContext) : "";\n'
        "  } catch (_e) {\n"
        '    return ""; // fail-degraded: un hook que falla nunca rompe la sesion.\n'
        "  }\n"
        "}\n"
        "\n"
        "function collectContext(payload) {\n"
        "  const chunks = [];\n"
        "  for (const script of USER_PROMPT_HOOKS) {\n"
        "    let ctx = runPythonHook(script, payload);\n"
        "    if (!ctx) continue;\n"
        "    for (const [re, rep] of CONTEXT_REWRITES) ctx = ctx.replace(re, rep);\n"
        "    chunks.push(ctx);\n"
        "  }\n"
        '  return chunks.join("\\n\\n");\n'
        "}\n"
        "\n"
        "function withTimeout(promise, ms) {\n"
        "  return Promise.race([\n"
        "    Promise.resolve(promise).catch(() => undefined),\n"
        "    new Promise((resolve) => setTimeout(() => resolve(undefined), ms)),\n"
        "  ]);\n"
        "}\n"
        "\n"
        "export const FluencyHooks = async ({ client, directory, worktree } = {}) => {\n"
        "  const subagentBySession = new Map(); // sessionID -> boolean (cache)\n"
        "  let agentModes = null; // nombre -> mode (cache de client.app.agents)\n"
        "\n"
        "  async function loadAgentModes() {\n"
        "    if (agentModes) return agentModes;\n"
        "    try {\n"
        "      const r = await withTimeout(client.app.agents(), 3000);\n"
        "      const list = (r && (r.data || r)) || [];\n"
        "      if (Array.isArray(list) && list.length) {\n"
        "        agentModes = {};\n"
        "        for (const a of list) if (a && a.name) agentModes[a.name] = a.mode;\n"
        "      }\n"
        "    } catch (_e) { /* fallback: KNOWN_SUBAGENTS */ }\n"
        "    return agentModes || {};\n"
        "  }\n"
        "\n"
        "  // Subagente = sesion hija (la tool task crea la sesion con parentID) o\n"
        "  // agente con mode \"subagent\"; fallback: lista estatica del bundle.\n"
        "  async function isSubagent(input) {\n"
        "    const sid = input && input.sessionID;\n"
        "    if (sid && subagentBySession.has(sid)) return subagentBySession.get(sid);\n"
        "    const agent = input && input.agent;\n"
        "    let sub = Boolean(agent && KNOWN_SUBAGENTS.has(agent));\n"
        "    if (!sub && client && sid) {\n"
        "      try {\n"
        "        const r = await withTimeout(client.session.get({ path: { id: sid } }), 3000);\n"
        "        const s = r && (r.data || r);\n"
        "        if (s && s.parentID) sub = true;\n"
        "      } catch (_e) { /* sin dato */ }\n"
        "    }\n"
        "    if (!sub && client && agent) {\n"
        "      const modes = await loadAgentModes();\n"
        "      if (modes[agent] === \"subagent\") sub = true;\n"
        "    }\n"
        "    if (sid) subagentBySession.set(sid, sub);\n"
        "    return sub;\n"
        "  }\n"
        "\n"
        "  return {\n"
        "    // chat.message = equivalente a UserPromptSubmit.\n"
        '    "chat.message": async (input, output) => {\n'
        "      try {\n"
        "        if (!output || !Array.isArray(output.parts)) return;\n"
        "        if (await isSubagent(input)) return; // subagentes: no inyectar\n"
        "        const parts = output.parts;\n"
        "        const userText = parts\n"
        '          .filter((p) => p && p.type === "text" && !p.synthetic'
        ' && typeof p.text === "string")\n'
        "          .map((p) => p.text)\n"
        '          .join("\\n");\n'
        "        const payload = {\n"
        "          session_id: (input && input.sessionID) || \"\",\n"
        '          hook_event_name: "UserPromptSubmit",\n'
        "          prompt: userText,\n"
        "          cwd: directory || worktree || process.cwd(),\n"
        '          permission_mode: (input && input.agent === "plan") ? "plan" : "default",\n'
        "        };\n"
        "        const extra = collectContext(payload);\n"
        "        if (!extra) return;\n"
        "        const ref = parts.find((p) => p && p.sessionID && p.messageID);\n"
        "        const messageID = (output.message && output.message.id)\n"
        "          || (ref && ref.messageID) || (input && input.messageID);\n"
        "        const sessionID = (input && input.sessionID) || (ref && ref.sessionID);\n"
        "        if (!messageID || !sessionID) return; // sin ids reales no se inventan\n"
        "        output.parts.push({\n"
        "          id: partIDAfter(parts),\n"
        "          sessionID,\n"
        "          messageID,\n"
        '          type: "text",\n'
        "          synthetic: true,\n"
        "          text: extra,\n"
        "        });\n"
        "      } catch (_e) {\n"
        "        // NO-OP seguro.\n"
        "      }\n"
        "    },\n"
        "  };\n"
        "};\n"
        "\n"
        "export default FluencyHooks;\n"
    ).replace("{VER}", M.OPENCODE_VERSION)


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


def build_opencode_readme(skills: list[Path], memory_cmds: list[Path],
                          agent_names: list[str]) -> str:
    cmd_names = sorted([p.parent.name for p in skills] + [p.stem for p in memory_cmds])
    skipped = "".join("- `%s`: %s\n" % (k, v) for k, v in M.OPENCODE_SKILLS_SKIPPED.items())
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
        "`X` via la tool `task`; la variable de raiz de plugin de Claude Code -> "
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
        "Python de `UserPromptSubmit` (bridge_router, plan_calibrator, "
        "caveman_injector, adhd_injector, suite_playbook) via `chat.message`. "
        "Payload: `session_id`, `hook_event_name`, `prompt`, `cwd`, "
        "`permission_mode` (`plan` si el agente es `plan`). Inyecta una parte "
        "`synthetic: true` (el modelo la ve; la TUI no la muestra como texto del "
        "usuario) con id ascendente posterior al prompt. No inyecta en "
        "subagentes. Fuerza `PYTHONUTF8=1` para que los acentos lleguen bien.\n"
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
        "- Hooks `PostToolUse` (doc_drift, memory_checkpoint) y `Stop` "
        "(discernment_gate) NO se puentean: solo `UserPromptSubmit`.\n"
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
        "existentes, y guardas OpenCode (parte `synthetic`, `session_id` y "
        "`PYTHONUTF8` en el shim, sin nombres calificados de sentinel-agents ni "
        "la variable de raiz de plugin de Claude, commands autocontenidos).\n"
        "- E2E en runtime real de `opencode %s` (`opencode run` + `opencode export`).\n"
        "- MCP (codebase-memory): fuera del bundle; se registra en el "
        "`opencode.json` del usuario.\n"
    ) % (
        M.OPENCODE_VERSION, len(cmd_names), ", ".join("`/%s`" % c for c in cmd_names),
        len(agent_names), oc_abs(OC_REFS_DIR), skipped, oc_abs(OC_REFS_DIR),
        M.OPENCODE_VERSION,
    )


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------
def build(dist_dir: Path) -> list[Path]:
    """Genera el bundle completo bajo dist_dir. Devuelve las rutas escritas."""
    skills = discover_skills()
    agents = discover_agents()
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
    written.append(write(dist_dir / "README.md", build_readme()))
    return written


def build_opencode(dist_dir: Path) -> list[Path]:
    """Genera el bundle OpenCode bajo dist_dir. Devuelve las rutas escritas.

    Todo lo que hay en dist/opencode sale de aca (check_harness falla si sobra
    o falta algo): commands (skills portables + commands de memory), agentes
    (todos los de sentinel-agents), references (contrato + KB ISO), shim de
    hooks, opencode.json y README.
    """
    agents = discover_agents()
    hooks = load_hooks()
    skills = discover_opencode_skills()
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
                             build_opencode_skill_command(skill_md)))
    for cmd_md in memory_cmds:
        written.append(write(dist_dir / "command" / cmd_md.name,
                             build_opencode_memory_command(cmd_md)))
    for name in names:
        written.append(write(dist_dir / "agent" / (name + ".md"),
                             build_opencode_agent(agents, name)))
    written.append(write(dist_dir / "references" / "agent-contract.md",
                         build_opencode_agent_contract()))
    kb_root = SENTINEL_ROOT / "references"
    for src in opencode_kb_files():
        dst = dist_dir / "references" / src.relative_to(kb_root)
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(src.read_bytes())
        written.append(dst)
    written.append(write(dist_dir / "plugin" / "fluency-hooks.js",
                         build_opencode_plugin(hooks, names)))
    written.append(write(dist_dir / "opencode.json", build_opencode_json()))
    written.append(write(dist_dir / "README.md",
                         build_opencode_readme(skills, memory_cmds, names)))
    return written


DEFAULT_HERMES_DIST = REPO_ROOT / "dist" / "hermes"


def build_hermes_md() -> str:
    """Genera .hermes.md desde CLAUDE.md."""
    claude_md = (REPO_ROOT / "CLAUDE.md").read_text(encoding="utf-8")
    rules, bridges = extract_hard_rules(claude_md)
    # Convertir paths .claude/ -> .hermes/
    bridges_hermes = []
    for b in bridges:
        bridges_hermes.append(b.replace(".claude/", ".hermes/"))
    parts = [
        "# .hermes.md — Contrato del proyecto (bundle Hermes)",
        "",
        "> Generado por `tools/multiharness/build_harness.py` desde `CLAUDE.md`.",
        "> Adaptado para Hermes Agent: skills bajo demanda en vez de hooks automaticos.",
        "",
        "<!-- BEGIN 4D-BRIDGES -->",
        "## Reglas del proyecto (siempre)",
        "",
    ]
    parts += rules if rules else ["- (sin reglas detectadas)"]
    parts += [
        "",
        "## Puentes de documentacion",
        "",
    ]
    parts += bridges_hermes if bridges_hermes else ["(sin puentes)"]
    parts += [
        "",
        "Si la pregunta o tarea toca un tema de la tabla, LEE ese archivo ANTES de responder.",
        "Al escribir codigo, respeta `.hermes/docs/convenciones.md`.",
        "<!-- END 4D-BRIDGES -->",
        "",
        "## Skills instalados (suite 4Dsentinel para Hermes)",
        "",
        "Carga los skills desde `~/.hermes/skills/productivity/`. Mira el README en",
        "`dist/hermes/` para la lista completa de comandos.",
    ]
    return "\n".join(parts)


def build_hermes(dist_dir: Path) -> list[Path]:
    """Genera el bundle Hermes bajo dist_dir. Devuelve las rutas escritas."""
    written: list[Path] = []
    written.append(write(dist_dir / ".hermes.md", build_hermes_md()))
    return written


def main() -> int:
    written = build(DEFAULT_DIST)
    written_oc = build_opencode(DEFAULT_OPENCODE_DIST)
    written_hm = build_hermes(DEFAULT_HERMES_DIST)
    print("Repo root : %s" % REPO_ROOT)
    print("Bundle    : %s" % DEFAULT_DIST)
    print("Bundle OC : %s" % DEFAULT_OPENCODE_DIST)
    print("Bundle HM : %s" % DEFAULT_HERMES_DIST)
    print("Skills    : %d descubiertos" % len(discover_skills()))
    print("Agentes   : %d descubiertos" % len(discover_agents()))
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
