---
name: test-api-security
description: How the PXQ Tester checks API usability and runs agent-environment security checks (default credentials, encryption, API pentest basics) on Wazuh 5.0, Hub and Cloud Console. Use for test type "api-security".
---

# Testing APIs and security

## API usability

1. Start from the public API reference only.
2. Authenticate exactly as documented, then call the core endpoints the ticket lists.
3. For each call, record the request, the response, whether it matches the docs, and whether errors are clear.
4. Check that examples in the docs run unchanged.
5. Check pagination, filtering and error codes on at least one list endpoint.

## Security checks

These only run against environments built for the ticket, or test tenants the ticket names. Never point them at production or anything outside `config/networks.yaml`.

- **Default credentials.** After a documented install, check whether default users or passwords are still active, and whether the docs tell users to change them.
- **Encryption.** Check that traffic between components and to the dashboard and API uses TLS. Record certificate details and protocol versions.
- **Authentication.** Check token expiry, logout, and that a revoked token stops working.
- **Authorization.** Check that a read-only user can't call write endpoints.
- **Input handling.** Send malformed and oversized input to a few endpoints and record how they fail. Don't attempt denial of service.
- **Exposure.** Check which ports are open after a default install, and whether the docs explain them.

Security findings bump one severity level, as the handbook says, and never go above S1. Write them so a developer can reproduce them, without step-by-step exploit chains. The owner decides what gets shared.
