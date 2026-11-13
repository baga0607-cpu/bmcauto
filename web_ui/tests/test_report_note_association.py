"""Read-only report note association regression checks."""
import copy
import unittest
from report_case import method_table_rows


class NoteAssociationTest(unittest.TestCase):
    def report(self, notes, case_note):
        result = {"note": case_note, "log_records": [
            {"kind": "step", "type": "Checkpoint", "step": "Check",
             "result": {"status": "C-PASS", "note": note}}
            for note in notes]}
        original = copy.deepcopy(result)
        rows = method_table_rows(result, {})
        self.assertEqual(result, original)
        return rows

    def test_aggregated_notes_keep_step_association(self):
        self.assertEqual(len(self.report(["Dialect accepted", "Endpoint accepted"],
                                        "Dialect accepted\nEndpoint accepted")), 2)

    def test_single_and_multiline_notes(self):
        note = "Scope checked\nReason accepted"
        self.assertEqual(len(self.report([note], note)), 1)
        self.assertEqual(len(self.report([note, "Other"], note + "\nOther")), 2)

    def test_long_note_is_not_duplicated_after_display_truncation(self):
        note = "Detailed evidence " * 200
        rows = self.report([note], note)
        self.assertEqual(len(rows), 1)
        self.assertIn("[Excerpt", rows[0][3])

    def test_unassociated_remainder_is_omitted(self):
        rows = self.report(["Known"], "Before\nKnown\nAfter")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][3], "Note: Known")

    def test_case_only_history_is_not_rendered(self):
        rows = self.report([], "Historical note")
        self.assertFalse(any("Historical note" in row[3] for row in rows))
        self.assertFalse(any("Case-level" in row[2] for row in rows))

    def test_only_step_note_is_rendered(self):
        rows = self.report(["Accepted"], "Accepted with extra restrictions")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][3], "Note: Accepted")

    def test_legacy_nested_checkpoint_note(self):
        result = {"note": "A\nB", "log_records": [{"kind": "step", "step": "Old",
                  "result": {"status": "PASS", "checks": [
                      {"label": "First", "passed": True, "note": "A"},
                      {"label": "Second", "passed": True, "note": "B"}]}}]}
        rows = method_table_rows(result, {})
        self.assertFalse(any(r[2].startswith("Case-level") for r in rows))


if __name__ == "__main__":
    unittest.main()
