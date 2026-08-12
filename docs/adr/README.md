# Architecture Decision Records

Each record states the decision, what was rejected, and what it costs us. They
are short on purpose — a decision that needs three pages of justification is
usually two decisions wearing a trenchcoat.

| # | Decision | Status |
|---|---|---|
| [001](001-pubsub-between-stages.md) | Pub/Sub between stages, not direct calls | accepted |
| [002](002-checkpoints-not-transactions.md) | Checkpoints + idempotency keys, not transactions | accepted |
| [003](003-separate-watchdog-agent.md) | A separate read-only watchdog, not self-critique | accepted |
| [004](004-firestore-not-cloud-sql.md) | Firestore, not Cloud SQL | accepted |
| [005](005-local-redaction-before-the-model.md) | Redact PII locally with Gemma before any hosted model | accepted |
| [006](006-eval-gate-and-anti-gaming-judge.md) | Eval gate + anti-gaming judge before promoting a self-improvement | accepted |
| [007](007-push-subscription-not-polling-worker.md) | Pub/Sub push to Cloud Run, not a polling worker | accepted |
| [008](008-two-layer-scope-enforcement.md) | Scope enforcement in two layers, not in the prompt | accepted |
| [009](009-redact-before-screening.md) | Redact before screening, not after | accepted |
| [010](010-hard-rules-before-confidence.md) | Hard policy rules run before confidence rules | accepted |
| [011](011-two-model-backends.md) | Two model backends, deliberately | accepted |
