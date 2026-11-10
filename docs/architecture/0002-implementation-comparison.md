# ADR-0002: Kubernetes MCP implementation comparison

Status: provisional, 2026-11-10. This decision does not authorize production deployment.

## Candidates

The existing [containers/kubernetes-mcp-server](https://github.com/containers/kubernetes-mcp-server/tree/190ab787ec93320583fea144a4fac980cf70aeb2) is Apache-2.0 licensed and was active and not archived when checked. Its documentation describes Streamable HTTP, OAuth/OIDC and TLS, current and previous pod logs, pagination, tool filtering, and configurable resource and response limits. It has a significantly broader tool surface, including mutation and arbitrary resource operations. Its documentation calls read-only filtering a best-effort guardrail and identifies Kubernetes RBAC as the actual authorization boundary. The project has more protocol and authentication functionality than this prototype; its full security properties and behavior under our exact policy have not been independently evaluated. See the [pinned README](https://github.com/containers/kubernetes-mcp-server/blob/190ab787ec93320583fea144a4fac980cf70aeb2/README.md) and [configuration reference](https://github.com/containers/kubernetes-mcp-server/blob/190ab787ec93320583fea144a4fac980cf70aeb2/docs/configuration.md).

The custom prototype exposes five diagnostic tools, selects pod status fields, requires an explicit namespace policy, and uses fixed log limits. Namespace-scoped RBAC is the default; an explicit option grants the same read-only resources across all namespaces. It has a smaller explicitly implemented API surface, but this is not proof of greater security. It has a hand-written MCP transport, limited pagination, one shared authorization scope, no listener TLS, and no verified live OAuth or revocation behavior. Its independent review and isolated tests do not replace full protocol conformance or production security review.

## Recommendation

Continue evaluating the narrow custom implementation as a prototype while completing the acceptance gates. Do not select it for production solely on the basis of its smaller size. Before rollout, compare the cost and risk of replacing its hand-written transport with a maintained MCP SDK or adopting the existing server with a narrowly configured toolset and equivalent RBAC. The custom server remains unapproved until authentication, protocol, isolation, operational recovery and historical-disclosure issues have been resolved.

## Alternatives and consequences

Adopting the existing server reduces ownership of protocol and generic server code but requires review and enforcement of its broader tool surface, configuration, authentication fit, and transitive dependencies. Using a maintained MCP SDK in the custom server narrows protocol-maintenance risk while retaining the explicit diagnostic API, at the cost of a larger dependency set and a migration. Building and maintaining the entire stack minimizes included functionality but creates an ongoing obligation to track MCP security and compatibility changes. None eliminates the need for independent origin authentication, bounded responses, RBAC, secure routing and controlled rollout.
