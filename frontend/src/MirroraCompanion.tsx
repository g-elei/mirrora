import React, { useEffect, useMemo, useState } from "react";
import ChatWindow from "./components/ChatWindow";
import GraphVisualizer from "./components/GraphVisualizer";
import HistoryPanel from "./components/HistoryPanel";
import ModeSelector from "./components/ModeSelector";
import PersonaPicker from "./components/PersonaPicker";
import { fetchModes, fetchUserGraph, sendChatMessage } from "./services/api";
import { GraphData, Message, Mode } from "./types/mirrora";

const USER_ID = "local";
const MODE_KEY = "mirrora.mode";

export default function MirroraCompanion() {
  const [modes, setModes] = useState<Record<string, Mode>>({});
  const [mode, setMode] = useState(() => localStorage.getItem(MODE_KEY) ?? "confidant");
  const [picking, setPicking] = useState(true);
  const [messages, setMessages] = useState<Message[]>([]);
  const [graph, setGraph] = useState<GraphData>({ nodes: [], edges: [] });
  const [loading, setLoading] = useState(false);
  const [apiError, setApiError] = useState<string | null>(null);
  const [historyRefresh, setHistoryRefresh] = useState(0);

  useEffect(() => {
    fetchModes()
      .then((m) => {
        setModes(m);
        const saved = localStorage.getItem(MODE_KEY);
        if (!saved || !m[saved]) setMode(m["confidant"] ? "confidant" : Object.keys(m)[0]);
      })
      .catch((err) => setApiError(String(err?.message ?? err)));
    fetchUserGraph(USER_ID)
      .then(setGraph)
      .catch((err) => setApiError(String(err?.message ?? err)));
  }, []);

  const choose = (id: string) => {
    setMode(id);
    localStorage.setItem(MODE_KEY, id);
    setPicking(false);
  };

  const handleSend = useMemo(
    () => async (text: string) => {
      setMessages((prev) => [...prev, { sender: "user", text }]);
      setLoading(true);
      setApiError(null);
      try {
        const res = await sendChatMessage(USER_ID, text, mode);
        setMessages((prev) => [
          ...prev,
          {
            sender: "mirrora",
            text: res.reply ?? "…",
            mode: res.mode,
            recommendations: res.recommendations ?? [],
            crisis: Boolean(res.crisis),
          },
        ]);
        if (res.personal_graph) setGraph(res.personal_graph);
        setHistoryRefresh((k) => k + 1);
      } catch (err: any) {
        setMessages((prev) => [
          ...prev,
          { sender: "mirrora", text: `Something went wrong: ${err?.message ?? err}` },
        ]);
        setApiError(String(err?.message ?? err));
      } finally {
        setLoading(false);
      }
    },
    [mode]
  );

  return (
    <div className="min-h-screen">
      <div className="max-w-6xl mx-auto px-6 py-8">
        <header className="mb-6">
          <div className="flex items-baseline gap-3">
            <h1 className="font-serif text-3xl text-gold-300 tracking-wide">Mirrora</h1>
            <span className="text-[10px] uppercase tracking-widest text-slate-600 border border-ink-700 rounded-full px-2.5 py-1">
              verified corpus
            </span>
          </div>
          <p className="text-sm text-slate-500 mt-1">
            A literary companion — every passage quoted verbatim from a verified classic.
          </p>
        </header>

        {apiError && (
          <div className="mb-4 text-xs text-amber-300 bg-amber-950/40 border border-amber-800/50 rounded-xl px-4 py-2.5">
            API unreachable ({apiError}). Start the backend with <code>uvicorn app.main:app --reload</code>, then refresh.
          </div>
        )}

        {picking && (
          <PersonaPicker
            modes={modes}
            currentMode={mode}
            onPick={choose}
            canDismiss
            onDismiss={() => setPicking(false)}
          />
        )}

        <ModeSelector
          modes={modes}
          currentMode={mode}
          onSelectMode={(id: string) => {
            setMode(id);
            localStorage.setItem(MODE_KEY, id);
          }}
        />

        <main className="flex flex-col lg:flex-row gap-4 items-start">
          <div className="flex-1 w-full">
            <ChatWindow messages={messages} onSendMessage={handleSend} loading={loading} />
          </div>
          <aside className="w-full lg:w-80 flex flex-col gap-4">
            <GraphVisualizer graph={graph} />
            <HistoryPanel userId={USER_ID} refreshKey={historyRefresh} />
          </aside>
        </main>

        <footer className="mt-8 text-center text-[11px] text-slate-700">
          Mirrora is a course prototype, not a medical service. If you are in crisis, please reach out
          to someone you trust or a professional hotline.
        </footer>
      </div>
    </div>
  );
}