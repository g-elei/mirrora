"""System tests for the four pieces that can be wrong silently: corpus validity,
matching, grounding, and persistence.

Run:  python -m unittest discover -s tests -v
"""
from __future__ import annotations

import json, os, subprocess, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import core.matching as matching
import core.personal_kg as pkg
import core.response as resp


class TestCorpus(unittest.TestCase):
    def test_validator_passes(self):
        r = subprocess.run([sys.executable, "scripts/validate_corpus.py"], cwd=ROOT,
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_validator_fails_fabrication(self):
        seed = json.loads((ROOT / "data/seed/passages.json").read_text(encoding="utf-8"))
        fake = dict(seed[0])
        fake["id"] = "passage.fake.001"
        fake["text"] = fake["text"] + " This is a completely fabricated sentence."
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
            json.dump([fake], fh)
            path = fh.name
        try:
            r = subprocess.run([sys.executable, "scripts/validate_corpus.py", path], cwd=ROOT,
                               capture_output=True, text=True)
            self.assertEqual(r.returncode, 0)
            self.assertIn("missing", r.stdout)
        finally:
            os.unlink(path)

    def test_every_tag_in_taxonomy(self):
        tax = matching.load_taxonomy()
        for p in matching.load_corpus():
            for t in p["themes"]:
                self.assertIn(t, tax["themes"], p["id"])
            for e in p["expresses"] + p["addresses"]:
                self.assertIn(e, tax["emotions"], p["id"])


class TestMatching(unittest.TestCase):
    def test_explanation_always_present(self):
        ms = matching.match("I feel behind everyone else", [("envy", 4)], "ambition", "identity")
        self.assertTrue(ms)
        for m in ms:
            self.assertTrue(m.explanation, f"{m.passage_id} has no explanation")

    def test_no_signal_returns_nothing(self):
        self.assertEqual(matching.match("", [], None), [])
        self.assertEqual(matching.match("hmm", [], None), [])

    def test_envy_prefers_passage_that_expresses_it(self):
        ms = matching.match("everyone got a better grade than me and I can't stand it",
                            [("envy", 5)], "ambition")
        top = ms[0]
        self.assertIn("envy", top.to_dict()["layers"] and top.passage_id and
                      next(p for p in matching.load_corpus() if p["id"] == top.passage_id)["expresses"])

    def test_weights_are_frozen(self):
        self.assertEqual(matching.WEIGHT_EMOTION, 0.45)
        self.assertEqual(matching.WEIGHT_THEME, 0.25)
        self.assertEqual(matching.WEIGHT_SEMANTIC, 0.30)


class TestGrounding(unittest.TestCase):
    def test_invented_quote_is_rejected(self):
        r = resp.validate_quotes("\u201cThe sea was angry that day, my friends\u201d")
        self.assertFalse(r.ok)

    def test_real_corpus_quote_is_accepted(self):
        p = matching.load_corpus()[0]
        r = resp.validate_quotes(f"\u201c{resp._first_sentence(p['text'])}\u201d")
        self.assertTrue(r.ok, r.violations)

    def test_composed_reply_is_grounded(self):
        ms = matching.match("I envy my friend's success", [("envy", 4)], "ambition")
        body, meta = resp.compose("I envy my friend's success", ms, "ambition")
        self.assertTrue(resp.validate_quotes(body).ok)
        self.assertEqual(meta["passage_id"], ms[0].passage_id)

    def test_crisis_offers_no_literature(self):
        body, meta = resp.compose("I don't want to be here anymore", [], None, crisis=True)
        self.assertFalse(resp.validate_quotes(body).violations)
        self.assertIsNone(meta["passage_id"])
        self.assertIn("crisis", body.lower())

    def test_ungrounded_llm_reply_falls_back(self):
        def bad_llm(system, user):
            return "\u201cTo be or not to be, that is the question\u201d"
        ms = matching.match("I envy my friend", [("envy", 4)], "ambition")
        body, meta = resp.generate("I envy my friend", ms, "ambition", llm=bad_llm)
        self.assertEqual(meta["source"], "rule")
        self.assertIn("grounding_rejected", meta)


class TestPersonalKG(unittest.TestCase):
    def setUp(self):
        self.db = Path(tempfile.mkdtemp()) / "t.db"
        self.con = pkg.connect(self.db)

    def tearDown(self):
        self.con.close()

    def test_entry_roundtrip_and_graph(self):
        out = {"emotions": [{"label": "envy", "intensity": 4}], "situation": "peer_comparison",
               "primary_theme": "ambition", "secondary_theme": "identity",
               "abstained": False, "crisis_flagged": False}
        ms = matching.match("I envy him", [("envy", 4)], "ambition", "identity")
        eid = pkg.add_entry(self.con, "u1", "I envy him", out, ms)
        recent = pkg.recent_entries(self.con, "u1", 2)
        self.assertEqual(len(recent), 1)
        self.assertEqual(recent[0]["emotions"][0]["label"], "envy")
        g = pkg.graph(self.con, "u1")
        # user -> emotion/theme edges must exist, and the recommended passage must be
        # linked into the same graph (that bridge is the point of the projection)
        ids = {n["id"] for n in g["nodes"]}
        self.assertIn("u1", ids)
        self.assertIn("emo:envy", ids)
        self.assertIn("theme:ambition", ids)
        self.assertTrue(any(n["group"] == "passage" for n in g["nodes"]))
        labels = {e["label"] for e in g["edges"]}
        self.assertTrue({"FELT", "EXPLORES", "QUOTED"} <= labels)
        # the projection must be a connected graph, not a star: emotion and theme are
        # linked to each other, and the quoted passage is linked to its own theme
        self.assertTrue(any(e["label"] == "IN" for e in g["edges"]))
        self.assertTrue(any(e["source"].startswith("passage.") for e in g["edges"]))

    def test_entity_kind_validated(self):
        pkg.add_entity(self.con, "u1", "goal", "finish the thesis")
        with self.assertRaises(ValueError):
            pkg.add_entity(self.con, "u1", "hobby", "chess")


if __name__ == "__main__":
    unittest.main()
