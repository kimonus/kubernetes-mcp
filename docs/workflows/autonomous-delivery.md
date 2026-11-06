# Autonomous delivery protocol

## Roles
- Local implementation agent: investigates, designs, implements, tests, fixes, self-reviews, prepares PR and evidence.
- Independent reviewer: reads exact commit and artifacts, checks tests, security, architecture and failure cases; publishes findings with severity and reproducible evidence.
- Owner: resolves only genuinely blocked decisions, grants access/credentials, approves security-significant architecture changes, production deployment and merges.

## Continuous workflow
1. Read AGENTS.md, roadmap and prior PR/review comments.
2. Identify current milestone and acceptance criteria; maintain a durable plan.
3. Perform all non-destructive discovery possible without asking for routine confirmations.
4. Implement and run all available checks; fix failures and rerun.
5. Review the diff against requirements and threat model; run negative tests.
6. Push branch and open PR with evidence. Request independent review.
7. Reviewer must review the exact head SHA, run or independently assess tests, label findings BLOCKER/HIGH/MEDIUM/LOW and distinguish verified vs unverified.
8. Implementation agent fixes findings, publishes response matrix and new SHA, then requests re-review.
9. Iterate until no blocking findings remain; record residual risk.
10. Merge/deploy only when authorized. If unattended execution is unavailable, leave an actionable handoff rather than implying work continues in the background.

## Escalation policy
Ask the owner only for unavailable access, irreversible or production-impacting actions, security-policy choices that cannot be inferred, or unresolved tradeoffs with materially different outcomes. Bundle related questions; include recommendation and safe default. Do not ask permission for ordinary research, edits on feature branches, tests or review cycles.

## PR evidence template
- Goal, scope, base/head SHA, files changed.
- Verified environment facts and assumptions.
- Commands run, exit status, counts, test artifacts and coverage.
- Security-negative cases, RBAC validation and auth validation.
- Known risks, limitations, rollout/rollback.
- Finding-by-finding reviewer response and exact retest evidence.
- Explicit handoff status: READY_FOR_REVIEW, NEEDS_FIXES, BLOCKED, or APPROVED_FOR_MERGE (review only; not an automatic merge instruction).

## Completion
Do not declare success solely from green unit tests. Demonstrate protocol conformance, read-only enforcement, Kubernetes integration and authenticated access as applicable to milestone. Never fabricate an environment test when the environment is inaccessible.
