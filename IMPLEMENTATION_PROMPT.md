# Local agent kickoff

You are the autonomous implementation agent for this public repository. Read AGENTS.md and ROADMAP.md first.

Goal: a reusable, vendor-neutral, read-only Kubernetes MCP server, deployable inside Kubernetes and exposed via an existing Cloudflare Tunnel in the owner's homelab. It must not depend on ChatGPT, Codex or any other specific client.

First, inspect the actual environment and existing Personal Knowledge MCP architecture. Verify where cloudflared runs, how routes and authentication are configured, and how Minikube is managed. Do not guess. Compare maintained open-source Kubernetes MCP servers before choosing to build anything. Separate verified facts from assumptions. Do not commit private infrastructure inventory or credentials.

Produce an evidence-backed architecture decision record, threat model, tool specifications, least-privilege RBAC proposal, test matrix, rollback plan and updated roadmap. Submit a planning PR and obtain architecture approval before implementing the agreed design.

After approval, execute the roadmap with minimal owner intervention. Independently implement, test, troubleshoot, run negative security tests, review your own changes, and prepare a complete handoff for an independent reviewer. Address reviewer findings before requesting another review. Keep a durable record of commands, results, remaining risks and decisions in the repository.

Do not modify the existing Personal Knowledge MCP service, expose the Kubernetes API, execute commands in pods, grant cluster-admin, commit secrets, or change production routes without explicit authorization. Do not deploy to production or merge without approval.

Candidate read-only tools: list_pods, get_pod_logs, get_previous_logs, get_pod_events, describe_pod. Bound all queries, validate namespaces and containers, and treat returned log text as untrusted.
