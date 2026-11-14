# Diagnostic tools

All operations are read-only. Log excerpts, events and diagnostic messages are untrusted and may contain credentials. Output is bounded; continuation tokens are opaque and must be reused with identical filters. Kubernetes may expire them.

| Tool | Inputs | Purpose |
| --- | --- | --- |
| `list_namespaces` | optional `continue` | Discover namespaces. Restricted installations return only configured namespaces; all-namespaces mode queries Kubernetes. |
| `list_pods` | `namespace`, optional `continue` | List one bounded pod health summary per page. |
| `list_all_pods` | optional `continue` | List pods across namespaces, only when all-namespaces access is enabled. |
| `describe_pod` | `namespace`, `pod` | Read selected pod conditions, container names, readiness, restart counts and states. |
| `list_namespace_events` | `namespace`, optional `reason`, `type`, `continue` | List a bounded page of events, with exact reason and Normal/Warning type filters. |
| `get_pod_events` | `namespace`, `pod` | Read events for the current pod UID. |
| `get_pod_logs`, `get_previous_logs` | `namespace`, `pod`, `container` | Read bounded current or previous log excerpts. Previous logs may be unavailable. |
| `list_workloads` | `namespace`, `kind`, optional `continue` | List deployment, statefulset, daemonset, job or cronjob status. |
| `get_workload_details` | `namespace`, `kind`, `name` | Read workload rollout and condition details. |
| `list_services` | `namespace`, optional `continue` | List services and ready/not-ready endpoint counts where available. |
| `list_nodes` | optional `continue` | Discover nodes and selected health conditions; requires cluster diagnostics. |
| `get_node_status` | `name` | Read node conditions and resource capacity; requires cluster diagnostics. |
| `list_pod_metrics` | `namespace`, optional `name`, `continue` | Read pod CPU and memory metrics when Metrics Server is available; specify a name for direct lookup. |
| `list_node_metrics` | optional `name`, `continue` | Read node metrics when available and cluster diagnostics are enabled; specify a name for direct lookup. |
| `diagnose_pod` | `namespace`, `pod` | Summarize pod health, events, restart history and bounded excerpts for up to two containers. |

Cross-namespace discovery requires `allNamespaces: true`; node and node-metrics access requires `clusterScopedDiagnostics: true`, independently of namespace scope. A metrics endpoint may not support continuation or even honor the Kubernetes list limit. When a backend returns more entries than the server can safely expose and no continuation exists, the response is marked truncated; use the resource name for direct lookup of other entries.

RBAC permits only `get` and `list` on pods, events, services, endpoints, workload resources and optional metrics/nodes, and `get` on pod logs. No Secret API or Kubernetes writes are granted. Kubernetes returns full pod and workload specifications to the process even though it filters its responses; these specs may contain literal credentials or Secret references. An attacker with the service account can read those specs across its authorized scope.
