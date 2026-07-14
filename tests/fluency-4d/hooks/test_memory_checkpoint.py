"""Congela la maquina de estados del checkpoint: intervalo en fallback,
caida en nativo, migracion v0.2 y guardas."""

from __future__ import annotations

HOOK = "memory_checkpoint.py"


def fb(project, transcript, session):
    return {
        "cwd": str(project),
        "session_id": session,
        "permission_mode": "default",
        "transcript_path": str(transcript),
    }


def nat(project, pct, session):
    return {
        "cwd": str(project),
        "session_id": session,
        "permission_mode": "default",
        "context_window": {"used_percentage": pct},
    }


def make_transcript(tmp_path, size_bytes):
    t = tmp_path / "tr.jsonl"
    t.write_bytes(b"x" * size_bytes)
    return t


def test_fallback_intervalo_y_reset(run_hook, project, state_of, tmp_path):
    t = make_transcript(tmp_path, 92_000)  # 23k tok < 100k
    assert run_hook(HOOK, fb(project, t, "f1")) == ""
    t = make_transcript(tmp_path, 420_000)  # 105k >= 100k -> dispara
    assert "estado-sesion.md" in run_hook(HOOK, fb(project, t, "f1"))
    t = make_transcript(tmp_path, 460_000)  # 115k < 205k -> vacio
    assert run_hook(HOOK, fb(project, t, "f1")) == ""
    t = make_transcript(tmp_path, 840_000)  # 210k >= 205k -> re-dispara
    assert "estado-sesion.md" in run_hook(HOOK, fb(project, t, "f1"))
    assert state_of("f1", "-ckpt")["disparos"] == 2
    t = make_transcript(tmp_path, 40_000)  # se achico: re-ancla
    assert run_hook(HOOK, fb(project, t, "f1")) == ""
    t = make_transcript(tmp_path, 420_000)  # vuelve a crecer -> dispara
    assert "estado-sesion.md" in run_hook(HOOK, fb(project, t, "f1"))
    assert state_of("f1", "-ckpt")["disparos"] == 3


def test_nativo_caida_re_arma(run_hook, project, state_of):
    assert "estado-sesion.md" in run_hook(HOOK, nat(project, 55, "n1"))
    assert run_hook(HOOK, nat(project, 58, "n1")) == ""
    assert run_hook(HOOK, nat(project, 30, "n1")) == ""  # caida >20: re-arma
    assert "estado-sesion.md" in run_hook(HOOK, nat(project, 55, "n1"))
    assert state_of("n1", "-ckpt")["disparos"] == 2


def test_migracion_v02_no_duplica_disparo(run_hook, project, tmp_path, state_of):
    import hashlib
    import json
    import time

    key = "sid-" + hashlib.sha256(b"m1").hexdigest()[:16] + "-ckpt"
    d = tmp_path / "fluency4d"
    d.mkdir(exist_ok=True)
    (d / f"{key}.json").write_text(
        json.dumps({"checkpoint_disparado": True, "_ts": time.time()}), encoding="utf-8"
    )
    t = make_transcript(tmp_path, 420_000)
    assert run_hook(HOOK, fb(project, t, "m1")) == ""
    assert state_of("m1", "-ckpt")["last_fired_tokens"] == 105_000.0


def test_guardas(run_hook, project, tmp_path, state_of):
    t = make_transcript(tmp_path, 420_000)
    agent = fb(project, t, "g1")
    agent["agent_type"] = "Explore"
    assert run_hook(HOOK, agent) == ""

    plan = fb(project, t, "g2")
    plan["permission_mode"] = "plan"
    assert run_hook(HOOK, plan) == ""
    assert state_of("g2", "-ckpt") is None  # plan mode NO marca estado
    assert "estado-sesion.md" in run_hook(HOOK, fb(project, t, "g2"))

    assert run_hook(HOOK, fb(project, t, "g3"), env_extra={"FLUENCY_4D_SAVE_PCT": "0"}) == ""

    sin_claude = {**fb(project, t, "g4"), "cwd": str(tmp_path)}
    assert run_hook(HOOK, sin_claude) == ""


def test_env_basura_cae_a_50(run_hook, project, tmp_path):
    t = make_transcript(tmp_path, 420_000)  # 105k tok = 52.5% > 50
    out = run_hook(HOOK, fb(project, t, "g5"), env_extra={"FLUENCY_4D_SAVE_PCT": "abc"})
    assert "estado-sesion.md" in out
