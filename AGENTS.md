# Agent instructions

This repository develops a vendor-neutral, read-only Kubernetes MCP service.

Work autonomously through research, implementation, tests, fixes, self-review, and evidence-backed handoff. Ask the owner only when blocked or when a risky infrastructure change needs approval.

Never expose credentials or private infrastructure data in this public repository. Do not mutate Kubernetes workloads or expose the Kubernetes API publicly. Use least-privilege RBAC and bounded log retrieval.

Before implementation, inspect the existing Cloudflare Tunnel and Personal Knowledge MCP architecture. Reuse the existing tunnel without changing the existing MCP service. Document assumptions, alternatives, security risks, tests, and rollback.

Do not deploy to production or merge unreviewed changes without approval.

## Autonomous execution and handoff

Follow [autonomous delivery protocol](docs/workflows/autonomous-delivery.md), [acceptance matrix](docs/testing/acceptance-matrix.md), and [architecture proposal](docs/architecture/0001-reference-architecture.md). Use [independent review prompt](INDEPENDENT_REVIEW_PROMPT.md) for a separate reviewer. Avoid repeated owner confirmation requests for routine research, tests, fixes or feature-branch commits. Collect related genuine blockers into one decision request with a recommended default.

The Knowledge Vault public README documents Cloudflare Access Managed OAuth and origin-side validation. This is reference documentation, not evidence of the live tunnel topology. Verify current state locally before proposing modifications. Keep any sensitive discovery output out of this public repository.
