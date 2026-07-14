"""Congela el edge-trigger del plan_calibrator: dispara solo al ENTRAR en plan
mode, se re-arma al salir y volver a entrar, se calla dentro del episodio."""

from __future__ import annotations

HOOK = "plan_calibrator.py"


def p(session, mode, prompt="hola"):
    return {"prompt": prompt, "cwd": "x", "session_id": session, "permission_mode": mode}


def test_no_plan_vacio(run_hook):
    assert run_hook(HOOK, p("s1", "default")) == ""


def test_entrada_a_plan_inyecta(run_hook):
    run_hook(HOOK, p("s2", "default"))
    out = run_hook(HOOK, p("s2", "plan"))
    assert "GRANDE" in out and "CHICA" in out and "sentinel-agents" in out


def test_dedup_dentro_del_episodio(run_hook):
    run_hook(HOOK, p("s3", "default"))
    assert run_hook(HOOK, p("s3", "plan")) != ""
    assert run_hook(HOOK, p("s3", "plan")) == ""  # 2do prompt del mismo episodio


def test_rearm_al_reentrar(run_hook):
    run_hook(HOOK, p("s4", "default"))
    assert run_hook(HOOK, p("s4", "plan")) != ""  # entra
    assert run_hook(HOOK, p("s4", "default")) == ""  # sale
    assert run_hook(HOOK, p("s4", "plan")) != ""  # re-entra → dispara de nuevo


def test_arranca_directo_en_plan(run_hook):
    # prev ausente (primer prompt de la sesión ya en plan) → inyecta
    assert run_hook(HOOK, p("s5", "plan")) != ""


def test_subagente_no_inyecta(run_hook):
    data = p("s6", "plan")
    data["agent_type"] = "Explore"
    assert run_hook(HOOK, data) == ""
