# 011 — Two model backends, deliberately

**Status:** accepted

## Context

The mandatory tier is Gemini 3.5 or newer. Vertex AI serves it, and serves it
under the deployed service account's own identity, so nothing long-lived sits in
the container.

Gemma, Veo and Lyria are not on Vertex for this project. `make models` lists them
on a Gemini API key and finds none of them in the Vertex catalogue. They are
worth having: Gemma redacts the names a regex cannot find, Lyria produces cues a
caregiver can tell apart without looking, Veo makes a week shareable.

Once a Gemini API key exists, the obvious simplification is to route everything
through it — it serves the mandatory models too, and one credential is simpler
than two.

## Decision

Keep both. Vertex for the reasoning tier, the Gemini API only for models Vertex
does not serve.

## Alternatives rejected

- **Everything through the Gemini API.** Simpler, and it puts a long-lived key in
  the runtime environment of a system whose entire argument is that boundaries
  are enforced rather than promised. It also gives up Vertex AI logs, which the
  rules name as evidence the backend runs on Google Cloud, and moves the project
  off the enterprise plane the category is about.
- **Everything through Vertex.** Not available: three of the models are not there.

## Consequences

Three clients in one process, and each one exists for a reason the others cannot
serve:

| client | why |
|---|---|
| Vertex, ADC | the mandatory tier, authenticated by identity rather than a key |
| Gemini API | Gemma, Veo — not served by Vertex |
| Gemini API, `v1alpha` | the Live Music socket, which exists only on that version |

Two of these were found by failing. `GOOGLE_GENAI_USE_VERTEXAI` is read globally
by the SDK, so the Gemma client answered 403 until it was told `vertexai=False` —
in a two-backend process, every client has to state which backend it is. And the
Lyria model that streams audio is `lyria-realtime-exp`, which does not appear in
`models.list()` at all; the two Lyria models that *are* in the catalogue answer
`generateContent` with musical notation rather than audio.

The second credential is optional. Without it the trust boundary falls back to
the regex tier and logs, in those words, that names and addresses are not
redacted on that path — see ADR 005.
