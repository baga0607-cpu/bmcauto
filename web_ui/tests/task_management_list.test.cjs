const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
const c={window:{}};vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../static/task_management_ui.js'),'utf8'),c);c.KeywordSearch=c.window.KeywordSearch;
const task=(id,status)=>({id,name:id,task_type:'Plan',project_id:'p',project_name:'Project',plan_name:'',setup:{task_status:status,owner:'David'}});
const tasks=[task('new-task','New'),task('pending-task','Pending'),task('unscheduled-task','Not Scheduled')];
let html=c.window.TaskManagement.content(tasks,'','list');
for(const t of tasks)assert.ok(html.includes('>'+t.name+'</a>'));
assert.ok(!html.includes('data-task-status-filter'));assert.ok(!html.includes('Filter Status'));
assert.ok(html.includes('class="task-list-label"'));assert.ok(html.includes('Assignee: '));assert.ok(html.includes('· Status: '));
assert.equal((html.match(/<th[ >]/g)||[]).length,8);
html=c.window.TaskManagement.content(tasks,'pending','my-task');assert.ok(html.includes('>pending-task</a>'));assert.ok(!html.includes('>new-task</a>'));
html=c.window.TaskManagement.content(tasks,'no-match','list');assert.ok(html.includes('colspan="8"'));assert.ok(html.includes('No matching Tasks'));

const dated=(end,start='2026-01-01')=>({setup:{start_date:start,end_date:end}});
assert.equal(c.window.TaskManagement.calendarRange([dated('2026-10-29')]).end,'2027-01-31');
assert.equal(c.window.TaskManagement.calendarRange([dated('2026-01-31')]).end,'2026-04-30');
assert.equal(c.window.TaskManagement.calendarRange([dated('2024-02-29','2024-02-01')]).end,'2024-05-31');
assert.equal(c.window.TaskManagement.calendarRange([dated('2026-06-15'),dated('2026-12-31')]).end,'2027-03-31');
assert.equal(c.window.TaskManagement.calendarRange([dated('2026-11-12','')]).end,'2027-02-28');
assert.equal(c.window.TaskManagement.calendarRange([dated('9999-12-31')]).end,'9999-12-31');
