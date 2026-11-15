import React from "react";
import { Mode } from "../types/mirrora";

interface Props {
  modes: Record<string, Mode>;
  currentMode: string;
  onSelectMode: (id: string) => void;
}

export default function ModeSelector({ modes, currentMode, onSelectMode }: Props) {
  return (
    <div className="flex flex-wrap gap-2 mb-5">
      {Object.entries(modes).map(([id, m]) => {
        const selected = currentMode === id;
        return (
          <button
            key={id}
            onClick={() => onSelectMode(id)}
            className={`flex items-center gap-2 pl-3 pr-4 py-1.5 rounded-full border text-xs transition ${
              selected
                ? "bg-gold-500/15 border-gold-500/70 text-gold-300"
                : "bg-ink-800/70 border-ink-700 text-slate-500 hover:text-slate-300 hover:border-ink-600"
            }`}
          >
            <span className={`w-1.5 h-1.5 rounded-full ${selected ? "bg-gold-400" : "bg-slate-600"}`} />
            {m.name}
          </button>
        );
      })}
    </div>
  );
}