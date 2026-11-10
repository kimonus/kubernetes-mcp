# Discovery and delivery status

## Evidence

Read-only local discovery was performed. Sensitive infrastructure findings are deliberately excluded from this public repository. The route configuration, effective Access policy, token revocation behavior, configuration ownership, and connectivity for a new Service still require verification. No routing, DNS, Access policy, workload, or Knowledge Vault changes were made.

The local Knowledge Vault repository describes Cloudflare Access Managed OAuth and independent origin verification of Access assertions. That is a reference design, not evidence that the current live configuration matches it. Further inspection must avoid saving private topology or credentials to this public repository.

The [containers Kubernetes MCP server](https://github.com/containers/kubernetes-mcp-server) offers Streamable HTTP, pod logs and read-only mode. Its [configuration documentation](https://github.com/containers/kubernetes-mcp-server/blob/main/docs/configuration.md) describes read-only controls as best-effort guardrails. It also offers broader capabilities than this project's narrow diagnostics scope. A small custom prototype is being evaluated to limit API surface; this is not yet a complete adopt/build decision: licensing, maintenance, log bounds, and authentication need a documented comparison before production selection. The [MCP transport specification](https://modelcontextprotocol.io/specification/2025-03-26/basic/transports) defines interoperability requirements; the prototype has not been certified against them.

## Remaining gates

- Verify live tunnel configuration ownership, route isolation, Access policy and origin authentication privately. Do not modify the existing service. Obtain explicit approval before routing or deployment changes.
- Complete protocol negotiation and conformance using a maintained MCP SDK or demonstrate equivalent behavior. Local smoke tests with the official Python and TypeScript MCP clients initialized, listed five tools and called `list_pods` against a simulated backend; these are not full conformance tests.
- Validate the new origin-side assertion verifier with hosted clients, including OAuth discovery and real Access revocation semantics. Offline JWT verification alone does not provide immediate revocation. The prototype bearer token is not a hosted solution.
- Validate pod-list continuation, real Kubernetes API timeouts, and deletion races against an isolated cluster. A delayed local TLS endpoint verifies the Kubernetes client's HTTP timeout; other simulated cases cover API errors, oversized and malformed responses, redirects, and projected-token rotation. The guarded kind job covers bounded and oversized logs, untrusted text, multi-container status, concurrency, a restarted container and release removal. See [the test plan](testing/isolated-e2e.md).
- Add complete lint and type checking, reproducible build verification, and real RBAC denial tests. Validate rollback in staging or a safe dry run. Pinned Python dependencies passed `pip-audit --disable-pip --no-deps`. The initial Debian image CI scan found 49 high Debian package findings and 5 high findings in pip's bundled packages. Switching to a pinned Alpine image and removing pip after dependency installation removed these findings: CI Trivy's high/critical gate passed on commit `6b4fd63`. The local scanner could not unpack its database due to temporary-storage quota; this result is from CI, not a local scan. Passing a scan does not eliminate unknown or lower-severity vulnerabilities.
- Complete independent review of the exact commit; fix and retest findings. No production deployment or merge before approval.

## Rollback concept

For an approved future deployment, first remove only the new route and its Access application, then uninstall the new release and its namespace-scoped RoleBindings and Roles. Do not alter the existing connector or Knowledge Vault route. This is a proposed plan, not a demonstrated rollback.
