"""RF-01-012 distinguishes coverage failures, unavailable evidence and inapplicability."""
import io
import json
import runpy
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import requests

from case_log import CaseLog, ReportedCase
from report_html import legacy_method_body


class RelativeUriCoverageTest(unittest.TestCase):
    def test_explicit_conditional_judgement(self):
        definition = {'test_method': [
            {'step_number': 2, 'type': 'Action', 'step': 'Inspect headers',
             'checkpoints': {'link_header_syntax': {'expected': 'Valid syntax'}}}]}
        for judgement, case_note, expected in [('PASS', 'Operator comment', 'Pass'),
                                                ('C-PASS', '', 'C-PASS'),
                                                ('C-PASS', '', 'Fail')]:
            with self.subTest(expected=expected):
                context = {'log': CaseLog(io.StringIO(), lambda event: None)}
                report = ReportedCase(context, definition)
                report.begin_step(2)
                with self.assertRaises(TypeError):
                    report.checkpoint('link_header_syntax', actual='header', note='Comment')
                with self.assertRaisesRegex(ValueError, 'reserved'):
                    report.checkpoint('link_header_syntax', 'PASS', actual='header', note='Comment')
                with self.assertRaisesRegex(ValueError, 'requires a Note'):
                    report.checkpoint('link_header_syntax', 'C-PASS', actual='header')
                detail = {'note': 'Accepted under documented exception'} if judgement == 'C-PASS' else {}
                report.checkpoint('link_header_syntax', judgement, actual='header', **detail)
                if expected == 'Fail':
                    report.checkpoint('link_header_syntax', 'FAIL', actual='bad header', reason='Invalid syntax')
                    with self.assertRaises(AssertionError):
                        report.finish({})
                else:
                    result = report.finish({}, note=case_note)
                    self.assertEqual(result['note'], case_note or detail['note'])
                self.assertEqual(context['case_result']['status'], expected)
                self.assertEqual(context['_tc_status'], expected.upper())
                self.assertEqual(context['log'].records[-1]['status'], expected)

    def test_checkpoint_applicability(self):
        case = runpy.run_path(str(Path(__file__).resolve().parents[2] /
                                 'test_assets/redfish/rf_01_012_relative_uri_references.py'))
        host = 'https://bmc.invalid'
        root = '/redfish/v1/'
        child = '/redfish/v1/Systems'
        def response(resource, link=None, member=False):
            body = {'@odata.id': resource, '@odata.type': '#ServiceRoot.ServiceRoot'}
            if member:
                body['Systems'] = {'@odata.id': child}
            return SimpleNamespace(status_code=200, text=json.dumps(body),
                                   headers={'Link': link} if link is not None else {})

        good = '</redfish/v1/>; rel=self'
        bad = '</redfish/v1/>; path=/Systems'
        timeout = requests.Timeout()
        scenarios = [
            ('invalid origin', '', [], ['Not executed'], 'Not executed'),
            ('root timeout', host, [timeout], ['Not executed'], 'FAIL'),
            ('no Link', host, [response(root)], ['Skip'], 'PASS'),
            ('one Link', host, [response(root, good, True), response(child)], ['PASS'], 'PASS'),
            ('mixed Link syntax', host, [response(root, good, True), response(child, bad)], ['PASS', 'FAIL'], 'PASS'),
            ('incomplete without Link', host, [response(root, member=True), timeout], ['Not executed'], 'FAIL'),
            ('incomplete with Link', host, [response(root, good, True), timeout], ['PASS'], 'FAIL'),
            ('only absolute references', host, [response(host + root)], ['Skip'], 'PASS'),
        ]
        for name, origin, replies, expected_a, expected_b in scenarios:
            with self.subTest(name=name):
                output = io.StringIO()
                log = CaseLog(output, lambda event: None)
                log.declare_methods(case['TEST_CASE']['test_method'])
                context = {'log': log, 'redfish': {'host': origin}}
                with patch('requests.Session.get', side_effect=replies) as get:
                    try:
                        case['execute'](None, context)
                    except case['CaseFailure']:
                        pass
                self.assertEqual(get.call_count, len(replies))
                results = context['case_result']['method_results']
                def statuses(index):
                    return [r['status'] for r in results if r.get('checkpoint_id', r.get('method_index')) == index]
                self.assertEqual(statuses('link_header_syntax'), expected_a)
                self.assertEqual(statuses('traversal_complete')[-1], expected_b)
                if name == 'only absolute references':
                    self.assertEqual(statuses('relative_reference_present'), ['FAIL'])
                html = legacy_method_body({'report_definition': case['TEST_CASE'], 'log_records': log.records}, {})
                for record in results:
                    if record['status'] in ('Skip', 'Not executed'):
                        self.assertTrue(record['reason'])
                        self.assertIn(record['reason'], output.getvalue())
                        self.assertIn('>' + record['status'] + '</span>', html)
                        self.assertIn(record['reason'], html)

    def test_checkpoint_letters_follow_declaration_even_when_evidence_arrives_in_reverse(self):
        case = runpy.run_path(str(Path(__file__).resolve().parents[2] /
                                 'test_assets/redfish/rf_01_012_relative_uri_references.py'))
        methods = case['TEST_CASE']['test_method']
        step = next(m for m in methods if m['step_number'] == 2)
        first = 'link_header_syntax'
        second = 'traversal_complete'
        for order in [(first, second), (second, first)]:
            step['checkpoints'] = {key: step['checkpoints'][key] for key in order}
            output = io.StringIO()
            log = CaseLog(output, lambda _: None)
            log.declare_methods(methods)
            for key, status in [(first, 'FAIL'), (first, 'PASS'), (second, 'PASS')]:
                item = dict(step_number=2, type='Checkpoint', checkpoint_id=key,
                            step=step['checkpoints'][key]['expected'])
                log.method_item(item, dict(step_number=2, type='Checkpoint', checkpoint_id=key,
                                           status=status, actual=key))
            log.finish('Fail', 'Invalid Link syntax')
            report = legacy_method_body(dict(report_definition=case['TEST_CASE'], log_records=log.records), {})
            for letter, key in zip('AB', order):
                label = 'Step 2 | Checkpoint ' + letter
                block = output.getvalue().split(label + ' | ', 1)[1].split('=' * 72)[0]
                row = report.split(label + '</td>', 1)[1].split('</tr>')[0]
                self.assertIn('Actual: "' + key + '"', block)
                self.assertIn(key, row)
                self.assertEqual('FAIL 1' in row, key == first)

    def test_interrupted_step_retains_acknowledged_observation(self):
        case = runpy.run_path(str(Path(__file__).resolve().parents[2] /
                                 'test_assets/redfish/rf_01_012_relative_uri_references.py'))
        methods = case['TEST_CASE']['test_method']
        stream = io.StringIO()
        history = []
        log = CaseLog(stream, history.append)
        log.declare_methods(methods)
        log.begin_step(2)
        item = log.named_checkpoints['link_header_syntax']
        result = dict(step_number=2, type='Checkpoint', checkpoint_id='link_header_syntax',
                      status='FAIL', actual={'source': '/redfish/v1/', 'issues': ['invalid parameter']})
        log.method_item(item, result)
        self.assertEqual(history[-1]['log_record']['result'], result)
        self.assertNotIn('Step 2 | Outcome', stream.getvalue())

        parent = CaseLog(stream, lambda _: None)
        parent.records = [e['log_record'] for e in history if 'log_record' in e]
        parent.recover_open_step('Execution stopped by operator', stopped=True)
        parent.finish('Stopped', 'Execution stopped by operator')
        text = stream.getvalue()
        self.assertLess(text.index('Step 2 | Outcome'), text.index('Step 2 | Checkpoint A'))
        self.assertIn('Judgement: Stopped', text)
        self.assertIn('Judgement: FAIL', text)
        self.assertEqual([r['result'] for r in parent.records if r.get('checkpoint_id')], [result])

    def test_redirect_headers_are_inspected_before_the_next_get(self):
        from urllib3._collections import HTTPHeaderDict
        case = runpy.run_path(str(Path(__file__).resolve().parents[2] /
                                 'test_assets/redfish/rf_01_012_relative_uri_references.py'))
        host = 'https://bmc.invalid'
        root = host + '/redfish/v1/'
        for location, follows in [('Members', False), ('/redfish/v1/Members', True),
                                  ('https://other.invalid/resource', False), ('/redfish/v1/Actions/x', False)]:
            with self.subTest(location=location):
                log = CaseLog(io.StringIO(), lambda event: None)
                log.declare_methods(case['TEST_CASE']['test_method'])
                context = {'log': log, 'redfish': {'host': host, 'username': 'tester',
                                                    'password': 'fixture', 'verify_ssl': True}}
                visited = []
                def get(session, uri, **options):
                    visited.append(uri)
                    self.assertEqual(session.auth, ('tester', 'fixture'))
                    self.assertFalse(session.trust_env)
                    self.assertFalse(options['allow_redirects'])
                    self.assertTrue(options['verify'])
                    if len(visited) == 1:
                        fields = HTTPHeaderDict()
                        fields.add('Location', location)
                        fields.add('Link', '</redfish/v1/>; rel="self"')
                        fields.add('Link', '</redfish/v1/>; path=/Systems')
                        return SimpleNamespace(status_code=302, text='', headers=dict(fields),
                                               raw=SimpleNamespace(headers=fields))
                    self.assertTrue(follows)
                    self.assertEqual(visited, [root, host + location])
                    self.assertTrue(any(r.get('checkpoint_id') == 'link_header_syntax'
                                        and r['result']['status'] == 'FAIL' for r in log.records))
                    return SimpleNamespace(status_code=200, headers={}, text=json.dumps(
                        {'@odata.id': '/redfish/v1/', '@odata.type': '#ServiceRoot.ServiceRoot'}))
                with patch('requests.Session.get', autospec=True, side_effect=get):
                    try:
                        case['execute'](None, context)
                    except case['CaseFailure']:
                        pass
                self.assertEqual(len(visited), 2 if follows else 1)
                observations = context['case_result']['observations']
                self.assertIn(location, [item['uri'] for item in observations['uris']
                                         if item['field'] == 'headers/location'])
                checks = [r['result'] for r in log.records if r.get('checkpoint_id') == 'link_header_syntax']
                self.assertEqual([r['status'] for r in checks], ['FAIL'])
                actual = checks[0]['actual']
                self.assertEqual(set(actual), {'uri', 'evidence_id', 'issues'})
                self.assertEqual(actual['uri'], root)
                issue, = actual['issues']
                self.assertEqual((issue['header_index'], issue['value']), (2, '/Systems'))
                http = [r for r in log.records if r['kind'] == 'http']
                self.assertEqual([r['evidence_id'] for r in http], list(range(1, len(visited) + 1)))
                evidence, = [r for r in http if r['evidence_id'] == actual['evidence_id']]
                self.assertEqual(evidence['headers']['Link'], ['</redfish/v1/>; rel="self"',
                                                              '</redfish/v1/>; path=/Systems'])
                self.assertNotIn('evidence', context['case_result'])
                if location == 'Members':
                    self.assertIn('relative-reference rules', observations['unread'][0]['reason'])
