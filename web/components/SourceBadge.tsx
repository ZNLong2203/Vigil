import type { Source } from "@/lib/api";

/**
 * Says where the data on screen came from.
 *
 * This exists because the alternative is worse than showing nothing: a screen
 * quietly displaying committed fixtures while implying it is live is a lie the
 * viewer cannot detect, and a demo that gets caught doing it loses the benefit
 * of everything else it shows. The badge is small, permanent, and honest.
 */
export function SourceBadge({ source, error }: { source: Source; error?: string }) {
  if (source === "live") {
    // Static. "live" means this was read from the deployed API, not that
    // something is happening right now — and a badge that pulses on every
    // screen at all times is decoration wearing the clothes of a signal. The
    // one animated element in this interface is the fleet indicator in the
    // header, and it moves only when an agent is actually working.
    return (
      <span className="chip chip-ok" title="Read from the deployed API">
        <span
          aria-hidden
          style={{
            width: "0.4rem",
            height: "0.4rem",
            borderRadius: "999px",
            background: "currentColor",
            display: "inline-block",
          }}
        />
        live
      </span>
    );
  }

  return (
    <span
      className="chip chip-muted"
      title={
        error
          ? `The API did not answer (${error}), so this is the committed sample data.`
          : "No API configured — showing the committed sample data."
      }
    >
      sample data
    </span>
  );
}
