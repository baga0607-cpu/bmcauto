// Five Plan layout prototypes. All mutations affect only this page's memory.
const $ = s => document.querySelector(s);
const esc = x => String(x ?? '').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const layouts=['目錄閱讀','列內展開','測項專頁','上下分割','整理／審閱'];
const button=(act,label,attrs='')=>'<button data-act="'+act+'" '+attrs+'>'+esc(label)+'</button>';
const attr=(key,value)=>'data-'+key+'="'+esc(value)+'"';
function makePlan(name,folders,cases){
  return {name,folders:[...folders],cases:structuredClone(cases),log:[],values:{}};
}
const plans=[makePlan(snapshot.name,snapshot.folders,snapshot.cases),makePlan('Demo · Smoke', ['Smoke'],snapshot.cases.slice(0,3).map(c=>({...c,folder:'Smoke'})))];
let variant=Math.max(1,Math.min(5,Number(new URLSearchParams(location.search).get('variant'))||1));
let plan=plans[0],focus=plan.cases[12].name,query='',folder=plan.folders[0],reading=true,reviewing=true;
let selected=new Set(),collapsed=new Set(),opened=new Set([focus]),panelState='',topSize=42,listScroll=0;
const current=()=>plan.cases.find(c=>c.name===focus);
const matching=c=>c.name.toLowerCase().includes(query.toLowerCase());
function usePlan(p){plan=p;focus=p.cases[0]?.name||'';folder=p.folders[0]||'';selected.clear();collapsed.clear();opened=new Set([focus]);query='';reading=false;listScroll=0;}
function toolbar(){return '<div class="tools"><input type="search" id="search" aria-label="Find Test Case" placeholder="Find Test Case" value="'+esc(query)+'">'+button('import','Import')+'<details><summary>Manage</summary><div class="menu">'+[['newfolder','New folder'],['rename','Rename folder'],['sort','Sort Test Cases'],['all','Select all'],['delete','Delete selected'],['history','History']].map(([a,t])=>button(a,t,(a==='delete'&&!selected.size||a==='rename'&&!folder)?'disabled':'')).join('')+'</div></details></div>'}
function article(c){if(!c)return '<p class="empty">Select a Test Case.</p>';
  const [code,...name]=c.name.split(' ');
  return '<div class="casehead"><div><span class="code">'+esc(code)+'</span><h2>'+esc(name.join(' '))+'</h2></div>'+(Object.keys(c.parameters).length?button('params','Parameters',attr('name',c.name)):'')+'</div>'+
    c.steps.map(s=>'<section class="step"><div class="stepname">Step '+s.step_number+' | Action</div><h3>'+esc(s.step)+'</h3>'+Object.values(s.checkpoints||{}).map((cp,i)=>'<div class="check"><span>Step '+s.step_number+' | Checkpoint '+String.fromCharCode(65+i)+'</span><p>'+esc(cp.expected)+'</p></div>').join('')+'</section>').join('');
}
function list(inline=false){
 const groups=[...plan.folders,...(plan.cases.some(c=>!c.folder)?['']:[])];
 return '<section class="sheet list '+(inline?'inline':'')+'">'+toolbar()+groups.map(f=>{
   const cases=plan.cases.filter(c=>(c.folder||'')===f&&matching(c));
   if(query&&!cases.length)return '';
   return '<div class="folder">'+button('folder',((collapsed.has(f)&&!query)?'▸ ':'▾ ')+(f||'Unfiled')+' · '+cases.length,attr('folder',f))+'</div>'+
     (collapsed.has(f)&&!query?'':cases.map(c=>{
       const id=c.name.split(' ')[0],title=c.name.slice(id.length+1);
       return '<div class="case '+(c.name===focus?'active':'')+'"><input type="checkbox" '+attr('pick',c.name)+' aria-label="Select '+esc(id)+'" '+(selected.has(c.name)?'checked':'')+'><button data-act="case" '+attr('name',c.name)+'>'+(inline?(opened.has(c.name)?'▾ ':'▸ '):'')+'<span class="code">'+esc(id)+'</span>'+esc(title)+'</button></div>'+
         (inline&&opened.has(c.name)?'<div class="article">'+article(c)+'</div>':'');
     }).join(''));
 }).join('')+(!plan.cases.some(matching)?'<p class="empty">'+(query?'No matching Test Cases.':'Import Test Cases to this Plan.')+'</p>':'')+'</section>';
}
function render(){
 $('#plan').innerHTML=plans.map((p,i)=>'<option value="'+i+'" '+(p===plan?'selected':'')+'>'+esc(p.name)+'</option>').join('');
 const content=()=>article(current());
 let body='';
 if(variant===1)body='<div class="split">'+list()+'<section class="reader">'+content()+'</section></div>';
 if(variant===2)body='<div class="full" style="display:grid">'+list(true)+'</div>';
 if(variant===3){
   const pos=plan.cases.indexOf(current());
   body=reading?'<section class="reader full reading"><div class="pager">'+button('back','← Test Cases')+button('prev','Previous',pos<=0?'disabled':'')+button('next','Next',pos===plan.cases.length-1?'disabled':'')+'</div>'+content()+'</section>':'<div class="full" style="display:grid">'+list()+'</div>';
 }
 if(variant===4)body='<div class="stack '+panelState+'" style="--top:'+topSize+'%">'+list()+'<button class="grip" aria-label="Resize panels" title="Drag or use arrow keys"></button><section class="reader"><div class="pager">'+button('expand',panelState==='expanded'?'Restore':'Expand')+button('collapse',panelState==='closed'?'Show steps':'Collapse')+'</div>'+(panelState==='closed'?esc(focus):content())+'</section></div>';
 if(variant===5)body='<div class="modes">'+button('organize','Organize','aria-pressed="'+!reviewing+'"')+button('review','Review steps','aria-pressed="'+reviewing+'"')+'</div>'+(reviewing?'<div class="review"><aside class="sheet">'+plan.cases.map((c,i)=>button('jump',c.name.split(' ')[0],attr('index',i)+' class="jump"')).join('')+'</aside><section class="sheet stream">'+plan.cases.map((c,i)=>'<div class="article" id="article-'+i+'">'+article(c)+'</div>').join('')+'</section></div>':'<div class="full" style="display:grid;height:calc(100dvh - 245px)">'+list()+'</div>');
 $('#work').innerHTML=body;
 $('#variants').innerHTML=button('left','‹','aria-label="上一個方案"')+layouts.map((name,i)=>button('variant',(i+1)+' '+name,attr('index',i+1)+' aria-current="'+(variant===i+1)+'"')).join('')+button('right','›','aria-label="下一個方案"');
 if($('.list'))$('.list').scrollTop=listScroll;
}
function showFocused(){if(variant===2&&opened.has(focus))$('.case.active')?.scrollIntoView({block:'start'});if(variant===5&&reviewing)jump(plan.cases.indexOf(current()));}
function changeVariant(v){variant=(v+4)%5+1;const u=new URL(location.href);u.searchParams.set('variant',variant);history.replaceState(null,'',u);render();showFocused();}
function modal(title,fields,save){
 $('#title').textContent=title;$('#fields').innerHTML=fields;$('#submit').textContent=save?'Apply':'Close';$('#dialog [data-act="close"]').hidden=!save;
 $('#form').onsubmit=e=>{e.preventDefault();if(save&&save(new FormData(e.target))===false)return;$('#dialog').close();render();};$('#dialog').showModal();
}
function textForm(title,value,apply){modal(title,'<label>Name<input name="name" required value="'+esc(value)+'"></label>',d=>{
 const name=String(d.get('name')).trim();if(!name||apply(name)===false){const input=$('#fields input');input.setCustomValidity('Enter a unique name.');input.reportValidity();input.oninput=()=>input.setCustomValidity('');return false;}
});}
function log(text){plan.log.unshift(text);}
function jump(i){const node=$('#article-'+i);if(node){$('.stream').scrollTop+=node.getBoundingClientRect().top-$('.stream').getBoundingClientRect().top;}}
document.addEventListener('click',e=>{
 const b=e.target.closest('[data-act]');if(!b)return;
 const a=b.dataset.act,n=b.dataset.name;listScroll=$('.list')?.scrollTop??listScroll;
 if(a==='close')return $('#dialog').close();
 if(a==='variant'||a==='left'||a==='right')return changeVariant(a==='variant'?+b.dataset.index:variant+(a==='left'?-1:1));
 if(a==='add'||a==='edit')return textForm(a==='add'?'Add Plan':'Edit Plan',a==='edit'?plan.name:'',s=>{if(plans.some(p=>p.name===s&&(a==='add'||p!==plan)))return false;if(a==='edit')plan.name=s;else{plans.push(makePlan(s,[],[]));usePlan(plans.at(-1));}log(a==='add'?'Created Plan':'Edited Plan');});
 if(a==='case'){focus=n;folder=current().folder;reading=true;if(variant===2){if(opened.has(n))opened.delete(n);else opened.add(n);}}
 if(a==='folder'){folder=b.dataset.folder;if(collapsed.has(folder))collapsed.delete(folder);else collapsed.add(folder);}
 if(a==='back')reading=false;
 if(a==='prev'||a==='next')focus=plan.cases[plan.cases.indexOf(current())+(a==='prev'?-1:1)].name;
 if(a==='expand')panelState=panelState==='expanded'?'':'expanded';
 if(a==='collapse')panelState=panelState==='closed'?'':'closed';
 if(a==='review'||a==='organize'){reviewing=a==='review';render();if(reviewing)jump(plan.cases.indexOf(current()));return;}
 if(a==='jump'){focus=plan.cases[+b.dataset.index].name;return jump(+b.dataset.index);}
 if(a==='all'){const visible=plan.cases.filter(matching),on=visible.every(c=>selected.has(c.name));for(const c of visible)on?selected.delete(c.name):selected.add(c.name);}
 if(a==='newfolder'||a==='rename')return textForm(a==='rename'?'Rename folder':'New folder',a==='rename'?folder:'',s=>{if(plan.folders.includes(s)&&!(a==='rename'&&s===folder))return false;if(a==='rename'){plan.folders[plan.folders.indexOf(folder)]=s;for(const c of plan.cases)if(c.folder===folder)c.folder=s;}else plan.folders.push(s);folder=s;log('Folder · '+s);});
 if(a==='sort'){plan.cases.sort((x,y)=>x.name.localeCompare(y.name));log('Sorted Test Cases');}
 if(a==='delete')return modal('Delete selected Test Cases?','<p>'+selected.size+' selected in '+esc(plan.name)+'</p>',()=>{log('Deleted '+selected.size+' Test Cases');plan.cases=plan.cases.filter(c=>!selected.has(c.name));selected.clear();if(!current())focus=plan.cases[0]?.name||'';});
 if(a==='history')return modal('History',plan.log.map(s=>'<p>'+esc(s)+'</p>').join('')||'<p>No edits in this demo session.</p>');
 if(a==='params'){const c=plan.cases.find(c=>c.name===n);return modal('Parameters · '+c.name.split(' ')[0],Object.entries(c.parameters).map(([k,v])=>'<label>'+esc(v)+'<input name="'+esc(k)+'" value="'+esc(plan.values[n]?.[k])+'"></label>').join(''),d=>{plan.values[n]=Object.fromEntries(d);log('Saved parameters · '+n);});}
 if(a==='import'){return modal('Import Test Cases','<label>Destination<select name="folder"><option value="">Unfiled</option>'+plan.folders.map(f=>'<option '+(folder===f?'selected':'')+'>'+esc(f)+'</option>').join('')+'</select></label>'+snapshot.cases.map((c,i)=>{const exists=plan.cases.some(x=>x.name===c.name);return '<label><input type="checkbox" name="case" value="'+i+'" '+(exists?'disabled':'')+'> '+esc(c.name)+(exists?' · In Plan':'')+'</label>';}).join(''),d=>{for(const i of d.getAll('case')){const c=structuredClone(snapshot.cases[i]);c.folder=d.get('folder');plan.cases.push(c);log('Imported '+c.name);focus=c.name;}});}
 render();
});
$('#plan').onchange=e=>{usePlan(plans[e.target.value]);render();};
document.addEventListener('change',e=>{if(e.target.matches('[data-pick]')){const n=e.target.dataset.pick;e.target.checked?selected.add(n):selected.delete(n);const del=$('[data-act="delete"]');if(del)del.disabled=!selected.size;}});
document.addEventListener('input',e=>{if(e.target.id==='search'){query=e.target.value;listScroll=0;render();$('#search').focus();}});
document.addEventListener('pointerdown',e=>{if(!e.target.matches('.grip'))return;const g=e.target,box=$('.stack').getBoundingClientRect();g.setPointerCapture(e.pointerId);g.onpointermove=m=>{topSize=Math.max(15,Math.min(75,(m.clientY-box.top)/box.height*100));$('.stack').style.setProperty('--top',topSize+'%');};g.onpointerup=()=>g.onpointermove=null;});
document.addEventListener('keydown',e=>{if(e.target.matches('.grip')&&['ArrowDown','ArrowUp'].includes(e.key)){e.preventDefault();topSize=Math.min(75,Math.max(15,topSize+(e.key==='ArrowDown'?5:-5)));$('.stack').style.setProperty('--top',topSize+'%');}});
render();
showFocused();
