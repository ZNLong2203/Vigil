/**
 * The API. There is no longer anything behind it.
 *
 * This module used to fall back to a committed fixture corpus whenever a request
 * failed, so that the page opened for a judge with no backend running. That
 * safety net is gone by decision: every screen now shows what the deployed
 * system actually returned, or says plainly that it could not reach it.
 *
 * The cost is real and worth naming — if the service is torn down, cold, or
 * erroring, the page is an error page rather than a walkthrough. The benefit is
 * that nothing on screen can be mistaken for something it is not, and there is
 * no second copy of the story to drift out of step with the first.
 *
 * Set NEXT_PUBLIC_VIGIL_API when the UI is hosted apart from the API. In the
 * normal deployment both come from the same container and requests are relative.
 */

const BASE = process.env.NEXT_PUBLIC_VIGIL_API?.replace(/\/$/, "") ?? "";

/**
 * A key baked in at build time, for the case where the UI is hosted apart from
 * the API. Empty in the normal deployment, where both are the same container.
 */
const BUILD_KEY = process.env.NEXT_PUBLIC_VIGIL_KEY ?? "";

/**
 * The key, fetched once from the API that is about to be called.
 *
 * This used to be build-time only, and that hid a total failure in plain sight.
 * The image serves the UI and the API from one container, so deploy.sh leaves
 * NEXT_PUBLIC_VIGIL_API empty on purpose — requests are same-origin and need no
 * host. But `isConfigured()` read that empty base as "no API", every reader
 * short-circuited to its fixture without attempting a single request, and each
 * screen honestly reported "sample data". The fallback did its job so well that
 * it concealed the fact that it was always the thing running.
 *
 * Reading the key at runtime also means rotating it is a config change on the
 * service rather than a rebuild of the image.
 */
let keyRequest: Promise<string> | null = null;

function apiKey(): Promise<string> {
  if (BUILD_KEY) return Promise.resolve(BUILD_KEY);
  if (!keyRequest) {
    keyRequest = fetch(`${BASE}/ui-config`)
      .then((r) => (r.ok ? r.json() : { api_key: "" }))
      .then((c: { api_key?: string | null }) => c.api_key ?? "")
      .catch(() => "");
  }
  return keyRequest;
}


/**
 * Whether it is worth attempting a request at all.
 *
 * True when an API host was configured, and also when the page is being served
 * over http(s) — that is the same-origin deployment, where the API is whatever
 * host this page came from. A build opened straight from the filesystem has no
 * host to call and fails immediately rather than hanging.
 */
export const isConfigured = () =>
  BASE.length > 0 ||
  (typeof window !== "undefined" && window.location.protocol.startsWith("http"));

async function call<T>(path: string, init?: RequestInit): Promise<T> {
  if (!isConfigured()) throw new Error("no API configured");

  // A judge watching a video should never sit through a hung fetch. The backend
  // takes ~50s for a full run, but every *read* here is a quick lookup.
  const abort = new AbortController();
  const timer = setTimeout(() => abort.abort(), 15_000);

  try {
    const response = await fetch(`${BASE}${path}`, {
      ...init,
      signal: abort.signal,
      headers: {
        "Content-Type": "application/json",
        "X-API-Key": await apiKey(),
        ...init?.headers,
      },
    });
    if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
    return (await response.json()) as T;
  } finally {
    clearTimeout(timer);
  }
}

/** Read a path. Throws on anything that is not a successful response. */
export const read = <T,>(path: string) => call<T>(path);

export interface SubmittedEvent {
  run_id: string;
  message_id: string;
  trace_id: string | null;
}

/** Submit an artifact. Returns the run to follow — the work itself is async. */
export async function submitEvent(body: {
  kind: string;
  subject: string;
  source_uri?: string;
  body?: Record<string, unknown>;
}): Promise<SubmittedEvent> {
  return call<SubmittedEvent>("/events", { method: "POST", body: JSON.stringify(body) });
}

export interface RunStatus {
  status: string;
  cursor: string | null;
  kind?: string;
  updated_at?: string;
}

export const getRun = (runId: string) => call<RunStatus>(`/runs/${runId}`);

export const getHealth = () =>
  call<{
    status: string;
    env: string;
    project: string;
    vertex_location: string;
    model_fast: string;
    model_deep: string;
  }>("/health");

export interface Uploaded {
  source_uri: string;
  content_type: string;
  bytes: number;
}

/** Store a file and get back the URI to submit as an event. */
export async function uploadArtifact(file: File): Promise<Uploaded> {
  if (!isConfigured()) throw new Error("no API configured");

  const form = new FormData();
  form.append("file", file);

  // No Content-Type header: the browser has to set the multipart boundary, and
  // overriding it produces a request the server cannot parse.
  const response = await fetch(`${BASE}/artifacts`, {
    method: "POST",
    headers: { "X-API-Key": await apiKey() },
    body: form,
  });

  if (!response.ok) {
    const detail = await response.text().catch(() => "");
    throw new Error(`${response.status} ${detail.slice(0, 200)}`);
  }
  return (await response.json()) as Uploaded;
}

/** Record a human's decision on a gated action. Does not execute it — the run
 *  picks the settled approval up on its next tick. */
export async function decideApproval(approvalId: string, approved: boolean): Promise<void> {
  await call(`/approvals/${approvalId}`, {
    method: "POST",
    body: JSON.stringify({ approved, decided_by: "caregiver" }),
  });
}
