import json
from pathlib import Path

base = Path(__file__).parent

with open(base / "taxonomy.json", encoding="utf-8") as f:
    tax = json.load(f)

with open(base / "scenarios.json", encoding="utf-8") as f:
    data = json.load(f)

emotions = set(tax["emotions"])
situations = set(tax["situations"])
themes = set(tax["themes"])

assert len(data) == 11, f"expected 11 scenarios, got {len(data)}"
assert len({s["id"] for s in data}) == 11, "duplicate scenario ids"

errors = []
for s in data:
    sid = s["id"]
    for key in ("id", "text", "language", "gold"):
        if key not in s:
            errors.append(f"{sid}: missing '{key}'")
    g = s["gold"]
    for e in g["emotions"]:
        if e["label"] not in emotions:
            errors.append(f"{sid}: emotion '{e['label']}' not in taxonomy")
        if not (1 <= e["intensity"] <= 5):
            errors.append(f"{sid}: intensity out of range for {e['label']}")
    if g["situation"] is not None and g["situation"] not in situations:
        errors.append(f"{sid}: situation '{g['situation']}' not in taxonomy")
    for k in ("primary_theme", "secondary_theme"):
        if g[k] is not None and g[k] not in themes:
            errors.append(f"{sid}: {k} '{g[k]}' not in taxonomy")
    if not isinstance(g["should_abstain"], bool):
        errors.append(f"{sid}: should_abstain not bool")
    if not isinstance(g["should_reject_ids"], list):
        errors.append(f"{sid}: should_reject_ids not list")
    if not isinstance(g["should_flag_crisis"], bool):
        errors.append(f"{sid}: should_flag_crisis not bool")

# Requirement coverage checks
langs = {s["language"] for s in data}
assert "zh" in langs, "missing Chinese scenario"
assert any(s["gold"]["should_abstain"] for s in data), "missing abstain scenario"
assert any(s["gold"]["should_reject_ids"] for s in data), "missing fake-ID scenario"
assert any(s["gold"]["should_flag_crisis"] for s in data), "missing crisis scenario"
assert any(s["gold"]["situation"] == "peer_comparison" for s in data), "missing peer_comparison"
assert any(s["gold"]["situation"] == "performing_wellness" for s in data), "missing performing_wellness"

if errors:
    print("ERRORS:")
    for e in errors:
        print(" -", e)
    raise SystemExit(1)

print(f"OK: {len(data)} scenarios valid; taxonomy consistent; all required cases present.")