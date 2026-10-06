---
name: test-web-journey
description: How the PXQ Tester walks web journeys on Wazuh Hub products and the Cloud Console (sign-up, email validation, organizations, activation, pricing, purchasing, CTI feed, UI clarity) as a new user. Use for test type "web-journey".
---

# Testing web journeys

You drive a real browser through the Playwright tools. Act as the persona in the ticket, for example "a SOC analyst at a 200-person company trying the product for the first time". Don't use internal knowledge or shortcuts.

## Accounts and payments

- Use only the test accounts named in the ticket. Read credentials from the password manager item at run time, and never write them down.
- Purchases use sandbox payment mode. If a flow has no sandbox mode, stop before the final payment step and record that as a finding about testability.
- Use the team test mailbox for email validation.

## Walk

1. Start from the ticket's start point, usually a public page, not a deep link.
2. Take a screenshot at every screen. Save the HAR file for the whole journey.
3. At each step, note what you expected to see, what you saw, and whether a new user would know what to do next.
4. Time the journey. Record steps where you had to search, guess or retry.

## What to check on every journey

- **Clarity.** Labels say what things do. Data shown has units and context.
- **Terminology.** Product names and terms match `config/services.yaml` and the terminology register.
- **Errors.** Every error says what went wrong and how to fix it.
- **Pricing.** Free and paid tiers say clearly what's included, and the price at checkout matches the pricing page.
- **Accounts.** Inviting a member, changing roles and removing a member all work, and emails arrive.
- **Consistency.** The same action works the same way in the Hub and the Cloud Console.

## Grade the journey

Use the handbook grades A to F. Open findings cap the grade, so any open S1 caps it at D.
