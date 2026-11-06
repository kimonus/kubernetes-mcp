# Agent instructions

This repository develops a vendor-neutral, read-only Kubernetes MCP service.

Work autonomously through research, implementation, tests, fixes, self-review, and evidence-backed handoff. Ask the owner only when blocked or when a risky infrastructure change needs approval.

Never expose credentials or private infrastructure data in this public repository. Do not mutate Kubernetes workloads or expose the Kubernetes API publicly. Use least-privilege RBAC and bounded log retrieval.

Before implementation, inspect the existing Cloudflare Tunnel and Personal Knowledge MCP architecture. Reuse the existing tunnel without changing the existing MCP service. Document assumptions, alternatives, security risks, tests, and rollback.

Do not deploy to production or merge unreviewed changes without approval.
