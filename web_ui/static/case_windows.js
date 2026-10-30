'use strict';
(() => {
let options={},epoch=0,activeKey=null;
const windows=new Map();
const labels={viewer:'Python Source Viewer',parameters:'Parameter Editor'};
const esc=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const key=ref=>[ref.kind,ref.planId||'',ref.caseId].join(':');
const notify=message=>options.onError?.(new Error(message));
function frame(type){
 if(windows.has(type))return windows.get(type);
 const el=document.createElement('section');el.className='case-floating-window case-docked-window';el.dataset.caseWindow=type;el.setAttribute('role','region');el.setAttribute('aria-label',labels[type]);
 el.innerHTML='<header class="case-window-bar"><h2>'+labels[type]+'</h2><div class="case-window-actions"><button type="button" data-window-close>Close</button></div></header><div class="case-window-body"></div>';
 const model={type,el,body:el.querySelector('.case-window-body'),ref:null,def:null,dirty:false,saving:false};windows.set(type,model);
 dockHost().append(el);updateDock();
 el.querySelector('[data-window-close]').addEventListener('click',()=>close(type));
 el.addEventListener('input',event=>{event.stopPropagation();if(type==='parameters'&&event.target.closest('form')){model.dirty=true;model.body.querySelector('[data-parameter-state]').textContent='Unsaved changes';}});
 el.addEventListener('change',event=>event.stopPropagation());
 el.addEventListener('submit',event=>{event.preventDefault();event.stopPropagation();if(type==='parameters')save(model,event.target);});
 front(model);return model;
}
function dockHost(){let host=document.getElementById('case-tools-dock');if(!host){host=document.createElement('aside');host.id='case-tools-dock';host.setAttribute('aria-label','Case tools');document.body.append(host);}return host;}
function updateDock(){const count=[...windows.values()].length;document.body.classList.toggle('has-case-tools-dock',count>0);const host=document.getElementById('case-tools-dock');if(host){host.hidden=!count;host.style.gridTemplateRows=count===2?'1fr 1fr':'1fr';}}
function front(){}
function prune(){updateDock();}
function confirmDiscard(){
 prune();const editor=windows.get('parameters');if(editor?.saving){notify('Wait for parameter saving to finish.');return false;}
 if(!editor?.dirty)return true;if(!window.confirm('Discard unsaved parameter changes?'))return false;
 editor.dirty=false;render(editor);return true;
}
function close(type,force=false){
 const model=windows.get(type);if(!model)return true;
 if(type==='parameters'&&!force&&!confirmDiscard())return false;
 model.dirty=false;model.saving=false;windows.delete(type);model.el.remove();updateDock();return true;
}
function caption(model){return '<div class="case-window-caption"><strong data-no-translate>'+esc(model.def?.tc_name||model.def?.name||model.ref.name)+'</strong><p class="help" data-no-translate>'+esc(model.ref.contextLabel||'')+'</p></div>';}
function render(model){
 const def=model.def;if(!def)return;
model.el.dataset.caseId=model.ref.caseId;model.el.dataset.planId=model.ref.planId||'';model.el.querySelector('[data-window-close]').disabled=model.saving;
 if(model.type==='viewer'){model.body.innerHTML=caption(model)+'<pre class="case-source-code" data-no-translate>'+esc(def.source)+'</pre>';return;}
 const specs=def.metadata?.parameters||{},readOnly=model.ref.kind!=='plan',locked=Boolean(def.editing_locked),settings=def.settings||Object.fromEntries(Object.entries(specs).map(([name,spec])=>[name,spec.default]));
 if(!Object.keys(specs).length){model.body.innerHTML=caption(model)+'<p class="help">No parameters declared for this Test Case.</p>';return;}
 model.body.innerHTML=caption(model)+(readOnly?'<p class="notice info">Repository defaults are read-only. Add the Test Case to a Plan to edit parameters.</p>':'')+(locked?'<p class="notice info">This Test Case is running. Parameters are locked until it finishes.</p>':'')+'<form id="floating-parameter-form"><fieldset '+(readOnly||locked?'disabled':'')+'><div class="fields">'+options.renderFields(def.metadata,settings,readOnly||locked)+'</div></fieldset><p class="case-window-error" role="alert"></p>'+(!readOnly?'<div class="form-actions"><button type="submit" class="primary" '+(locked?'disabled':'')+'>Save parameters</button><span class="help" data-parameter-state>Saved</span></div>':'<span class="help" data-parameter-state>Read-only</span>')+'</form>';
}
async function show(ref,type){
 prune();const editor=windows.get('parameters'),same=editor?.ref&&key(editor.ref)===key(ref);
 if(editor?.saving){notify('Wait for parameter saving to finish.');return false;}
 if(editor?.dirty&&!same&&!confirmDiscard())return false;
 if(type&&!frame(type))return false;if(!windows.size)return false;
 const token=++epoch;activeKey=key(ref);options.onSelected?.(ref);
 const requested=[...windows.values()].filter(model=>!(model.type==='parameters'&&same&&model.dirty));
 for(const model of requested){model.ref={...ref};model.def=null;model.dirty=false;model.body.innerHTML='<p class="help" role="status">Loading Test Case…</p>';}
 try{
   const def=await options.api(ref.kind==='plan'?'/api/plans/'+encodeURIComponent(ref.planId)+'/testcases/'+encodeURIComponent(ref.caseId)+'/definition':'/api/repository/testcases/'+encodeURIComponent(ref.caseId));
   if(token!==epoch||activeKey!==key(ref))return false;
   if(def.id&&def.id!==ref.caseId)throw Error('The response does not match the selected Test Case.');
   for(const model of requested)if(windows.get(model.type)===model&&key(model.ref)===key(ref)){model.def=def;render(model);}
   return true;
 }catch(error){if(token===epoch)for(const model of requested)if(windows.get(model.type)===model)model.body.innerHTML='<p class="case-window-error" role="alert">'+esc(error.message)+'</p>';throw error;}
}
async function save(model,form){
 if(model.saving||!model.def||model.ref.kind!=='plan'||model.def.editing_locked||!form.reportValidity())return;
 const ref={...model.ref},def=model.def,settings={};
 for(const [name,spec] of Object.entries(def.metadata.parameters||{})){const field=form.elements.namedItem('p:'+name);settings[name]=spec.type==='boolean'?field.checked:['integer','number'].includes(spec.type)?Number(field.value):field.value;}
 model.saving=true;model.el.querySelector('[data-window-close]').disabled=true;form.querySelector('fieldset').disabled=true;form.querySelector('[type=submit]').disabled=true;form.querySelector('.case-window-error').textContent='';
 try{
   const result=await options.api('/api/plans/'+encodeURIComponent(ref.planId)+'/testcases/'+encodeURIComponent(ref.caseId)+'/definition','PUT',{source:def.source,settings,settings_revision:def.settings_revision});
   model.def=result;model.dirty=false;model.saving=false;render(model);
   const viewer=windows.get('viewer');if(viewer?.ref&&key(viewer.ref)===key(ref)){viewer.def=result;render(viewer);}
   try{await options.onSaved?.(ref,result);}catch(error){options.onError?.(error);}
 }catch(error){if(error.status===423)model.def.editing_locked=true;form.querySelector('.case-window-error').textContent=error.message;}
 finally{model.saving=false;model.el.querySelector('[data-window-close]').disabled=false;const current=model.body.querySelector('form');if(current){current.querySelector('fieldset').disabled=Boolean(model.def?.editing_locked);const submit=current.querySelector('[type=submit]');if(submit)submit.disabled=Boolean(model.def?.editing_locked);}}
}
window.addEventListener('beforeunload',event=>{if(windows.get('parameters')?.dirty||windows.get('parameters')?.saving){event.preventDefault();event.returnValue='';}});
window.CaseWindows={configure(value){options=value;},open:(type,ref)=>show(ref,type),select:ref=>windows.size?show(ref):Promise.resolve(false),isOpen:()=>{prune();return windows.size>0;},confirmDiscard,closeAll(force=false){if(!force&&!confirmDiscard())return false;++epoch;for(const type of [...windows.keys()])close(type,true);return true;}};
})();