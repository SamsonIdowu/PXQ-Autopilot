---
name: test-detection
description: How the PXQ Tester validates Wazuh detection use cases (FIM, threat detection, vulnerability detection, rules, decoders, integrations, POC guide) and audits false positives and negatives. Use for test types "detection" and "fp-audit".
---

# Testing detection and alert quality

## Use cases

For each use case in the ticket, or each section of the POC guide:

1. Prepare the endpoint exactly as the guide says. Use agent environments only.
2. Trigger the behaviour, for example change a monitored file, run the simulated attack, or install a known-vulnerable package version.
3. Wait for the time the guide states, or 5 minutes if it doesn't say.
4. Check the dashboard view the guide points to, and query the alerts index for the expected rule.
5. Record the expected rule, the actual alerts with IDs and levels, the time to appear, and screenshots of what the guide says the user will see.

Pass when the alert fires, its details are correct, and the user can find it where the guide says.

## Custom rules and decoders

1. Add the guide's custom decoder and rule exactly as written.
2. Test them with the rule-testing tool the 5.0 docs describe.
3. Restart or reload as documented, and confirm the alert fires on real input.
4. Note anything that needs an undocumented step.

## Alert noise audit (fp-audit)

The CEO's rule is that a false negative is better than a false positive, because users drop products that flood them.

1. On a fresh install with one or two idle agents, sample all alerts for 30 minutes.
2. Group them by rule ID and count alerts per rule per hour.
3. Flag rules that fire more than 10 times an hour on an idle system, and rules whose alerts describe expected default behaviour.
4. Pay special attention to these.
   - **IT hygiene and rootcheck.** Findings that are true for every default install are noise.
   - **Login and logout.** One finding per logon or logout event is right. More than one per event is a finding.
   - **Vulnerability detection.** Findings for packages the default install ships with, without a clear way to act on them.
5. For each noisy rule, record the rule ID, the rate, three sample alerts, and why a user would see it as noise.

Severity for noise follows `pxq-findings`. A noise flood on a first install counts as someone's first experience, so the bump rule applies.

## False negatives

When a use case doesn't alert, check that the agent is connected and the module is enabled as the guide says before calling it a finding. If the guide forgot to say how to enable it, the finding is the guide.
