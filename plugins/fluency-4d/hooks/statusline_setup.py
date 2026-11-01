#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""statusline_setup.py - Instala / quita / inspecciona la barra de estado de fluency-4d.

NO es un hook de evento: lo invoca la skill /statusline (setup | remove | status).
Vive en hooks/ para compartir hook_utils (escritura atomica) y quedar bajo
ruff, mypy y coverage igual que los hooks.

- setup: chequea node (>= 18), copia statusline/statusline.js a la ruta fija
  ~/.claude/fluency4d/statusline.js y agrega SOLO lo que falta: statusLine con
  refreshInterval (si no hay otro; un statusLine ajeno sale con codigo 2 salvo
  --force; al nuestro de una version previa le agrega el refreshInterval), quita
  env.CLAUDE_CODE_PLUGIN_DIRS si apunta a un mod panel-4d local, y opcionalmente
  el atajo (--keybinding) y el tema (--copy-theme). ANTES de tocar nada escribe
  ~/.claude/fluency4d/setup.json con la intencion, los valores previos y el texto
  original de cada JSON; si un paso posterior falla, revierte lo ya escrito.
  Backups solo de lo que cambia: fechados (quedan los 3 mas recientes) mas un
  <archivo>.orig.bak fijo de la primera instalacion que la poda nunca borra.
  setup.json anota que .orig.bak creo ESTA instalacion; uno anterior (de una
  instalacion vieja) se renombra a <archivo>.orig.<fecha>.bak y nunca se borra.
- remove: revierte lo registrado en setup.json. Si el resultado equivale al
  original, reescribe el texto ORIGINAL byte a byte; si el usuario edito entre
  medio, aplica la reversion minima conservando el salto de linea (CRLF/LF).
  Si todo se restauro limpio, borra solo los .orig.bak propios. Si el statusLine
  no se pudo revertir (cambio desde el setup), conserva la copia fija y avisa.
  Las rutas que borra se calculan siempre (nunca se toman de setup.json).
- status: muestra que esta instalado y si la copia fija difiere del plugin.

setup y remove toman el lock exclusivo fluency4d/.setup.lock (O_CREAT|O_EXCL).
Si settings.json (o keybindings.json, cuando se va a tocar) no es JSON valido,
aborta sin escribir nada. Todas las escrituras son atomicas.
Codigos de salida: 0 ok, 1 error, 2 statusLine ajeno (pedir confirmacion).
Strings ASCII (consola cp1252 en Windows).

