"""Congela el comportamiento del bridge_router: arranque, puentes, dedup y
el bloque de emision/persistencia unico."""

from __future__ import annotations

import os
import time

from conftest import write_bridges

HOOK = "bridge_router.py"


def payload(project, session, prompt="hola que tal"):
    return {"prompt": prompt, "cwd": str(project), "session_id": session}


def test_arranque_lecciones_sin_bridges(run_hook, project, state_of):
    (project / ".claude" / "docs" / "lecciones.md").write_text("# L", encoding="utf-8")
    out = run_hook(HOOK, payload(project, "s1"))
    assert "lecciones.md" in out
    assert state_of("s1")["arranque_inyectado"] is True


def test_arranque_con_bridges_sin_keyword(run_hook, project):
    write_bridges(project)
    (project / ".claude" / "docs" / "lecciones.md").write_text("# L", encoding="utf-8")
    out = run_hook(HOOK, payload(project, "s2", "hola, arranquemos"))
    assert "lecciones.md" in out  # los early-returns de temas no se la tragan


def test_dedup_arranque_y_tema(run_hook, project):
    write_bridges(project)
    (project / ".claude" / "docs" / "lecciones.md").write_text("# L", encoding="utf-8")
    first = run_hook(HOOK, payload(project, "s3"))
    assert "lecciones.md" in first
    second = run_hook(HOOK, payload(project, "s3", "como funciona el login?"))
    assert "lecciones.md" not in second and "auth.md" in second
    third = run_hook(HOOK, payload(project, "s3", "gracias"))
    assert third == ""


def test_estado_sesion_viejo_avisa_edad(run_hook, project):
    estado = project / ".claude" / "docs" / "estado-sesion.md"
    estado.write_text("# viejo", encoding="utf-8")
    old = time.time() - 3 * 86400
    os.utime(estado, (old, old))
    out = run_hook(HOOK, payload(project, "s4"))
    assert "sesion anterior" in out and "dia" in out


def test_sin_archivos_vacio_pero_marca_estado(run_hook, project, state_of):
    out = run_hook(HOOK, payload(project, "s5"))
    assert out == ""
    assert state_of("s5")["arranque_inyectado"] is True


def test_keyword_con_acentos_normaliza(run_hook, project):
    write_bridges(project)
    out = run_hook(HOOK, payload(project, "s6", "¿cómo funciona la autenticación acá?"))
    assert "auth.md" in out


def test_subagente_no_inyecta(run_hook, project, state_of):
    write_bridges(project)
    (project / ".claude" / "docs" / "lecciones.md").write_text("# L", encoding="utf-8")
    data = payload(project, "s7", "login")
    data["agent_type"] = "Explore"
    assert run_hook(HOOK, data) == ""
    assert state_of("s7") is None


def test_arranque_y_tema_combinados_trailer_una_vez(run_hook, project):
    write_bridges(project)
    (project / ".claude" / "docs" / "lecciones.md").write_text("# L", encoding="utf-8")
    out = run_hook(HOOK, payload(project, "s8", "revisá el login"))
    assert "lecciones.md" in out and "auth.md" in out
    assert out.count("(inyectado por fluency-4d") == 1


def test_cap_dos_temas_por_prompt(run_hook, project):
    write_bridges(project)
    out = run_hook(
        HOOK, payload(project, "s9", "login, endpoints y migraciones de database")
    )
    assert out.count("Este proyecto documenta") == 2


def test_bridges_malformado_no_rompe(run_hook, project):
    write_bridges(project, data="{esto no es json")
    (project / ".claude" / "docs" / "lecciones.md").write_text("# L", encoding="utf-8")
    out = run_hook(HOOK, payload(project, "s10", "login"))
    assert "lecciones.md" in out  # el arranque sobrevive al JSON roto
