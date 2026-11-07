#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""fluency_hooks - shim de hooks Google Antigravity para fluency-4d.

Generado por tools/multiharness/build_harness.py. NO editar a mano.

Proposito: PUENTEAR (no reescribir) los hooks Python canonicos de
fluency-4d al contrato de hooks de Google Antigravity:
  - PreInvocation (cuando invocationNum == 0, inicio del turno del
    usuario) -> ejecuta los hooks de UserPromptSubmit y traduce
    hookSpecificOutput.additionalContext a
    {"injectSteps": [{"ephemeralMessage": "..."}]}.
  - Stop -> ejecuta discernment_gate y traduce
    {"decision": "block", "reason": "..."} a
    {"decision": "continue", "reason": "..."}.

Ante cualquier error el shim degrada a NO-OP ({}) y nunca rompe la sesion.
ASCII puro (regla de CLAUDE.md).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from typing import Any

HOOK_TIMEOUT_S = 5

USER_PROMPT_HOOKS: tuple[str, ...] = (
    "C:\\Users\\espin\\OneDrive\\Desktop\\sentinelas_antigravity\\isolated_study\\4Dsentinel-suite\\plugins\\fluency-4d\\hooks\\bridge_router.py",
    "C:\\Users\\espin\\OneDrive\\Desktop\\sentinelas_antigravity\\isolated_study\\4Dsentinel-suite\\plugins\\fluency-4d\\hooks\\plan_calibrator.py",
    "C:\\Users\\espin\\OneDrive\\Desktop\\sentinelas_antigravity\\isolated_study\\4Dsentinel-suite\\plugins\\fluency-4d\\hooks\\caveman_injector.py",
    "C:\\Users\\espin\\OneDrive\\Desktop\\sentinelas_antigravity\\isolated_study\\4Dsentinel-suite\\plugins\\fluency-4d\\hooks\\adhd_injector.py",
    "C:\\Users\\espin\\OneDrive\\Desktop\\sentinelas_antigravity\\isolated_study\\4Dsentinel-suite\\plugins\\fluency-4d\\hooks\\suite_playbook.py",
)

STOP_HOOKS: tuple[str, ...] = (
    "C:\\Users\\espin\\OneDrive\\Desktop\\sentinelas_antigravity\\isolated_study\\4Dsentinel-suite\\plugins\\fluency-4d\\hooks\\discernment_gate.py",
)


def _read_stdin() -> dict[str, Any]:
    try:
        raw = sys.stdin.buffer.read().decode("utf-8", errors="replace").strip()
        if not raw:
            return {}
        data = json.loads(raw)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _to_claude_payload(data: dict[str, Any], event_name: str) -> dict[str, Any]:
    ws = data.get("workspacePaths")
    cwd = (
        ws[0]
        if isinstance(ws, list) and ws and isinstance(ws[0], str)
        else ""
    )
    return {
        "session_id": str(data.get("conversationId") or ""),
        "hook_event_name": event_name,
        "cwd": cwd or os.getcwd(),
        "transcript_path": str(data.get("transcriptPath") or ""),
        "prompt": str(data.get("lastUserInput") or ""),
    }


def _run_hook(script_path: str, payload: dict[str, Any]) -> dict[str, Any]:
    try:
        res = subprocess.run(
            [sys.executable, script_path],
            input=json.dumps(payload, ensure_ascii=False),
            text=True,
            encoding="utf-8",
            capture_output=True,
            env={**os.environ, "PYTHONUTF8": "1"},
            timeout=HOOK_TIMEOUT_S,
            check=False,
        )
        if res.returncode != 0 or not res.stdout.strip():
            return {}
        out = json.loads(res.stdout)
        return out if isinstance(out, dict) else {}
    except Exception:
        return {}


def _handle_pre_invocation(data: dict[str, Any]) -> dict[str, Any]:
    inv = data.get("invocationNum", 0)
    try:
        if int(inv or 0) > 0:
            return {}
    except (TypeError, ValueError):
        pass
    payload = _to_claude_payload(data, "UserPromptSubmit")
    chunks: list[str] = []
    for script in USER_PROMPT_HOOKS:
        out = _run_hook(script, payload)
        spec = out.get("hookSpecificOutput")
        if isinstance(spec, dict):
            ctx = spec.get("additionalContext")
            if isinstance(ctx, str) and ctx.strip():
                chunks.append(ctx)
    if not chunks:
        return {}
    return {"injectSteps": [{"ephemeralMessage": "\n\n".join(chunks)}]}


def _handle_stop(data: dict[str, Any]) -> dict[str, Any]:
    payload = _to_claude_payload(data, "Stop")
    for script in STOP_HOOKS:
        out = _run_hook(script, payload)
        if out.get("decision") == "block" and out.get("reason"):
            return {
                "decision": "continue",
                "reason": str(out["reason"]),
            }
    return {}


def main() -> int:
    try:
        event = sys.argv[1] if len(sys.argv) > 1 else "PreInvocation"
        data = _read_stdin()
        if event == "PreInvocation":
            res = _handle_pre_invocation(data)
        elif event == "Stop":
            res = _handle_stop(data)
        else:
            res = {}
        sys.stdout.write(json.dumps(res, ensure_ascii=True) + "\n")
    except Exception:
        sys.stdout.write("{}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
