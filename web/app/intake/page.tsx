"use client";

import { useCallback, useEffect, useState } from "react";
import { Dropzone, type Dropped } from "@/components/Dropzone";
import { ScreenIntro } from "@/components/ScreenIntro";
import { SourceBadge } from "@/components/SourceBadge";
import { isConfigured, submitEvent, uploadArtifact, withFallback } from "@/lib/api";
import { INTAKE_SAMPLES, SUBJECT } from "@/lib/mock";
import type { IntakeArtifact } from "@/lib/types";

/**
 * Intake — the multimodal surface, and the only screen that writes.
 *
 * The argument of this page is the pairing: the messy thing that arrived, and
 * the structured thing that came out, with the transformation legible between
 * them. A clean render of a clean document proves nothing.
 *
 * The second argument is time. A fleet run is three agent hops and takes about a
 * minute and a half, so the honest thing to show is progress — which agent has
 * the work, what it has done — rather than a spinner that could equally mean
 * "thinking" or "dead". Every step below is read from the real audit trail.
 */

type Stage = "idle" | "uploading" | "queued" | "running" | "done" | "failed";

interface Tracked {
  id: string;
  filename: string;
  kind: Dropped["kind"];
  bytes: number;
  stage: Stage;
  runId?: string;
  sourceUri?: string;
  error?: string;
  events: { action: string; actor: string; decision: string; at: string }[];
}

const STAGE_LABEL: Record<Stage, string> = {
  idle: "waiting",
  uploading: "storing",
  queued: "queued",
  running: "the fleet has it",
  done: "done",
  failed: "failed",
};

const STAGE_CHIP: Record<Stage, string> = {
  idle: "chip chip-muted",
  uploading: "chip chip-info",
  queued: "chip chip-info",
  running: "chip chip-ok",
  done: "chip chip-ok",
  failed: "chip chip-deny",
};

/** Plain language for the audit actions that show up during a run. */
const STEP_LABEL: Record<string, string> = {
  "event.ingested": "Event accepted",
  "artifact.uploaded": "Artifact stored",
  "guardrail.blocked": "Injected instructions blocked",
  "tool.denied": "Cross-boundary read denied",
  "tool.loop_broken": "Agent loop broken",
  "agent.step_replayed": "Step already done — skipped",
  "escalation.raised": "Escalated for a human",
  "watchdog.escalated": "Verification escalated",
  "run.finished": "Run finished",
};

function kb(bytes: number) {
  return bytes > 1e6 ? `${(bytes / 1e6).toFixed(1)} MB` : `${Math.round(bytes / 1e3)} KB`;
}

function Progress({ item }: { item: Tracked }) {
  return (
    <div className="panel overflow-hidden">
      <div className="panel-head">
        <div className="flex items-center gap-2.5 min-w-0">
          <span className="mono text-[0.85rem] truncate">{item.filename}</span>
          <span className="chip chip-muted">{item.kind.replace("_", " ")}</span>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          {item.stage === "running" && <span className="live-dot" aria-hidden />}
          <span className={STAGE_CHIP[item.stage]}>{STAGE_LABEL[item.stage]}</span>
          <span className="eyebrow">{kb(item.bytes)}</span>
        </div>
      </div>

      <div className="p-4">
        {item.error && (
          <p className="text-[0.86rem]" style={{ color: "var(--rose)" }}>
            {item.error}
          </p>
        )}

        {item.runId && (
          <p className="mono text-[0.72rem] text-[var(--text-2)] mb-2">run {item.runId}</p>
        )}

        {item.events.length === 0 && !item.error ? (
          <p className="text-[0.86rem] text-[var(--text-1)]">
            {item.stage === "uploading"
              ? "Storing the file…"
              : "Waiting for the orchestrator to pick it up. A full run is three agents and takes about a minute and a half."}
          </p>
        ) : (
          <ol className="space-y-1.5">
            {item.events.map((event, index) => (
              <li key={`${event.at}-${index}`} className="flex items-baseline gap-2 text-[0.86rem]">
                <span className="mono text-[0.72rem] text-[var(--text-2)] shrink-0">
                  {new Date(event.at).toLocaleTimeString("en-GB", {
                    hour: "2-digit",
                    minute: "2-digit",
                    second: "2-digit",
                  })}
                </span>
                <span
                  className={
                    event.decision === "blocked" || event.decision === "denied"
                      ? "chip chip-deny"
                      : event.decision === "escalated"
                        ? "chip chip-wait"
                        : "chip chip-ok"
                  }
                >
                  {event.actor}
                </span>
                <span className="text-[var(--text-1)]">
                  {STEP_LABEL[event.action] ?? event.action.replace(/[._]/g, " ")}
                </span>
              </li>
            ))}
          </ol>
        )}
      </div>
    </div>
  );
}

