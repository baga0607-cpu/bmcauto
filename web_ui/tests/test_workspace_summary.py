import json
from sqlalchemy import event
import test_single_case_repository as fixtures
from models import TaskTestCase


class WorkspaceSummaryTest(fixtures.SingleCaseRepositoryTest):
    def test_summary_excludes_evidence_and_log_endpoint_preserves_full_text(self):
        tc = self.add_case()
        text = 'Full evidence 中文\n' * 100000
        result = {'log_records': [{'kind': 'step', 'result': text}]}
        with self.Session() as session:
            session.add(TaskTestCase(task_id='task1', testcase_id=tc['id'],
                                     status='Passed', log_text=text,
                                     result_json=json.dumps(result)))
            session.commit()
        queries = []
        def capture(conn, cursor, statement, parameters, context, executemany):
            queries.append(statement)
        event.listen(self.engine, 'before_cursor_execute', capture)
        try:
            for url in ['/api/projects', '/api/tasks/task1/summary']:
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)
                self.assertLess(len(response.data), 30000)
                self.assertNotIn(b'log_records', response.data)
                self.assertNotIn(b'log_text', response.data)
        finally:
            event.remove(self.engine, 'before_cursor_execute', capture)
        selects = [q for q in queries if q.lstrip().upper().startswith('SELECT')]
        self.assertFalse(any('task_testcases.log_text' in q or 'task_testcases.result_json' in q for q in selects))
        url = f'/api/tasks/task1/testcases/{tc["id"]}/logs'
        full = self.client.get(url).get_json()
        self.assertEqual(full['log_text'], text)
        self.assertEqual(full['result'], result)
        lightweight = self.client.get(url+'?text_only=1').get_json()
        self.assertEqual(lightweight['log_text'], text)
        self.assertNotIn('result', lightweight)
        self.assertEqual(self.client.get(f'/api/tasks/task2/testcases/{tc["id"]}/logs?text_only=1').status_code, 404)
