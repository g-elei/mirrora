import React, { useMemo, useState } from "react";
import { GraphData } from "../types/mirrora";

interface Props {
  graph: GraphData;
}

const W = 300;
const H = 280;
const CX = W / 2;
const CY = H / 2;

const RING: Record<string, number> = {
  emotion: 62,
  goal: 62,
  value: 62,
  struggle: 62,
  achievement: 62,
  preference: 92,
  theme: 96,
  passage: 122,
};

const FILL: Record<string, string> = {
  user: "#e6bd7f",
  emotion: "#f59e0b",
  theme: "#34d399",
  passage: "#38bdf8",
};

const LABEL: Record<string, string> = {
  user: "you",
  emotion: "felt",
  theme: "themes",
  passage: "quoted",
  goal: "goals",
  value: "values",
  struggle: "struggles",
  achievement: "wins",
  preference: "preferences",
};

function short(label: string | undefined, id: string) {
  const s = label || id.split(":").pop() || id;
  return s.length > 13 ? s.slice(0, 12) + "…" : s;
}

export default function GraphVisualizer({ graph }: Props) {
  const [active, setActive] = useState<string | null>(null);

  const root = graph.nodes.find((n) => n.group === "user");
  const others = graph.nodes.filter((n) => n.group !== "user");

  const { pos, neighbors } = useMemo(() => {
    const pos: Record<string, { x: number; y: number }> = {};
    if (root) pos[root.id] = { x: CX, y: CY };
    const groups: Record<string, typeof others> = {};
    others.forEach((n) => {
      (groups[n.group] = groups[n.group] || []).push(n);
    });
    Object.keys(groups).forEach((g) => {
      const list = groups[g];
      const r = RING[g] ?? 100;
      list.forEach((n, i) => {
        const a = (2 * Math.PI * i) / list.length - Math.PI / 2;
        pos[n.id] = { x: CX + r * Math.cos(a), y: CY + r * Math.sin(a) };
      });
    });
    const neighbors = new Set<string>();
    if (active) {
      neighbors.add(active);
      graph.edges.forEach((e) => {
        if (e.source === active) neighbors.add(e.target);
        if (e.target === active) neighbors.add(e.source);
      });
    }
    return { pos, neighbors };
  }, [graph, root, others, active]);

  const counts = useMemo(() => {
    const c: Record<string, number> = {};
    others.forEach((n) => {
      c[n.group] = (c[n.group] || 0) + 1;
    });
    return c;
  }, [others]);

  const legendGroups = Object.keys(FILL).filter((g) => graph.nodes.some((n) => n.group === g));

  return (
    <div className="w-full bg-ink-900 rounded-2xl border border-ink-700/70 p-4 flex flex-col shadow-[0_10px_40px_rgba(0,0,0,0.35)]">
      <div className="flex items-baseline justify-between mb-1">
        <h2 className="text-sm font-semibold text-gold-400 font-serif">Your map</h2>
        <span className="text-[10px] text-slate-600">{graph.nodes.length} nodes</span>
      </div>
      <p className="text-xs text-slate-500 mb-3">
        What you felt, what it points to, and which books answered.
      </p>

      {graph.nodes.length === 0 ? (
        <div className="py-10 text-center">
          <p className="text-xs text-slate-600 italic">
            No personal nodes yet — your graph grows with every check-in.
          </p>
        </div>
      ) : (
        <>
          <svg viewBox={`0 0 ${W} ${H}`} className="w-full">
            <circle cx={CX} cy={CY} r={RING.passage} fill="none" stroke="#28313f" strokeDasharray="2 5" />
            <circle cx={CX} cy={CY} r={RING.theme} fill="none" stroke="#28313f" strokeDasharray="2 5" />
            {graph.edges.map((e, i) => {
              const a = pos[e.source];
              const b = pos[e.target];
              if (!a || !b) return null;
              const w = Math.min(Number(e.weight ?? 1), 9);
              const dim = active && !(neighbors.has(e.source) && neighbors.has(e.target));
              return (
                <line
                  key={`e${i}`}
                  x1={a.x} y1={a.y} x2={b.x} y2={b.y}
                  stroke={dim ? "#1c232e" : "#4a5568"}
                  strokeWidth={1 + w / 6}
                  strokeOpacity={dim ? 0.5 : 0.8}
                />
              );
            })}
            {root && (
              <g>
                <circle cx={CX} cy={CY} r={9} fill={FILL.user} stroke="#0d1015" strokeWidth={2} />
                <text x={CX} y={CY + 22} textAnchor="middle" fontSize={9} fill="#e6bd7f">
                  you
                </text>
              </g>
            )}
            {others.map((n) => {
              const p = pos[n.id];
              if (!p) return null;
              const w = Math.min(Number(n.weight ?? 1), 8);
              const r = 4.5 + w;
              const dim = active && !neighbors.has(n.id);
              const isActive = active === n.id;
              return (
                <g
                  key={n.id}
                  onMouseEnter={() => setActive(n.id)}
                  onMouseLeave={() => setActive(null)}
                  onClick={() => setActive(isActive ? null : n.id)}
                  style={{ cursor: "pointer", opacity: dim ? 0.3 : 1, transition: "opacity .2s" }}
                >
                  <circle
                    cx={p.x} cy={p.y} r={r + (isActive ? 2 : 0)}
                    fill={FILL[n.group] ?? "#64748b"}
                    fillOpacity={0.9}
                    stroke={isActive ? "#f0d3a3" : "#0d1015"}
                    strokeWidth={isActive ? 2 : 1}
                  >
                    <title>{`${n.label ?? n.id} — ${LABEL[n.group] ?? n.group}${n.weight ? ` · weight ${n.weight}` : ""}`}</title>
                  </circle>
                  <text x={p.x} y={p.y - r - 4} textAnchor="middle" fontSize={8.5} fill={dim ? "#374252" : "#94a3b8"}>
                    {short(n.label, n.id)}
                  </text>
                </g>
              );
            })}
          </svg>

          <div className="flex flex-wrap gap-x-3 gap-y-1 mt-2 pt-3 border-t border-ink-700/60">
            {legendGroups.map((g) => (
              <span key={g} className="flex items-center gap-1 text-[10px] text-slate-500">
                <span className="w-2 h-2 rounded-full inline-block" style={{ background: FILL[g] }} />
                {LABEL[g] ?? g}
                {counts[g] ? ` ${counts[g]}` : ""}
              </span>
            ))}
          </div>
        </>
      )}
    </div>
  );
}