function Sample({ item }: { item: IntakeArtifact }) {
  return (
    <article className="panel overflow-hidden">
      <div className="panel-head">
        <span className="mono text-[0.85rem] truncate">{item.filename}</span>
        <span className="eyebrow shrink-0">{kb(item.bytes)}</span>
      </div>
      <div className="grid md:grid-cols-2 divide-y md:divide-y-0 md:divide-x divide-[var(--line-soft)]">
        <div className="p-4">
          <p className="eyebrow mb-2">As received</p>
          <p className="text-[0.9rem] leading-relaxed text-[var(--text-1)]">{item.difficulty}</p>
          {item.blocked && (
            <div
              className="mt-3 rounded-md border p-3"
              style={{
                borderColor: "color-mix(in oklab, var(--rose) 40%, transparent)",
                background: "color-mix(in oklab, var(--rose) 8%, transparent)",
              }}
            >
              <p className="chip chip-deny mb-2">
                <span aria-hidden>⊘</span> blocked at the trust boundary
              </p>
              <p className="text-[0.85rem] text-[var(--text-1)]">{item.blocked.reason}</p>
              <p className="mono text-[0.72rem] mt-2 text-[var(--text-2)] leading-relaxed">
                &ldquo;{item.blocked.excerpt}&rdquo;
              </p>
            </div>
          )}
        </div>
        <div className="p-4">
          <p className="eyebrow mb-2">Extracted</p>
          <dl className="space-y-1.5">
            {Object.entries(item.extracted).map(([key, value]) => (
              <div key={key} className="flex gap-3 text-[0.88rem]">
                <dt className="mono text-[var(--text-2)] min-w-[10rem] shrink-0">{key}</dt>
                <dd className="text-[var(--text-0)]">{String(value)}</dd>
              </div>
            ))}
          </dl>
          <div className="mt-3 pt-3 border-t border-[var(--line-soft)] flex items-center gap-2.5 flex-wrap">
            <span className="chip chip-memory">{item.redactions} identifiers tokenised</span>
            <span className="mono text-[0.72rem] text-[var(--text-2)]">{item.model}</span>
          </div>
        </div>
      </div>
    </article>
  );
}

export default function IntakePage() {
  const [tracked, setTracked] = useState<Tracked[]>([]);
  const live = isConfigured();

  const update = useCallback((id: string, patch: Partial<Tracked>) => {
    setTracked((current) =>
      current.map((item) => (item.id === id ? { ...item, ...patch } : item)),
    );
  }, []);

  const handleFiles = useCallback(
    async (dropped: Dropped[]) => {
      for (const { file, kind } of dropped) {
        const id = `${file.name}-${Date.now()}-${Math.round(Math.random() * 1e6)}`;
        setTracked((current) => [
          { id, filename: file.name, kind, bytes: file.size, stage: "uploading", events: [] },
          ...current,
        ]);

        try {
          const stored = await uploadArtifact(file);
          update(id, { stage: "queued", sourceUri: stored.source_uri });

          const submitted = await submitEvent({
            kind: kind === "photo" ? "photo" : kind === "voice_note" ? "voice_note" : "document",
            subject: SUBJECT,
            source_uri: stored.source_uri,
            body: { filename: file.name },
          });
          update(id, { stage: "running", runId: submitted.run_id });
        } catch (error) {
          update(id, {
            stage: "failed",
            error: error instanceof Error ? error.message : String(error),
          });
        }
      }
    },
    [update],
  );

  // Poll the audit trail for anything still in flight. Stops on its own once
  // every tracked run is finished, so an idle tab is not a background job.
  useEffect(() => {
    const inFlight = tracked.filter((t) => t.stage === "running" && t.runId);
    if (!inFlight.length) return;

    const timer = setInterval(async () => {
      for (const item of inFlight) {
        const { data, source } = await withFallback<{
          entries: { action: string; actor: string; decision: string; at: string }[];
        }>(`/audit?run_id=${item.runId}&limit=50`, { entries: [] });
        if (source !== "live") continue;

        const events = [...data.entries].sort((a, b) => a.at.localeCompare(b.at));
        const finished = events.some((e) => e.action === "run.finished");
        update(item.id, { events, stage: finished ? "done" : "running" });
      }
    }, 5000);

    return () => clearInterval(timer);
  }, [tracked, update]);

  return (
    <div data-density="calm" className="h-full overflow-y-auto">
      <div className="mx-auto max-w-4xl px-4 py-6">
        <ScreenIntro title="Intake" aside={<SourceBadge source={live ? "live" : "fixture"} />}>
          {live ? (
            <>
              Drop in a photo, a recording or a scan. Three agents read it, check each other,
              and stop for you if they are not sure. <em>Watch the steps appear</em> — a full
              run takes about a minute and a half, and you can see which agent has it.
            </>
          ) : (
            <>
              No backend is answering, so nothing can be uploaded. The examples below show
              what the pipeline does with each kind of difficult input.
            </>
          )}
        </ScreenIntro>

        <Dropzone onFiles={handleFiles} disabled={!live} />

        {tracked.length > 0 && (
          <>
            <div className="flex items-center gap-3 mt-6 mb-3">
              <span className="eyebrow">In flight</span>
              <span className="h-px flex-1 bg-[var(--line-soft)]" />
            </div>
            <div className="space-y-4">
              {tracked.map((item) => (
                <Progress key={item.id} item={item} />
              ))}
            </div>
          </>
        )}

        {/* Worked examples, labelled as such.
            
            These are hand-written illustrations of what the pipeline does with
            each kind of difficult input — not captured output. Presenting
            authored data under a heading like "recently processed" would be the
            exact ambiguity the source badge exists to prevent, so the heading
            says what they are and they sit below anything real. */}
        <div className="flex items-center gap-3 mt-6 mb-3">
          <span className="eyebrow">Worked examples — illustrations, not captured output</span>
          <span className="h-px flex-1 bg-[var(--line-soft)]" />
        </div>
        <div className="space-y-4">
          {INTAKE_SAMPLES.map((item) => (
            <Sample key={item.id} item={item} />
          ))}
        </div>
      </div>
    </div>
  );
}
