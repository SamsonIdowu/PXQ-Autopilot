---
name: pxq-report
description: The PXQ report template and naming rule. Use when writing or polishing a ticket report.
---

# Report

**Name.** `PXQ-### · <Wazuh services, comma separated> · <what was tested>`, using names from `config/services.yaml`.

**Result.** Either "Issues found" with a severity count such as `1×S2 · 2×S3`, or "Passed".

## Sections

1. **Summary.** Two or three sentences on what a user experiences.
2. **Findings.** One block per finding with severity, type, Wazuh service, title, expected, actual, steps, evidence links, related issues and suggested fix if any.
3. **What passed.** The checks that worked, so teams hear what's good too.
4. **Environment.** Template, versions, agent type (cloud or local), playbook and skill versions.
5. **Reviewer notes.** Added by the Reviewer.

## Style

- Lead with the user.
- Prefer numbers to adjectives.
- Keep sentences short, with one idea each.
- No jargon or bare ticket numbers.
- Never join sentences with a semicolon or a colon.
