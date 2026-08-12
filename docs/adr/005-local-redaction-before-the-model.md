# 005 — Redact PII locally with Gemma before any hosted model

**Status:** accepted

## Context

Vigil's inputs are among the most sensitive categories of personal data: health
records, insurance identifiers, home addresses, the name of a real person who
did not choose to be in a hackathon project. Most of the reasoning work does not
need any of it — deciding that a deadline is in nine days does not require
knowing whose deadline it is.

## Decision

Untrusted input passes through a local Gemma pass that replaces identifiers with
stable tokens (`[PERSON_1]`, `[POLICY_3]`) before any hosted model sees it.
De-tokenisation happens only in the action layer, at the moment a side effect
genuinely needs the real value.

## Alternatives rejected

- **Send everything to Gemini and rely on policy.** Simpler, and it makes the
  privacy story a promise rather than a property of the system.
- **Regex redaction.** Cheap, and it fails on exactly the messy inputs this
  project is built for — handwriting OCR, mixed-language voice transcripts.

## Consequences

An extra hop and an extra model to operate, plus a token map that is itself
sensitive and must be access-controlled. In exchange, the reasoning tier holds
no raw identifiers, the audit log can be shared with an auditor without
exposing them, and the cheapest model in the stack handles the highest-volume
step. It also satisfies the additional-Google-model bonus without inventing a
use for one.
