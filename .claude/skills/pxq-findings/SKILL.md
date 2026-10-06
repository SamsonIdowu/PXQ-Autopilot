---
name: pxq-findings
description: The PXQ finding format, types, severity matrix and bump rule. Use whenever writing, reviewing or grading a finding.
---

# Findings

Every finding validates against `schemas/finding.schema.json`.

## Types

functional-bug, broken-flow, content-error, clarity, terminology, docs-product-mismatch, findability, workflow-complexity, cross-product-inconsistency, conversion-friction, error-handling, alert-noise, missed-detection, security.

## Severity

| Impact on the user | Most users or a core journey | Some users | Few users or an edge case |
|---|---|---|---|
| Blocks them from finishing | S1 | S1 | S2 |
| Slows them down or confuses them a lot | S2 | S2 | S3 |
| Annoys them but is easy to work around | S3 | S3 | S4 |
| Cosmetic only | S4 | S4 | S4 |

**Bump rule.** Move up one level, never above S1, if the finding touches money, security claims, legal wording, or someone's first install, sign-up or login.

**Persistence.** If it happens every time, lean to the higher level when unsure.

## Writing rules

- Write the title in the user's words.
- Expected and actual get one line each.
- Steps to reproduce are numbered and start from a fresh environment.
- `repro_count` must be 2 or more for any finding with a severity. Single reproductions go in `unconfirmed`.
- Never join sentences with a semicolon or a colon.
