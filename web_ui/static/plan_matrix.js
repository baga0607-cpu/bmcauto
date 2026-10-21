/* Plan results are reduced across current Task memberships, never by Task name. */
'use strict';
window.PlanMatrix = (() => {
  function label(status) {
    return ({Passed:'PASS',Failed:'FAIL',Block:'Block',Blocked:'Block',Running:'Running',PASS:'PASS',FAIL:'FAIL'})[status] || 'NR';
  }
  function resultTime(c) {
    const raw=c.result_updated_at || c.manual_override?.modified_at || c.executed_at;
    const time=Date.parse(raw || '');
    return Number.isFinite(time)?time:-Infinity;
  }
  function summarize(plan) {
    const tasks=plan.tasks || [];
    const maps=tasks.map(task=>new Map(task.testcases.map(c=>[c.id,c])));
    const counts={PASS:0,FAIL:0,Block:0,NR:0};
    const rows=plan.testcases.map(tc=>{
      const cells=maps.map(map=>map.get(tc.id));
      let final='NR', latest=-Infinity;
      // Equal/missing timestamps use stable API Task order; later column wins.
      for(const c of cells) {
        if(!c)continue;
        const value=label(c.status), time=resultTime(c);
        if(['PASS','FAIL','Block'].includes(value)&&time>=latest){final=value;latest=time;}
      }
      counts[final]++;
      return {id:tc.id,name:tc.tc_name,cells:cells.map(c=>c?label(c.status):null),final};
    });
    return {rows,counts,total:rows.length,completed:rows.length-counts.NR};
  }
  return {summarize,label};
})();
