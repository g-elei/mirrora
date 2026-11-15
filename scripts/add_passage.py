"""Add one passage to the corpus, verbatim, by pointing at a phrase in a source text.

The whole difficulty of this project's corpus is that a passage must be *real text*, not
a paraphrase. So this script does not accept a quote — it accepts an ANCHOR (a short
phrase you know is in the book) and extracts a contiguous window around it from the local
Gutenberg file. You cannot accidentally invent prose, because none of it is typed by you.

Typical run:
  python scripts/add_passage.py --book "Jane Eyre" --anchor "I envy you your peace" \\
      --location "Chapter XIV" --themes identity,loss --expresses envy,shame

  add --dry-run to preview without writing.
"""
from __future__ import annotations

import argparse, json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from validate_corpus import SOURCES, norm, MAX_WORDS          # reuse the same rules

SEED = ROOT / "data" / "seed" / "passages.json"
TAX = json.loads((ROOT / "evaluation" / "taxonomy.json").read_text(encoding="utf-8"))
TEXTS = ROOT.parent / "literary_kg" / "texts"


def extract(stem: str, anchor: str, lo: int = 55, hi: int = MAX_WORDS) -> str:
    raw = TEXTS / f"{stem}.txt"
    if not raw.exists():
        raise SystemExit(f"source text missing: {raw}")
    text = norm(raw.read_text(encoding="utf-8", errors="replace"))
    i = text.find(norm(anchor))
    if i < 0:
        raise SystemExit(f"anchor not found in {raw.name}: {anchor!r}\n"
                         f"Pick a phrase you can see in the file (case-sensitive, punctuation matters).")
    # if the anchor sits mid-sentence, start at the previous sentence boundary so the
    # quotation reads as a sentence rather than a fragment
    prev = text.rfind(".", max(0, i - 400), i)
    if prev >= 0 and (i - prev) < 400:
        i = prev + 1
        while i < len(text) and text[i] == " ":
            i += 1
    end = text.find(".", i + len(anchor)) + 1
    if end <= 0:
        raise SystemExit("could not find a sentence boundary after the anchor")
    while len(text[i:end].split()) < lo and end > 0:
        nxt = text.find(".", end)
        if nxt < 0:
            break
        end = nxt + 1
        if len(text[i:end].split()) > hi:
            end = text.rfind(".", i, end - 1) + 1
            break
    return text[i:end].strip()


def next_id(stem: str, existing: list[dict]) -> str:
    nums = [int(p["id"].rsplit(".", 1)[1]) for p in existing
            if p["id"].startswith(f"passage.{stem}.") and p["id"].rsplit(".", 1)[1].isdigit()]
    return f"passage.{stem}.{max(nums, default=0) + 1:03d}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--book", required=True)
    ap.add_argument("--anchor", required=True, help="a short phrase that exists in the text")
    ap.add_argument("--location", required=True, help="chapter / section, human-readable")
    ap.add_argument("--themes", default="", help="comma separated, from taxonomy")
    ap.add_argument("--expresses", default="", help="comma separated emotions the passage FEELS")
    ap.add_argument("--addresses", default="", help="comma separated emotions it CONSULTS")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    book_l = a.book.lower()
    stem = next((v for k, v in SOURCES.items() if k in book_l), None)
    if stem is None:
        raise SystemExit(f"no local source text mapped for {a.book!r}. Known: {sorted(SOURCES)}")

    text = extract(stem, a.anchor)
    words = len(text.split())

    themes = [t.strip() for t in a.themes.split(",") if t.strip()]
    exp = [e.strip() for e in a.expresses.split(",") if e.strip()]
    addr = [x.strip() for x in a.addresses.split(",") if x.strip()]
    for t in themes:
        if t not in TAX["themes"]:
            raise SystemExit(f"unknown theme {t!r}; allowed: {TAX['themes']}")
    for e in exp + addr:
        if e not in TAX["emotions"]:
            raise SystemExit(f"unknown emotion {e!r}; allowed: {TAX['emotions']}")
    if set(exp) & set(addr):
        raise SystemExit("an emotion cannot be both expressed and addressed")

    existing = json.loads(SEED.read_text(encoding="utf-8"))
    pid = next_id(stem, existing)
    rec = {"id": pid, "text": text, "book": a.book, "location": a.location,
           "themes": themes, "expresses": exp, "addresses": addr}

    print(f"{pid}  ({words} words)\n\n{text}\n")
    if a.dry_run:
        print("dry run — nothing written")
        return 0

    existing.append(rec)
    SEED.write_text(json.dumps(existing, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"added; corpus now {len(existing)} passages")

    import subprocess
    r = subprocess.run([sys.executable, "scripts/validate_corpus.py"], cwd=ROOT)
    return r.returncode


if __name__ == "__main__":
    sys.exit(main())
