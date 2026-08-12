import { INTAKE_SAMPLES } from "@/lib/mock";
import type { IntakeArtifact } from "@/lib/types";

/**
 * Intake — the multimodal surface.
 *
 * The whole argument of this screen is the pairing: the messy thing on the left,
 * the structured thing on the right, and the transformation legible between
 * them. A clean render of a clean document proves nothing.
 */

const KIND_GLYPH: Record<IntakeArtifact["kind"], string> = {
  photo: "▣",
  voice_note: "◈",
  document: "▤",
};

const KIND_LABEL: Record<IntakeArtifact["kind"], string> = {
  photo: "Photo",
  voice_note: "Voice note",
  document: "Document",
};

function kb(bytes: number) {
  return bytes > 1e6 ? `${(bytes / 1e6).toFixed(1)} MB` : `${Math.round(bytes / 1e3)} KB`;
}

function Artifact({ item }: { item: IntakeArtifact }) {
  return (
    <article className="panel overflow-hidden">
      <div className="panel-head">
        <div className="flex items-center gap-2.5 min-w-0">
          <span className="text-[var(--text-2)] text-lg leading-none" aria-hidden>
            {KIND_GLYPH[item.kind]}
          </span>
          <span className="mono text-[0.85rem] truncate">{item.filename}</span>
          <span className="chip chip-muted">{KIND_LABEL[item.kind]}</span>
        </div>
        <span className="eyebrow shrink-0">{kb(item.bytes)}</span>
      </div>

      <div className="grid md:grid-cols-2 divide-y md:divide-y-0 md:divide-x divide-[var(--line-soft)]">
        {/* Left: what makes this input hard. */}
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
              <p className="text-[0.8rem] mt-2 text-[var(--text-1)]">
                The document&rsquo;s legitimate content was still processed. Blocking the payload
                did not cost us the lab values.
              </p>
            </div>
          )}
        </div>

        {/* Right: what came out. */}
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
            <span className="mono text-[0.72rem] text-[var(--text-2)]">{item.duration_ms} ms</span>
          </div>
        </div>
      </div>
    </article>
  );
}

export default function IntakePage() {
  return (
    <div data-density="calm" className="h-full overflow-y-auto">
      <div className="mx-auto max-w-4xl px-4 py-6">
        <h1 className="text-lg font-medium">Intake</h1>
        <p className="text-[var(--text-1)] text-[0.9rem] mt-1 mb-5">
          Drop a photo, a voice note or a scan. Nothing is expected to be tidy.
        </p>

        {/* Drop target. Wired to the API in the next pass; the shape is settled. */}
        <div
          className="rounded-[var(--radius)] border border-dashed p-8 text-center mb-6"
          style={{ borderColor: "var(--line)" }}
        >
          <p className="text-[0.95rem]">Drop files here</p>
          <p className="text-[var(--text-2)] text-[0.82rem] mt-1">
            JPEG · PNG · PDF · M4A · WAV — or record a voice note
          </p>
          <div className="flex items-center justify-center gap-2 mt-3">
            <button type="button" className="btn">
              Choose files
            </button>
            <button type="button" className="btn">
              ◈ Record
            </button>
          </div>
        </div>

        <div className="flex items-center gap-3 mb-3">
          <span className="eyebrow">Recently processed</span>
          <span className="h-px flex-1 bg-[var(--line-soft)]" />
        </div>

        <div className="space-y-4">
          {INTAKE_SAMPLES.map((item) => (
            <Artifact key={item.id} item={item} />
          ))}
        </div>
      </div>
    </div>
  );
}
