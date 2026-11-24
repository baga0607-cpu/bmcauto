"""Run the child body inline only in SDK-mocked tests. Process stops have separate integration coverage."""
from unittest.mock import patch
import case_worker


def install_inline_worker(test, api):
    def run(config, session, emit):
        def publish(event):
            if event['type'] == 'input_required':
                session['input_prompt'] = event['text']
            emit(event)
        return case_worker.execute(config, publish, session['input_queue'].get)
    patcher = patch.object(api, 'run_case_worker', run)
    patcher.start()
    test.addCleanup(patcher.stop)
