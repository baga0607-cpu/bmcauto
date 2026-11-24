"""Formatting must preserve evidence and identify only recorded Note fields."""
import copy
import unittest
from html.parser import HTMLParser

from report_case import method_table_rows, MethodResult
from report_html import method_row_html
from report_presentation import result_parts


class TextReader(HTMLParser):
    def __init__(self):
        super().__init__()
        self.text = ''

    def handle_data(self, value):
        self.text += value


class ReportEmphasisTest(unittest.TestCase):
    def row(self, **values):
        result = {'log_records': [{'kind': 'step', 'type': 'Checkpoint',
                                  'step': 'Check', 'result': values}]}
        original = copy.deepcopy(result)
        row = method_table_rows(result, {})[0]
        self.assertEqual(result, original)
        return row

    def test_note_boundary_is_not_inferred_from_actual_text(self):
        row = self.row(status='C-PASS', actual='body\nNote: not a note', note='Accepted <tag> & reason\nsecond line')
        before, note = result_parts(row[3])
        self.assertEqual(before, 'Actual: body\nNote: not a note\n')
        self.assertEqual(note, 'Note: Accepted <tag> & reason\nsecond line')
        html = method_row_html(row)
        self.assertEqual(html.count('class="result-note"'), 1)
        self.assertIn('Actual: body\nNote: not a note\n<span', html)
        self.assertIn('&lt;tag&gt; &amp;', html)
        reader = TextReader(); reader.feed(html)
        self.assertEqual(reader.text, ''.join((row[0], row[2], row[4], row[3])))

    def test_unstructured_note_words_are_not_promoted(self):
        row = self.row(status='PASS', actual='Note: just an observation')
        self.assertEqual(result_parts(row[3])[1], '')
        self.assertNotIn('result-note', method_row_html(row))

    def test_excerpt_preserves_boundary_only_when_note_is_visible(self):
        row = self.row(status='C-PASS', actual='x'*1250, note='Not visible')
        self.assertIn('[Excerpt', row[3])
        self.assertEqual(result_parts(row[3])[1], '')
        row = self.row(status='C-PASS', actual='short', note='n'*1500)
        self.assertTrue(result_parts(row[3])[1].startswith('Note: '))
        self.assertIn('[Excerpt', result_parts(row[3])[1])

    def test_note_only_manual_and_failed_action_preserve_text(self):
        for row in [self.row(status='FAIL', note='Failure evidence'),
                    ('', '—', 'Manual case judgement', MethodResult('Note: Reviewed', 0), 'C-PASS'),
                    self.row(status='FAILED', reason='Request failed')]:
            reader = TextReader(); reader.feed(method_row_html(row))
            self.assertEqual(reader.text, ''.join((row[0], row[2], row[4], row[3])))


if __name__ == '__main__':
    unittest.main()
