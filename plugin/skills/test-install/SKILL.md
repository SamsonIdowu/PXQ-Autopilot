---
name: test-install
description: How the PXQ Tester validates Wazuh installs and deployments (AIO, multi-node cluster, Kubernetes, Ansible, Docker) from the public docs. Use for tickets with test type "install".
---

# Testing installs and deployments

The goal is to find where a new user following the public docs gets stuck, confused or misled. Being able to make the install work some other way doesn't count.

## Setup

1. Read the ticket's deployment type and target version.
2. Pick the environment template from `config/environments.yaml`.

| Deployment | Template | Agent |
|---|---|---|
| All-in-one | `ubuntu-24.04-aio` | cloud or local |
| Multi-node cluster | `rhel9-cluster-x3` | cloud only |
| Kubernetes | `k3s-cluster` | cloud only |
| Ansible | `ansible-control` plus `ubuntu-24.04-aio` targets | cloud or local |
| Docker | `ubuntu-24.04-docker` | cloud or local |

3. Open the exact docs page the ticket names. Save a copy of the page to `evidence/docs-page.md` with the fetch time, because docs change.

## Walk the docs

For every numbered step on the page:

1. Run the commands exactly as written. Copy and paste, including line breaks.
2. Save the command, its output and its exit code to `evidence/step-NN.log`.
3. Compare what happened with what the docs say should happen.
4. Note anything the docs leave out, such as missing prerequisites, unexplained prompts, passwords printed and lost, or required ports.

## Check health after install

Check these the way the docs tell users to. Where the docs don't say how, use the commands below.

- Every service the docs install is running and stays running for 10 minutes.
- The dashboard login page loads, and the documented credentials work.
- The indexer cluster health is green, or yellow for one node.
- One agent installed from the docs enrols and shows as active.
- Logs show no repeated errors in the first 10 minutes.

Wazuh 5.0 moves and renames several components compared with 4.x. Follow the 5.0 docs for service names, paths and ports. Any 4.x habit, such as `/var/ossec/` paths or `systemctl status wazuh-manager`, is only a hint. If the 5.0 docs are silent and only a 4.x habit works, that's a docs finding.

## Always also run

After every successful install, run the alert-noise check from `test-detection`. The CEO asked for no false-positive floods on any deployment type.

## Typical findings

- A command fails on a clean host, which is a docs and product mismatch.
- A prerequisite is missing from the docs.
- The output is confusing, or a password scrolls away.
- An error message doesn't say how to recover.
- The same step works differently from another deployment type's docs, which is a consistency finding.
