# Acceptance matrix

## Protocol
- MCP initialize, tool discovery, valid calls and structured error handling via Streamable HTTP.
- Test with at least two independent MCP client implementations where feasible.
- Authentication: anonymous, expired, wrong issuer, wrong audience, revoked token and unauthorized tool denied.

## Kubernetes
- List healthy pods, restart counts and multi-container pods.
- Current logs with tail/time bounds and timestamps.
- Previous logs when container restarted; clean unavailable result otherwise.
- Pod events and status, including pending, failed and terminated.
- Namespace allowlist and RBAC restrictions; cannot list secrets or mutate pods.
- API timeout, permission denied, pod deleted during query, malformed response, oversized logs, concurrent requests.

## Security
- Injection-like text in logs must remain data.
- Output byte caps and request size caps enforced.
- No credentials, sensitive environment or raw pod specs in responses.
- No exec, shell, arbitrary API proxy, write tools or public Kubernetes API endpoint.

## Delivery
- Automated unit/integration tests, lint/type checks, dependency/image scans, reproducible container build, Helm lint/template and Kubernetes schema checks.
- Isolated local E2E tests before real cluster deployment.
- Remote E2E tests only with owner-approved access and non-disruptive procedures.
- Validate existing Knowledge Vault endpoint unchanged after routing changes.
- Document rollback and demonstrate it in staging or a safe dry run.
