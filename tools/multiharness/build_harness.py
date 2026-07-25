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
  OpenCode (dist/opencode/):
    - command: handoff (.opencode/command/handoff.md)
    - agente : critic, advisor (.opencode/agent/*.md, mode: subagent)
    - hooks  : plugin shim JS (.opencode/plugin/fluency-hooks.js) que puentea
               a los hooks Python via subprocess.
    - config : opencode.json (MCP diferido).

Idempotente: correrlo N veces produce el mismo arbol de salida.

ASCII puro (regla de CLAUDE.md): sin acentos en los strings de codigo. Los
archivos de CONTENIDO que emite (SKILL.md, config.toml, AGENTS.md...) SI llevan
acentos, porque su texto proviene de leer los archivos fuente en UTF-8.
"""

from __future__ import annotations

import json
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
# Descubrimiento
# ---------------------------------------------------------------------------
def discover_skills() -> list[Path]:
    """Globea plugins/*/skills/*/SKILL.md (NO lee el campo skills de plugin.json)."""
    return sorted(PLUGINS.glob("*/skills/*/SKILL.md"))


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
    """Lee plugins/fluency-4d/hooks/hooks.json."""
    return json.loads((FLUENCY_ROOT / "hooks" / "hooks.json").read_text(encoding="utf-8"))


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
    memory_checkpoint) y Stop (discernment_gate), tal cual la fuente.
    """
    resolved = resolve_plugin_root(hooks)
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
def yaml_dq(s: str) -> str:
    """Escala YAML entre comillas dobles (escapa backslash y comilla doble)."""
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


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


def build_opencode_command_handoff() -> str:
    meta = parse_frontmatter(
        (FLUENCY_ROOT / "skills" / "handoff" / "SKILL.md").read_text(encoding="utf-8"))
    desc = meta.get("description", "Checkpoint de cierre de sesion.")
    return (
        "---\n"
        "description: " + yaml_dq(desc) + "\n"
        "agent: build\n"
        "---\n\n"
        "<!-- Generado por tools/multiharness/build_harness.py desde "
        "plugins/fluency-4d/skills/handoff/SKILL.md. NO editar a mano. -->\n\n"
        "# /handoff - checkpoint de cierre de sesion (OpenCode)\n\n"
        "Wrapper del skill `handoff` de fluency-4d. El cuerpo canonico del flujo "
        "vive en el `SKILL.md` de la suite; este comando lo dispara en OpenCode.\n\n"
        "Segui el flujo `handoff` al pie de la letra:\n\n"
        "1. Recolecta el contexto real de git (rama, ultimos commits, "
        "`git status`, diff) y el plan/estado de sesion previo.\n"
        "2. Actualiza `.claude/docs/estado-sesion.md` (o el equivalente del "
        "proyecto) con rutas, lo hecho y lo pendiente.\n"
        "3. Sugeri el mensaje de commit -- **NO** lo ejecutes.\n"
        "4. Si no quedan pendientes, borra el estado viejo (persistencia).\n"
        "5. Copia el resumen del handoff al portapapeles para pegar en la "
        "sesion nueva.\n\n"
        "Argumentos opcionales: `$ARGUMENTS` (nota libre para el handoff).\n\n"
        "NOTA (OpenCode): el paso del \"plan activo\" degrada a \"sin plan\" si "
        "el proyecto no tiene un directorio de planes -- el resto del flujo es "
        "cross-harness.\n\n"
        "TODO(PoC): portar el resto de los skills de fluency-4d "
        "(`4d`, `4d-init`, `4d-status`, `4d-quiz`, `caveman`) como comandos "
        "OpenCode -- mismo patron de wrapper.\n"
    )


def opencode_permission(tools: str) -> str:
    """Deriva el bloque `permission` de OpenCode desde el allowlist `tools` del
    frontmatter fuente (Claude Code): deniega lo que el agente NO tiene permitido,
    para que un agente read-only (tools: Read, Grep, Glob) sea REALMENTE read-only
    en OpenCode (edit/bash/webfetch denegados, no solo edit)."""
    allowed = {t.strip().lower() for t in tools.split(",") if t.strip()}
    if not allowed or "*" in allowed:
        return ""  # acceso amplio: sin restricciones
    denies = []
    if not (allowed & {"write", "edit", "multiedit", "notebookedit"}):
        denies.append("edit: deny")
    if "bash" not in allowed:
        denies.append("bash: deny")
    if "webfetch" not in allowed:
        denies.append("webfetch: deny")
    if not denies:
        return ""
    return "permission: { " + ", ".join(denies) + " }\n"


def build_opencode_agent(agents: dict[str, dict[str, str]], name: str) -> str:
    meta = agents.get(name, {})
    if not meta:
        raise SystemExit("ERROR: no se encontro el agente '%s'" % name)
    desc = meta.get("description", "")
    src = Path(meta["_path"]).read_text(encoding="utf-8")
    body = strip_frontmatter(src).lstrip("\n")
    # Deniega en OpenCode lo que el allowlist `tools` fuente no permite
    # (read-only Read/Grep/Glob -> edit/bash/webfetch: deny), no solo edit.
    banner = (
        "<!-- Portado de plugins/sentinel-agents/agents/%s.md por "
        "tools/multiharness/build_harness.py. Frontmatter reescrito al schema "
        "de OpenCode. NO editar a mano. -->\n"
        "<!-- NOTA(PoC): la referencia a references/agent-contract.md NO esta "
        "incluida en este bundle; portarla es un TODO. -->\n\n" % name
    )
    perm = opencode_permission(meta.get("tools", ""))
    return (
        "---\n"
        "description: " + yaml_dq(desc) + "\n"
        "mode: subagent\n"
        + perm
        + "---\n\n"
        + banner + body
    )


def build_opencode_plugin(hooks: dict) -> str:
    scripts = opencode_userprompt_scripts(hooks)
    js_list = ",\n".join(
        '  "' + s.replace("\\", "\\\\") + '"' for s in scripts
    )
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
        "// API OpenCode 1.17.11 (verificada): el hook `chat.message` se dispara\n"
        "// cuando el usuario envia un mensaje, ANTES de que el modelo lo procese.\n"
        "// El texto del usuario vive en output.parts (partes type:text), NO en\n"
        "// input.prompt; la inyeccion de contexto es por output.parts.push(...).\n"
        "// Ante cualquier fallo el shim degrada a NO-OP: nunca rompe la sesion.\n"
        "\n"
        'import { spawnSync } from "node:child_process";\n'
        "\n"
        "// Rutas absolutas a los hooks Python de fluency-4d (resueltas al generar).\n"
        "const USER_PROMPT_HOOKS = [\n"
        + js_list + "\n"
        "];\n"
        "\n"
        "// Invoca un hook Python y devuelve su additionalContext (o '' si no aplica).\n"
        "function runPythonHook(scriptPath, payload) {\n"
        "  try {\n"
        '    const res = spawnSync("uv", ["run", "--script", scriptPath], {\n'
        "      input: JSON.stringify(payload || {}),\n"
        '      encoding: "utf8",\n'
        "      timeout: 5000,\n"
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
        "    const ctx = runPythonHook(script, payload);\n"
        "    if (ctx) chunks.push(ctx);\n"
        "  }\n"
        '    return chunks.join("\\n\\n");\n'
        "}\n"
        "\n"
        "// export: forma de plugin de OpenCode (funcion async que recibe el ctx\n"
        "// del harness y devuelve el mapa de hooks).\n"
        "export const FluencyHooks = async ({ project, client, $ } = {}) => {\n"
        "  return {\n"
        "    // chat.message = equivalente a UserPromptSubmit (dispara al enviar el\n"
        "    // mensaje del usuario, antes del modelo).\n"
        '    "chat.message": async (input, output) => {\n'
        "      try {\n"
        "        // El texto del usuario esta en output.parts (partes type:text),\n"
        "        // NO en input.prompt.\n"
        "        const parts = (output && Array.isArray(output.parts)) ? output.parts : [];\n"
        "        const userText = parts\n"
        '          .filter((p) => p && p.type === "text" && typeof p.text === "string")\n'
        "          .map((p) => p.text)\n"
        '          .join("\\n");\n'
        "        const payload = {\n"
        "          prompt: userText,\n"
        "          cwd: (project && project.worktree) || process.cwd(),\n"
        "        };\n"
        "        const extra = collectContext(payload);\n"
        "        // Inyeccion: se MUTA output.parts empujando una parte de texto\n"
        "        // (output.additionalContext no existe en la API de OpenCode).\n"
        "        if (extra && output && Array.isArray(output.parts)) {\n"
        '          output.parts.push({ type: "text", text: extra });\n'
        "        }\n"
        "      } catch (_e) {\n"
        "        // NO-OP seguro.\n"
        "      }\n"
        "    },\n"
        "  };\n"
        "};\n"
        "\n"
        "export default FluencyHooks;\n"
    )


def build_opencode_json() -> str:
    data = {
        "$schema": "https://opencode.ai/config.json",
        "//": (
            "opencode.json - bundle OpenCode generado por "
            "tools/multiharness/build_harness.py. NO editar a mano."
        ),
        "//mcp": (
            "MCP codebase-memory (cbm) DIFERIDO: binario no instalado -> sin "
            "bloque 'mcp'. Cuando este, agregar: \"mcp\": { \"codebase-memory\": "
            "{ \"type\": \"local\", \"command\": [\"cbm\"], \"enabled\": true } }"
        ),
    }
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


def build_opencode_readme() -> str:
    return (
        "# Bundle OpenCode de la suite 4Dsentinel (PoC)\n"
        "\n"
        "Bundle regenerable que porta parte de la suite de plugins de Claude "
        "Code a **OpenCode 1.17.11**. Generado por "
        "`tools/multiharness/build_harness.py` desde la fuente canonica en "
        "`plugins/*` (read-only).\n"
        "\n"
        "## Que incluye este PoC\n"
        "\n"
        "- **Command** `handoff` -> `command/handoff.md` (frontmatter "
        "`description` + `agent`; cuerpo que dispara el flujo del skill "
        "`handoff`).\n"
        "- **Agentes** `critic` y `advisor` -> `agent/*.md` "
        "(`mode: subagent`, `permission: { edit: deny, bash: deny, webfetch: "
        "deny }` derivado del allowlist read-only Read/Grep/Glob del "
        "frontmatter fuente).\n"
        "- **Hooks** -> `plugin/fluency-hooks.js`: shim que puentea los hooks "
        "Python de `UserPromptSubmit` por subprocess (no reescribe la logica).\n"
        "- **Config** -> `opencode.json` (MCP diferido).\n"
        "\n"
        "## Instalacion\n"
        "\n"
        "Copia los directorios `command/`, `agent/` y `plugin/` bajo la carpeta "
        "`.opencode/` del proyecto (o de `~/.config/opencode/` para uso global), "
        "y `opencode.json` a la raiz del proyecto (o `~/.config/opencode/`):\n"
        "\n"
        "```bash\n"
        "# por proyecto\n"
        "mkdir -p .opencode\n"
        "cp -r dist/opencode/command dist/opencode/agent dist/opencode/plugin .opencode/\n"
        "cp dist/opencode/opencode.json ./opencode.json\n"
        "```\n"
        "\n"
        "```powershell\n"
        "# Windows PowerShell (por proyecto)\n"
        "New-Item -ItemType Directory -Force .opencode | Out-Null\n"
        "Copy-Item -Recurse -Force dist\\opencode\\command,dist\\opencode\\agent,dist\\opencode\\plugin .opencode\\\n"
        "Copy-Item -Force dist\\opencode\\opencode.json .\\opencode.json\n"
        "```\n"
        "\n"
        "## Que se verifico\n"
        "\n"
        "- El generador corre sin error y es idempotente (`check_harness.py` no "
        "reporta drift).\n"
        "- `opencode.json` parsea como JSON.\n"
        "- Las rutas de los hooks en el shim JS son absolutas y apuntan a `.py` "
        "existentes.\n"
        "\n"
        "## Pendiente / no verificado\n"
        "\n"
        "- **E2E con OpenCode**: shim smoke-tested (harness Node que importa "
        "`fluency-hooks.js`, simula `chat.message` y verifica la inyeccion en "
        "`output.parts` corriendo los hooks Python reales) -> PASS. Falta solo el "
        "E2E en runtime real de `opencode` (lo valida el humano).\n"
        "- **API de plugins de OpenCode**: VERIFICADA (1.17.11) e implementada. El "
        "shim `fluency-hooks.js` usa el hook `chat.message` (equivalente a "
        "`UserPromptSubmit`): lee el texto del usuario de `output.parts` e inyecta "
        "contexto con `output.parts.push({type:'text', text})`. Degrada a NO-OP "
        "seguro ante fallos. Falta solo el E2E (ver arriba).\n"
        "- **Resto de skills** (`4d`, `4d-init`, `4d-status`, `4d-quiz`, "
        "`caveman`) y **resto de subagentes**: TODO.\n"
        "- **MCP** (codebase-memory / `cbm`): DIFERIDO, binario no instalado.\n"
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
    """Genera el bundle OpenCode bajo dist_dir. Devuelve las rutas escritas."""
    agents = discover_agents()
    hooks = load_hooks()

    if "critic" not in agents:
        raise SystemExit("ERROR: no se encontro el agente 'critic' en sentinel-agents")
    if "advisor" not in agents:
        raise SystemExit("ERROR: no se encontro el agente 'advisor' en sentinel-agents")

    written: list[Path] = []
    written.append(write(dist_dir / "command" / "handoff.md",
                         build_opencode_command_handoff()))
    written.append(write(dist_dir / "agent" / "critic.md",
                         build_opencode_agent(agents, "critic")))
    written.append(write(dist_dir / "agent" / "advisor.md",
                         build_opencode_agent(agents, "advisor")))
    written.append(write(dist_dir / "plugin" / "fluency-hooks.js",
                         build_opencode_plugin(hooks)))
    written.append(write(dist_dir / "opencode.json", build_opencode_json()))
    written.append(write(dist_dir / "README.md", build_opencode_readme()))
    return written


def main() -> int:
    written = build(DEFAULT_DIST)
    written_oc = build_opencode(DEFAULT_OPENCODE_DIST)
    print("Repo root : %s" % REPO_ROOT)
    print("Bundle    : %s" % DEFAULT_DIST)
    print("Bundle OC : %s" % DEFAULT_OPENCODE_DIST)
    print("Skills    : %d descubiertos" % len(discover_skills()))
    print("Agentes   : %d descubiertos" % len(discover_agents()))
    print("Archivos escritos (codex):")
    for p in written:
        print("  - %s" % p.relative_to(REPO_ROOT))
    print("Archivos escritos (opencode):")
    for p in written_oc:
        print("  - %s" % p.relative_to(REPO_ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
