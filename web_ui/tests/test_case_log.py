import io
import json
import sys
import unittest
import tempfile
from unittest.mock import patch
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from case_log import CaseLog, PrintLogWriter, log_filenames, open_log_files, test_log_text


class CaseLogTest(unittest.TestCase):
    def test_readable_names_are_safe_unique_and_bounded(self):
        names = log_filenames('Regression task', 'RF-01-003 OData Service Document Endpoint', 'task1', 'case1')
        self.assertIn('Regression task__RF-01-003', names['test'])
        self.assertNotEqual(names, log_filenames('Regression task', 'RF-01-003 OData Service Document Endpoint', 'task1', 'case1'))
        self.assertRegex(names['test'], r'^\d{8}_\d{6}_\d{6}[+-]\d{4}__')
        self.assertEqual(set(names), {'test'})
        self.assertTrue(names['test'].endswith('__test.log'))
        self.assertNotEqual(names, log_filenames('Regression task', 'RF-01-003 OData Service Document Endpoint', 'task2', 'case1'))
        unsafe = log_filenames('../../CON<>:"\\|?*\n' * 50, '中文測項' * 100, 'task', 'case')
        for value in unsafe.values():
            self.assertLess(len(value.encode('utf-16-le')) // 2, 150)
            self.assertFalse(any(char in value for char in '<>:"/\\|?*\n'))

    def test_rerun_and_collision_preserve_old_file(self):
        with tempfile.TemporaryDirectory() as root:
            first, output = open_log_files(root, 'Task', 'RF-01-001 Example', 'task', 'case')
            with output:
                output.write('old evidence')
            fresh = {'test': 'fresh__test.log'}
            with patch('case_log.log_filenames', side_effect=[first, fresh]):
                names, output = open_log_files(root, 'Task', 'Case', 'task', 'case')
            output.close()
            self.assertEqual(names, fresh)
            self.assertEqual((Path(root) / first['test']).read_text(), 'old evidence')

    def test_legacy_logs_preserve_unique_protocol_evidence(self):
        self.assertEqual(test_log_text('', 'HTTP only'), 'HTTP only')
        self.assertEqual(test_log_text('full HTTP', 'HTTP'), 'full HTTP')
        self.assertIn('separate body', test_log_text('result', 'separate body'))
        separator = '\n' + '=' * 72 + '\n'
        block = separator + 'HTTP evidence #1\nbody\n'
        self.assertEqual(test_log_text('header' + block + 'final', 'header' + block),
                         'header' + block + 'final')

    def test_sections_checks_http_and_final_share_readable_output(self):
        result, events = io.StringIO(), []
        log = CaseLog(result, events.append)
        log.section('Inspect document')
        raw = '{"nested":{"value":1}}'
        log.http('GET', 'https://user:secret@bmc.invalid/redfish?token=secret', 200,
                 {'Set-Cookie': 'secret', 'X-Auth-Token': 'secret', 'Content-Type': 'application/json'},
                 raw, {'Authorization': 'secret', 'Accept': 'application/json'})
        log.check('HTTP status', True, expected=200, actual=200)
        log.finish('Pass', 'All checks met')
        log.finish('Fail', 'must not duplicate')
        text = result.getvalue()
        for label in ('[1] Inspect document', 'HTTP evidence #1', 'PASS | HTTP status', 'Final result'):
            self.assertIn(label, text)
        self.assertIn('    "value": 1', text)
        self.assertNotIn('secret', text)
        self.assertNotIn('secret', json.dumps(log.records))
        self.assertEqual(log.records[1]['body'], raw)
        self.assertEqual(len(events), 4)
        self.assertEqual(text, ''.join(event['text'] + '\n' for event in events))

    def test_checks_stay_in_section_and_empty_sections_are_explicit(self):
        output, events = io.StringIO(), []
        log = CaseLog(output, events.append)
        log.section('Connection setup')
        log.section('JSON document validation')
        log.check('Valid JSON', True)
        log.check('Top-level JSON object', True, expected='object', actual='object')
        log.section('Document content validation')
        log.check('Version discovery mapping', False, expected='/redfish/v1/', actual='/redfish/v1')
        log.section('HTTP evidence only')
        log.http('GET', '/redfish', 200, {}, '{"v1":"/redfish/v1"}')
        log.finish('Fail', 'Mapping mismatch')
        text = output.getvalue()
        sections = text.split('=' * 72)
        self.assertIn('No check results recorded for this section.', sections[1])
        self.assertIn('PASS | Valid JSON', sections[2])
        self.assertIn('PASS | Top-level JSON object', sections[2])
        self.assertNotIn('No check results recorded', sections[2])
        self.assertIn('FAIL | Version discovery mapping', sections[3])
        self.assertIn('Expected: "/redfish/v1/"', sections[3])
        self.assertIn('Actual: "/redfish/v1"', sections[3])
        self.assertIn('HTTP evidence #1', sections[4])
        self.assertIn('No check results recorded for this section.', sections[4])
        self.assertIn('Final result', sections[5])
        self.assertNotIn('Validation result', text)
        self.assertEqual(text, ''.join(event['text'] + '\n' for event in events))
        self.assertEqual([r['passed'] for r in log.records if r['kind'] == 'check'], [True, True, False])

    def test_non_json_body_and_separate_log_instances(self):
        files = [io.StringIO() for _ in range(4)]
        one = CaseLog(files[0], lambda event: None)
        two = CaseLog(files[2], lambda event: None)
        one.http('GET', '/one', 500, {}, 'first\n  second\n')
        two.section('Other Task')
        self.assertIn('first\n  second\n', files[0].getvalue())
        self.assertNotIn('first', files[2].getvalue())
        self.assertEqual(two.records[0]['kind'], 'section')

    def test_print_fragments_preserve_lines_indentation_and_flush(self):
        output, events = io.StringIO(), []
        writer = PrintLogWriter(output, events.append)
        writer.write('hello')
        writer.write(' world\n\n  indented\nlast')
        writer.flush()
        self.assertEqual([event['text'] for event in events], ['hello world', ' ', '  indented', 'last'])
        self.assertIn('hello world\n\n', output.getvalue())
        self.assertIn(' - INFO -   indented\n', output.getvalue())


if __name__ == '__main__': unittest.main()
