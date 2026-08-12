"use client";

import { useCallback, useEffect, useState } from "react";
import { Dropzone, type Dropped } from "@/components/Dropzone";
import { ScreenIntro } from "@/components/ScreenIntro";
import { read, submitEvent, uploadArtifact } from "@/lib/api";
import { IntakeRun } from "@/components/IntakeHistory";
import { useLive } from "@/lib/live";

/** The person this deployment coordinates care for. One subject, because the
 *  demo is about depth over weeks rather than breadth across accounts. */
const SUBJECT = "care-subject-001";

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

interface RunRow {
  run_id: string;
  kind?: string;
  status?: string;
  metadata?: { source_uri?: string | null } | null;
}

export default function IntakePage() {
  const [tracked, setTracked] = useState<Tracked[]>([]);

  // What the fleet has already read. This screen used to show nothing at all
  // until you dropped a file in — the in-flight list lives in component state,
  // so a reload emptied it and a first visit was a dropzone on an empty page.
  // Everything below is work the deployed system actually did.
  const runs = useLive<{ runs: RunRow[] }>("/runs?limit=25", 30_000);
  const history = (runs.data?.runs ?? [])
    .filter((r) => ["document", "photo", "voice_note"].includes(r.kind ?? ""))
    .slice(0, 8);

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
        try {
          const data = await read<{
            entries: { action: string; actor: string; decision: string; at: string }[];
          }>(`/audit?run_id=${item.runId}&limit=50`);

          const events = [...data.entries].sort((a, b) => a.at.localeCompare(b.at));
          const finished = events.some((e) => e.action === "run.finished");
          update(item.id, { events, stage: finished ? "done" : "running" });
        } catch {
          // One missed poll during a run is not worth reporting: the next tick
          // is five seconds away and the run is unaffected either way. A failure
          // that matters shows up as the run never reaching run.finished.
        }
      }
    }, 5000);

    return () => clearInterval(timer);
  }, [tracked, update]);

  return (
    <div data-density="calm" className="h-full overflow-y-auto">
      <div className="mx-auto max-w-4xl px-4 py-6">
        <ScreenIntro title="Intake">
          Drop in a photo, a recording or a scan. Three agents read it, check each other, and
          stop for you if they are not sure. <em>Watch the steps appear</em> — a full run takes
          about a minute and a half, and you can see which agent has it.
        </ScreenIntro>

        <Dropzone onFiles={handleFiles} />

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

        {history.length > 0 && (
          <>
            <div className="flex items-center gap-3 mt-7 mb-3">
              <span className="eyebrow">Already read</span>
              <span className="h-px flex-1 bg-[var(--line-soft)]" />
              <span className="eyebrow">what arrived · what was understood</span>
            </div>
            <div className="space-y-4">
              {history.map((run) => (
                <IntakeRun
                  key={run.run_id}
                  runId={run.run_id}
                  sourceUri={run.metadata?.source_uri}
                />
              ))}
            </div>
          </>
        )}

        {history.length === 0 && runs.status === "ready" && tracked.length === 0 && (
          <p className="mt-7 text-[0.9rem] leading-relaxed text-[var(--text-2)]">
            Nothing has been through intake yet. Drop a photo, a recording or a scan above and
            it appears here with the claims the agents extracted from it, and how sure they
            were about each one.
          </p>
        )}
      </div>
    </div>
  );
}
