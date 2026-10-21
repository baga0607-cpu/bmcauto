const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
const source=fs.readFileSync(path.join(__dirname,'../static/workbench.js'),'utf8');
const code=source.slice(source.indexOf('let planDrag=null,repositoryDrag=null;'),source.indexOf("document.addEventListener('dragend',()=>{planDrag=null;repositoryDrag=null;clearPlanDrop(true);clearRepositoryDrop(true);});")+"document.addEventListener('dragend',()=>{planDrag=null;repositoryDrag=null;clearPlanDrop(true);clearRepositoryDrop(true);});".length);
function setup(){
 const listeners={},nodes=[];
 const plan={id:'p',locked:false,folders:[{id:'f',parent_id:null},{id:'child',parent_id:'f'},{id:'g',parent_id:null}],testcases:[{id:'a',folder_id:'f'},{id:'b',folder_id:'f'}]};
 const state={repositoryFolders:[{id:'root',is_root:true,parent_id:null},{id:'f',parent_id:'root'},{id:'child',parent_id:'f'},{id:'g',parent_id:'root'}],repository:[{id:'a',folder_id:'f'},{id:'b',folder_id:'f'}]};
 const c=vm.createContext({document:{addEventListener:(name,fn)=>listeners[name]=fn},$$:()=>nodes,state,context:()=>({plan})});vm.runInContext(code,c);
 function node(dataset){const n={dataset,getBoundingClientRect:()=>({top:100,height:40}),removeAttribute(name){delete this.dataset[name.replace(/^data-/, '').replace(/-([a-z])/g,(_,x)=>x.toUpperCase())];},contains:()=>false};nodes.push(n);return n;}
 function fire(type,n,y=120,source=false){const e={target:{closest:sel=>sel==='.import-source-pane'?(source?{}:null):n},clientY:y,dataTransfer:{},preventDefault(){this.prevented=true;}};listeners[type](e);return e;}
 return {c,plan,state,node,fire,listeners};
}
test('dragenter accepts folders and shows inside frame; dragend removes all frames',()=>{
 const x=setup(),n=x.node({folderNode:'g'});vm.runInContext("repositoryDrag={kind:'case',id:'a'}",x.c);
 const event=x.fire('dragenter',n);assert.equal(event.prevented,true);assert.equal(n.dataset.drop,'inside');
 x.listeners.dragend();assert.equal(n.dataset.drop,undefined);
});
test('case upper/lower halves represent before/after; self is rejected',()=>{
 const x=setup(),n=x.node({repositoryId:'b'});vm.runInContext("repositoryDrag={kind:'case',id:'a'}",x.c);
 x.fire('dragover',n,105);assert.equal(n.dataset.drop,'before');x.fire('dragover',n,135);assert.equal(n.dataset.drop,'after');
 const self=x.node({repositoryId:'a'});assert.equal(x.fire('dragover',self).prevented,undefined);assert.equal(n.dataset.drop,undefined);
});
test('folder cycles and batch folders beside cases are not shown as destinations',()=>{
 const x=setup(),n=x.node({folderNode:'child'});vm.runInContext("repositoryDrag={kind:'folder',id:'f'}",x.c);
 assert.equal(x.fire('dragenter',n).prevented,undefined);
 vm.runInContext("repositoryDrag={kind:'batch',folder_ids:['g'],case_ids:['a']}",x.c);
 assert.equal(x.fire('dragover',x.node({repositoryId:'b'})).prevented,undefined);
});
test('Plan insertion frame, root target, execution lock and read-only source',()=>{
 const x=setup(),n=x.node({planCase:'b'});vm.runInContext("planDrag={kind:'case',id:'a',planId:'p'}",x.c);
 x.fire('dragenter',n,105);assert.equal(n.dataset.drop,'before');
 assert.equal(x.fire('dragover',n,105,true).prevented,undefined);assert.equal(n.dataset.drop,undefined);
 const root=x.node({planFolder:''});assert.equal(x.fire('dragenter',root).prevented,true);assert.equal(root.dataset.drop,'inside');
 x.plan.locked=true;assert.equal(x.fire('dragover',n).prevented,undefined);
});
