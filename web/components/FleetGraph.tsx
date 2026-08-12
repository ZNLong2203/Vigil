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
  const byName = new Map(registry.map((r) => [r.name, r]));
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

      {/* ── The refused call. Dashed, and it crosses a boundary. ──────── */}
      {denied.map((d) => {
        const from = byName.get(d.from);
        const target = registry.find((r) => r.owner === d.to_department);
        if (!from || !target) return null;
        const x1 = from.pos.x - NODE_W / 2;
        const x2 = target.pos.x + NODE_W / 2;
        const mid = (x1 + x2) / 2;
        return (
          <g key={`denied-${d.from}`}>
            <line
              x1={x1}
              y1={from.pos.y}
              x2={x2}
              y2={target.pos.y}
              stroke="var(--rose)"
              strokeWidth={1.5}
              strokeDasharray="5 4"
            />
            <circle cx={mid} cy={from.pos.y} r={11} fill="var(--bg-0)" stroke="var(--rose)" />
            <text
              x={mid}
              y={from.pos.y + 4}
              textAnchor="middle"
              fontSize="12"
              fill="var(--rose)"
              aria-hidden
            >
              ⊘
            </text>
            <text x={mid} y={from.pos.y - 20} textAnchor="middle" fontSize="10" fill="var(--rose)">
              denied by Agent Identity
            </text>
          </g>
        );
      })}

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
