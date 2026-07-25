"""Congela las 4 ramas del gate de discernimiento (opt-in)."""

from __future__ import annotations

import json

HOOK = "discernment_gate.py"
STRICT = {"FLUENCY_4D_STRICT": "1"}


def payload(session, **extra):
    return {"session_id": session, "cwd": "x", **extra}


def _enable_verify(tmp_path):
    """Prende el flag verify.json en el HOME aislado que usa run_hook.

    run_hook fija HOME/USERPROFILE a tmp_path/home; load_verify() lee de
    ~/.claude/fluency4d/verify.json -> tmp_path/home/.claude/fluency4d/verify.json.
    """
    flag = tmp_path / "home" / ".claude" / "fluency4d" / "verify.json"
    flag.parent.mkdir(parents=True, exist_ok=True)
    flag.write_text(json.dumps({"on": True}), encoding="utf-8")


def test_sin_env_var_vacio(run_hook):
    assert run_hook(HOOK, payload("q1")) == ""


def test_flag_off_por_default_vacio(run_hook, tmp_path):
    # Sin env var y sin verify.json escrito -> gate apagado (pass-through).
    assert run_hook(HOOK, payload("q1b")) == ""


def test_flag_verify_bloquea_una_vez(run_hook, tmp_path):
    _enable_verify(tmp_path)
    first = run_hook(HOOK, payload("v1"))
    assert '"decision": "block"' in first
    assert "DISCERNIMIENTO" in first
    # el mensaje nuevo ordena la verificacion del diff
    assert "diff" in first and "VERIFICACION DEL DIFF" in first
    # segundo Stop en la misma sesion -> ya no bloquea
    assert run_hook(HOOK, payload("v1")) == ""


def test_flag_verify_respeta_stop_hook_active(run_hook, tmp_path):
    _enable_verify(tmp_path)
    assert run_hook(HOOK, payload("v2", stop_hook_active=True)) == ""


def test_flag_verify_respeta_agent_type(run_hook, tmp_path):
    _enable_verify(tmp_path)
    assert run_hook(HOOK, payload("v3", agent_type="Explore")) == ""


def test_strict_bloquea_una_vez(run_hook):
    first = run_hook(HOOK, payload("q2"), env_extra=STRICT)
    assert '"decision": "block"' in first and "DISCERNIMIENTO" in first
    assert run_hook(HOOK, payload("q2"), env_extra=STRICT) == ""


def test_stop_hook_active_no_bloquea(run_hook):
    assert run_hook(HOOK, payload("q3", stop_hook_active=True), env_extra=STRICT) == ""


def test_subagente_no_bloquea(run_hook):
    assert run_hook(HOOK, payload("q4", agent_type="Explore"), env_extra=STRICT) == ""


def test_estado_usa_sufijo_gate(run_hook, state_of):
    # MINOR #4: el gate escribe su estado con sufijo -gate, aislado de la key
    # pelada que compartia con el resto de los hooks.
    run_hook(HOOK, payload("q5"), env_extra=STRICT)
    assert state_of("q5", "-gate")["gate_bloqueado"] is True
    assert state_of("q5") is None  # nada en la key pelada
