"""Mirrora API — Phase 3 capture, Phase 4 matching, Phase 5 grounded response.

The previous version answered with hardcoded moods and one hardcoded book. This version
has no hardcoded knowledge: passages come from data/seed/passages.json, tags are checked
against evaluation/taxonomy.json, and every reply is verified against the corpus before
it leaves the server.
"""
from __future__ import annotations

import os, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.config import settings   # import early so .env is loaded at startup
from app.models import ChatRequest
from app.personas import CHARACTER_MODES
import core.matching as matching
import core.personal_kg as pkg
import core.response as resp
from evaluation.offline_path import offline_fallback

app = FastAPI(title="Mirrora Literary Companion", version="0.4.0")

# Your React build is the product UI. `web/` is only a fallback for when it is absent.
DIST = ROOT / "frontend" / "dist"
if (DIST / "assets").is_dir():
    app.mount("/assets", StaticFiles(directory=DIST / "assets"), name="assets")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


class CheckinRequest(BaseModel):
    user_id: str = "local"
    text: str
    interpreter: str = "offline"     # "offline" | "qwen"
    mode: str = "confidant"


class EntityRequest(BaseModel):
    user_id: str = "local"
    kind: str
    label: str
    note: str = ""


def _interpret(text: str, which: str):
    if which == "qwen":
        from evaluation.qwen_path import live_qwen
        try:
            return live_qwen(text)
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Qwen unavailable: {exc}") from exc
    return offline_fallback(text)


def _llm_callable(mode: str):
    """Return a callable(system, user) or None when no key is configured."""
    key = settings.QWEN_API_KEY or os.getenv("DASHSCOPE_API_KEY") or os.getenv("QWEN_API_KEY")
    if not key:
        return None
    from app.llm_service import QwenLLMService
    svc = QwenLLMService()

    def call(system: str, user: str) -> str:
        persona = CHARACTER_MODES.get(mode, {}).get("system_prompt", "")
        return svc.generate_chat_response(f"{system}\n{persona}", user)
    return call


@app.get("/api/health")
def health():
    corpus = matching.load_corpus()
    return {"ok": True, "passages": len(corpus), "interpreter_default": "offline",
            "llm_configured": bool(settings.QWEN_API_KEY or os.getenv("DASHSCOPE_API_KEY"))}


@app.get("/api/modes")
def get_modes():
    return CHARACTER_MODES


@app.get("/api/corpus")
def corpus():
    c = matching.load_corpus()
    return {"count": len(c), "passages": [
        {k: p[k] for k in ("id", "book", "author", "location", "themes", "expresses", "addresses")}
        for p in c]}


@app.post("/api/checkin")
def checkin(req: CheckinRequest):
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="empty check-in")
    if req.mode not in CHARACTER_MODES:
        raise HTTPException(status_code=400, detail="invalid mode")

    out = _interpret(req.text, req.interpreter)
    d = out.to_dict()

    crisis = d.get("crisis_flagged") or d.get("crisis") or False
    abstained = d.get("abstained") or False

    # Crisis never receives a literary match: routing beats resonance.
    ms = [] if (crisis or abstained) else matching.match(
        req.text, d.get("emotions", []), d.get("primary_theme"), d.get("secondary_theme"))

    con = pkg.connect()
    try:
        eid = pkg.add_entry(con, req.user_id, req.text, d, ms)
        recent = pkg.recent_entries(con, req.user_id, limit=4)
        g = pkg.graph(con, req.user_id)
    finally:
        con.close()

    labels = [e.get("label", "") for e in d.get("emotions", [])]
    reply, meta = resp.generate(req.text, ms, d.get("primary_theme"), labels=labels,
                                persona=req.mode, llm=_llm_callable(req.mode),
                                recent=[r for r in recent if r["id"] != eid], crisis=crisis)
    meta["grounding"] = resp.validate_quotes(reply).to_dict()

    return {"entry_id": eid, "interpretation": d, "matches": [m.to_dict() for m in ms],
            "reply": reply, "reply_meta": meta, "graph": g}


@app.get("/api/history/{user_id}")
def history(user_id: str, limit: int = 20):
    con = pkg.connect()
    try:
        return {"entries": pkg.recent_entries(con, user_id, limit=limit)}
    finally:
        con.close()


@app.get("/api/graph/{user_id}")
def graph(user_id: str):
    con = pkg.connect()
    try:
        return pkg.graph(con, user_id)
    finally:
        con.close()


@app.post("/api/entities")
def add_entity(req: EntityRequest):
    con = pkg.connect()
    try:
        return {"id": pkg.add_entity(con, req.user_id, req.kind, req.label, req.note)}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        con.close()


@app.post("/api/chat")
def chat_endpoint(req: ChatRequest):
    """Compatibility projection over the real pipeline, so the React UI keeps its
    designed shape without touching its components. Every field here is derived from
    the corpus match — nothing is hardcoded."""
    data = checkin(CheckinRequest(user_id=req.user_id, text=req.message, mode=req.mode))
    d = data["interpretation"]
    recs = [{
        "title": m["book"],
        "media_type": "Book",
        "creator": m["author"],
        "pitch": m["explanation"][0] if m["explanation"] else "matched on theme",
        "score": m["score"],
        "graph_reasoning": m["explanation"],
    } for m in data["matches"]]
    data["mode"] = CHARACTER_MODES[req.mode]["name"]
    data["detected_signals"] = {
        "moods": [e["label"] for e in d.get("emotions", [])],
        "traits": [x for x in [d.get("situation"), d.get("primary_theme")] if x],
    }
    data["recommendations"] = recs
    data["personal_graph"] = data["graph"]
    return data


@app.get("/")
def index():
    built = DIST / "index.html"
    if built.exists():
        return FileResponse(built)
    fallback = ROOT / "web" / "index.html"
    if fallback.exists():
        return FileResponse(fallback)
    raise HTTPException(status_code=404,
                        detail="No UI built. Run: cd frontend && npm install && npm run build")
