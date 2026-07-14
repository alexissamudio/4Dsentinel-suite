"""Congela el matching por segmento y las guardas de doc_drift."""

from __future__ import annotations

import os

from conftest import write_bridges

HOOK = "doc_drift.py"


def payload(project, session, file_path=None, notebook_path=None):
    tool_input = {}
    if file_path is not None:
        tool_input["file_path"] = file_path
    if notebook_path is not None:
        tool_input["notebook_path"] = notebook_path
    return {"cwd": str(project), "session_id": session, "tool_input": tool_input}


def win(project, rel):
    """Path absoluto en estilo nativo: backslashes SOLO en Windows (en Linux
    el backslash no es separador y el caso mixto no existe fuera de NTFS)."""
    p = str(project / rel)
    return p.replace("/", "\\") if os.name == "nt" else p


def test_backslash_absoluto_case_insensitive(run_hook, project, state_of):
    write_bridges(project)
    out = run_hook(HOOK, payload(project, "d1", file_path=win(project, "src/Auth/login.py")))
    assert "auth" in out and "auth.md" in out
    assert state_of("d1", "-drift")["temas_avisados"] == ["auth"]


def test_segmento_parcial_no_matchea(run_hook, project):
    write_bridges(project)
    out = run_hook(
        HOOK, payload(project, "d2", file_path=win(project, "src/authentication/x.py"))
    )
    assert out == ""


def test_fuera_del_proyecto(run_hook, project, tmp_path):
    write_bridges(project)
    otro = tmp_path / "otro" / "src" / "auth" / "x.py"
    assert run_hook(HOOK, payload(project, "d3", file_path=str(otro))) == ""


def test_bajo_claude_excluido(run_hook, project):
    write_bridges(project)
    out = run_hook(HOOK, payload(project, "d4", file_path=win(project, ".claude/docs/auth.md")))
    assert out == ""


def test_dedup_por_tema(run_hook, project):
    write_bridges(project)
    assert run_hook(HOOK, payload(project, "d5", file_path=win(project, "src/auth/a.py"))) != ""
    assert run_hook(HOOK, payload(project, "d5", file_path=win(project, "src/auth/b.py"))) == ""


def test_notebook_path(run_hook, project):
    write_bridges(project)
    out = run_hook(
        HOOK, payload(project, "d6", notebook_path=win(project, "src/auth/analisis.ipynb"))
    )
    assert "auth" in out


def test_tema_sin_rutas_no_trackea(run_hook, project):
    write_bridges(project)
    out = run_hook(HOOK, payload(project, "d7", file_path=win(project, "api/endpoints.py")))
    assert out == ""
