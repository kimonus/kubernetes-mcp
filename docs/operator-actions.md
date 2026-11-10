# Operator actions collected for later

This file collects the owner actions needed for hosted deployment. Do not put real tokens, account identifiers, email addresses, or private hostnames in this public repository or in chat.

## 1. Create a separate Cloudflare API token

Create a **new token**; do not widen the existing DNS token. Restrict it to the account that owns the existing tunnel and the relevant DNS zone, with the following minimum capabilities:

- Account: **Cloudflare Tunnel Edit** (including reading the current tunnel configuration and updating the new route).
- Zone: **Access: Apps and Policies Edit** (including reading the existing policy and creating the separate application and policy).

Keep the existing DNS-scoped credential for the DNS change. If the Cloudflare dashboard uses newer permission names, choose the equivalent connector and Access application permissions. The agent must verify the exact granted capabilities before making changes. Do not create a new tunnel or change the existing service.

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

The intended namespace scope is **all current and future namespaces**, including system namespaces. This is an explicit choice; the service account still cannot read Kubernetes Secrets or mutate resources, but logs and events in any namespace can contain sensitive information. No further namespace selection is needed.

Use a separate hostname and Access application. The agent can check whether a suitable unused hostname under the existing zone is available and recommend one privately. The allowed identities must be explicitly defined for the new Access policy; the agent can inspect the existing policy once the new token has the required access and propose matching its authorized identities. Do not reuse the existing application's audience or alter its route.

## 3. Review prior public history

An earlier commit in the draft PR included limited live-infrastructure configuration details. Those details were removed from the current tree, but remain in previously published history; no credential values were included. Rewriting published history or closing/replacing the PR can disrupt collaborators and does not by itself guarantee removal of cached copies. Decide separately whether history remediation is required before authorizing any rewrite; follow GitHub's sensitive-data removal procedure if applicable.

After these items are available, the agent can verify the existing route and Access policy, prepare a separate route and identity policy, run the remaining tests, and document rollback. The current state and unverified acceptance gates are in [discovery.md](discovery.md) and [operations.md](operations.md).
