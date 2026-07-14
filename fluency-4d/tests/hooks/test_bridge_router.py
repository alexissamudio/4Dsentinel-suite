"""Congela el comportamiento del bridge_router: arranque, puentes, dedup y
el bloque de emision/persistencia unico."""

from __future__ import annotations

import json as _json
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


# --- Relaciones entre puentes (v0.11) ----------------------------------------

BRIDGES_REL = {
    "version": 1,
    "temas": [
        {
            "tema": "testing",
            "archivo": ".claude/docs/testing.md",
            "keywords": ["pytest", "testing"],
            "relaciones": [{"verbo": "alimenta_a", "tema": "release"}],
        },
        {
            "tema": "release",
            "archivo": ".claude/docs/release.md",
            "keywords": ["release", "deploy"],
        },
    ],
}


def test_relacion_sugiere_destino_con_archivo(run_hook, project):
    write_bridges(project, data=BRIDGES_REL)
    out = run_hook(HOOK, payload(project, "r1", "corramos pytest"))
    assert "Este proyecto documenta 'testing'" in out
    assert "Tema relacionado: 'testing' alimenta a 'release'" in out
    assert ".claude/docs/release.md" in out


def test_relacion_no_marca_destino_como_inyectado(run_hook, project, state_of):
    write_bridges(project, data=BRIDGES_REL)
    run_hook(HOOK, payload(project, "r2", "corramos pytest"))
    inyectados = state_of("r2")["temas_inyectados"]
    assert "testing" in inyectados
    assert "release" not in inyectados  # la sugerencia no consume el cap ni el state


def test_relacion_dedup_si_destino_ya_es_hit_directo(run_hook, project):
    write_bridges(project, data=BRIDGES_REL)
    # el prompt matchea testing (fuente) y release (destino) directamente
    out = run_hook(HOOK, payload(project, "r3", "pytest antes del release"))
    assert out.count("Este proyecto documenta") == 2
    assert "Tema relacionado" not in out  # release ya fue hit directo -> no se sugiere


def test_relacion_dangling_no_crashea(run_hook, project):
    dangling = {
        "version": 1,
        "temas": [
            {
                "tema": "solo",
                "archivo": ".claude/docs/solo.md",
                "keywords": ["solo"],
                "relaciones": [{"verbo": "depende_de", "tema": "fantasma"}],
            }
        ],
    }
    write_bridges(project, data=dangling)
    out = run_hook(HOOK, payload(project, "r4", "trabajo solo hoy"))
    assert "Este proyecto documenta 'solo'" in out
    assert "Tema relacionado" not in out  # destino inexistente -> skip silencioso


def test_relacion_verbo_desconocido_frase_neutra(run_hook, project):
    data = {
        "version": 1,
        "temas": [
            {
                "tema": "testing",
                "archivo": ".claude/docs/testing.md",
                "keywords": ["pytest"],
                "relaciones": [{"verbo": "verbo_raro", "tema": "release"}],
            },
            {"tema": "release", "archivo": ".claude/docs/release.md", "keywords": ["release"]},
        ],
    }
    write_bridges(project, data=data)
    out = run_hook(HOOK, payload(project, "r5", "corramos pytest"))
    assert "se relaciona con" in out


def test_relacion_tope_uno_por_prompt(run_hook, project):
    data = {
        "version": 1,
        "temas": [
            {
                "tema": "multi",
                "archivo": ".claude/docs/multi.md",
                "keywords": ["multi"],
                "relaciones": [
                    {"verbo": "va_con", "tema": "uno"},
                    {"verbo": "va_con", "tema": "dos"},
                ],
            },
            {"tema": "uno", "archivo": ".claude/docs/uno.md", "keywords": ["uno"]},
            {"tema": "dos", "archivo": ".claude/docs/dos.md", "keywords": ["dos"]},
        ],
    }
    write_bridges(project, data=data)
    out = run_hook(HOOK, payload(project, "r6", "esto es multi"))
    assert out.count("Tema relacionado") == 1  # tope MAX_RELACIONADOS


def test_relacion_malformada_no_rompe_inyeccion(run_hook, project):
    data = {
        "version": 1,
        "temas": [
            {
                "tema": "testing",
                "archivo": ".claude/docs/testing.md",
                "keywords": ["pytest"],
                "relaciones": "esto no es una lista",
            }
        ],
    }
    write_bridges(project, data=data)
    out = run_hook(HOOK, payload(project, "r7", "corramos pytest"))
    assert "Este proyecto documenta 'testing'" in out  # la inyeccion directa sobrevive
    assert "Tema relacionado" not in out


