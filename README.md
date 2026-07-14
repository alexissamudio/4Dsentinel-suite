# 4Dsentinel-suite

Monorepo que unifica en **un solo install** el ecosistema propio de Claude Code:

| Plugin | Qué trae |
|--------|----------|
| **fluency-4d** | Marco 4D de AI Fluency (`/4d`, `/4d-init`, `/4d-status`, `/4d-quiz`) + CLAUDE.md modular con puentes + hooks (incl. `plan_calibrator`) |
| **sentinel-agents** | 11 agentes de auditoría (security, compliance ISO 27000, advisor, critic, code-reviewer, risk-assessor, bug-hunter, debugger, librarian, validator, y `auditor-de-redaccion` —calidad de redacción de specs/docs, domain-agnostic, read-only—) + `/sentinel-audit` |
| **4dsentinel-memory** | Cablea `codebase-memory-mcp` (grafo de codebase, ~99% menos tokens en repos grandes) vía `mcpServers`; `/suite-setup` instala el binario |

Layout unificado y plano: cada plugin vive en `plugins/<nombre>/`, sus tests en
`tests/<nombre>/`, y los scripts de desarrollo (con prefijo por plugin ante colisiones)
en `scripts/`. Docs por plugin: [`docs/fluency-4d.md`](docs/fluency-4d.md) y
[`docs/sentinel-agents.md`](docs/sentinel-agents.md).

## Instalar
```
claude plugin marketplace add alexissamudio/4Dsentinel-suite
claude plugin install fluency-4d@4Dsentinel-suite
claude plugin install sentinel-agents@4Dsentinel-suite
claude plugin install 4dsentinel-memory@4Dsentinel-suite   # luego: /suite-setup + reiniciar
```

## Notas
- No hay batch install: un `marketplace add` + un `install` por plugin.
- El binario de codebase-memory-mcp NO se vendoriza (externo); `/suite-setup` lo baja firmado.
- Los agentes de plugin no ven `mcpServers`: el conductor consulta el grafo y **relaya** al resto.
