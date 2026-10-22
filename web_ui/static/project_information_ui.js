'use strict';
window.ProjectInformationUI=(()=>{
 const esc=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 function capture(doc){
  document.querySelectorAll('#project-information-form [data-sku-name]').forEach(el=>{const sku=doc.skus.find(s=>s.id===el.dataset.skuName);if(sku)sku.name=el.value;});
  const items=new Map(doc.categories.flatMap(c=>c.items).map(i=>[i.id,i]));
  document.querySelectorAll('#project-information-form [data-info-item]').forEach(el=>{const item=items.get(el.dataset.infoItem);if(el.hasAttribute('data-info-target'))item.target=el.value;else item.sku_values[el.dataset.infoSku]=el.value;});
 }
 function render(record,editing=false,collapsed=new Set(),tab='spec'){
  const doc=record.document,columns=doc.skus.length?doc.skus:[{id:null,name:record.project_name}];
  const controls=editing?'<div class="actions"><span id="save-state" class="help" role="status"></span><button type="button" data-action="info-cancel">Cancel</button><button type="submit" class="primary">Save project information</button></div>':'<button type="button" class="primary" data-action="info-edit">Edit Project</button>';
  const skuEditor=editing?`<div class="toolbar"><button type="button" data-action="info-add-sku">Add SKU</button></div><div class="info-sku-names">${doc.skus.map(s=>`<div><label class="field"><span>SKU name</span><input data-sku-name="${esc(s.id)}" value="${esc(s.name)}" required maxlength="200"></label><button type="button" class="small-button danger" data-action="info-remove-sku" data-id="${esc(s.id)}">Remove SKU</button></div>`).join('')}</div>`:'';
  const table=`<div class="table-wrap info-specifications info-grouped" tabindex="0" role="region" aria-label="Project Spec"><table style="min-width:${250+columns.length*210}px"><thead><tr><th scope="col">Item</th>${columns.map(s=>`<th scope="col" data-no-translate>${esc(s.name)}</th>`).join('')}</tr></thead>${doc.categories.map((category,index)=>{
   const closed=collapsed.has(category.id),groupId='info-category-items-'+index;
   return `<tbody class="info-category-heading"><tr><th colspan="${columns.length+1}"><button type="button" class="info-category-toggle" data-action="info-toggle-category" data-id="${esc(category.id)}" aria-expanded="${!closed}" aria-controls="${groupId}"><span class="info-chevron" aria-hidden="true">${closed?'▸':'▾'}</span><span data-no-translate>${esc(category.name)}</span></button></th></tr></tbody><tbody id="${groupId}" ${closed?'hidden':''}>${category.items.map(item=>{
    if(item.heading)return `<tr><th colspan="${columns.length+1}" data-no-translate>${esc(item.name)}</th></tr>`;
    return `<tr><th scope="row"><strong data-no-translate>${esc(item.name)}</strong></th>${columns.map((s,index)=>{
     const value=s.id===null?item.target:(item.sku_values[s.id]||'');
     const different=index>0&&value!==(item.sku_values[columns[0].id]||'');
     return `<td class="${different?'info-sku-different':''}">${editing?`<textarea rows="3" aria-label="${esc(item.name+' — '+s.name)}" data-info-item="${esc(item.id)}" ${s.id===null?'data-info-target':`data-info-sku="${esc(s.id)}"`}>${esc(value)}</textarea>`:`<div class="info-value" data-no-translate>${esc(value||'—')}</div>`}</td>`;
    }).join('')}</tr>`;
   }).join('')}</tbody>`;
  }).join('')}</table></div>`;
  const tabs=`<div class="tabs" role="tablist" aria-label="Project sections">${[['spec','Project Spec'],['members','Members']].map(([id,label])=>`<button type="button" role="tab" id="project-info-tab-${id}" aria-selected="${tab===id}" aria-controls="project-info-panel" data-action="info-section" data-section="${id}">${label}</button>`).join('')}</div>`;
  const content=tab==='members'?'<div class="empty"><h2>Members</h2><p>Project member management is not configured yet.</p></div>':`${skuEditor}${(doc.skus.length||doc.source.filename)?table:'<div class="empty"><h3>No SKUs yet</h3><p>Add a SKU to compare its specifications.</p></div>'}`;
  return `<form id="project-information-form"><div class="page-heading info-project-heading"><h1 data-no-translate>${esc(record.project_name)}</h1>${controls}</div>${tabs}<div id="project-info-panel" role="tabpanel" aria-labelledby="project-info-tab-${tab}">${content}</div></form>`;
 }
 function fitSpec(){
  const table=document.querySelector('.info-specifications');
  if(!table)return;
  table.style.setProperty('--spec-height',Math.max(120,window.innerHeight-table.getBoundingClientRect().top-24)+'px');
 }
 let bound=false;
 function bind(){
  fitSpec();
  if(!bound){window.addEventListener('resize',fitSpec);bound=true;}
 }
 return {capture,render,bind};
})();