def test_bridges_reales_integridad_referencial():
    from conftest import REPO_ROOT

    data = _json.loads(
        (REPO_ROOT / ".claude" / "docs" / "bridges.json").read_text(encoding="utf-8")
    )
    temas = {t["tema"] for t in data["temas"]}
    for t in data["temas"]:
        for rel in t.get("relaciones", []):
            assert rel["tema"] in temas, (
                f"relacion dangling en bridges.json: {t['tema']} -> {rel['tema']}"
            )


# --- C2: keywords con puntuacion al borde (c++, .net, c#) --------------------


def _bridges_kw(tema, archivo, *keywords):
    return {"version": 1, "temas": [{"tema": tema, "archivo": archivo, "keywords": list(keywords)}]}


def test_keyword_cpp_matchea(run_hook, project):
    write_bridges(project, data=_bridges_kw("cpp", ".claude/docs/cpp.md", "c++"))
    out = run_hook(HOOK, payload(project, "kp1", "estoy programando en c++ hoy"))
    assert "cpp.md" in out  # \\b nunca casaba c++; los lookarounds si


def test_keyword_dotnet_matchea(run_hook, project):
    write_bridges(project, data=_bridges_kw("dotnet", ".claude/docs/dotnet.md", ".net"))
    out = run_hook(HOOK, payload(project, "kp2", "migramos el backend a .net core"))
    assert "dotnet.md" in out


def test_keyword_csharp_matchea(run_hook, project):
    # c# tiene 2 chars: el piso de longitud NO aplica a keywords con puntuacion.
    write_bridges(project, data=_bridges_kw("csharp", ".claude/docs/csharp.md", "c#"))
    out = run_hook(HOOK, payload(project, "kp3", "prefiero c# antes que java"))
    assert "csharp.md" in out


def test_keyword_no_matchea_como_subcadena(run_hook, project):
    # 'auth' NO debe dispararse dentro de 'authenticate' (lookaround = borde).
    write_bridges(project)  # BRIDGES_AUTH: keyword 'auth'
    out = run_hook(HOOK, payload(project, "kp4", "please authenticate the request"))
    assert out == ""  # ninguna keyword de auth aparece como palabra completa


# --- Metricas (v0.4) ---------------------------------------------------------


def stats_de(tmp_path, project):
    path = tmp_path / "home" / ".claude" / "fluency4d" / "stats.json"
    if not path.is_file():
        return None
    stats = _json.loads(path.read_text(encoding="utf-8"))
    from pathlib import Path as _P

    return stats.get(str(_P(str(project)).resolve()).casefold())


def test_stats_cuenta_sesion_aunque_no_inyecte(run_hook, project, tmp_path):
    run_hook(HOOK, payload(project, "m1"))  # sin archivos: salida vacia
    entry = stats_de(tmp_path, project)
    assert entry["sesiones"] == 1 and entry["temas"] == {}


def test_stats_cuenta_tema_y_segunda_sesion(run_hook, project, tmp_path):
    write_bridges(project)
    run_hook(HOOK, payload(project, "m2", "como anda el login?"))
    run_hook(HOOK, payload(project, "m3", "mas login por favor"))  # otra sesion
    entry = stats_de(tmp_path, project)
    assert entry["sesiones"] == 2
    assert entry["temas"]["auth"]["inyecciones"] == 2


def test_stats_ilegible_no_rompe_la_inyeccion(run_hook, project, tmp_path):
    # stats.json como DIRECTORIO: toda escritura falla -> degradacion silenciosa
    (tmp_path / "home" / ".claude" / "fluency4d" / "stats.json").mkdir(parents=True)
    write_bridges(project)
    out = run_hook(HOOK, payload(project, "m4", "login"))
    assert "auth.md" in out  # la inyeccion sale igual


def test_stats_poda_entradas_viejas(run_hook, project, tmp_path):
    import time

    stats_path = tmp_path / "home" / ".claude" / "fluency4d" / "stats.json"
    stats_path.parent.mkdir(parents=True)
    viejo = {"sesiones": 9, "temas": {}, "_ts": time.time() - 91 * 86400}
    stats_path.write_text(_json.dumps({"c:\\proyecto\\muerto": viejo}), encoding="utf-8")
    run_hook(HOOK, payload(project, "m5"))
    todo = _json.loads(stats_path.read_text(encoding="utf-8"))
    assert "c:\\proyecto\\muerto" not in todo and len(todo) == 1
