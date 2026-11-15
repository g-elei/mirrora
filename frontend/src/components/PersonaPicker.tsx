import React from "react";
import { Mode } from "../types/mirrora";

interface Props {
  modes: Record<string, Mode>;
  currentMode: string;
  onPick: (id: string) => void;
  canDismiss: boolean;
  onDismiss: () => void;
}

const SAMPLE_LINES: Record<string, string> = {
  warm: "“That weight you're carrying — someone has carried it before you.”",
  wise: "“Look at the pattern, not the moment.”",
  confidant: "“Tell it straight. I've got you.”",
  mentor: "“Name the obstacle. Then we move.”",
};

export default function PersonaPicker({ modes, currentMode, onPick, canDismiss, onDismiss }: Props) {
  const entries = Object.entries(modes);
  const current = modes[currentMode];

  return (
    <div
      className="fixed inset-0 z-50 bg-ink-950/85 backdrop-blur-sm flex items-center justify-center p-4"
      role="dialog"
      aria-modal="true"
    >
      <div className="w-full max-w-2xl bg-ink-900 border border-ink-700 rounded-2xl p-6 shadow-[0_20px_80px_rgba(0,0,0,0.6)] animate-fade-up">
        <h2 className="text-xl font-serif text-gold-300">Who should answer you today?</h2>
        <p className="text-xs text-slate-500 mt-1 mb-5">
          Same verified passages, different voice. You can switch any time.
        </p>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {entries.length === 0 && (
            <div className="text-xs text-slate-500 col-span-2">Loading personas…</div>
          )}
          {entries.map(([id, m]) => {
            const selected = id === currentMode;
            return (
              <button
                key={id}
                onClick={() => onPick(id)}
                className={`text-left p-4 rounded-xl border transition ${
                  selected
                    ? "bg-gold-500/10 border-gold-500/70"
                    : "bg-ink-800/70 border-ink-700 hover:border-ink-600"
                }`}
              >
                <div className="flex items-center gap-2">
                  <span className={`w-2 h-2 rounded-full ${selected ? "bg-gold-400" : "bg-slate-600"}`} />
                  <span className="text-sm font-medium text-slate-100">{m.name}</span>
                  {selected && (
                    <span className="ml-auto text-[10px] uppercase tracking-wide text-gold-400">last used</span>
                  )}
                </div>
                <div className="text-[11px] text-slate-500 mt-1">{m.role}</div>
                <div className="font-serif text-xs text-gold-300/80 mt-2 italic">
                  {SAMPLE_LINES[id] ?? "“I'll meet you where you are.”"}
                </div>
              </button>
            );
          })}
        </div>

        {canDismiss && (
          <button
            onClick={onDismiss}
            className="mt-5 w-full text-xs text-slate-500 hover:text-slate-300 transition"
          >
            Continue as {current?.name ?? "Mirrora"}
          </button>
        )}
      </div>
    </div>
  );
}