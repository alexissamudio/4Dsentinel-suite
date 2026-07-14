"""Verifica el nudge de suite_playbook: frases ESTRECHAS disparan el nudge
correcto, dedup una vez por tipo por sesion, self-silence en subagentes y en
plan mode, y salida ASCII pura."""

from __future__ import annotations

HOOK = "suite_playbook.py"


def p(session, prompt, mode="default"):
    return {"prompt": prompt, "cwd": "x", "session_id": session, "permission_mode": mode}


def test_indexar_dispara_nudge(run_hook):
    out = run_hook(HOOK, p("i1", "quiero entender este repo desde cero"))
    assert "/indexar" in out and "/arquitectura" in out


def test_auditar_dispara_nudge(run_hook):
    out = run_hook(HOOK, p("a1", "voy a mergear esto a main"))
    low = out.lower()
    assert "auditar" in low and "opt-in" in low


def test_sin_keyword_estrecha_vacio(run_hook):
    # "revisar"/"antes de" solas NO alcanzan: las frases son estrechas.
    assert run_hook(HOOK, p("n1", "podes revisar antes de seguir?")) == ""


def test_dedup_una_vez_por_tipo(run_hook):
    assert run_hook(HOOK, p("d1", "ayudame a mapear el codebase")) != ""
    # 2do prompt del mismo tipo en la misma sesion: no repite.
    assert run_hook(HOOK, p("d1", "de nuevo, mapear el codebase")) == ""


def test_dedup_no_bloquea_otro_tipo(run_hook):
    assert run_hook(HOOK, p("d2", "mapear el codebase")) != ""  # indexar
    assert run_hook(HOOK, p("d2", "voy a mergear esto")) != ""  # auditar, otro tipo


def test_subagente_no_inyecta(run_hook):
    data = p("s1", "voy a mergear esto")
    data["agent_type"] = "Explore"
    assert run_hook(HOOK, data) == ""


def test_plan_mode_no_inyecta(run_hook):
    assert run_hook(HOOK, p("pm1", "voy a mergear esto", mode="plan")) == ""


def test_output_es_ascii_puro(run_hook):
    out = run_hook(HOOK, p("x1", "voy a mergear esto"))
    assert out != ""
    assert out == out.encode("ascii", "ignore").decode("ascii")
