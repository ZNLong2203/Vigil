"use client";

import type { DeniedEdge, RegistryEntry } from "@/lib/registry";
import { DEPARTMENT_BANDS } from "@/lib/registry";
import type { Department } from "@/lib/types";

/**
 * The registry, drawn.
 *
 * Hand-placed coordinates rather than a force layout: a demo needs the same
 * frame on every take, and a graph that rearranges itself between renders is
 * useless for that. It also lets the four department bands mean something
 * spatially — an agent sits inside the boundary that owns it, and the one
 * refused edge visibly crosses a boundary it does not hold.
 */

const DEPT_VAR: Record<Department, string> = {
  family: "var(--phosphor)",
  clinical: "var(--azure)",
  benefits: "var(--amber)",
  audit: "var(--violet)",
};

const NODE_W = 170;
const NODE_H = 52;

export function FleetGraph({
  registry,
  denied,
  selected,
  onSelect,
}: {
  registry: RegistryEntry[];
  denied: DeniedEdge[];
  selected: string;
  onSelect: (name: string) => void;
}) {
  const byName = new Map<string, RegistryEntry>(registry.map((r) => [r.name, r]));
  const root = registry.find((r) => r.name === "orchestrator")!;
  const workers = registry.filter((r) => r.name !== "orchestrator");

  return (
    <svg
      viewBox="0 0 1000 360"
      className="w-full h-auto"
      role="img"
      aria-label="Agent registry: five agents across four department boundaries"
    >
      {/* ── Department boundaries ─────────────────────────────────────── */}
      {DEPARTMENT_BANDS.map((band) => (
        <g key={band.id}>
          {/* color-mix() goes through `style` rather than a presentation
              attribute — attribute parsing for newer colour functions is not
              uniform across engines, CSS property parsing is. */}
          <rect
            x={band.x}
            y={30}
            width={band.width}
            height={150}
            rx={10}
            strokeDasharray="3 4"
            style={{
              fill: `color-mix(in oklab, ${DEPT_VAR[band.id]} 6%, transparent)`,
              stroke: `color-mix(in oklab, ${DEPT_VAR[band.id]} 28%, transparent)`,
            }}
          />
          <text
            x={band.x + 12}
            y={52}
            className="mono"
            fontSize="11"
            letterSpacing="1.6"
            fill={DEPT_VAR[band.id]}
          >
            {band.label.toUpperCase()}
          </text>
          <text x={band.x + 12} y={166} fontSize="10.5" fill="var(--text-2)">
            {band.note}
          </text>
        </g>
      ))}

      {/* ── Allowed calls: orchestrator reaches every worker ──────────── */}
      {workers.map((w) => (
        <path
          key={`edge-${w.name}`}
          d={`M ${root.pos.x} ${root.pos.y - NODE_H / 2} C ${root.pos.x} 210, ${w.pos.x} 210, ${w.pos.x} ${w.pos.y + NODE_H / 2}`}
          fill="none"
          stroke="var(--line)"
          strokeWidth={1.25}
        />
      ))}

      {/* ── The boundary the selected agent is sealed inside. ─────────────

          Drawn as an enclosure rather than as lines reaching outward, and the
          route to that is worth recording because two earlier versions were
          confidently wrong in ways that only arithmetic caught.

          The first drew one hand-written denial as a line between two boxes.
          When the data became real, one agent had a boundary against every other
          department, and that code inherited an assumption it never stated —
          that the target lies to the left — so every rightward line was drawn
          back through the agent's own box. Fixing the direction was not enough:
          a line aimed at "some agent in the audit department" resolved to
          whichever agent happened to be first in the list, which for `family` is
          the orchestrator sitting well below the row, and long lines to distant
          departments cut straight across the boxes in between.

          The mistake underneath both was the metaphor. "Cannot reach department
          D" is not an arrow pointing at a member of D. Checked against the
          deployed registry, every agent holds only scopes its own department
          owns — no exceptions — so the true shape is a closed boundary around
          the agent's own band. It cannot collide with anything, it does not have
          to choose a representative agent, and it stays correct as the fleet
          grows. The departments it is kept out of are named in the panel beside
          the figure, where there is room to list the scopes as well. */}
      {(() => {
        const agent = byName.get(selected);
        const band = DEPARTMENT_BANDS.find((b) => b.id === agent?.owner);
        if (!agent || !band || denied.length === 0) return null;

        const left = band.x;
        const right = band.x + band.width;
        const y = agent.pos.y;
        const blocked = denied.map((d) => d.to_department).join(", ");

        return (
          <g>
            <title>
              {`${agent.name} holds only ${agent.owner} scopes. It is never handed a tool belonging to ${blocked}.`}
            </title>
            <rect
              x={left}
              y={30}
              width={band.width}
              height={150}
              rx={10}
              fill="none"
              stroke="var(--rose)"
              strokeWidth={1.5}
              strokeDasharray="6 4"
              opacity={0.9}
            />
            {[left, right].map((x) => (
              <g key={`seal-${x}`}>
                <circle cx={x} cy={y} r={11} fill="#0d1219" stroke="var(--rose)" strokeWidth={1.5} />
                <text
                  x={x}
                  y={y + 4}
                  textAnchor="middle"
                  fontSize="12"
                  fill="var(--rose)"
                  aria-hidden
                >
                  ⊘
                </text>
              </g>
            ))}
          </g>
        );
      })()}

      {/* ── Agents ───────────────────────────────────────────────────── */}
      {registry.map((entry) => {
        const active = entry.name === selected;
        const tint = DEPT_VAR[entry.owner];
        const rejected = entry.history.some((h) => h.status === "rejected");

        return (
          <g
            key={entry.name}
            transform={`translate(${entry.pos.x - NODE_W / 2}, ${entry.pos.y - NODE_H / 2})`}
            onClick={() => onSelect(entry.name)}
            style={{ cursor: "pointer" }}
            role="button"
            tabIndex={0}
            aria-pressed={active}
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                onSelect(entry.name);
              }
            }}
          >
            <rect
              width={NODE_W}
              height={NODE_H}
              rx={8}
              fill={active ? "var(--bg-3)" : "var(--bg-2)"}
              stroke={active ? tint : "var(--line)"}
              strokeWidth={active ? 1.75 : 1}
            />
            <rect width={3} height={NODE_H} rx={2} fill={tint} />
            <text x={14} y={22} className="mono" fontSize="12.5" fill="var(--text-0)">
              {entry.name}
            </text>
            <text x={14} y={39} className="mono" fontSize="10.5" fill="var(--text-2)">
              v{entry.version} · eval {entry.eval.score.toFixed(2)}
            </text>
            {rejected && (
              <>
                <circle cx={NODE_W - 15} cy={16} r={6} fill="var(--amber)" opacity={0.18} />
                <text
                  x={NODE_W - 15}
                  y={20}
                  textAnchor="middle"
                  fontSize="9"
                  fill="var(--amber)"
                >
                  !
                </text>
              </>
            )}
          </g>
        );
      })}

      <text x={root.pos.x} y={root.pos.y + 46} textAnchor="middle" fontSize="10.5" fill="var(--text-2)">
        holds no business tools — it can only look agents up and call them
      </text>
    </svg>
  );
}
