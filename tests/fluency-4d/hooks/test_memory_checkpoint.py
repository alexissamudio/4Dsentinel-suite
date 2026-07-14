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
    # Cadencia absoluta por defecto: 120k tokens (DEFAULT_CHECKPOINT_INTERVAL_TOKENS).
    t = make_transcript(tmp_path, 92_000)  # 23k tok < 120k
    assert run_hook(HOOK, fb(project, t, "f1")) == ""
    t = make_transcript(tmp_path, 520_000)  # 130k >= 120k -> dispara
    assert "estado-sesion.md" in run_hook(HOOK, fb(project, t, "f1"))
    t = make_transcript(tmp_path, 600_000)  # 150k < 250k -> vacio
    assert run_hook(HOOK, fb(project, t, "f1")) == ""
    t = make_transcript(tmp_path, 1_040_000)  # 260k >= 250k -> re-dispara
    assert "estado-sesion.md" in run_hook(HOOK, fb(project, t, "f1"))
    assert state_of("f1", "-ckpt")["disparos"] == 2
    t = make_transcript(tmp_path, 40_000)  # se achico: re-ancla
    assert run_hook(HOOK, fb(project, t, "f1")) == ""
    t = make_transcript(tmp_path, 520_000)  # vuelve a crecer -> dispara
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
    t = make_transcript(tmp_path, 520_000)  # 130k tok >= 120k -> dispara (fallback)
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
    # SAVE_PCT basura NO desactiva (cae a 50, > 0): en fallback igual dispara al
    # cruzar la cadencia absoluta por defecto (120k tokens).
    t = make_transcript(tmp_path, 520_000)  # 130k tok >= 120k
    out = run_hook(HOOK, fb(project, t, "g5"), env_extra={"FLUENCY_4D_SAVE_PCT": "abc"})
    assert "estado-sesion.md" in out


def test_save_pct_inf_cae_a_default(run_hook, project, tmp_path):
    # OverflowError: float("inf") tiene exito pero int(inf) revienta. Antes escapaba
    # el except (TypeError, ValueError) -> subia a hook_main -> pass-through cada
    # corrida -> checkpoint DESACTIVADO. Ahora cae a DEFAULT (50, > 0) y en fallback
    # dispara al cruzar la cadencia por defecto (120k tok).
    t = make_transcript(tmp_path, 520_000)  # 130k tok >= 120k
    for i, val in enumerate(("inf", "1e999", "-inf")):
        out = run_hook(
            HOOK, fb(project, t, f"inf{i}"), env_extra={"FLUENCY_4D_SAVE_PCT": val}
        )
        assert "estado-sesion.md" in out, val


def test_intervalo_configurable(run_hook, project, tmp_path):
    # FLUENCY_4D_CHECKPOINT_EVERY_TOKENS gobierna cuando dispara el fallback,
    # INDEPENDIENTE de la ventana de contexto (que el host no expone al hook).
    env = {"FLUENCY_4D_CHECKPOINT_EVERY_TOKENS": "500000"}
    t = make_transcript(tmp_path, 420_000)  # 105k tok < 500k -> NO dispara
    assert run_hook(HOOK, fb(project, t, "c1"), env_extra=env) == ""
    t = make_transcript(tmp_path, 2_400_000)  # 600k tok >= 500k -> dispara
    assert "estado-sesion.md" in run_hook(HOOK, fb(project, t, "c1"), env_extra=env)


def test_intervalo_invalido_cae_a_default(run_hook, project, tmp_path):
    # Un valor no-entero o <= 0 usa el default 120k: 130k dispara.
    t = make_transcript(tmp_path, 520_000)  # 130k tok >= 120k
    assert "estado-sesion.md" in run_hook(
        HOOK, fb(project, t, "c2"), env_extra={"FLUENCY_4D_CHECKPOINT_EVERY_TOKENS": "mil"}
    )
    assert "estado-sesion.md" in run_hook(
        HOOK, fb(project, t, "c3"), env_extra={"FLUENCY_4D_CHECKPOINT_EVERY_TOKENS": "0"}
    )
