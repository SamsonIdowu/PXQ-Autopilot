---
name: test-docs
description: How the PXQ Tester verifies documentation pages, guides and tutorials against real product behaviour. Use for test type "docs" and whenever another test type follows a docs page.
---

# Testing documentation

1. Save the page with its URL, the version selector value and the fetch time.
2. Check the page is reachable from the docs navigation and from search for the term a user would type.
3. Run every step as written in a fresh environment.
4. Check every link resolves, every screenshot matches the current UI, and every version number matches the version under test.
5. Check terminology against `config/services.yaml` and the terminology register.
6. Mark each step Good, Friction or Blocker, the same way as a friction log.

A typo fix or broken link is a low-risk content finding the team may fix directly under SOP-06. Say so in the finding.
