"""Offline RF-01 series audit; no DUT or formal workspace access."""
import ast
import importlib.util
import io
import json
from pathlib import Path
import socket
import unittest
from unittest.mock import patch
import zipfile
import requests
from case_log import CaseLog
from report_case import method_rows, method_table_rows
from result_policy import method_status
ROOT = Path(__file__).resolve().parents[2]
MODULES = {}
for path in sorted((ROOT / 'test_assets/redfish').glob('rf_01_*.py')):
    number = int(path.name.split('_')[2])
    spec = importlib.util.spec_from_file_location('audit_rf_' + str(number), path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    MODULES[number] = module
ROOT_BODY = {'@odata.type':'#ServiceRoot.v1_0_0.ServiceRoot', '@odata.id':'/redfish/v1/'}
PREFERRED = 'http://redfish.dmtf.org/schemas/v1/redfish-schema-v1.json'
def reply(body, status=200, headers=None):
    raw = body if isinstance(body, bytes) else (body if isinstance(body, str) else json.dumps(body)).encode()
    return type('Response', (), dict(status_code=status, headers=headers or {}, content=raw, text=raw.decode('utf-8', errors='replace')))()

def schema_routes(locations=None, body=None):
    return {'/redfish/v1/':reply(dict(ROOT_BODY,JsonSchemas={'@odata.id':'/redfish/v1/JsonSchemas'})),
            '/redfish/v1/JsonSchemas':reply({'Members':[{'@odata.id':'/redfish/v1/JsonSchemas/1'}]}),
            '/redfish/v1/JsonSchemas/1':reply({'Location':locations or [{'Uri':'/redfish/v1/Schemas/Test.json'}]}),
            '/redfish/v1/Schemas/Test.json':reply(body if body is not None else {'$schema':PREFERRED,'definitions':{}})}

class SeriesAudit(unittest.TestCase):
    def run_case(self, number, routes, expected='Pass', settings=None):
        module = MODULES[number]
        output = io.StringIO()
        log = CaseLog(output, lambda e:None)
        ctx = {'log':log,'redfish':{'host':'https://bmc.invalid','username':'synthetic','password':'test','verify_ssl':True},'case_settings':{'preset':'1.20.0'}}
        if settings is not None: ctx['redfish'] = settings
        calls=[]
        class Session:
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def get(self,url,**kwargs):
                calls.append(url)
                if not url.startswith('https://bmc.invalid/'):raise AssertionError('Unexpected origin '+url)
                value=routes[url.removeprefix('https://bmc.invalid')]
                if isinstance(value,Exception):raise value
                return value
        error = None
        with patch.object(socket.socket,'connect',side_effect=AssertionError('No network')),patch.object(requests,'Session',Session),patch('builtins.input',return_value='1.20.0'):
            try:module.execute(None,ctx)
            except (AssertionError,RuntimeError) as exc:error=exc
        self.assertIn('case_result',ctx, str(error))
        self.assertEqual(ctx['case_result']['status'],expected,(ctx['case_result'],str(error)))
        if expected in ('Pass','C-PASS','Block'):self.assertIsNone(error)
        rows=[r['result'] for r in log.records if r['kind']=='step']
        definitions=module.TEST_CASE['test_method']
        self.assertEqual({r['method_index'] for r in rows},set(range(len(definitions))))
        for row in rows:
            definition=definitions[row['method_index']]
            self.assertEqual((row['type'],row['step_number']),(definition['type'],definition['step_number']))
            self.assertIn(row['status'],('COMPLETED','FAILED','ERROR','PASS','FAIL','C-PASS','Skip'))
            if row['status']=='Skip':self.assertTrue(row.get('reason'))
            if row['status']=='C-PASS':
                self.assertEqual(row['type'],'Checkpoint')
                self.assertTrue(row.get('note'))
            if row['type']=='Record':self.assertIn(row['status'],('COMPLETED','Skip'))
        self.assertEqual(len(method_rows({'log_records':log.records},module.TEST_CASE)),len(rows))
        table = method_table_rows({'log_records':log.records, 'report_definition':module.TEST_CASE}, {})
        typed = [r for r in table if r[1] in ('Command','Action','Checkpoint','Record')]
        self.assertEqual(len(typed),len(rows))
        expected_order = sorted(rows,key=lambda r:r['method_index'])
        self.assertEqual([r[2] for r in typed],[definitions[r['method_index']]['step'] for r in expected_order])
        self.assertEqual([r[4] for r in typed],[r['status'] for r in expected_order])
        self.assertEqual(len([r for r in log.records if r['kind']=='finish']),1)
        self.assertNotRegex(output.getvalue(),r'(?m)^\[\d+\] ')
        json.dumps(log.records,allow_nan=False)
        return rows,ctx,calls

    def test_all_thirteen_literal_definitions(self):
        self.assertEqual(set(MODULES),set(range(1,14)))
        for number,module in MODULES.items():
            with self.subTest(case=number):
                tree=ast.parse(Path(module.__file__).read_text(encoding='utf-8'))
                meta=ast.literal_eval(next(n.value for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='TEST_CASE' for t in n.targets)))
                steps=[]
                for item in meta['test_method']:
                    self.assertIn(item['type'],('Command','Action','Checkpoint','Record'))
                    self.assertNotIn('id',item)
                    self.assertNotIn('criteria',item)
                    self.assertNotIn('step_id',item)
                    if item['type'] in ('Command','Action'):steps.append(item['step_number'])
                    else:self.assertEqual(item['step_number'],steps[-1])
                self.assertEqual(steps,list(range(1,len(steps)+1)))
                self.assertTrue(meta['description'])
                self.assertNotRegex(Path(module.__file__).read_text(encoding='utf-8'),r'"(?:CP|NOT_RUN|NOT_EVALUATED|NOT_RECORDED|RECORDED)"')

    def test_remaining_simple_pass(self):
        inputs={3:('/redfish/v1/odata',{'@odata.context':'/redfish/v1/$metadata','value':[{'name':'Systems','url':'/redfish/v1/Systems'}]}),
                4:('/redfish/v1/$metadata','<edmx:Edmx xmlns:edmx="http://docs.oasis-open.org/odata/ns/edmx" Version="4.0"/>'),
                5:('/redfish/v1/',{'RedfishVersion':'1.20.0'}),
                6:('/redfish/v1',dict(ROOT_BODY,RedfishVersion='1.20.0')),
                7:('/redfish/',{'v1':'/redfish/v1/'})}
        for number,(uri,body) in inputs.items():
            with self.subTest(case=number):self.run_case(number,{uri:reply(body)})

    def test_remaining_missing_configuration_and_http_failures(self):
        paths={3:'/redfish/v1/odata',4:'/redfish/v1/$metadata',5:'/redfish/v1/',6:'/redfish/v1',7:'/redfish/',9:'/redfish/v1/',10:'/redfish/v1/',11:'/redfish/v1/',12:'/redfish/v1/',13:'/redfish/v1/'}
        for number,uri in paths.items():
            with self.subTest(case=number):
                self.run_case(number,{},'Fail',{})
                self.run_case(number,{uri:reply({},404)},'Fail')

    def test_parse_and_required_field_failures(self):
        for number,uri in [(3,'/redfish/v1/odata'),(4,'/redfish/v1/$metadata'),(5,'/redfish/v1/'),(6,'/redfish/v1'),(7,'/redfish/')]:
            with self.subTest(case=number):
                self.run_case(number,{uri:reply('not a document')},'Fail')
                self.run_case(number,{uri:reply({})},'Fail')

    def test_traversal_multi_uri_keeps_every_result(self):
        for number in (9,10,12):
            with self.subTest(case=number):
                routes={'/redfish/v1/':reply(dict(ROOT_BODY,Items=[{'@odata.id':'/redfish/v1/Systems/1'},{'@odata.id':'/redfish/v1/Systems/2'}]))}
                for n in (1,2):routes['/redfish/v1/Systems/'+str(n)]=reply({'@odata.type':'#ComputerSystem.v1_0_0.ComputerSystem','@odata.id':'/redfish/v1/Systems/'+str(n)})
                rows,ctx,calls=self.run_case(number,routes)
                self.assertEqual(len(calls),3)
                self.assertGreater(len(rows),len(MODULES[number].TEST_CASE['test_method']))
                routes['/redfish/v1/Systems/2']=reply({},500)
                self.run_case(number,routes,'Fail')

    def test_fragment_reference_and_missing_target(self):
        body=dict(ROOT_BODY,ProbeUri='/redfish/v1/#/Target',Target=123)
        routes={'/redfish/v1/':reply(body,headers={'Link':'</schema.json>; rel=describedby'}),'/schema.json':reply({'properties':{'ProbeUri':{'type':'string','format':'uri-reference'}}})}
        self.run_case(11,routes)
        del body['Target']
        routes['/redfish/v1/']=reply(body,headers={'Link':'</schema.json>; rel=describedby'})
        self.run_case(11,routes,'Fail')
        self.run_case(11,{'/redfish/v1/':reply(ROOT_BODY)},'Fail')

    def test_schema_conditional_and_failure_precedence(self):
        self.run_case(13,schema_routes())
        self.run_case(13,schema_routes(body={'$schema':'https://json-schema.org/draft/2020-12/schema','$defs':{}}),'C-PASS')
        routes=schema_routes([{'Uri':'/schema/Test.json'}])
        routes['/schema/Test.json']=routes.pop('/redfish/v1/Schemas/Test.json')
        self.run_case(13,routes,'C-PASS')
        routes['/schema/Test.json']=reply('invalid schema')
        self.run_case(13,routes,'Fail')

    def test_schema_multiple_files_and_archive_block(self):
        routes=schema_routes([{'Uri':'/redfish/v1/Schemas/Test.json'},{'Uri':'/schema/Other.json'}])
        routes['/schema/Other.json']=reply({'$schema':'https://json-schema.org/draft/2020-12/schema','$defs':{}})
        rows,_,_=self.run_case(13,routes,'C-PASS')
        acquired=[r for r in rows if r['method_index']==6]
        self.assertEqual(len(acquired),2)
        self.assertEqual({r['actual']['value']['uri'] for r in acquired},{'https://bmc.invalid/redfish/v1/Schemas/Test.json','https://bmc.invalid/schema/Other.json'})
        routes=schema_routes([{'ArchiveUri':'/bundle.tar','ArchiveFile':'Test.json'}])
        routes['/bundle.tar']=reply(b'unsupported archive')
        self.run_case(13,routes,'Block')
        output=io.BytesIO()
        with zipfile.ZipFile(output,'w') as archive:archive.writestr('Test.json',json.dumps({'$schema':PREFERRED,'definitions':{}}))
        routes=schema_routes([{'ArchiveUri':'/bundle.zip','ArchiveFile':'Test.json'}])
        routes['/bundle.zip']=reply(output.getvalue())
        self.run_case(13,routes,'C-PASS')

    def test_legacy_cp_normalizes_at_output(self):
        self.assertEqual(method_status('CP'),'C-PASS')
        output=io.StringIO();log=CaseLog(output,lambda e:None)
        item={'type':'Checkpoint','step_number':1,'step':'Conditional check'}
        log.method_item(item,dict(item,method_index=0,status='CP',note='Accepted condition'))
        log.finish('CP','Accepted','Accepted condition')
        self.assertNotIn('Judgement: CP',output.getvalue())
        self.assertIn('Result: C-PASS',output.getvalue())
