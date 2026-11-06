# ADR-0001: Reference architecture (proposed)

Status: PROPOSED, pending local environment validation.

## Decision
Develop a vendor-neutral MCP server for read-only Kubernetes diagnostics. Package as an in-cluster Deployment, ClusterIP Service and dedicated ServiceAccount. Use Kubernetes API in-cluster credentials and narrowly scoped RBAC. Publish an authenticated Streamable HTTP endpoint through an existing Cloudflare Tunnel route, without a new tunnel or public Kubernetes API.

## Verified reference context
The public README of kimonus/knowledge-vault-mcp documents an in-cluster Helm deployment, Cloudflare Tunnel + Access Managed OAuth for hosted clients, and a separate LAN/WireGuard endpoint with scoped bearer tokens. It describes signed Cloudflare Access assertions verified at the application origin, host-bound credential rules and a chart option for cloudflared. This is documentation of the reference design, NOT verification of the currently running cluster or tunnel.

## To verify locally
- Current Minikube context, cluster topology, Kubernetes version, CNI and NetworkPolicy enforcement.
- Actual cloudflared process/pod, existing tunnel identifier (do not publish), configuration owner and routing change procedure.
- Current Access policy, JWT validation, OAuth client compatibility, hostnames, ingress, DNS and rollback.
- Whether hosted and local MCP clients require separate endpoints or authentication mechanisms.
- Whether another project already provides an acceptable maintained Kubernetes MCP server.

## Data flow
Client -> authenticated HTTPS edge -> existing cloudflared -> private Kubernetes Service -> MCP app -> Kubernetes API -> pod logs/status/events. The MCP origin must independently validate appropriate authentication; edge-only authentication is not a sufficient assumed guarantee.

## Trust boundaries
Public Internet to edge; edge to origin; MCP identity to Kubernetes ServiceAccount; Kubernetes API to logs. Kubernetes RBAC constrains resources but cannot by itself guarantee namespace restrictions based on request parameters; tool-level authorization must enforce allowed namespaces and rate/size limits.

## Tool semantics (proposed)
- list_pods: allowed namespace, bounded page size, sanitized metadata, restart counts.
- get_pod_logs: explicit namespace/pod/container, bounded tail lines and since seconds, timestamps optional; no follow/stream in v1.
- get_previous_logs: previous terminated container logs, with clear not-found/unavailable result.
- get_pod_events: bounded namespace-scoped events filtered by involved object.
- describe_pod: selected status and conditions, no environment variables, secret references, volume details or full pod spec by default.

All outputs are untrusted, may contain secrets and must have byte limits. Disallow arbitrary selectors or selectors with unbounded fanout until threat-reviewed.

## Non-goals for v1
No mutation, kubectl exec, shell, secret read, cluster-wide inventory by default, log persistence, Loki, Prometheus integration, custom identity provider or proprietary client adapters.

## Open decisions
1. Adopt vs build, based on evidence.
2. Namespace policy (allowlist vs one namespace per deployment).
3. Authentication pattern: reuse proven origin-side Cloudflare Access JWT validation and optional private scoped tokens; ensure MCP client interoperability.
4. Multi-user support: out of scope unless required.
5. NetworkPolicy support depends on CNI.

## Rollback
Remove new tunnel route and Access application, stop new Deployment, leave existing Knowledge Vault endpoint untouched. Test route isolation before and after change.
