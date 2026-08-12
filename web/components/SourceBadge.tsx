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
    return (
      <span className="chip chip-ok" title="Read from the deployed API">
        <span className="live-dot" style={{ width: "0.4rem", height: "0.4rem" }} aria-hidden />
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
