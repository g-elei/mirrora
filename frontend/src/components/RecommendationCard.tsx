import React from "react";
import { Recommendation } from "../types/mirrora";

interface Props {
  recommendations: Recommendation[];
}

const FIT_STYLE: Record<string, string> = {
  strong: "bg-emerald-950/70 text-emerald-300 border-emerald-800/60",
  fair: "bg-amber-950/70 text-amber-300 border-amber-800/60",
  weak: "bg-slate-800 text-slate-400 border-slate-700",
};

function asPercent(score: unknown): number | null {
  const n = Number(score);
  if (!Number.isFinite(n) || n <= 0) return null;
  return Math.round(n <= 1 ? n * 100 : n);
}

function QuoteCard({ rec }: { rec: Recommendation }) {
  const r = rec as Record<string, any>;
  const quote = r.quote ?? r.passage ?? r.text ?? r.pitch ?? "";
  const book = r.book ?? r.title ?? "";
  const location = r.location ?? "";
  const byline = [book, location].filter(Boolean).join(" · ");
  const creator = r.creator ? `by ${r.creator}` : "";
  const explanation = r.explanation ?? "";
  const reasoning: string[] = r.graph_reasoning ?? [];
  const pct = asPercent(r.score);
  const fit = String(r.fit ?? "").toLowerCase();
  const badge = FIT_STYLE[fit];

  return (
    <div className="bg-ink-800/80 border border-gold-500/25 rounded-xl p-4 mt-3 max-w-xl w-full">
      <div className="flex items-start justify-between gap-2 mb-2">
        <span className="font-serif text-gold-300 text-xl leading-none select-none">❝</span>
        <div className="flex items-center gap-2">
          {badge && (
            <span className={`px-2 py-0.5 rounded border text-[10px] ${badge}`}>
              fit: {fit}
            </span>
          )}
          {pct !== null && (
            <span className="px-2 py-0.5 rounded bg-ink-700/70 text-slate-300 text-[10px]">
              score {pct}{Number(rec.score) <= 1 ? "%" : ""}
            </span>
          )}
        </div>
      </div>
      <p className="font-serif text-[15px] leading-relaxed text-slate-100">{quote}</p>
      {byline && (
        <p className="text-[11px] text-gold-400/80 mt-2">
          — {byline}
          {creator && <span className="text-slate-500"> {creator}</span>}
        </p>
      )}
      {explanation && (
        <p className="text-xs text-slate-400 mt-2 leading-relaxed border-t border-ink-700/60 pt-2">
          {explanation}
        </p>
      )}
      {reasoning.length > 0 && (
        <div className="flex flex-wrap gap-1.5 mt-2">
          {reasoning.map((reason, i) => (
            <span key={i} className="bg-ink-700/60 text-slate-300 px-2 py-0.5 rounded text-[10px]">
              {reason}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

export default function RecommendationCard({ recommendations }: Props) {
  if (!recommendations || recommendations.length === 0) return null;
  return (
    <>
      {recommendations.map((rec, idx) => (
        <QuoteCard key={idx} rec={rec} />
      ))}
    </>
  );
}