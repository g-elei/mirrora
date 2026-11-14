# scripts/validate_corpus.py
import json
from pathlib import Path

# Which themes are coherent with which emotions.
# An `addresses` emotion must be backed by at least one theme in this set.
COHERENCE = {
    "envy":          {"ambition", "identity"},
    "self_doubt":    {"identity", "failure"},
    "shame":         {"identity", "fear"},
    "grief":         {"loss", "love"},
    "loneliness":    {"belonging", "love"},
    "anxiety":       {"fear", "time"},
    "frustration":   {"failure", "ambition"},
    "exhaustion":    {"time", "meaning"},
    "hope":          {"courage", "meaning"},
    "pride":         {"courage", "identity"},
    "love":          {"love", "belonging"},
    "fear":          {"fear", "identity"},
    "confusion":     {"identity", "meaning"},
    # extend as the corpus grows
}

def validate_passage(p: dict) -> list[str]:
    errors = []
    for emo in p.get("addresses", []):
        allowed = COHERENCE.get(emo)
        if allowed is None:
            continue  # unmapped emotion: don't block, flag in a separate list
        if not (set(p.get("themes", [])) & allowed):
            errors.append(
                f"'{p.get('id')}': addresses '{emo}' but themes "
                f"{p.get('themes', [])} have no coherent theme in {allowed}"
            )
    return errors

def main(path="data/seed/passages.json"):
    passages = json.loads(Path(path).read_text(encoding="utf-8"))
    all_errors = []
    for p in passages:
        all_errors += validate_passage(p)
    if all_errors:
        print(f"{len(all_errors)} coherence errors:")
        for e in all_errors:
            print(" -", e)
        raise SystemExit(1)
    print(f"OK: {len(passages)} passages pass coherence validation.")

if __name__ == "__main__":
    main()