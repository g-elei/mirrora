import React, { useEffect, useState } from "react";
import { fetchHistory } from "../services/api";
import { HistoryEntry } from "../types/mirrora";

interface Props {
  userId: string;
  refreshKey: number;
}

function normalize(payload: any): HistoryEntry[] {
  if (Array.isArray(payload)) return payload;
  return payload?.history ?? payload?.entries ?? [];
}

function emotionName(e: any): string {
  return typeof e === "string" ? e : e?.label ?? e?.name ?? "";
}

function emotionIntensity(e: any): number | null {
  const n = Number(e?.intensity);
  return Number.isFinite(n) && n > 0 ? n : null;
}

export default function HistoryPanel({ userId, refreshKey }: Props) {
  const [entries, setEntries] = useState<HistoryEntry[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetchHistory(userId)
      .then((data) => {
        if (!cancelled) {
          setEntries(normalize(data).slice().reverse());
          setError(null);
        }
      })
      .catch((err) => {
        if (!cancelled) setError(String(err?.message ?? err));
      });
    return () => {
      cancelled = true;
    };
  }, [userId, refreshKey]);

  return (
    <div className="w-full bg-ink-900 rounded-2xl border border-ink-700/70 p-4 shadow-[0_10px_40px_rgba(0,0,0,0.35)]">
      <div className="flex items-baseline justify-between mb-2">
        <h2 className="text-sm font-semibold text-gold-400 font-serif">Earlier entries</h2>
        <span className="text-[10px] text-slate-600">{entries.length} recorded</span>
      </div>

      {error ? (
        <p className="text-xs text-slate-600 italic">
          History endpoint unreachable — is the API running?
        </p>
      ) : entries.length === 0 ? (
        <p className="text-xs text-slate-600 italic">Nothing yet. Your past check-ins will gather here.</p>
      ) : (
        <ul className="space-y-3 max-h-64 overflow-y-auto pr-1">
          {entries.map((e, i) => (
            <li key={e.id ?? i} className="bg-ink-800/60 border border-ink-700/60 rounded-xl p-3">
              <div className="flex items-center justify-between gap-2 mb-1">
                <span className="text-[10px] text-slate-600">
                  {e.created_at ?? e.date ?? ""}
                </span>
                {e.crisis && (
                  <span className="text-[10px] px-1.5 py-0.5 rounded bg-rose-950 text-rose-300 border border-rose-800/60">
                    crisis routed
                  </span>
                )}
                {e.abstained && (
                  <span className="text-[10px] px-1.5 py-0.5 rounded bg-ink-700 text-slate-400">
                    abstained
                  </span>
                )}
              </div>
              <p className="text-xs text-slate-300 leading-relaxed line-clamp-3">{e.text}</p>
              <div className="flex flex-wrap gap-1 mt-2">
                {(e.emotions ?? []).map((em, j) => (
                  <span key={j} className="text-[10px] px-2 py-0.5 rounded-full bg-amber-950/60 text-amber-300 border border-amber-800/50">
                    {emotionName(em)}
                    {emotionIntensity(em) ? ` · ${emotionIntensity(em)}` : ""}
                  </span>
                ))}
                {(e.themes ?? []).map((t, j) => (
                  <span key={j} className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-950/60 text-emerald-300 border border-emerald-800/50">
                    {t}
                  </span>
                ))}
              </div>
              {typeof e.passage === "object" && e.passage?.book && (
                <p className="text-[10px] text-sky-300/80 mt-2">quoted: {e.passage.book}</p>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}