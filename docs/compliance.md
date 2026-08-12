# Data handling, and what this system is not

Vigil coordinates care admin for one person at home. That means the inputs are
among the most sensitive categories of personal data there are: health records,
insurance identifiers, home addresses, and the name of someone who did not choose
to be in a hackathon project.

This document says what is done about that, and — more usefully — what is not.

## What this is not

**Not a medical device, and not medical advice.** Vigil reads paperwork, spots
collisions in a schedule, and tracks deadlines. It does not diagnose, does not
recommend treatment, and does not decide a dose. The `meds-agent` instruction
says so, the policy engine gates every clinical action on a human regardless of
confidence, and the golden set contains cases whose only correct answer is *"that
is a treatment decision, outside my scope"*.

**Not tested with real people.** Every artifact in this repository is synthetic
and generated — the PDFs by ReportLab, the photographs by Gemini, the voice notes
by Gemini TTS. No real prescription, record, or person is depicted. `All data
shown is synthetic` is displayed permanently in the UI header for the same reason
it is written here.

**Not a complete defence against prompt injection.** The trust boundary blocks
what it can see. Pattern matching does not catch a paraphrase, and an instruction
painted into a photograph is not something a regex will find — images and audio
reach the model as attachments precisely because a transcription would destroy
the evidence the model needs to judge its own certainty. The mitigation is
layered rather than absolute: content is declared to be data in every agent's
instruction, no agent holds a capability it does not need, and every irreversible
action waits for a person.

## Personal data

### What is collected

Only what a caregiver uploads: photographs, voice recordings, and scanned
documents, plus the structured claims extracted from them. There is no account
system, no analytics, and no third-party processor outside Google Cloud.

Care recipients are referred to by a pseudonymous id (`care-subject-001`).
Real names appear only inside uploaded artifacts, and are removed before those
artifacts reach the reasoning tier.

### Redaction, and its limits

Two tiers, in this order:

1. **Regex** finds structured identifiers — email addresses, phone numbers,
   policy and accession numbers.
2. **Gemma** finds what patterns cannot: names of people, street addresses, dates
   of birth. It runs on its own credential and does the one job that must happen
   before anything reaches the reasoning tier.

Identifiers are replaced with stable tokens (`[PERSON_1]`, `[POLICY_1]`) so an
agent can reason about identity without holding the value. De-tokenisation
happens only in the action layer, at the moment a side effect genuinely needs a
real value.

Two limits worth stating plainly:

- **The token map is as sensitive as the original.** It is held in the action
  layer and never enters a prompt.
- **Without the Gemma credential the system falls back to regex alone**, which
  means names and addresses are *not* redacted. It does not do this quietly: the
  result carries `used_model=False` and the log says, in those words, that names
  and addresses are not redacted on that path. See
  [ADR 005](adr/005-local-redaction-before-the-model.md).

Redaction runs *before* screening, so an audit entry recording an attempted
exfiltration does not itself contain the attacker's address — see
[ADR 009](adr/009-redact-before-screening.md).

### What is never redacted

Dosages, units, times, reference ranges and clinical values. A redactor that eats
the dose has destroyed the record it was protecting, and extraction downstream
would report a confident value for `[ID_1] mg`. This is enforced in code and
covered by tests.

## Access boundaries

Four departments, four data boundaries, enforced by what each agent *holds*
rather than by what it is told:

| Department | Agent | May reach | May not |
|---|---|---|---|
| Family | `intake-agent` | uploaded artifacts, staging | anything with an external effect |
| Clinical | `meds-agent` | the medication graph | financial and benefits data |
| Benefits | `benefits-agent` | obligations, invoices, drafts | **clinical notes** |
| Audit | `watchdog` | run state, all traces | any capability that changes something |

Enforced twice: an agent is only handed the tools its registry entry authorises,
and every call is re-checked at invocation. A refused call is short-circuited and
written to the audit log with the boundary that refused it. See
[ADR 008](adr/008-two-layer-scope-enforcement.md).

## Where data lives

| | Where | Retention |
|---|---|---|
| Uploaded artifacts | Cloud Storage, `us-central1`, uniform access, no public reads | **30-day lifecycle rule** |
| Run state, claims, audit | Firestore, `us-central1` | kept; append-only for audit |
| Traces | Cloud Trace, `us-central1` | provider default |
| Logs | Cloud Logging, `us-central1` | 30 days |

**Model calls are the exception, and it is deliberate.** Gemini 3.5+ is served
from Vertex AI's `global` location, not from `us-central1`: regional endpoints
serve only up to Gemini 2.5, and the mandatory tier for this project is 3.5 or
newer. A request may therefore be served from any region. For a deployment
handling real health data this would need a decision by whoever owns that data —
either accepting global routing or accepting an older model. It is stated here
rather than buried because it is exactly the sort of thing that should not be
discovered later.

Gemma, Veo and Lyria run on the Gemini API rather than Vertex, for the same
reason: Vertex does not serve them. See
[ADR 011](adr/011-two-model-backends.md).

## Human control

- Every **clinical** change waits for a person. Always, at any confidence — a
  confident agent is the one you least want acting alone.
- Every **irreversible** action outside the system waits for a person.
- Below a confidence floor, anything waits for a person.
- Contradictions are **surfaced, never resolved**. When two documents disagree
  about a dose, both survive to the human with their sources attached. Recency is
  not evidence.
- An approval records a decision and returns; it does not execute. The run picks
  it up on its next tick, so an approval granted while the worker is down is not
  lost and a worker that restarts twice does not act twice.

## Audit

Every decision is written append-only: what was attempted, by which agent, what
was decided, and which rule decided it. Refusals are recorded as fully as
successes — an auditor asks what an agent *tried* to do, not only what it
managed.

The audit write is bounded and degrades to structured logging if Firestore is
unreachable, because a security control that stops the system when its logbook is
unavailable has become the outage. Entries are never lost silently: the failure
itself is recorded.

## Credentials

No key is committed. `.env` is gitignored, secrets are read from the environment,
and the deployed service authenticates to Vertex AI with its own service account
identity rather than a key.

One exception is stated openly in `deploy.sh`: the UI is a static bundle, so the
API key it uses is readable by anyone who opens the page. It is a throttle
against stray traffic, not an access control. The real cost ceiling does not
depend on secrecy — `--max-instances=3`, a per-run token budget, and billing
alerts.

## If you found something

This is a hackathon entry, not a product. If you find a way through any of the
above, the interesting thing is the mechanism — please open an issue describing
it rather than a patch, so the reasoning can be written down alongside the fix.
