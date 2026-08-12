"use client";

/**
 * What a screen shows when it has no data yet, and when it cannot get any.
 *
 * These two states used to be invisible. Every reader fell back to a committed
 * fixture the moment a request failed, so a page that could not reach the API
 * looked identical to one that could — and for the entire life of the deployment
 * that is the page everybody saw. Removing the fallback means these two
 * components are now the honest answer, and they have to be good: an error state
 * a viewer cannot act on is only a prettier way of showing nothing.
 */

/** The skeleton is shaped like the content that replaces it, so the page does
 *  not jump when the data lands. */
export function LoadingScreen({ what }: { what: string }) {
  return (
    <div data-density="calm" className="h-full overflow-y-auto">
      <div className="mx-auto max-w-3xl px-4 py-10">
        <div className="flex items-center gap-2.5">
          <span className="live-dot" aria-hidden />
          <p className="eyebrow">Reading {what}</p>
        </div>

        <div className="panel mt-5 overflow-hidden" aria-hidden>
          <div className="panel-head">
            <span className="eyebrow">&nbsp;</span>
          </div>
          <div className="p-4 space-y-3">
            {[0, 1, 2, 3].map((i) => (
              <div
                key={i}
                className="skeleton h-3"
                style={{ width: `${[92, 74, 83, 58][i]}%`, animationDelay: `${i * 0.12}s` }}
              />
            ))}
          </div>
        </div>

        <p className="mt-4 text-[0.86rem] text-[var(--text-2)]">
          The service scales to zero when idle, so the first request after a quiet
          period waits for a container to start.
        </p>
      </div>
    </div>
  );
}

/**
 * The error state, written for someone who cannot read the source.
 *
 * It names what was being fetched, what came back, and the two things that are
 * actually likely — a service scaled to zero and still starting, or one that has
 * been torn down after filming — because "something went wrong" tells a viewer
 * nothing they did not already know from the blank screen.
 */
export function ErrorScreen({
  what,
  error,
  onRetry,
}: {
  what: string;
  error?: string;
  onRetry?: () => void;
}) {
  return (
    <div data-density="calm" className="h-full overflow-y-auto">
      <div className="mx-auto max-w-2xl px-4 py-12">
        <p className="eyebrow" style={{ color: "var(--rose)" }}>
          Cannot reach the fleet
        </p>
        <h1 className="mt-2 text-[1.35rem] font-medium tracking-tight">
          This screen reads {what} from the deployed service, and the request did not
          come back.
        </h1>

        <div
          className="panel mt-6 p-4"
          style={{ borderColor: "color-mix(in oklab, var(--rose) 35%, var(--line))" }}
        >
          <p className="eyebrow">What came back</p>
          <p className="mono text-[0.85rem] mt-1.5" style={{ color: "var(--text-1)" }}>
            {error ?? "no response"}
          </p>
        </div>

        <p className="mt-6 text-[0.95rem] leading-relaxed text-[var(--text-1)]">
          Two explanations are likely. The service runs at zero instances when idle, so a
          first request after a quiet spell can time out while a container starts —
          trying again usually works. Otherwise the deployment has been shut down, which
          happens to this one after filming.
        </p>

        <p className="mt-3 text-[0.95rem] leading-relaxed text-[var(--text-1)]">
          There is deliberately nothing to fall back to. This page previously carried a
          committed copy of the data and displayed it whenever a request failed, which
          meant a broken connection and a working one looked the same.
        </p>

        {onRetry && (
          <button
            type="button"
            onClick={onRetry}
            className="chip mt-6"
            style={{ borderColor: "var(--azure)", color: "var(--azure)" }}
          >
            Try again
          </button>
        )}
      </div>
    </div>
  );
}

/** Nothing failed; there is genuinely nothing yet. Distinct from an error, and
 *  a screen that conflates the two teaches a viewer to distrust both. */
export function EmptyScreen({ title, detail }: { title: string; detail: string }) {
  return (
    <div data-density="calm" className="h-full overflow-y-auto">
      <div className="mx-auto max-w-2xl px-4 py-12">
        <p className="eyebrow">Nothing here yet</p>
        <h1 className="mt-2 text-[1.25rem] font-medium tracking-tight">{title}</h1>
        <p className="mt-3 text-[0.95rem] leading-relaxed text-[var(--text-1)]">{detail}</p>
      </div>
    </div>
  );
}
