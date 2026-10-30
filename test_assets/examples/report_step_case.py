"""Single-file author example for Worksheet-1 report rows."""
TEST_CASE = {
    'created_at': "2026-10-28T04:05:09.560Z",
    'name': 'Example - Service Root response',
    'description': 'Verify the Service Root response status using Task connection settings.',
    'automation': 'automatic',
    'test_method': [{'step':'GET /redfish/v1/', 'criteria':'HTTP status equals 200'}],
    'parameters': {},
}


def execute(client, context=None, preset=None):
    log = context['log']
    step, criteria = 'GET /redfish/v1/', 'HTTP status equals 200'
    try:
        response = client.get('/redfish/v1/')
    except Exception as error:
        log.step(step, criteria, 'ERROR: '+str(error))
        raise
    passed = response.status == 200
    log.step(step, criteria, {'status':'PASS' if passed else 'FAIL', 'actual':response.status})
    if not passed:
        raise AssertionError('Service Root response status is not 200')
