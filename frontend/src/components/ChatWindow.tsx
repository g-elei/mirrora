import React, { useEffect, useRef, useState } from "react";
import { Message } from "../types/mirrora";
import RecommendationCard from "./RecommendationCard";

interface Props {
  messages: Message[];
  onSendMessage: (text: string) => void;
  loading: boolean;
  suggestions?: string[];
}

const SUGGESTIONS = [
  "I failed my midterm and everyone else did fine…",
  "Everyone thinks I'm doing great, but it's costing me sleep.",
  "I'm scared of graduating and losing this community.",
];

export default function ChatWindow({ messages, onSendMessage, loading, suggestions }: Props) {
  const [input, setInput] = useState("");
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = scrollRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [messages, loading]);

  const handleSend = (text?: string) => {
    const value = (text ?? input).trim();
    if (!value || loading) return;
    onSendMessage(value);
    setInput("");
  };

  const showSuggestions = messages.length === 0 && !loading;

  return (
    <div className="flex-1 flex flex-col bg-ink-900 rounded-2xl border border-ink-700/70 overflow-hidden shadow-[0_10px_40px_rgba(0,0,0,0.35)]">
      <div ref={scrollRef} className="flex-1 p-5 space-y-5 overflow-y-auto max-h-[62vh] min-h-[42vh]">
        {showSuggestions && (
          <div className="h-full flex flex-col items-center justify-center text-center px-6 py-10">
            <div className="font-serif text-3xl text-gold-300 mb-2">❝</div>
            <p className="text-sm text-slate-400 max-w-sm leading-relaxed">
              Write a sentence or two about how today actually went — not the version you
              tell other people. Mirrora reads the feeling behind it and answers with a real
              passage from a verified classic.
            </p>
            <div className="mt-6 w-full max-w-md space-y-2">
              {(suggestions ?? SUGGESTIONS).map((s) => (
                <button
                  key={s}
                  onClick={() => handleSend(s)}
                  className="w-full text-left text-xs text-slate-400 bg-ink-800/70 hover:bg-ink-800 hover:text-slate-200 border border-ink-700/70 rounded-xl px-4 py-2.5 transition"
                >
                  {s}
                </button>
              ))}
            </div>
            <p className="mt-5 text-[11px] text-slate-600">
              Every quotation is verified verbatim against the source text — never generated from memory.
            </p>
          </div>
        )}

        {messages.map((msg, idx) => (
          <div key={idx} className={`flex flex-col animate-fade-up ${msg.sender === "user" ? "items-end" : "items-start"}`}>
            <div
              className={`max-w-xl rounded-2xl px-4 py-3 text-sm leading-relaxed ${
                msg.sender === "user"
                  ? "bg-ink-700 text-slate-100 rounded-br-sm"
                  : msg.crisis
                    ? "bg-rose-950/60 border border-rose-800/60 text-rose-100 rounded-bl-sm"
                    : "bg-ink-800 border border-ink-700/70 text-slate-200 rounded-bl-sm"
              }`}
            >
              {msg.mode && (
                <div className="flex items-center gap-1.5 text-[10px] uppercase tracking-widest text-gold-400 mb-1.5">
                  <span className="w-1.5 h-1.5 rounded-full bg-gold-400 inline-block" />
                  {msg.mode}
                </div>
              )}
              <p className="whitespace-pre-wrap">{msg.text}</p>
            </div>
            {msg.recommendations && msg.recommendations.length > 0 && (
              <RecommendationCard recommendations={msg.recommendations} />
            )}
          </div>
        ))}

        {loading && (
          <div className="flex items-center gap-1.5 text-xs text-slate-500">
            <span className="w-1.5 h-1.5 rounded-full bg-gold-400 animate-dot-bounce" />
            <span className="w-1.5 h-1.5 rounded-full bg-gold-400 animate-dot-bounce [animation-delay:0.15s]" />
            <span className="w-1.5 h-1.5 rounded-full bg-gold-400 animate-dot-bounce [animation-delay:0.3s]" />
            <span className="ml-1">Mirrora is reading…</span>
          </div>
        )}
      </div>

      <div className="p-4 border-t border-ink-700/70 flex gap-2 bg-ink-900">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSend()}
          placeholder="Share how you're feeling or what's on your mind…"
          className="flex-1 bg-ink-800 border border-ink-700/70 rounded-xl px-4 py-2.5 text-sm placeholder:text-slate-600 focus:outline-none focus:border-gold-500/60 transition"
        />
        <button
          onClick={() => handleSend()}
          disabled={loading || !input.trim()}
          className="bg-gold-500 hover:bg-gold-400 disabled:opacity-40 disabled:cursor-not-allowed text-ink-950 px-5 py-2.5 rounded-xl text-sm font-semibold transition"
        >
          Send
        </button>
      </div>
    </div>
  );
}