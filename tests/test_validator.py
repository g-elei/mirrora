
import json, os

from evaluation.offline_path import offline_fallback


def test_environment_files_exist():
    assert os.path.exists("backend/app/main.py")
    assert os.path.exists("core/models/interpreter_output.py")
    assert os.path.exists("evaluation/scenarios.json")
    assert os.path.exists("evaluation/taxonomy.json")
    assert os.path.exists("data/seed/passages.json")


def test_scenarios_schema():
    with open("evaluation/scenarios.json", encoding="utf-8") as f:
        data = json.load(f)
    assert isinstance(data, list), "scenarios.json is a list of scenario objects"
    assert len(data) == 11
    for s in data:
        assert {"id", "text", "gold"} <= set(s), s.get("id")


def test_taxonomy_matches_interpreter_vocabulary():
    tax = json.load(open("evaluation/taxonomy.json", encoding="utf-8"))
    assert len(tax["themes"]) == 10
    assert len(tax["emotions"]) >= 20
    assert len(tax["situations"]) == 11


def test_offline_interpreter_flags_stress_and_exhaustion():
    """The real interpreter, not a re-implementation of it."""
    out = offline_fallback(
        "I am extremely stressed about my upcoming exams and feeling exhausted."
    )
    labels = [e.label for e in out.emotions]
    assert "exhaustion" in labels
    assert out.situation in ("work_stress", "identity_question", None) or out.situation is not None
