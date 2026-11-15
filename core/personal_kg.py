"""Phase 3 — the Personal Knowledge Graph.

Entities from Phase 1 §3: Entry, Goal, Value, Struggle, Achievement, Preference, Emotion.
Entries are check-ins; emotions attach to entries with intensity; the rest are long-lived
entities the user or the system records. SQLite, no AI, no server dependency.

Phase 3 is deliberately standalone: this module never calls a model. Phase 5 reads from it.
"""
from __future__ import annotations

import json, sqlite3, time
from pathlib import Path

DB = Path(__file__).resolve().parent.parent / "data" / "personal" / "mirrora.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS entries (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id TEXT NOT NULL, created_at TEXT NOT NULL, text TEXT NOT NULL,
  situation TEXT, primary_theme TEXT, secondary_theme TEXT,
  abstained INTEGER DEFAULT 0, crisis INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS entry_emotions (
  entry_id INTEGER NOT NULL, label TEXT NOT NULL, intensity INTEGER NOT NULL,
  FOREIGN KEY(entry_id) REFERENCES entries(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS entities (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id TEXT NOT NULL, kind TEXT NOT NULL, label TEXT NOT NULL,
  note TEXT, status TEXT DEFAULT 'active', created_at TEXT NOT NULL,
  UNIQUE(user_id, kind, label)
);
CREATE TABLE IF NOT EXISTS entry_matches (
  entry_id INTEGER NOT NULL, passage_id TEXT NOT NULL, score REAL NOT NULL,
  FOREIGN KEY(entry_id) REFERENCES entries(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS ix_entries_user ON entries(user_id, created_at);
"""

KINDS = ("goal", "value", "struggle", "achievement", "preference")


def connect(db: Path | str = DB) -> sqlite3.Connection:
    p = Path(db)
    p.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(p)
    con.row_factory = sqlite3.Row
    con.executescript(SCHEMA)
    return con


def add_entry(con, user_id: str, text: str, interpretation, matches=None) -> int:
    """interpretation: InterpreterOutput or dict with emotions/situation/primary_theme/..."""
    if hasattr(interpretation, "to_dict"):
        d = interpretation.to_dict()
    else:
        d = dict(interpretation)
    cur = con.execute(
        "INSERT INTO entries (user_id, created_at, text, situation, primary_theme, secondary_theme, abstained, crisis)"
        " VALUES (?,?,?,?,?,?,?,?)",
        (user_id, time.strftime("%Y-%m-%dT%H:%M:%S"), text, d.get("situation"),
         d.get("primary_theme"), d.get("secondary_theme"),
         int(bool(d.get("abstained"))), int(bool(d.get("crisis_flagged")))))
    eid = cur.lastrowid
    for e in d.get("emotions", []):
        con.execute("INSERT INTO entry_emotions (entry_id, label, intensity) VALUES (?,?,?)",
                    (eid, e["label"], int(e.get("intensity", 3))))
    for m in matches or []:
        pid = m["passage_id"] if isinstance(m, dict) else m.passage_id
        sc = m["score"] if isinstance(m, dict) else m.score
        con.execute("INSERT INTO entry_matches (entry_id, passage_id, score) VALUES (?,?,?)",
                    (eid, pid, float(sc)))
    con.commit()
    return eid


def recent_entries(con, user_id: str, limit: int = 10) -> list[dict]:
    rows = con.execute(
        "SELECT id, created_at, text, situation, primary_theme, secondary_theme, abstained, crisis"
        " FROM entries WHERE user_id=? ORDER BY id DESC LIMIT ?", (user_id, limit)).fetchall()
    out = []
    for r in rows:
        emo = con.execute("SELECT label, intensity FROM entry_emotions WHERE entry_id=?",
                          (r["id"],)).fetchall()
        out.append({**dict(r), "emotions": [dict(e) for e in emo]})
    return out


def graph(con: sqlite3.Connection, user_id: str, limit: int = 12) -> dict:
    """Projection for the viz.

    The earlier version was a star: user -> emotions, user -> themes, user -> entities,
    with nothing connecting the leaves. That renders as disconnected chips because it *is*
    disconnected. This version adds the two kinds of structure that actually carry meaning:

      - emotion <-> theme co-occurrence, from what the user actually wrote together
      - passages the user was actually shown, linked to their own themes and emotions,
        so the personal graph and the literary graph share nodes instead of being two
        parallel universes
    """
    from core.matching import load_corpus

    nodes, edges, seen = [], [], set()

    def node(nid, label, group, **kw):
        if nid not in seen:
            seen.add(nid)
            nodes.append({"id": nid, "label": label, "group": group, **kw})

    def edge(src, dst, label, weight=1):
        if src in seen and dst in seen:
            edges.append({"source": src, "target": dst, "label": label, "weight": weight})

    node(user_id, user_id, "user")

    # emotions the user has felt
    rows = con.execute(
        "SELECT e.label, MAX(e.intensity) i, COUNT(*) n FROM entry_emotions e"
        " JOIN entries t ON t.id=e.entry_id WHERE t.user_id=? GROUP BY e.label ORDER BY n DESC LIMIT ?",
        (user_id, limit)).fetchall()
    for r in rows:
        node(f"emo:{r['label']}", r["label"], "emotion", weight=r["n"], intensity=r["i"])
        edge(user_id, f"emo:{r['label']}", "FELT", r["n"])

    # themes the user has explored
    themes = con.execute(
        "SELECT primary_theme t, COUNT(*) n FROM entries WHERE user_id=? AND primary_theme IS NOT NULL"
        " GROUP BY primary_theme ORDER BY n DESC LIMIT ?", (user_id, limit)).fetchall()
    for r in themes:
        node(f"theme:{r['t']}", r["t"], "theme", weight=r["n"])
        edge(user_id, f"theme:{r['t']}", "EXPLORES", r["n"])

    # emotion <-> theme co-occurrence: this is the structure the star version lacked
    co = con.execute(
        "SELECT e.label emo, t.primary_theme th, COUNT(*) n FROM entry_emotions e"
        " JOIN entries t ON t.id=e.entry_id"
        " WHERE t.user_id=? AND t.primary_theme IS NOT NULL GROUP BY e.label, t.primary_theme",
        (user_id,)).fetchall()
    for r in co:
        node(f"emo:{r['emo']}", r["emo"], "emotion")
        node(f"theme:{r['th']}", r["th"], "theme")
        edge(f"emo:{r['emo']}", f"theme:{r['th']}", "IN", r["n"])

    # entities (goals, values, struggles...)
    for r in con.execute("SELECT kind, label, status FROM entities WHERE user_id=? ORDER BY kind, label",
                         (user_id,)).fetchall():
        nid = f"{r['kind']}:{r['label']}"
        node(nid, r["label"], r["kind"], status=r["status"])
        edge(user_id, nid, r["kind"].upper(), 1)

    # passages actually recommended, plus their own themes/emotions from the seed corpus
    corpus = {p["id"]: p for p in load_corpus()}
    used = con.execute(
        "SELECT passage_id, MAX(score) s, COUNT(*) n FROM entry_matches WHERE entry_id IN"
        " (SELECT id FROM entries WHERE user_id=?) GROUP BY passage_id ORDER BY s DESC LIMIT ?",
        (user_id, limit)).fetchall()
    for r in used:
        p = corpus.get(r["passage_id"])
        if not p:
            continue
        nid = p["id"]
        node(nid, p.get("book", p["id"]), "passage", weight=r["n"], score=round(r["s"], 2),
             passage_id=p["id"])
        edge(user_id, nid, "QUOTED", r["n"])
        for t in p.get("themes", [])[:2]:
            node(f"theme:{t}", t, "theme")
            edge(nid, f"theme:{t}", "EXPLORES", 1)
        for e in p.get("expresses", [])[:2] + p.get("addresses", [])[:2]:
            node(f"emo:{e}", e, "emotion")
            edge(nid, f"emo:{e}", "EXPRESSES" if e in p.get("expresses", []) else "ADDRESSES", 1)

    return {"nodes": nodes, "edges": edges}


def add_entity(con, user_id: str, kind: str, label: str, note: str = "") -> int:
    kind = kind.lower().strip()
    if kind not in KINDS:
        raise ValueError(f"kind must be one of {KINDS}")
    con.execute("INSERT OR IGNORE INTO entities (user_id, kind, label, note, created_at) VALUES (?,?,?,?,?)",
                (user_id, kind, label.strip(), note, time.strftime("%Y-%m-%dT%H:%M:%S")))
    con.commit()
    return con.execute("SELECT id FROM entities WHERE user_id=? AND kind=? AND label=?",
                       (user_id, kind, label.strip())).fetchone()["id"]
