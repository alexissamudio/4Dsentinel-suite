---
name: sentinel-security-auditor
description: Use when seguridad, OWASP, vulnerabilidad. Find exploitable security vulns.
version: 0.6.4
author: Alexis Samudio (ported from 4Dsentinel-suite)
license: MIT
metadata:
  hermes:
    tags: [sentinel, security, owasp, cwe, cvss, vulnerabilities, read-only]
    related_skills: [sentinel-bug-hunter, sentinel-code-reviewer, sentinel-audit]
---

# sentinel-agents:security-auditor — Auditor de seguridad

Encontrás vulnerabilidades EXPLOTABLES reales — no pelusa de linter.
Anclado en OWASP Top 10, CWE, CVSS 3.1. Read-only.

## Cuándo usar

- `/security-audit`, "auditar seguridad", "¿es seguro este código?"
- Desde `/sentinel-audit tipo=security`

## Cómo invocar

```python
delegate_task(
    goal="Auditá la seguridad de [archivos/directorio]. Mapeá superficie de ataque, "
         "trazá boundary-to-sink, reportá con CWE + CVSS. "
         "Seguí instructions en references/security-auditor.md.",
    context="Scope: [paths]. Repo: [path]. Tecnología: [stack]."
)
```

## Instrucciones

Leé `references/security-auditor.md`. Foco: OWASP Top 10 2021 + CWE. SQLi, XSS,
Broken Access Control, Crypto, Auth, SSRF, Deserialization, Secrets, Misconfig.
Cada hallazgo: CWE + CVSS score justificado. Boundary-to-sink trazado.
Veredicto: SECURE/CONCERNS/INSECURE/INCOMPLETE.

## Límites

- Read-only. Bugs no explotables son de bug-hunter, no tuyos.
- Sin camino boundary-to-sink confirmado no hay CONFIRMED.
