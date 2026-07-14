"""Congela las 4 ramas del gate de discernimiento (opt-in)."""

from __future__ import annotations

HOOK = "discernment_gate.py"
STRICT = {"FLUENCY_4D_STRICT": "1"}


def payload(session, **extra):
    return {"session_id": session, "cwd": "x", **extra}


def test_sin_env_var_vacio(run_hook):
    assert run_hook(HOOK, payload("q1")) == ""


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
