# Operations and rollout plan

The service has been installed in a dedicated namespace and a separate protected route has been configured. Anonymous requests and OAuth discovery have been checked; authenticated hosted access and revocation remain unverified. Keep site-specific hostnames, Access settings, identities and credentials outside this public repository. The service exposes logs and events, which can contain sensitive data and hostile instructions. Grant access only to clients allowed to read every configured namespace.

## Prerequisites

- A cluster with namespace-scoped Role and RoleBinding support, a working in-cluster API Service, and DNS connectivity. Verify NetworkPolicy enforcement for the CNI in use.
- A reviewed and scanned immutable image digest available to the cluster. Build and scan the image in CI, then publish it to an authorized registry; don't substitute a mutable tag.
- An explicit namespace policy. For a limited scope, create the namespaces before installation and grant the operator permission to create Roles and RoleBindings there. `allNamespaces: true` instead creates a read-only ClusterRole and ClusterRoleBinding, covering all current and future namespaces, including system namespaces; this requires cluster-scoped RBAC privileges. These permissions do not include the Secrets API or writes. However, Kubernetes supplies complete pod specs to the service account, and those specs may contain literal credentials or Secret references. Logs and events may also contain sensitive data.
- For hosted access, a separate Cloudflare Access application with Managed OAuth, a dedicated audience and an explicit identity policy, plus a route through the existing connector. Do not reuse an existing application's audience merely to avoid provisioning a separate policy. The origin must verify the assertion on every request. A Cloudflare API credential must be scoped to the needed account and zone operations; never commit it or print it in logs.
- The chart creates a ClusterIP Service without an ingress or NetworkPolicy. ClusterIP does not prevent other pods from connecting. Arrange and verify network isolation appropriate to the cluster. Cloudflare mode requires origin TLS, and the connector must verify the origin certificate using the correct server name and trust chain. Do not expose the Kubernetes API.

## Configuration

For a private, isolated test, use a strong random bearer token supplied in a Kubernetes Secret under key `token`, set `authMode: bearer`, reference that Secret with `tokenSecret`, and choose either `namespaces` or `allNamespaces: true` plus an immutable `image` digest. Bearer mode is not suitable for a public endpoint. Token changes require a server restart.

For Cloudflare Access, set `authMode: cloudflare`, `accessIssuer`, `accessAudience`, `accessEmails`, and `tlsSecret` in a private values file. The TLS Secret must contain `tls.crt` and `tls.key`; the certificate must be trusted by the connector and valid for its configured origin server name. Restart the Deployment after certificate rotation because the process loads the certificate at startup. Set `allowedOrigins` only to exact browser origins that should be allowed; requests without an Origin still require authentication. Run `helm lint` and `helm template` using that private file and check the generated RBAC. Do not upload private rendered manifests or values to the public repository. Store sensitive configuration with appropriate Kubernetes RBAC, and avoid putting it into CI logs.

Install in a staging namespace and test an anonymous request, a valid authorized client, a denied identity and namespace, current and previous logs, restart and API failures, and log caps. Verify the connector reaches only the intended Service. Before and after any approved routing change, verify the existing endpoint independently without disclosing its hostname or credentials. Validate OAuth discovery and token revocation at the edge: origin-side JWT validation alone does not immediately revoke an already issued assertion.

## Rollback

For a new hosted route, remove only the route and Access application created for this service, then uninstall the release and confirm its Service, ServiceAccount, Roles and RoleBindings are gone. Keep the existing connector and other services untouched. Preserve the previous route configuration privately before making any route change. The isolated kind CI job verifies Helm release removal; it does not test Cloudflare rollback or production routing.