Rutas: settings.json, keybindings.json y themes/ son de Claude Code y se resuelven
desde CLAUDE_CONFIG_DIR si esta definido (si no, ~/.claude). La copia fija,
setup.json, los backups y el lock viven SIEMPRE en ~/.claude/fluency4d/ (igual que
los flags de hook_utils), que es donde la barra los busca.
"""

from __future__ import annotations

import argparse
import datetime
import functools
import hashlib
import json
import os
import re
import shlex
import shutil
import stat
import subprocess
import sys
import tempfile
import time
import unicodedata
import uuid
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent))

from hook_utils import atomic_write_json, atomic_write_text  # noqa: E402

EXIT_OK = 0
EXIT_ERROR = 1
EXIT_CONFLICT = 2

# refreshInterval del statusLine (segundos): Claude Code re-ejecuta la barra cada N s
# ademas de con cada mensaje. Compromiso entre feedback rapido (el modo elegido en el
# Panel 4D, "vence en Nm" de la cache, "vuelve HH:MM" del plan) y costo: un proceso
# node cada 5 s. Si el usuario lo cambia a mano, setup no lo pisa.
REFRESH_INTERVAL_S = 5

KEYBINDING_KEY = "ctrl+x ctrl+p"
KEYBINDING_CMD = "command:panel"
# Compatibilidad: el setup de 0.22.0 registraba el atajo como command:fluency-4d:panel,
# un comando que no existe (los comandos de un mod no llevan el prefijo del plugin).
# remove lo sigue quitando y setup lo migra a KEYBINDING_CMD. No borrar mientras
# puedan quedar setup.json de 0.22.0.
LEGACY_KEYBINDING_CMD = "command:fluency-4d:panel"
KNOWN_KEYBINDING_CMDS = (KEYBINDING_CMD, LEGACY_KEYBINDING_CMD)
KEYBINDING_CONTEXT = "Chat"
KEYBINDINGS_SCHEMA = "https://www.schemastore.org/claude-code-keybindings.json"
PLUGIN_DIRS_KEY = "CLAUDE_CODE_PLUGIN_DIRS"
PANEL_MOD_NAME = "panel-4d"
THEME_FILE = "templado.json"
MAX_BACKUPS = 3
MIN_NODE_MAJOR = 18
LOCK_STALE_S = 60.0
# Solo tests: nombre de archivo cuya escritura falla como si fuera de solo lectura.
FAIL_WRITE_ENV = "FLUENCY_4D_FAIL_WRITE"


class SetupError(Exception):
    """Error que aborta la operacion ANTES de escribir (o con mensaje claro)."""


# --- Rutas ------------------------------------------------------------------


def claude_dir() -> Path:
    """Config de Claude Code: CLAUDE_CONFIG_DIR si esta definido, si no ~/.claude."""
    raw = os.environ.get("CLAUDE_CONFIG_DIR", "").strip()
    return Path(os.path.expanduser(raw)) if raw else Path.home() / ".claude"


def fluency_dir() -> Path:
    """Siempre ~/.claude/fluency4d (como hook_utils y la barra), aun con CLAUDE_CONFIG_DIR."""
    return Path.home() / ".claude" / "fluency4d"


def settings_path() -> Path:
    return claude_dir() / "settings.json"


def keybindings_path() -> Path:
    return claude_dir() / "keybindings.json"


def copy_path() -> Path:
    return fluency_dir() / "statusline.js"


def record_path() -> Path:
    return fluency_dir() / "setup.json"


def backups_dir() -> Path:
    return fluency_dir() / "backups"


def lock_path() -> Path:
    return fluency_dir() / ".setup.lock"


def orig_backup_path(path: Path) -> Path:
    return backups_dir() / f"{path.name}.orig.bak"


# Unicos archivos con .orig.bak: los nombres de setup.json se validan contra esto.
ORIG_NAMES = ("settings.json", "keybindings.json")


def theme_dst() -> Path:
    return claude_dir() / "themes" / THEME_FILE


def plugin_root(arg: str | None) -> Path:
    """Arg explicito > CLAUDE_PLUGIN_ROOT > carpeta padre de hooks/."""
    raw = arg or os.environ.get("CLAUDE_PLUGIN_ROOT")
    return Path(raw) if raw else Path(__file__).resolve().parent.parent


def plugin_version(root: Path) -> str:
    try:
        data = json.loads((root / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return "desconocida"
    version = data.get("version") if isinstance(data, dict) else None
    return str(version) if version else "desconocida"


# --- Utilidades ---------------------------------------------------------------


def sha256_of(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def norm(path_text: str) -> str:
    unified = path_text.replace("\\", "/")
    return unified.casefold() if os.name == "nt" else unified


def our_command(copy: Path) -> str:
    """`node <ruta>` citada con shlex.quote (comillas simples POSIX).

    Claude Code corre statusLine con bash (Git Bash en Windows, o PowerShell si no
    hay Git Bash): en ambos las comillas simples son literales, asi que `$` y
    backtick en HOME no se expanden. El escape de una comilla simple embebida
    ('"'"') solo vale en bash: en Windows esa ruta se rechaza con un mensaje.
    """
    posix = copy.resolve().as_posix()
    if os.name == "nt":
        bad = sorted({c for c in posix if not _safe_win_char(c)})
        if bad:
            shown = " ".join(f"U+{ord(c):04X}" for c in bad)
            raise SetupError(
                f"la ruta {posix} tiene caracteres no permitidos ({shown}): en Windows solo "
                "se aceptan letras (con acentos), numeros, espacio y _ . / : - para que el "
                "comando no cambie de sentido entre Git Bash y PowerShell. Usa una carpeta "
                "de usuario sin comillas, $, %, ` ni simbolos."
            )
    return "node " + shlex.quote(posix)


_WIN_SAFE_ASCII = frozenset("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_ ./:-")


def _safe_win_char(char: str) -> bool:
    """Lista blanca de Windows: ASCII seguro o letra Unicode (L*/M*, p. ej. acentos).

    Las comillas tipograficas (U+2018-U+201B) son Pi/Pf, no letras: se rechazan.
    """
    if char in _WIN_SAFE_ASCII:
        return True
    if ord(char) < 128:
        return False  # ' " ` $ % ; & ( ) etc.
    return unicodedata.category(char)[0] in ("L", "M")


def _legacy_command(copy: Path) -> str:
    """Forma de versiones previas del setup (comillas dobles): se sigue reconociendo."""
    return f'node "{copy.resolve().as_posix()}"'


def points_to_ours(value: object, copy: Path) -> bool:
    """True solo si es `type: command` y el comando es EXACTAMENTE el que generamos.

    Compara solo `type` y `command` (barras normalizadas): el resto de las claves
    (p. ej. refreshInterval, presente o no, con nuestro valor o el del usuario) no
    cambia que sea nuestro. Un wrapper ajeno que mencione la ruta (p. ej.
    `bash -c "node ... | otro"`) NO es nuestro: setup no lo pisa sin --force y remove
    no lo borra.
    """
    if not isinstance(value, dict) or value.get("type") != "command":
        return False
    command = value.get("command")
    if not isinstance(command, str):
        return False
    accepted = {norm(_legacy_command(copy))}
    try:
        accepted.add(norm(our_command(copy)))
    except SetupError:
        pass
    return norm(command.strip()) in accepted


def parse_node_major(version: str) -> int | None:
    """Major de `vX.Y.Z` (con o sin `v`), o None si no se puede leer."""
    match = re.match(r"v?(\d+)\.(\d+)\.(\d+)", version.strip())
    return int(match.group(1)) if match else None


def node_version() -> str | None:
    """Version de node, o None si no esta. FLUENCY_4D_NODE_BIN lo sobreescribe (tests)."""
    exe = shutil.which(os.environ.get("FLUENCY_4D_NODE_BIN", "node"))
    if not exe:
        return None
    try:
        out = subprocess.run(
            [exe, "--version"], capture_output=True, text=True, timeout=15, check=False
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if out.returncode != 0:
        return None
    return out.stdout.strip() or None


def insert_at(data: dict[str, Any], key: str, value: Any, index: int) -> dict[str, Any]:
    """Devuelve una copia de `data` con `key` en la posicion `index` (orden estable)."""
    items = [(k, v) for k, v in data.items() if k != key]
    items.insert(max(0, min(index, len(items))), (key, value))
    return dict(items)


def copy_atomic(src: Path, dst: Path) -> None:
    dst = dst.resolve()  # symlink: se escribe en su destino, no se reemplaza el link
    dst.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(dst.parent), prefix=dst.name + ".", suffix=".tmp")
    os.close(fd)
    try:
        shutil.copyfile(src, tmp)
        os.replace(tmp, dst)
    except OSError:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def _copy_backup(path: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, dst)  # conserva permisos restrictivos (secretos en env)
    try:  # ...pero el backup tiene que poder podarse/borrarse (solo lectura en Windows)
        os.chmod(dst, stat.S_IMODE(os.stat(dst).st_mode) | stat.S_IWUSR)
    except OSError:
        pass


def _dated_backups(name: str) -> list[Path]:
    """Solo backups PROPIOS, por patron exacto <name>.AAAAMMDD-HHMMSS-ffffff.bak."""
    pattern = re.compile(re.escape(name) + r"\.\d{8}-\d{6}-\d{6}\.bak")
    directory = backups_dir()
    if not directory.is_dir():
        return []
    return sorted(p for p in directory.iterdir() if pattern.fullmatch(p.name))


def backup(path: Path) -> Path | None:
    """Copia fechada en fluency4d/backups/ y poda a los MAX_BACKUPS mas recientes.

    La poda nunca toca <name>.orig.bak ni archivos ajenos.
    """
    if not path.is_file():
        return None
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    dst = backups_dir() / f"{path.name}.{stamp}.bak"
    _copy_backup(path, dst)
    for old in _dated_backups(path.name)[:-MAX_BACKUPS]:
        try:
            old.unlink()
        except OSError:
            pass
    return dst


def stash_foreign_orig(path: Path) -> Path | None:
    """Renombra un <name>.orig.bak que NO creo esta instalacion a <name>.orig.<ts>.bak.

    Asi el respaldo de una instalacion vieja nunca se reutiliza ni se borra (la poda
    solo matchea <name>.<ts>.bak). Devuelve la ruta nueva, o None si no habia.
    """
    src = orig_backup_path(path)
    if not src.exists():
        return None
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    dst = backups_dir() / f"{path.name}.orig.{stamp}.bak"
    os.replace(src, dst)
    return dst


def ensure_orig_backup(path: Path) -> Path | None:
    """<name>.orig.bak fijo de la primera instalacion. Devuelve la ruta si lo CREO."""
    dst = orig_backup_path(path)
    if not path.is_file() or dst.exists():
        return None
    _copy_backup(path, dst)
    return dst


def _unstash(stashed: Path, orig: Path) -> None:
    if not orig.exists():
        os.replace(stashed, orig)


def write_user_text(path: Path, text: str) -> None:
    """Escritura atomica de un archivo del usuario (con fault-injection para tests)."""
    if os.environ.get(FAIL_WRITE_ENV) == path.name:
        raise PermissionError(f"[simulado] {path}: archivo de solo lectura")
    atomic_write_text(path, text)


@contextmanager
def setup_lock(wait_s: float | None = None) -> Iterator[None]:
    """Lock exclusivo fluency4d/.setup.lock que cubre toda la operacion.

    Si existe y tiene menos de LOCK_STALE_S segundos se espera con reintentos
    cortos; si es mas viejo es huerfano (proceso muerto) y se retoma. Se libera
    siempre en finally. FLUENCY_4D_LOCK_WAIT acota la espera (tests).
    """
    if wait_s is None:
        wait_s = float(os.environ.get("FLUENCY_4D_LOCK_WAIT", LOCK_STALE_S + 5))
    directory = fluency_dir()
    created_dir = not directory.exists()
    path = lock_path()
    token = f"{os.getpid()} {uuid.uuid4().hex}"
    deadline = time.monotonic() + wait_s
    while True:
        try:
            # Dentro del bucle: el dueno anterior puede haber hecho rmdir de fluency4d/.
            directory.mkdir(parents=True, exist_ok=True)
            fd = os.open(str(path), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileNotFoundError:
            if time.monotonic() >= deadline:
                raise
            continue  # fluency4d/ desaparecio entre el mkdir y el open: reintentar
        except FileExistsError:
            try:
                st = path.stat()
                seen = path.read_bytes()
            except OSError:
                continue  # se libero entre el open y el stat: reintentar ya
            if time.time() - st.st_mtime > LOCK_STALE_S:
                _take_stale_lock(path, st.st_mtime_ns, seen)
                continue
            if time.monotonic() >= deadline:
                raise SetupError(
                    f"otra ejecucion de /statusline tiene el lock {path}; reintenta en un "
                    "momento (si no hay ninguna corriendo, se libera solo a los 60 s)."
                ) from None
            time.sleep(0.1)
            continue
        with os.fdopen(fd, "w", encoding="ascii") as fh:
            fh.write(token)
        break
    try:
        yield
    finally:
        try:
            if path.read_text(encoding="ascii") == token:
                path.unlink()
        except OSError:
            pass
        if created_dir:
            try:
                directory.rmdir()  # no dejar fluency4d/ vacio si no se escribio nada
            except OSError:
                pass


def _take_stale_lock(path: Path, mtime_ns: int, seen: bytes) -> None:
    """Retira un lock huerfano sin robar uno recien tomado (TOCTOU).

    Se renombra atomicamente a un nombre unico: de varios procesos solo uno logra
    el rename. Despues se compara con lo observado (mtime y contenido); si no es el
    mismo lock viejo (otro proceso lo retomo entre medio), se devuelve a su lugar.
    """
    grave = path.with_name(f"{path.name}.stale.{uuid.uuid4().hex}")
    try:
        os.replace(path, grave)
    except OSError:
        return  # otro proceso gano el rename (o ya no existe): reintentar con O_EXCL
    try:
        st = grave.stat()
        same = st.st_mtime_ns == mtime_ns and grave.read_bytes() == seen
    except OSError:
        same = False
    if not same:
        try:
            os.link(grave, path)  # atomico y sin pisar: si ya hay otro lock, falla
        except OSError:
            pass
    try:
        grave.unlink()
    except OSError:
        pass


# --- Documentos JSON del usuario ----------------------------------------------


@dataclass
class JsonDoc:
    path: Path
    data: dict[str, Any]
    existed: bool
    indent: int | str = 2
    trailing_newline: bool = True
    original: str = field(default="", repr=False)
    newline: str = "\n"

    def dumps(self) -> str:
        return json.dumps(self.data, ensure_ascii=False, indent=self.indent)

    def text(self) -> str:
        """Serializacion con el salto de linea (CRLF/LF) y el newline final detectados."""
        out = self.dumps() + ("\n" if self.trailing_newline else "")
        return out.replace("\n", self.newline) if self.newline != "\n" else out

    def changed(self) -> bool:
        if not self.existed:
            return True
        try:
            before = json.loads(self.original) if self.original.strip() else {}
        except json.JSONDecodeError:
            return True
        # Sensible al orden de claves: insert_at reubica claves y eso cuenta.
        return json.dumps(before, ensure_ascii=False, indent=self.indent) != self.dumps()

    def save(self) -> None:
        write_user_text(self.path, self.text())

    def snapshot(self) -> dict[str, Any]:
        """Lo que remove necesita para volver byte a byte."""
        raw = self.original.encode("utf-8", "surrogatepass")
        return {
            "existed": self.existed,
            "text": self.original,
            "sha256": hashlib.sha256(raw).hexdigest(),
        }


def load_doc(path: Path, default: dict[str, Any] | None = None) -> JsonDoc:
    """Lee un JSON objeto del usuario. Si no se puede parsear -> SetupError (no se pisa)."""
    if not path.exists():
        return JsonDoc(path, dict(default or {}), existed=False)
    try:
        with path.open(encoding="utf-8", newline="") as fh:  # sin traducir CRLF
            text = fh.read()
        data = json.loads(text) if text.strip() else {}
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SetupError(f"{path} no es JSON valido ({exc}); no se toca. Arreglalo y reintenta.")
    if not isinstance(data, dict):
        raise SetupError(f"{path} no es un objeto JSON; no se toca.")
    indent: int | str = 2
    match = re.search(r"\n([ \t]+)\S", text)
    if match:
        ws = match.group(1)
        indent = ws if "\t" in ws else len(ws)
    newline = "\r\n" if "\r\n" in text else "\n"
    return JsonDoc(path, data, True, indent, text.endswith("\n"), text, newline)


def revert_target(doc: JsonDoc, snap: object, *, delete_if_created: bool) -> str | None:
    """Texto final de `doc` tras revertir, o None si hay que borrar el archivo.

    Si el JSON resultante es semanticamente igual al original registrado, devuelve
    el texto ORIGINAL exacto (CRLF, formato inline, claves duplicadas, newline
    final). Si no (el usuario edito entre medio), la reversion minima con su estilo.
    """
    if isinstance(snap, dict):
        if snap.get("existed"):
            text = snap.get("text")
            if isinstance(text, str):
                try:
                    odata = json.loads(text) if text.strip() else {}
                except json.JSONDecodeError:
                    odata = None
                if odata == doc.data:
                    return text
        elif not doc.data:
            return None
    if delete_if_created:
        return None
    return doc.text()


def read_record_text() -> str | None:
    try:
        return record_path().read_text(encoding="utf-8")
    except FileNotFoundError:
        return None


def load_record() -> dict[str, Any] | None:
    path = record_path()
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SetupError(f"{path} esta corrupto ({exc}); revisalo a mano.") from None
    if not isinstance(data, dict):
        raise SetupError(f"{path} no es un objeto JSON; revisalo a mano.")
    return data


def save_record(record: dict[str, Any]) -> None:
    atomic_write_json(record_path(), record, indent=2, trailing_newline=True)


# --- Piezas del setup -----------------------------------------------------------


def _split_dirs(value: str) -> tuple[list[str], str]:
    """Separa SOLO por os.pathsep (';' en Windows, ':' en POSIX), nunca por ','
    (una coma es un caracter valido dentro de una ruta)."""
    sep = os.pathsep
    return [e for e in value.split(sep) if e.strip()], sep


def _is_panel_mod(entry: str) -> bool:
    return norm(entry.strip()).rstrip("/").rsplit("/", 1)[-1] == norm(PANEL_MOD_NAME)


def strip_panel_mod(settings: JsonDoc) -> dict[str, Any] | None:
    """Quita el mod panel-4d local de env.CLAUDE_CODE_PLUGIN_DIRS. Devuelve el registro."""
    env = settings.data.get("env")
    if not isinstance(env, dict) or not isinstance(env.get(PLUGIN_DIRS_KEY), str):
        return None
    previous = env[PLUGIN_DIRS_KEY]
    entries, sep = _split_dirs(previous)
    if not any(_is_panel_mod(e) for e in entries):
        return None
    rec: dict[str, Any] = {
        "previous": previous,
        "env_index": list(env).index(PLUGIN_DIRS_KEY),
        "env_pos": list(settings.data).index("env"),
        "env_removed": False,
        "left": None,
    }
    keep = [e for e in entries if not _is_panel_mod(e)]
    if keep:
        env[PLUGIN_DIRS_KEY] = sep.join(keep)
        rec["left"] = env[PLUGIN_DIRS_KEY]
    else:
        del env[PLUGIN_DIRS_KEY]
        if not env:
            del settings.data["env"]
            rec["env_removed"] = True
    return rec


def restore_panel_mod(settings: JsonDoc, rec: dict[str, Any]) -> str:
    """Devuelve "restored", "already" (ya estaba como antes) o "conflict"."""
    env = settings.data.get("env")
    if isinstance(env, dict) and env.get(PLUGIN_DIRS_KEY) == rec.get("previous"):
        return "already"
    if env is None:
        env = {}
        settings.data = insert_at(settings.data, "env", env, int(rec.get("env_pos", 0)))
    if not isinstance(env, dict):
        print("AVISO: env ya no es un objeto; no se restaura CLAUDE_CODE_PLUGIN_DIRS.")
        return "conflict"
    current = env.get(PLUGIN_DIRS_KEY)
    if current is not None and current != rec.get("left"):
        print("AVISO: CLAUDE_CODE_PLUGIN_DIRS cambio desde el setup; no se toca.")
        return "conflict"
    new_env = insert_at(env, PLUGIN_DIRS_KEY, rec.get("previous"), int(rec.get("env_index", 0)))
    settings.data["env"] = new_env
    return "restored"


def _chat_blocks(kb: JsonDoc) -> list[dict[str, Any]]:
    bindings = kb.data.get("bindings")
    if not isinstance(bindings, list):
        return []
    return [b for b in bindings if isinstance(b, dict) and isinstance(b.get("bindings"), dict)]


def add_keybinding(kb: JsonDoc) -> dict[str, Any] | None:
    """Agrega el atajo solo si la tecla esta libre. Devuelve el registro o None."""
    if "bindings" in kb.data and not isinstance(kb.data["bindings"], list):
        print("AVISO: keybindings.json tiene 'bindings' con formato inesperado; no se toca.")
        return None
    for block in _chat_blocks(kb):
        if block.get("context") not in (KEYBINDING_CONTEXT, "Global"):
            continue
        bound = block["bindings"].get(KEYBINDING_KEY)
        if bound == KEYBINDING_CMD:
            # Ya apunta al panel (p. ej. lo dejo el mod local panel-4d): no es conflicto,
            # pero tampoco es nuestro, asi que remove no lo borra.
            print(f"El atajo {KEYBINDING_KEY} -> /panel ya estaba configurado; no se toca.")
            return {"block_created": False, "file_created": False, "preexisting": True}
        if bound is not None:
            print(f"AVISO: el atajo {KEYBINDING_KEY} ya esta ocupado ({bound}); no se toca.")
            return None
    if not kb.existed:
        kb.data = {"$schema": KEYBINDINGS_SCHEMA, "bindings": []}
    bindings = kb.data.setdefault("bindings", [])
    for block in _chat_blocks(kb):
        if block.get("context") == KEYBINDING_CONTEXT:
            block["bindings"][KEYBINDING_KEY] = KEYBINDING_CMD
            return {"block_created": False, "file_created": not kb.existed}
    bindings.append({"context": KEYBINDING_CONTEXT, "bindings": {KEYBINDING_KEY: KEYBINDING_CMD}})
    return {"block_created": True, "file_created": not kb.existed}


def migrate_keybinding(kb: JsonDoc) -> bool:
    """Pasa el atajo de 0.22.0 (LEGACY_KEYBINDING_CMD) a KEYBINDING_CMD. True si cambio."""
    for block in _chat_blocks(kb):
        if block.get("context") != KEYBINDING_CONTEXT:
            continue
        if block["bindings"].get(KEYBINDING_KEY) == LEGACY_KEYBINDING_CMD:
            block["bindings"][KEYBINDING_KEY] = KEYBINDING_CMD
            return True
    return False


def remove_keybinding(kb: JsonDoc, rec: dict[str, Any]) -> str:
    """Devuelve "removed", "already" (la tecla ya no esta) o "conflict"."""
    ours = rec.get("command")
    expected = ours if ours in KNOWN_KEYBINDING_CMDS else KEYBINDING_CMD
    bindings = kb.data.get("bindings")
    blocks = [b for b in _chat_blocks(kb) if b.get("context") == KEYBINDING_CONTEXT]
    if not any(KEYBINDING_KEY in b["bindings"] for b in blocks):
        return "already"
    for block in blocks:
        if block["bindings"].get(KEYBINDING_KEY) != expected:
            continue
        del block["bindings"][KEYBINDING_KEY]
        if not block["bindings"] and rec.get("block_created") and isinstance(bindings, list):
            bindings.remove(block)
        return "removed"
    print("AVISO: el atajo ya no es el de fluency-4d; no se toca.")
    return "conflict"


# --- Transaccion del setup -------------------------------------------------------


def _restore_record(before: str | None) -> None:
    if before is None:
        record_path().unlink(missing_ok=True)
    else:
        atomic_write_text(record_path(), before)


def _restore_doc(doc: JsonDoc) -> None:
    if doc.existed:
        atomic_write_text(doc.path, doc.original)
    else:
        doc.path.unlink(missing_ok=True)


def _rollback(undo: list[tuple[str, Callable[[], None]]]) -> list[str]:
    """Deshace en orden inverso. El primer paso (setup.json) solo se deshace si todo
    lo demas se pudo revertir: si no, el registro queda para que remove funcione."""
    failed: list[str] = []
    for index in range(len(undo) - 1, -1, -1):
        label, fn = undo[index]
        if index == 0 and failed:
            break
        try:
            fn()
        except OSError:
            failed.append(label)
    return failed


def _node_ok(nv: str | None) -> bool:
    if nv is None:
        print(
            "ERROR: no se encontro Node.js (node --version fallo). La barra y el panel lo\n"
            "necesitan: instalalo desde https://nodejs.org (LTS), abri una terminal nueva\n"
            "y volve a correr /statusline setup."
        )
        return False
    major = parse_node_major(nv)
    if major is None or major < MIN_NODE_MAJOR:
        print(
            f"ERROR: Node.js {nv} no sirve: la barra necesita Node >= {MIN_NODE_MAJOR}.\n"
            "Actualizalo desde https://nodejs.org (LTS), abri una terminal nueva y volve a\n"
            "correr /statusline setup."
        )
        return False
    return True


# --- Subcomandos --------------------------------------------------------------


def cmd_setup(args: argparse.Namespace) -> int:
    root = plugin_root(args.plugin_root)
    src = root / "statusline" / "statusline.js"
    if not src.is_file():
        raise SetupError(f"no se encontro {src}; revisa la instalacion del plugin.")
    nv = node_version()
    if not _node_ok(nv):
        return EXIT_ERROR

    # 1) Todo lo que puede abortar se lee y se planifica EN MEMORIA.
    record_before = read_record_text()
    record = load_record() or {}
    owned_raw = record.get("orig_backups")
    owned_before = [n for n in owned_raw if n in ORIG_NAMES] if isinstance(owned_raw, list) else []
    settings = load_doc(settings_path())
    old_kb = record.get("keybinding")
    legacy_kb = isinstance(old_kb, dict) and old_kb.get("command") == LEGACY_KEYBINDING_CMD
    kb_wanted = args.keybinding or (legacy_kb and keybindings_path().exists())
    kb = load_doc(keybindings_path()) if kb_wanted else None
    copy = copy_path()
    command = our_command(copy)
    had_key = "statusLine" in settings.data
    current = settings.data.get("statusLine")
    ours = points_to_ours(current, copy)
    if current is not None and not ours and not args.force:
        print("CONFLICTO: ya hay un statusLine configurado que no es el de fluency-4d:")
        print(json.dumps(current, ensure_ascii=True, indent=2))
        print("No se toco nada. Para reemplazarlo (se guarda y remove lo restaura): --force")
        return EXIT_CONFLICT

    msgs: list[str] = []
    if not ours:
        record["statusline"] = {
            "had_key": had_key,
            "had_previous": current is not None,
            "previous": current,
        }
        settings.data["statusLine"] = {
            "type": "command",
            "command": command,
            "refreshInterval": REFRESH_INTERVAL_S,
        }
        msgs.append(f"statusLine -> {command} (refresco cada {REFRESH_INTERVAL_S} s)")
    else:
        sl_rec = record.setdefault(
            "statusline", {"had_key": False, "had_previous": False, "previous": None}
        )
        if isinstance(current, dict):
            migrated = dict(current)
            if current.get("command") != command:
                migrated["command"] = command  # migra la forma vieja (comillas dobles)
            if "refreshInterval" not in current:
                # Instalacion previa (<= 0.22.0) sin refresco: se agrega. Si el usuario
                # ya puso su propio valor, se respeta. El cambio queda en settings_doc
                # (remove vuelve al texto original byte a byte).
                migrated["refreshInterval"] = REFRESH_INTERVAL_S
                if isinstance(sl_rec, dict):
                    sl_rec["refresh_added"] = True
                msgs.append(f"statusLine: agregado refreshInterval {REFRESH_INTERVAL_S} s.")
            settings.data["statusLine"] = migrated

    pd_rec = strip_panel_mod(settings)
    if pd_rec is not None:
        record["plugin_dirs"] = pd_rec
        msgs.append(
            "Quitado el mod panel-4d local de env.CLAUDE_CODE_PLUGIN_DIRS (remove lo restaura)."
        )

    settings_changed = settings.changed()
    if settings_changed:
        record.setdefault("settings_doc", settings.snapshot())
        if not settings.existed:
            record["settings_created"] = True
    kb_changed = False
    if kb is not None and legacy_kb and isinstance(old_kb, dict):
        if migrate_keybinding(kb):
            record.setdefault("keybindings_doc", kb.snapshot())
            kb_changed = True
            msgs.append(f"Atajo {KEYBINDING_KEY} migrado a /panel (el de 0.22.0 no existia).")
            old_kb["command"] = KEYBINDING_CMD
    if kb is not None and args.keybinding:
        kb_rec = add_keybinding(kb)
        if kb_rec is not None and not kb_rec.pop("preexisting", False):
            record["keybinding"] = {"key": KEYBINDING_KEY, "command": KEYBINDING_CMD, **kb_rec}
            record.setdefault("keybindings_doc", kb.snapshot())
            kb_changed = True
            msgs.append(f"Atajo {KEYBINDING_KEY} -> /panel (contexto {KEYBINDING_CONTEXT}).")

    # .orig.bak: solo los que crea ESTA instalacion quedan anotados (remove borra esos).
    owned = list(owned_before)
    for doc, changed in ((settings, settings_changed), (kb, kb_changed)):
        if doc is not None and changed and doc.path.is_file() and doc.path.name not in owned:
            owned.append(doc.path.name)
    if owned:
        record["orig_backups"] = owned

    record["copy"] = str(copy)
    record["version"] = plugin_version(root)
    record["node"] = nv
    record["pending"] = True  # intencion: si el proceso muere, remove igual revierte

    # 2) Escrituras, cada una con su undo. setup.json va PRIMERO.
    undo: list[tuple[str, Callable[[], None]]] = []
    try:
        save_record(record)
        undo.append((str(record_path()), functools.partial(_restore_record, record_before)))
        if not copy.exists():
            undo.append((str(copy), functools.partial(copy.unlink, missing_ok=True)))
        copy_atomic(src, copy)
        for doc, changed in ((settings, settings_changed), (kb, kb_changed)):
            if doc is None or not changed:
                continue
            orig = orig_backup_path(doc.path)
            if doc.path.name not in owned_before and orig.exists():
                stashed = stash_foreign_orig(doc.path)
                if stashed is not None:
                    undo.append((str(stashed), functools.partial(_unstash, stashed, orig)))
                    msgs.append(f"Respaldo de una instalacion anterior conservado en {stashed}.")
            created = ensure_orig_backup(doc.path)
            if created is not None:
                undo.append((str(created), functools.partial(created.unlink, missing_ok=True)))
            backup(doc.path)
            doc.save()
            undo.append((str(doc.path), functools.partial(_restore_doc, doc)))

        if args.copy_theme:
            theme_src = root / "themes" / THEME_FILE
            dst = theme_dst()
            if not theme_src.is_file():
                msgs.append(f"AVISO: el plugin no trae {theme_src}; no se copia el tema.")
            elif dst.exists() and "theme" not in record:
                msgs.append(f"AVISO: {dst} ya existe; no se pisa.")
            else:
                if not dst.exists():
                    undo.append((str(dst), functools.partial(dst.unlink, missing_ok=True)))
                copy_atomic(theme_src, dst)
                record["theme"] = {"path": str(dst), "sha256": sha256_of(dst)}
                msgs.append(f"Tema copiado a {dst}.")

        record.pop("pending", None)
        save_record(record)
    except (OSError, UnicodeError) as exc:
        failed = _rollback(undo)
        if failed:
            raise SetupError(
                f"setup fallo ({exc}) y no se pudo revertir: {', '.join(failed)}. "
                f"{record_path()} quedo con los valores previos: corre /statusline remove "
                "para volver al original."
            ) from exc
        raise SetupError(
            f"setup fallo ({exc}); se revirtio todo lo escrito, no quedo nada a medias."
        ) from exc

    for msg in msgs:
        print(msg)
    print(f"OK: barra instalada en {copy} (plugin {record['version']}, node {nv}).")
    return EXIT_OK


def _write_reverted(doc: JsonDoc, snap: object, *, delete_if_created: bool) -> None:
    target = revert_target(doc, snap, delete_if_created=delete_if_created)
    backup(doc.path)
    if target is None:
        doc.path.unlink(missing_ok=True)
    else:
        write_user_text(doc.path, target)


def cmd_remove(args: argparse.Namespace) -> int:
    record = load_record()
    if record is None:
        print("No hay instalacion registrada (setup.json): nada que revertir.")
        return EXIT_OK
    settings = load_doc(settings_path())
    kb_rec = record.get("keybinding")
    kb_exists = keybindings_path().exists()
    kb = load_doc(keybindings_path()) if isinstance(kb_rec, dict) and kb_exists else None
    copy = copy_path()  # nunca record["copy"]: setup.json no decide que se borra

    clean = True  # todo volvio a como estaba (sin avisos)
    keep_copy = False  # el statusLine no se revirtio: puede seguir llamando a la copia
    changed = False
    sl = record.get("statusline")
    if isinstance(sl, dict):
        had_key = bool(sl.get("had_key", sl.get("had_previous")))
        previous = sl.get("previous")
        current = settings.data.get("statusLine")
        if points_to_ours(current, copy):
            if had_key:
                settings.data["statusLine"] = previous
            else:
                del settings.data["statusLine"]
            changed = True
        elif ("statusLine" in settings.data) != had_key or current != previous:
            print("AVISO: statusLine cambio desde el setup; no se toca.")
            clean = False
            keep_copy = True
    pd = record.get("plugin_dirs")
    if isinstance(pd, dict):
        result = restore_panel_mod(settings, pd)
        changed = changed or result == "restored"
        clean = clean and result != "conflict"
    if changed:
        created = bool(record.get("settings_created")) and not settings.data
        _write_reverted(settings, record.get("settings_doc"), delete_if_created=created)

    if kb is not None and isinstance(kb_rec, dict):
        result = remove_keybinding(kb, kb_rec)
        clean = clean and result != "conflict"
        if result == "removed":
            created = bool(kb_rec.get("file_created")) and not kb.data.get("bindings")
            _write_reverted(kb, record.get("keybindings_doc"), delete_if_created=created)

    theme = record.get("theme")
    if isinstance(theme, dict):
        tpath = theme_dst()  # nunca theme["path"]: ruta calculada
        if tpath.exists() and sha256_of(tpath) not in (None, theme.get("sha256")):
            print(f"AVISO: {tpath} fue modificado desde el setup; no se borra.")
        else:
            tpath.unlink(missing_ok=True)
    if keep_copy:
        print(f"AVISO: la copia fija {copy} no se borra: el statusLine actual no se revirtio.")
    else:
        copy.unlink(missing_ok=True)
    owned = record.get("orig_backups")
    names = [n for n in owned if n in ORIG_NAMES] if isinstance(owned, list) else []
    origs = [backups_dir() / f"{n}.orig.bak" for n in names]
    if clean:
        for orig in origs:
            try:
                orig.unlink(missing_ok=True)
            except OSError as exc:
                print(f"AVISO: no se pudo borrar {orig} ({exc}).")
    else:
        kept = [str(o) for o in origs if o.exists()]
        if kept:
            print("Se conserva el original de la instalacion: " + ", ".join(kept))
    record_path().unlink(missing_ok=True)
    print("OK: barra de fluency-4d quitada; se restauro lo previo. Reinicia Claude Code.")
    return EXIT_OK


def cmd_status(args: argparse.Namespace) -> int:
    root = plugin_root(args.plugin_root)
    src = root / "statusline" / "statusline.js"
    record_err = None
    try:
        record = load_record()
    except SetupError as exc:
        record, record_err = None, str(exc)
    copy = copy_path()  # nunca record["copy"]
    nv = node_version()
    major = parse_node_major(nv) if nv else None
    if nv is None:
        print("Node: NO encontrado (la barra y el panel lo necesitan)")
    elif major is None or major < MIN_NODE_MAJOR:
        print(f"Node: {nv} (DEMASIADO VIEJO: hace falta >= {MIN_NODE_MAJOR})")
    else:
        print(f"Node: {nv}")
    if record_err:
        print(f"Registro: CORRUPTO ({record_err})")
    else:
        print(f"Registro: {record_path() if record else 'sin setup.json (no instalado)'}")
    if record and record.get("pending"):
        print("Registro: operacion incompleta (setup interrumpido); corre setup o remove.")
    src_ok = src.is_file()
    if not src_ok:
        print(f"Script del plugin: NO encontrado ({src}); revisa la instalacion del plugin.")
    resync = False
    if copy.is_file():
        if src_ok:
            same = sha256_of(copy) == sha256_of(src)
            estado = "sincronizada con el plugin" if same else "DIFIERE del script del plugin"
            resync = not same
        else:
            estado = "no se puede comparar: falta el script del plugin"
        print(f"Copia fija: {copy} ({estado})")
    else:
        print(f"Copia fija: {copy} (ausente)")
    try:
        settings = load_doc(settings_path())
        current = settings.data.get("statusLine")
        if current is None:
            print("statusLine: sin configurar")
        elif points_to_ours(current, copy):
            interval = current.get("refreshInterval")
            if interval is None:
                refresco = "sin refreshInterval: solo con cada mensaje; corre setup"
            else:
                refresco = f"refresco cada {json.dumps(interval, ensure_ascii=True)} s"
            print(f"statusLine: apunta a la copia fija de fluency-4d ({refresco})")
        else:
            print("statusLine: otro comando -> " + json.dumps(current, ensure_ascii=True))
    except SetupError as exc:
        print(f"statusLine: no se pudo leer settings.json ({exc})")
    if record:
        if record.get("plugin_dirs"):
            print("CLAUDE_CODE_PLUGIN_DIRS: mod panel-4d local quitado (remove lo restaura)")
        kb = "registrado" if record.get("keybinding") else "no agregado (--keybinding)"
        print(f"Atajo {KEYBINDING_KEY}: {kb}")
        copied = isinstance(record.get("theme"), dict)
        where = "copiado a " + str(theme_dst()) if copied else "desde el plugin"
        print(f"Tema Templado: {where}")
        plugin_v = plugin_version(root)
        print(f"Version del setup: {record.get('version')} (plugin: {plugin_v})")
        resync = resync or record.get("version") != plugin_v
    if resync and src_ok:
        print("SUGERENCIA: corre /statusline setup de nuevo para re-sincronizar la copia fija.")
    return EXIT_OK


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Barra de estado de fluency-4d")
    sub = parser.add_subparsers(dest="cmd", required=True)
    for name in ("setup", "remove", "status"):
        sp = sub.add_parser(name)
        sp.add_argument("--plugin-root", default=None)
        if name == "setup":
            sp.add_argument("--force", action="store_true", help="reemplaza un statusLine ajeno")
            sp.add_argument("--keybinding", action="store_true", help="agrega ctrl+x ctrl+p")
            sp.add_argument("--copy-theme", action="store_true", help="copia el tema a ~/.claude")
    return parser


def main(argv: list[str] | None = None) -> int:
    reconfigure = getattr(sys.stdout, "reconfigure", None)
    if callable(reconfigure):
        reconfigure(errors="replace")  # rutas con chars fuera de cp1252
    args = build_parser().parse_args(argv)
    handlers = {"setup": cmd_setup, "remove": cmd_remove, "status": cmd_status}
    try:
        if args.cmd == "status":  # solo lectura: sin lock
            return handlers[args.cmd](args)
        with setup_lock():
            return handlers[args.cmd](args)
    except SetupError as exc:
        print(f"ERROR: {exc}")
        return EXIT_ERROR
    except OSError as exc:
        print(f"ERROR de archivo: {exc}")
        return EXIT_ERROR
    except UnicodeError as exc:
        print(f"ERROR: texto no codificable en UTF-8 ({exc}); no quedo nada a medias.")
        return EXIT_ERROR


if __name__ == "__main__":
    sys.exit(main())
