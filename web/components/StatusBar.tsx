import { FLEET } from "@/lib/mock";

const STATE_STYLE: Record<string, { chip: string; glyph: string }> = {
  working: { chip: "chip chip-ok", glyph: "●" },
  waiting: { chip: "chip chip-wait", glyph: "⏸" },
  idle: { chip: "chip chip-muted", glyph: "○" },
};

/**
 * The fleet, always visible. This is the one place density is justified on
 * every screen: five agents and their state is the ambient fact the whole
 * product is about.
 */
export function StatusBar() {
  return (
    <footer
      data-density="dense"
      className="shrink-0 border-t border-[var(--line-soft)] px-4 py-1.5 flex items-center gap-3 flex-wrap"
    >
      <span className="eyebrow">Fleet</span>
      {FLEET.map((agent) => {
        const s = STATE_STYLE[agent.state] ?? STATE_STYLE.idle;
        return (
          <span key={agent.name} className={`${s.chip} dept-${agent.department}`}>
            <span aria-hidden>{s.glyph}</span>
            {agent.name}
          </span>
        );
      })}
      <span className="ml-auto eyebrow">
        gemini-3.5-flash · cloud run · us-central1
      </span>
    </footer>
  );
}
