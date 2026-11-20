"""Who executes a planned row (d-work #732): the record `dmc:executor-unit` decides it from the charters' fences
before scale-out and the unit lifecycle; it names five outcomes, its precedence orders each once, its default is the
charter gap, a path no fence covers being never dispatched unseen, and the Operating Guide's Step 0 cites it."""
import json
import unittest
from pathlib import Path
CRAFT = Path(__file__).resolve().parents[1]
RECORD = CRAFT / "dmc" / "executor-unit.jsonld"
GUIDE = CRAFT / "docs" / "operating-guide.md"
OUTCOMES = {"requester": "settles", "one-unit": "settles", "split": "settles",
            "charter-gap": "asks", "new-unit": "asks"}
NAMES = ["the requester", "one other unit", "a split by lane", "a charter gap", "a new unit"]

def record() -> dict:
    return json.loads(RECORD.read_text())

class ExecutorUnitTests(unittest.TestCase):
    def test_record_names_five_outcomes_with_their_effects(self):
        rec = record()
        self.assertEqual(rec["@id"], "urn:dyad:dmc:cabinet/executor-unit")
        self.assertEqual(rec["identifier"], "executor-unit")
        terms = {t["termCode"]: t["dyad:effect"] for t in rec["hasDefinedTerm"]}
        self.assertEqual(terms, OUTCOMES)

    def test_precedence_names_each_outcome_once_in_order(self):
        rec = record()
        order = rec["dyad:precedence"].split(":")[0]
        positions = [order.find(n) for n in NAMES]
        self.assertTrue(all(p >= 0 for p in positions), positions)
        self.assertEqual(positions, sorted(positions))
        for n in NAMES:
            self.assertEqual(order.count(n), 1, n)
        names = {t["termCode"]: t["name"] for t in rec["hasDefinedTerm"]}
        self.assertEqual([names[c] for c in OUTCOMES], NAMES)

    def test_default_is_the_charter_gap(self):
        self.assertTrue(record()["dyad:default"].startswith("a charter gap:"))

    def test_home_is_never_an_outcome(self):
        rec = record()
        self.assertIn("home executes no plan", " ".join(rec["dyad:inputs"]))
        self.assertNotIn("home", {t["termCode"] for t in rec["hasDefinedTerm"]})

    def test_guide_step_zero_cites_the_record(self):
        text = GUIDE.read_text()
        self.assertIn("**Before Step 0: who executes a planned row** (`dmc:executor-unit`", text)
        self.assertEqual(record()["dyad:home"], "docs/operating-guide.md")

if __name__ == "__main__":
    unittest.main()
