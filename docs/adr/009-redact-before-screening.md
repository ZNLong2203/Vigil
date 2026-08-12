# 009 — Redact before screening, not after

**Status:** accepted

## Context

The trust boundary does two things to untrusted content: replaces identifiers
with tokens, and looks for instructions hidden inside it. The order looked
arbitrary until we wrote the first blocked-document audit entry.

A finding includes an excerpt, so a human can see what was caught. The demo
payload is an exfiltration instruction — and the thing being exfiltrated *to* is
an email address sitting in the middle of that excerpt. Screen first, and the
audit log written by the control that caught the attack becomes the place the
attacker's address is recorded in the clear.

## Decision

`screen()` calls `redact()` first and matches patterns against the redacted text.
Findings, excerpts and the returned text are all post-redaction. Callers get
redacted text back even on a block, so the finding can be shown to a person
without leaking anything.

## Alternatives rejected

- **Screen then redact.** Cheaper — no redaction cost on documents about to be
  thrown away — and it leaks through the audit trail.
- **Redact only the excerpt.** Two code paths that must agree about what counts
  as an identifier. They will not, eventually.

## Consequences

Every rejected document pays for redaction it did not need. Accepted, because
the alternative is a leak in the audit log. Detection patterns must be written
against redacted text: a rule matching a literal address would never fire, since
by then it is `[EMAIL_1]`.

Locked in by `test_the_attackers_address_never_appears_in_the_finding`.
