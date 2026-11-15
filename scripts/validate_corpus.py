"""Validate data/seed/passages.json.

This replaces a no-op: the previous version looked for a "content" field the seed
never had, printed a complaint per passage, and exited 0 regardless — so a fabricated
quotation would have "passed".

Checks:
  schema      required keys, id format, unique ids, duplicate texts, <=120 words
  taxonomy    themes and expresses/addresses must exist; the two sets must not overlap
  provenance  the text must appear VERBATIM in the named Gutenberg source

Usage:
  python scripts/validate_corpus.py
  python scripts/validate_corpus.py data/seed/passages.json [texts_dir]
"""
from __future__ import annotations

import json, re, sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
TAXONOMY = json.loads((BASE / "evaluation" / "taxonomy.json").read_text(encoding="utf-8"))
REQUIRED = {"id", "text", "book", "location", "themes", "expresses", "addresses"}
MAX_WORDS = 120

# book title fragment -> local Gutenberg text stem
SOURCES = {
    "meditations": "meditations",
    "pride and prejudice": "pride_prejudice",
    "frankenstein": "frankenstein",
    "jane eyre": "jane_eyre",
    "crime and punishment": "crime_punishment",
    "moby-dick": "moby_dick",
    "moby dick": "moby_dick",
    "odyssey": "odyssey",
    "walden": "walden",
    "leaves of grass": "leaves_of_grass",
    "great expectations": "great_expectations",
}


def norm(s: str) -> str:
    """Fold typographic quotes and whitespace so a line break or a curly apostrophe
    cannot make a genuine quotation look fabricated."""
    s = (s.replace("\u2019", "'").replace("\u2018", "'").replace("\u201c", '"')
         .replace("\u201d", '"').replace("\u2014", "—").replace("\u2013", "-")
         .replace("\u00a0", " "))
    return re.sub(r"\s+", " ", s).strip()


def main() -> int:
    rel = sys.argv[1] if len(sys.argv) > 1 else "data/seed/passages.json"
    path = Path(rel) if Path(rel).is_absolute() else BASE / rel
    texts = Path(sys.argv[2]) if len(sys.argv) > 2 else BASE.parent / "literary_kg" / "texts"

    if not path.exists():
        print(f"ERROR: {path} not found")
        return 1
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"ERROR: not valid JSON: {exc}")
        return 1
    if not isinstance(data, list):
        print("ERROR: seed file must be a JSON array of passages")
        return 1

    errors, warnings = [], []
    themes, emotions = set(TAXONOMY["themes"]), set(TAXONOMY["emotions"])
    ids, texts_seen = set(), {}

    for i, p in enumerate(data):
        tag = p.get("id", f"<index {i}>")
        if REQUIRED - set(p):
            errors.append(f"{tag}: missing fields {sorted(REQUIRED - set(p))}")
            continue
        if p["id"] in ids:
            errors.append(f"{tag}: duplicate id")
        ids.add(p["id"])
        if not re.fullmatch(r"passage\.[a-z0-9_]+\.\d{3}", p["id"]):
            warnings.append(f"{tag}: id does not match passage.<book>.<nnn>")

        words = len(p["text"].split())
        if words > MAX_WORDS:
            errors.append(f"{tag}: {words} words exceeds {MAX_WORDS}")

        folded = norm(p["text"])
        if folded in texts_seen:
            errors.append(f"{tag}: duplicate text (same as {texts_seen[folded]})")
        texts_seen[folded] = tag

        if bad := [t for t in p["themes"] if t not in themes]:
            errors.append(f"{tag}: unknown theme(s) {bad}")
        if bad := [e for e in p["expresses"] + p["addresses"] if e not in emotions]:
            errors.append(f"{tag}: unknown emotion(s) {bad}")
        if overlap := set(p["expresses"]) & set(p["addresses"]):
            warnings.append(f"{tag}: both expressed and addressed {sorted(overlap)} — "
                            f"redundant; the matcher counts it once at the higher weight")
        if not p["themes"]:
            warnings.append(f"{tag}: no themes")
        if not p["expresses"] and not p["addresses"]:
            warnings.append(f"{tag}: no emotions — the matcher can never reach it")

        book = p["book"].lower()
        stem = next((v for k, v in SOURCES.items() if k in book), None)
        if stem is None:
            warnings.append(f"{tag}: no local source for '{p['book']}' — verbatim check skipped")
            continue
        src = texts / f"{stem}.txt"
        if not src.exists():
            warnings.append(f"{tag}: {src} missing — verbatim check skipped")
            continue
        haystack = norm(src.read_text(encoding="utf-8", errors="replace"))
        if folded not in haystack:
            head = folded[:60]
            pos = haystack.find(head)
            where = f"found quotation start at char {pos}, then diverges" if pos >= 0 else "nothing resembling it"
            errors.append(f"{tag}: NOT verbatim in {stem}.txt ({where}) — altered or fabricated")

    print(f"{path.name}: {len(data)} passages | {len(themes)} themes | {len(emotions)} emotions")
    print(f"errors: {len(errors)}   warnings: {len(warnings)}")
    for e in errors:
        print(f"  error  {e}")
    for w in warnings:
        print(f"  warn   {w}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
