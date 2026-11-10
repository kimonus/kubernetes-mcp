# Isolated Kubernetes acceptance test

The `isolated-kubernetes` CI job creates a disposable kind cluster on a GitHub-hosted runner. The test obtains a fresh kubeconfig from the named kind cluster and checks its node label before changing resources. It creates two test namespaces and fixture pods, installs the chart, and loads a locally built image into the cluster. The fixture credentials and log markers are synthetic.

The script checks that the service account can read allowed pods but cannot read secrets, create pods, or list pods in a denied namespace. It checks anonymous denial, namespace policy, bounded current logs and untrusted text, unavailable previous logs, and previous logs after a fixture container restarts. It uninstalls the release and verifies its Service, Role and RoleBinding were removed. The test does not exercise Cloudflare, external clients, production traffic, or network policies.

The script refuses to run unless `GITHUB_ACTIONS=true` and the dedicated single-node kind cluster exists. Do not point it at a shared or production cluster. The initial version passed in CI at commit `cec2e2a`; expanded log and status checks require a new CI run. This is isolated-cluster evidence, not a production deployment or a complete acceptance result.
