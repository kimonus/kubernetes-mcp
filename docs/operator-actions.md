# Operator actions collected for later

This file collects the owner actions needed for hosted deployment. Do not put real tokens, account identifiers, email addresses, or private hostnames in this public repository or in chat.

## 1. Create a separate Cloudflare API token

Create a **new token**; do not widen the existing DNS token. In the [Cloudflare dashboard](https://dash.cloudflare.com/):

1. Sign in with a user who can manage the account and the relevant zone. Open **My Profile → API Tokens**. This creates a user API token, which is separate from a tunnel connector token.
2. Select **Create Token**, then select **Create Custom Token** (or the custom-token option). Name it `kubernetes-mcp-deployment`.
3. Add these three permission rows. The scope and permission group are separate dropdowns; select **Edit** (or **Write** if that is the label shown):

   | Scope | Permission group | Access |
   | --- | --- | --- |
   | Account | Cloudflare Tunnel | Edit |
   | Account | Access: Apps and Policies | Edit |
   | Zone | Access: Apps and Policies | Edit |

   In the Account API token interface, the tunnel permission may appear as **Cloudflare Tunnel Write** or **Argo Tunnel (Legacy)**. The supplied token was verified to read the existing tunnel configuration; write access has not yet been verified. For zone access, the interface may call the resource scope **Specified Domains** and the permission **Zone Access**.

4. Under resource rules, select **Include → Specific account** and choose the account that owns the existing tunnel. For zone resources, select **Include → Specific zone** and choose the zone for the new hostname. Do not select all accounts or all zones. Depending on the dashboard version, these rules may be configured inside separate account and zone policies.
5. Optionally set an expiration long enough for the deployment work. Leave client IP filtering unset unless you know the public outbound IP used by the machine running the agent; an incorrect filter blocks the token.
6. Select **Continue to summary**, check the three permissions and resource restrictions, then select **Create Token**. Copy the displayed secret immediately; Cloudflare shows it only once. Save it using the commands below, and do not paste it into chat.

### If zone Access returns 403

The supplied account token was updated with a separate **Specified Domains → Zone Access → Read** policy. The agent then verified that listing the existing zone application and its application-specific policies succeeds. Listing standalone zone policies still returned 403; it is not yet established whether that endpoint is needed. Creating or changing an application has not been tested. Account API tokens use different labels from the user-token interface described above. Keep the token in the same private file if its value changes; do not share the secret in chat.

These permissions provide:

- Account: **Cloudflare Tunnel Edit** (including reading the current tunnel configuration and updating the new route).
- Account and zone: **Access: Apps and Policies Edit** for the relevant account and zone, to inspect existing policies as authorized and configure the new application. Cloudflare exposes separate account- and zone-scoped Access permission groups; both may be needed for this setup.

Keep the existing DNS-scoped credential for the DNS change. If the Cloudflare dashboard uses newer permission names, choose the equivalent connector and Access application permissions. The agent must verify the exact endpoints and granted capabilities before making changes; remove any scope found unnecessary afterward. Do not create a new tunnel or change the existing service. See Cloudflare's [token creation guide](https://developers.cloudflare.com/fundamentals/api/get-started/create-token/), [Managed OAuth guide](https://developers.cloudflare.com/cloudflare-one/access-controls/applications/http-apps/managed-oauth/) and [permission reference](https://developers.cloudflare.com/fundamentals/api/reference/permissions/).

On the machine running this agent, save the new token outside the repository. The following Bash commands do not echo the token:

```bash
install -d -m 700 "$HOME/.config/kubernetes-mcp"
umask 077
read -r -s -p 'Cloudflare API token: ' kubernetes_mcp_cf_token
printf '\n'
printf '%s' "$kubernetes_mcp_cf_token" > "$HOME/.config/kubernetes-mcp/cloudflare-api-token"
unset kubernetes_mcp_cf_token
chmod 600 "$HOME/.config/kubernetes-mcp/cloudflare-api-token"
```

Tell the agent only the file path, not the token. Remove the temporary file after the credential has been securely transferred or the work is finished. The token may instead be supplied through an existing private secret-management mechanism if its location is communicated to the agent.

## 2. Confirm the hosted identity and hostname

The intended namespace scope is **all current and future namespaces**, including system namespaces. This is an explicit choice. The service account cannot use the Kubernetes Secrets API or mutate resources, but Kubernetes returns complete pod specs to it: those specs may contain literal credentials or Secret references. A compromised service process or service account token can read those specs across the cluster. Logs and events in any namespace can also contain credentials. No further namespace selection is needed.

Use a separate hostname and Access application. The agent can check whether a suitable unused hostname under the existing zone is available and recommend one privately. The allowed identities must be explicitly defined for the new Access policy; the agent can inspect the existing policy once the new token has the required access and propose matching its authorized identities. Do not reuse the existing application's audience or alter its route.

The new origin requires TLS. The agent will first check privately whether the cluster can issue a certificate for the chosen origin name. If it cannot, supply a `kubernetes.io/tls` Secret in the service's namespace containing a certificate and key trusted by the connector; share only the Secret name and the corresponding origin server name, never the private key. The connector must verify the certificate rather than disabling verification. This fallback cannot be finalized until the hostname and existing certificate-issuer capabilities are known.

## 3. Review prior public history

An earlier commit in the draft PR included limited live-infrastructure configuration details. Those details were removed from the current tree, but remain in previously published history; no credential values were included. Rewriting published history or closing/replacing the PR can disrupt collaborators and does not by itself guarantee removal of cached copies. Decide separately whether history remediation is required before authorizing any rewrite; follow GitHub's sensitive-data removal procedure if applicable.

After these items are available, the agent can verify the existing route and Access policy, prepare a separate route and identity policy, run the remaining tests, and document rollback. The current state and unverified acceptance gates are in [discovery.md](discovery.md) and [operations.md](operations.md).
