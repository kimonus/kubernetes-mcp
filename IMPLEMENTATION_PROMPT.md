# Autonomous implementation assignment — Kubernetes MCP

You are the lead local Codex implementation agent. Read AGENTS.md, ROADMAP.md, and every referenced architecture, workflow, acceptance and review document. The repository is public: never publish sensitive homelab data.

## Mission
Deliver a reusable, vendor-neutral, read-only Kubernetes MCP server, deployed in Kubernetes and reachable through the existing Cloudflare Tunnel. Optimize for minimum owner involvement, strong security, evidence-based testing and independently reviewable results.

## Execution mode: keep going
Do not stop at ordinary milestones, ask for routine confirmations, or hand off incomplete work. Continue through discovery, design, implementation, tests, debugging, self-review, packaging and review preparation. If one step is blocked, proceed with independent safe work and record the blocker. Do not claim background execution or tests you did not perform.

## Phase 0: evidence-driven discovery
Inspect the real Minikube deployment and the existing Knowledge Vault MCP architecture, including Cloudflare Tunnel, Access/OAuth, origin-side authentication, Helm practices and CI. Check current runtime rather than trusting repository documentation. Identify where cloudflared runs and how an additional route can reach an in-cluster Service. Do not alter the existing Knowledge Vault service.

Evaluate maintained open-source Kubernetes MCP projects against building a minimal server. Document licensing, maintenance, attack surface, log capabilities, read-only guarantees, transport and authentication. Make an evidence-backed adopt/build recommendation. If a genuinely material security or architecture choice remains, present one consolidated decision request with recommendation; otherwise use safe defaults and proceed.

## Required product scope
MCP Streamable HTTP; list_pods, get_pod_logs, get_previous_logs, get_pod_events and describe_pod. Read-only Kubernetes API using a dedicated ServiceAccount and least-privilege RBAC. Strict namespace policy, bounded tail/time/bytes, timeouts, concurrency controls, error sanitization, safe handling of untrusted log contents, and no access to secrets or arbitrary pod specs. No shell, exec, resource mutations, cluster-admin or public Kubernetes API.

Package container image, Helm chart, configuration examples, CI, tests and operator documentation. The implementation must be deployable to a different Kubernetes cluster without requiring Knowledge Vault or Cloudflare.

## Authentication and transport
Reuse the existing Cloudflare Tunnel rather than creating another. Investigate existing Cloudflare Access Managed OAuth and origin verification patterns as a reference, not an unverified fact about the live cluster. Support standards-compliant MCP clients; test at least two where available. Validate Origin, authentication and protocol negotiation. No site-specific credentials in the public repository.

## Quality gates
Run unit, integration, negative security and protocol tests; lint, type checks, dependency checks, image build and Helm lint/template validation. Verify denied namespaces, unauthenticated access, oversize logs, Kubernetes API errors, restarted containers, and prompt-injection-like log text. Run real cluster checks only if safe and authorized; distinguish simulated from live evidence.

## Independent review loop
Create a feature branch and PR with exact commit SHA, commands, outputs, test evidence, threat assessment, deployment/rollback plan and known limitations. Perform self-review and fix findings before requesting independent review. Provide INDEPENDENT_REVIEW_PROMPT.md to a separate reviewer. Address reviewer findings, retest, and request re-review until blocking issues are resolved. If no independent reviewer can be invoked, leave a complete ready-to-review handoff rather than falsely claiming review.

## Owner escalation and safety boundaries
Only ask the owner for missing permissions or credentials, material unresolved design decisions, or actions that alter live infrastructure, DNS, tunnel routes, production secrets or service availability. Bundle questions with clear recommendation and safest default. Do not deploy to production or merge without explicit authorization. Continue all safe non-production work while waiting.

## Completion report
Provide PR URL, exact head SHA, implemented scope, test commands and results, security checks, reviewed/unreviewed status, remaining blockers and the smallest next owner action. Do not mark the project complete before the applicable acceptance matrix is satisfied.

## Scope clarification
Filesystem MCP is explicitly out of scope. Do not implement host directory mounts, file moves, renames, creation, deletion or other host filesystem tools. This project is restricted to read-only Kubernetes diagnostics and container logs.
