const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const context={window:{}};vm.createContext(context);
vm.runInContext(fs.readFileSync(path.join(__dirname,'../static/plan_matrix.js'),'utf8'),context);
const matrix=context.window.PlanMatrix;
const plan={testcases:[{id:'a',tc_name:'A'},{id:'b',tc_name:'B'}],tasks:[
 {testcases:[{id:'a',status:'Passed',executed_at:'2026-11-01T00:00:00Z'}]},
 {testcases:[{id:'a',status:'C-PASS',executed_at:'2026-11-02T00:00:00Z'}]}]};
const before=JSON.stringify(plan),summary=matrix.summarize(plan);
assert.equal(summary.counts['C-PASS'],1);assert.equal(summary.counts.PASS,0);
assert.equal(summary.counts.NR,1);assert.equal(summary.completed,1);
assert.equal(summary.rows[0].final,'C-PASS');assert.equal(JSON.stringify(plan),before);
plan.tasks.push({testcases:[{id:'a',status:'Failed',executed_at:'2026-11-03T00:00:00Z'}]});
assert.equal(matrix.summarize(plan).rows[0].final,'FAIL');
console.log('PASS: C-PASS counts, completion, latest winner, retained evidence');

plan.tasks[1].testcases[0].status='CP';plan.tasks.pop();assert.equal(matrix.summarize(plan).rows[0].final,'C-PASS');
