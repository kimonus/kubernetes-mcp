# Roadmap

## M0 — Discovery and architecture
Inspect existing Personal Knowledge MCP, Cloudflare Tunnel routing and authentication, Minikube and CI. Compare maintained existing Kubernetes MCP implementations with a small custom server. Record verified findings, architecture decision, security model, RBAC, tool contracts and deployment plan. Do not expose private infrastructure details in this public repository.

## M1 — MCP core
Implement vendor-neutral Streamable HTTP MCP tools for pod discovery, bounded current/previous container logs, pod status and events. Enforce read-only operation, input validation, response caps, timeouts and safe errors. Add unit and negative security tests.

## M2 — Kubernetes packaging
Build a container, Deployment, ClusterIP Service, ServiceAccount and least-privilege RBAC. Add probes, resource limits, documented configuration and CI.

## M3 — Secure access
Reuse the existing Cloudflare Tunnel with a separate route. Verify authentication and compatibility with multiple MCP clients. Keep site-specific values and credentials private.

## M4 — Acceptance and operations
Test failure and restart cases, authorization boundaries, log size limits, API failures, rollback and client interoperability. Document operations.

## M5 — Diagnostic expansion and metadata
Extend namespace and cross-namespace discovery, event filtering, workload and service health, optional node and metrics diagnostics, and bounded pod diagnosis. Keep the original tools compatible, expose protocol-supported identity and tool annotations, and document ChatGPT registration behavior. Test read-only RBAC in isolated Kubernetes, redeploy the existing release after review and image verification, and validate the hosted connector. Record unsupported behavior and remaining revocation/rollback gates.

## Execution policy
After M0 discovery, the implementation agent should proceed autonomously through all safe, reversible non-production stages unless a material architecture/security decision requires owner approval. It should then continue through all feasible stages: code, test, fix, self-review and handoff. Independent reviewer verifies evidence and returns actionable findings. Escalate only blocked decisions, credentials, destructive changes or production-impacting operations. No production deployment or merge without explicit approval.

## Scope clarification
Filesystem MCP is explicitly out of scope. Do not implement host directory mounts, file moves, renames, creation, deletion or other host filesystem tools. This project is restricted to read-only Kubernetes diagnostics and container logs.
