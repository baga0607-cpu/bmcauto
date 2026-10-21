'use strict';
window.ProjectInformationUI=(()=>{
 const esc=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 function capture(doc){
  document.querySelectorAll('#project-information-form [data-sku-name]').forEach(el=>{const sku=doc.skus.find(s=>s.id===el.dataset.skuName);if(sku)sku.name=el.value;});
  const items=new Map(doc.categories.flatMap(c=>c.items).map(i=>[i.id,i]));
  document.querySelectorAll('#project-information-form [data-info-item]').forEach(el=>{items.get(el.dataset.infoItem).sku_values[el.dataset.infoSku]=el.value;});
 }
 function render(record,editing=false,collapsed=new Set(),tab='spec'){
  const doc=record.document;
  const controls=editing?'<div class="actions"><span id="save-state" class="help" role="status"></span><button type="button" data-action="info-cancel">Cancel</button><button type="submit" class="primary">Save project information</button></div>':'<button type="button" class="primary" data-action="info-edit">Edit Project</button>';
  const skuEditor=editing?`<div class="toolbar"><button type="button" data-action="info-add-sku">Add SKU</button></div><div class="info-sku-names">${doc.skus.map(s=>`<div><label class="field"><span>SKU name</span><input data-sku-name="${esc(s.id)}" value="${esc(s.name)}" required maxlength="200"></label><button type="button" class="small-button danger" data-action="info-remove-sku" data-id="${esc(s.id)}">Remove SKU</button></div>`).join('')}</div>`:'';
  const table=`<div class="table-wrap info-specifications info-grouped" tabindex="0" role="region" aria-label="Project Spec"><table style="min-width:${250+doc.skus.length*210}px"><thead><tr><th scope="col">Item</th>${doc.skus.map(s=>`<th scope="col" data-no-translate>${esc(s.name)}</th>`).join('')}</tr></thead>${doc.categories.map((category,index)=>{
   const closed=collapsed.has(category.id),groupId='info-category-items-'+index;
   return `<tbody class="info-category-heading"><tr><th colspan="${doc.skus.length+1}"><button type="button" class="info-category-toggle" data-action="info-toggle-category" data-id="${esc(category.id)}" aria-expanded="${!closed}" aria-controls="${groupId}"><span class="info-chevron" aria-hidden="true">${closed?'▸':'▾'}</span><span data-no-translate>${esc(category.name)}</span></button></th></tr></tbody><tbody id="${groupId}" ${closed?'hidden':''}>${category.items.map(item=>{
    if(item.heading)return `<tr><th colspan="${doc.skus.length+1}" data-no-translate>${esc(item.name)}</th></tr>`;
    return `<tr><th scope="row"><strong data-no-translate>${esc(item.name)}</strong></th>${doc.skus.map((s,index)=>`<td class="${index>0&&(item.sku_values[s.id]||'')!==(item.sku_values[doc.skus[0].id]||'')?'info-sku-different':''}">${editing?`<textarea rows="3" aria-label="${esc(item.name+' — '+s.name)}" data-info-item="${esc(item.id)}" data-info-sku="${esc(s.id)}">${esc(item.sku_values[s.id]||'')}</textarea>`:`<div class="info-value" data-no-translate>${esc(item.sku_values[s.id]||'—')}</div>`}</td>`).join('')}</tr>`;
   }).join('')}</tbody>`;
  }).join('')}</table></div>`;
  const tabs=`<div class="tabs" role="tablist" aria-label="Project sections">${[['spec','Project Spec'],['members','Members']].map(([id,label])=>`<button type="button" role="tab" id="project-info-tab-${id}" aria-selected="${tab===id}" aria-controls="project-info-panel" data-action="info-section" data-section="${id}">${label}</button>`).join('')}</div>`;
  const content=tab==='members'?'<div class="empty"><h2>Members</h2><p>Project member management is not configured yet.</p></div>':`${skuEditor}${doc.skus.length?table:'<div class="empty"><h3>No SKUs yet</h3><p>Add a SKU to compare its specifications.</p></div>'}`;
  return `<form id="project-information-form"><div class="page-heading info-project-heading"><h1 data-no-translate>${esc(record.project_name)}</h1>${controls}</div>${tabs}<div id="project-info-panel" role="tabpanel" aria-labelledby="project-info-tab-${tab}">${content}</div></form>`;
 }
 return {capture,render};
})();
