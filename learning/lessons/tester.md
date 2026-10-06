# Tester lessons

Read before every run. Sections match test types. Brackets name the evidence.

## All test types

- Follow the 5.0 docs exactly. Don't fall back to 4.x paths or service names without recording a docs finding. [team decision 2026-10-06]
- Check for an existing issue before writing a finding, and link it. [CEO golden rule 2]

## fp-audit

- One finding per logon or logout event is expected. Flag more than one per event as alert noise. [CEO directive 2026-10-06]
- Rootcheck and IT hygiene findings that are true for every default install are noise. [CEO directive 2026-10-06]

## web-journey

- Stop before any real payment step if no sandbox mode exists, and record that as a finding. [handbook 6.4]
