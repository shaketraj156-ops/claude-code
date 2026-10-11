let dataset, selected, currentBrief = '', requestVersion = 0, pendingRequest;
let uploadedDataset;
let activeDataset = new URLSearchParams(location.search).get('dataset') === 'sample' ? 'sample' : 'full';
let priority = 'pollution', activeTab = 'overview', selectedEvent, historyFestival, historyParameter = 'Dissolved oxygen';
const $ = id => document.getElementById(id);
const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const core = ['pH', 'Dissolved oxygen', 'BOD'];
const phases = ['pre', 'during', 'after'];
const phaseLabels = {pre:'Before', during:'During', after:'After'};
const assessed = r => Boolean(r && ['Outside reference', 'Within reference'].includes(r.status));
const pct = (a,b=1) => b ? Math.round(a/b*100)+'%' : '—';
const number = value => Number.isInteger(value) ? String(value) : Number(value.toPrecision(8)).toString();
const format = r => !r ? 'No record' : r.flag || (r.value === null ? 'Unavailable' : String(r.value));
const eventKey = event => `${event.year}|${event.festival}`;
const view = () => dataset?.model.views[`${$('year').value}|${$('festival').value}`];
const group = () => view()?.sites.find(g=>g.site===selected);
const row = id => id === null || id === undefined ? undefined : dataset.rows[id];
const eventRows = event => event.row_ids.map(row);
// Open on the event holding the reading that drove the rank, so the table shows the
// evidence the stated reason cites. An event with no records is only a last resort.
function defaultEvent(g) {
  const reason = g.priority_reading;
  return (reason && g.events.find(e=>e.year===reason.year && e.festival===reason.festival))
    || [...g.events].reverse().find(e=>!e.absent) || g.events.at(-1);
}
const currentEvent = () => {
  const g = group();
  return g && (g.events.find(e=>eventKey(e)===selectedEvent) || defaultEvent(g));
};

function download(text, filename, type='text/plain;charset=utf-8') {
  const url = URL.createObjectURL(new Blob([text], {type}));
  const anchor = document.createElement('a');
  anchor.href=url; anchor.download=filename; anchor.click();
  setTimeout(()=>URL.revokeObjectURL(url),1000);
}

function csvCell(value) {
  let text = String(value ?? '');
  // Treat user-provided names as text when opened in a spreadsheet.
  if (typeof value === 'string' && /^[\s]*[=+\-@]/.test(text)) text = "'" + text;
  return '"' + text.replaceAll('"','""') + '"';
}

async function load(body, source=activeDataset) {
  const version=++requestVersion;
  pendingRequest?.abort();
  $('error').textContent='';
  if(location.protocol==='file:') {
    $('detail').innerHTML='<div class="empty"><h2>Start your local workspace</h2><p>Double-click <b>start-demo.cmd</b> in this folder, then <a href="http://127.0.0.1:8765/">open Visarjan Ghat Watch</a>.</p></div>';
    try {
      await fetch('http://127.0.0.1:8765/api/data',{mode:'no-cors',signal:AbortSignal.timeout(2000)});
      location.replace('http://127.0.0.1:8765/');
    } catch { $('loading').textContent='Start the local server to load measurements.'; }
    return;
  }
  const controller=new AbortController();
  pendingRequest=controller;
  const timeout=setTimeout(()=>controller.abort(),15000);
  $('loading').textContent='Loading measurements and calculating priorities…';
  $('year').disabled=$('festival').disabled=true;
  $('open-brief').disabled=$('export-ranks').disabled=true;
  try {
    let result;
    if(body===undefined && source==='upload') {
      if(!uploadedDataset)throw new Error('Upload a CSV before selecting uploaded measurements.');
      result=uploadedDataset;
    } else {
      const response=await fetch(body===undefined ? (source==='sample'?'/api/sample':'/api/data') : '/api/analyze', {signal:controller.signal,...(body===undefined?{}:{method:'POST',body})});
      result=await response.json();
      if(version!==requestVersion)return;
      if(!response.ok)throw new Error(result.error || 'Could not load data.');
    }
    dataset=result;
    activeDataset=body===undefined?source:'upload';
    if(activeDataset==='upload')uploadedDataset=result;
    if(activeDataset==='upload' && !$('dataset').querySelector('[value="upload"]'))$('dataset').insertAdjacentHTML('beforeend','<option value="upload">Uploaded measurements</option>');
    $('dataset').value=activeDataset;
    const address=new URL(location.href);
    if(activeDataset==='upload')address.searchParams.delete('dataset');
    else address.searchParams.set('dataset',activeDataset);
    history.replaceState(null,'',address);
    const years=[...result.model.years].sort((a,b)=>b-a);
    $('year').innerHTML='<option value="all">All years</option>'+years.map(y=>`<option value="${y}">${y}</option>`).join('');
    $('year').value=source==='sample' && body===undefined ? String(years[0]) : 'all';
    $('festival').innerHTML='<option value="all">Both / all festivals</option>'+result.model.festivals.map(f=>`<option value="${esc(f)}">${esc(f)}</option>`).join('');
    $('festival').value=source==='sample' && body===undefined ? (result.model.festivals.includes('Ganesh')?'Ganesh':result.model.festivals[0]) : 'all';
    $('year').disabled=$('festival').disabled=false;
    $('open-brief').disabled=$('export-ranks').disabled=false;
    selectedEvent=undefined;
    $('search').value='';
    $('loading').textContent=`${activeDataset==='upload'?'Uploaded CSV':activeDataset==='sample'?'Built-in 2025 sample':'Bhopal reports · 2023–2025'} · ${result.rows.length.toLocaleString('en-US')} readings · ${result.model.years.length} report year${result.model.years.length===1?'':'s'}`;
    render();
  } catch(error) {
    if(version!==requestVersion)return;
    const reason=error.name==='AbortError'?'The request timed out.':error.message;
    $('error').textContent=`Could not load measurements: ${reason} ${dataset?'Your previous dataset is still displayed.':'Start the server with start-demo.cmd, then choose Reload data.'}`;
    $('dataset').value=activeDataset;
    $('loading').textContent=dataset?`${dataset.rows.length.toLocaleString('en-US')} previous readings retained`:'Data unavailable';
    if(!dataset)$('detail').innerHTML='<div class="empty"><h2>Measurements unavailable</h2><p>Start the local server, then choose Reload data.</p></div>';
  } finally {
    clearTimeout(timeout);
    if(version===requestVersion){
      pendingRequest=null;
      $('year').disabled=$('festival').disabled=!dataset;
      $('open-brief').disabled=$('export-ranks').disabled=!dataset;
    }
  }
}

function filterChanged() {
  // An upload may not contain every festival in every year.
  for(const option of $('festival').options) option.disabled=!dataset.model.views[`${$('year').value}|${option.value}`];
  if(!view())$('festival').value='all';
  selectedEvent=undefined;
  render();
}

function render() {
  const v=view();
  if(!v)return;
  $('sites').textContent=v.site_count;
  $('breaches').textContent=`${v.breaches} / ${v.assessed}`;
  $('coverage').textContent=pct(v.assessed,v.expected);
  $('gaps').textContent=v.expected-v.assessed;
  if(!v.sites.some(g=>g.site===selected))selected=v[`${priority}_order`][0];
  renderRanking();
  renderDetail();
}

function renderRanking() {
  if(!view())return;
  $('pollution-tab').setAttribute('aria-pressed',priority==='pollution');
  $('testing-tab').setAttribute('aria-pressed',priority==='testing');
  $('ranking-description').textContent=priority==='pollution'?'Low dissolved oxygen first: lowest measured oxygen, then recurrence. Other breaches follow. Missing oxygen is never treated as normal.':'Lowest coverage first, then older evidence and uncertain site identity. These are evidence gaps, not predicted pollution.';
  const query=$('search').value.trim().toLocaleLowerCase();
  const groups=view()[`${priority}_order`].map(name=>view().sites.find(g=>g.site===name)).filter(g=>g.site.toLocaleLowerCase().includes(query));
  $('ranking').innerHTML=groups.map((g,index)=>`<button class="ghat ${g.site===selected?'active':''}" data-index="${index}" aria-pressed="${g.site===selected}"><span class="rank-number">${g[`${priority}_rank`]??'—'}</span><span style="flex:1;min-width:0"><b>${esc(g.site)}</b><small>${priority==='pollution'?(g.assessed?`${g.breaches}/${g.assessed} assessed outside reference`:'Unranked · no assessable core readings'):`${g.missing}/${g.expected} checks unassessed · latest ${g.latest_year??'unknown'}`}</small><small>${pct(g.coverage)} coverage${g.absent_events?` · ${g.absent_events} absent event${g.absent_events===1?'':'s'}`:''}</small><span class="mini-bar"><i style="width:${g.coverage*100}%"></i></span></span></button>`).join('') || '<p class="empty">No matching ghat in this dataset.</p>';
  $('ranking').querySelectorAll('button').forEach(button=>button.onclick=()=>{
    const site=groups[Number(button.dataset.index)].site;
    // A new ghat re-opens on its own rank-driving event; the year/festival filters
    // above are the way to hold one event steady across ghats.
    if(site!==selected){selected=site;selectedEvent=undefined;}
    renderRanking();renderDetail();
  });
}

function sourceLabel(r) {
  if(r?.report && r.source_page)return `${r.report}, PDF p. ${r.source_page}`;
  return `Uploaded source not matched${r?.source_document?`: ${r.source_document}`:''}${r?.source_page?` (supplied p. ${r.source_page})`:''}`;
}

function sourceLink(r) {
  return r?.report && r.source_page ? `<a class="evidence-link" target="_blank" rel="noopener" href="/reports/${encodeURIComponent(r.report)}#page=${r.source_page}">${esc(sourceLabel(r))} ↗</a>` : `<span class="muted">${esc(sourceLabel(r))}</span>`;
}

function readingCell(r, link=true) {
  const value=esc(format(r));
  const content=link && r?.report && r.source_page ? `<a class="reading-link" title="${esc(sourceLabel(r))}" target="_blank" rel="noopener" href="/reports/${encodeURIComponent(r.report)}#page=${r.source_page}">${value}</a>`:value;
  return `<td title="${esc(r?.status || 'Not sampled')}" class="${r?.severity>0?'bad':r?.status==='Within reference'?'ok':''}">${content}</td>`;
}

function coverageText(event) {
  return `${event.assessed===9?'All 9 core checks are available.':`${9-event.assessed} of 9 core checks could not be assessed.`} ${event.before_after_pairs===3?'Before/after comparison is available for all three core parameters.':`Before/after comparison is available for ${event.before_after_pairs} of 3 core parameters.`}`;
}

function renderDetail() {
  const g=group();
  if(!g)return;
  const worst=g.priority_reading;
  const reason=worst?`${worst.parameter} was ${worst.value}${worst.parameter==='pH'?'':' mg/l'} in ${worst.festival} ${worst.year} (${phaseLabels[worst.phase].toLowerCase()} immersion), against ${dataset.limits[worst.parameter]}. ${g.breaches} of ${g.assessed} assessed readings were outside reference across this scope.`:g.assessed?'No breaches among the assessed core readings in this scope. This does not establish full compliance or current safety.':'No core readings can be assessed in this scope. Prioritise obtaining evidence; pollution cannot be ranked.';
  const event=currentEvent(); selectedEvent=eventKey(event);
  $('detail').innerHTML=`<div class="detail-heading"><div><p class="water-body">${esc(g.water_body)} · ${g.events.length} event${g.events.length===1?'':'s'} in selected scope</p><h2>${esc(g.site)}</h2><span class="badge ${!g.assessed?'neutral':!g.breaches?'green':''}">${g.breaches?'Recorded breaches':g.assessed?'No breaches in assessed readings':'Insufficient data'}</span></div><button id="site-brief" class="quiet">Site brief ↗</button></div><p class="lead-reason">${esc(reason)}</p>${worst?sourceLink(worst):''}${g.identity_uncertain?'<div class="warning">Confirm this site identity. The dataset marks its site matching as uncertain; verify that these records refer to the same location before using cross-year comparisons.</div>':''}<div class="site-metrics"><div><span>Pollution / testing rank</span><b>${g.pollution_rank??'—'} / ${g.testing_rank}</b><span>Within this selected scope</span></div><div><span>Assessed / expected</span><b>${g.assessed} / ${g.expected}</b><span>${pct(g.coverage)} core coverage</span></div><div><span>After-immersion breaches</span><b>${g.after_breaches} / ${g.after_assessed}</b><span>Assessed after readings only</span></div></div><nav class="detail-tabs" role="tablist" aria-label="Ghat detail views">${[['overview','Readings'],['recovery','Recovery'],['history','Across years'],['evidence','All evidence']].map(([id,label])=>`<button id="tab-${id}" role="tab" aria-selected="${activeTab===id}" aria-controls="detail-content" data-tab="${id}">${label}</button>`).join('')}</nav><div id="detail-content" role="tabpanel" aria-labelledby="tab-${activeTab}"></div>`;
  $('site-brief').onclick=()=>showBrief(true);
  document.querySelectorAll('[data-tab]').forEach(button=>button.onclick=()=>{activeTab=button.dataset.tab;renderDetail();});
  if(activeTab==='history')renderHistory();
  else renderEventContent();
}

function eventBar(event) {
  return `<div class="event-bar"><div><h3>${activeTab==='recovery'?'Recovery check':activeTab==='evidence'?'Measurement register':'Before, during & after'}</h3><p class="muted">${esc(event.festival)} ${event.year} · ${event.absent?'No records for this site/event':`${event.row_ids.length} recorded parameter readings`}</p></div><label>Inspect event<select id="event">${[...group().events].reverse().map(e=>`<option value="${esc(eventKey(e))}" ${eventKey(e)===selectedEvent?'selected':''}>${esc(e.festival)} ${e.year}${e.absent?' · no data':''}</option>`).join('')}</select></label></div>`;
}

function renderEventContent() {
  const event=currentEvent(), readings=eventRows(event);
  let content=eventBar(event);
  if(event.absent)content+='<div class="warning">This site has no records for the selected event. It remains in the testing priorities; missing measurements are not evidence of clean water.</div>';
  if(activeTab==='overview') {
    content+=`<div class="tablewrap"><table id="core-table"><thead><tr><th>Parameter</th><th>Before</th><th>During</th><th>After</th><th>Class B reference</th></tr></thead><tbody>${core.map(p=>`<tr><td>${esc(p)}${p==='pH'?'':'<small>mg/l · assumed</small>'}</td>${phases.map(phase=>readingCell(readings.find(r=>r.parameter===p&&r.phase===phase))).join('')}<td>${esc(dataset.limits[p])}</td></tr>`).join('')}</tbody></table></div><p id="coverage-note" class="muted">${esc(coverageText(event))}</p><p class="legend"><span class="dot"></span>Outside reference <span class="dot green"></span>Within reference for this reading only. BDL/ND are not zero.</p>${actionBox(group())}`;
  } else if(activeTab==='recovery') {
    content+=`<div class="tablewrap"><table id="recovery-table"><thead><tr><th>Parameter</th><th>During</th><th>After</th><th>Evidence-based finding</th><th>After − before</th></tr></thead><tbody>${event.recovery.map(check=>`<tr><td>${esc(check.parameter)}</td>${readingCell(row(check.during_id))}${readingCell(row(check.after_id))}<td>${esc(check.status)}</td><td>${check.before_after_delta===null?'Not assessable':`${check.before_after_delta>0?'+':''}${number(check.before_after_delta)}${check.parameter==='pH'?'':' mg/l'}`}</td></tr>`).join('')}</tbody></table></div><p class="muted">“Returned within reference” compares during and after readings. It does not mean a return to baseline, establish safety, or prove the cause of a change. pH differences have no single “better” direction.</p>`;
  } else {
    content+=`<div class="event-bar"><label>Parameter<select id="evidence-parameter"><option value="all">All parameters</option>${[...new Set(readings.map(r=>r.parameter))].map(p=>`<option>${esc(p)}</option>`).join('')}</select></label><button id="export-evidence">Download event CSV ↓</button></div><p class="muted">PDF links match bundled records. Uploaded source descriptions are unverified. Missing sample rows may be absent from the register.</p><div class="tablewrap" id="evidence-register"></div>`;
  }
  $('detail-content').innerHTML=content;
  $('event').onchange=()=>{selectedEvent=$('event').value;renderEventContent();};
  if(activeTab==='evidence') {
    renderEvidence();$('evidence-parameter').onchange=renderEvidence;
    $('export-evidence').onclick=()=>{
      // identity_needs_check travels with the rows, so a forwarded event CSV keeps the
      // same site-identity caveat shown on screen and carried in the briefs.
      const fields=['year','festival','site','water_body','phase','parameter','value','flag','source_page','unit_assumed','source_document','site_match_confidence'];
      const uncertain=group().identity_uncertain?'yes':'no';
      download('\ufeff'+[[...fields,'identity_needs_check'].map(csvCell).join(','),...readings.map(r=>[...fields.map(f=>csvCell(r[f]??'')),csvCell(uncertain)].join(','))].join('\r\n'),'ghat-event-evidence.csv','text/csv;charset=utf-8');
    };
  }
}

function actionBox(g) {
  const text=g.missing?`Fill ${g.missing} unassessed core checks across ${g.events.length} event(s), and collect current samples. Latest numeric evidence in the selected festival scope: ${g.latest_year??'unavailable'}.`:`All expected core checks in this scope are available. Collect current samples before making operational decisions; report years do not establish today’s conditions.`;
  const review=g.breaches?'Review cleaning and aeration needs against current site conditions. Historical breaches alone do not specify an intervention or guarantee its effect.':'Continue monitoring. A lack of breaches among these three parameters is not full water-quality compliance.';
  return `<div class="action-box"><h3>Suggested officer follow-up</h3><p><b>Testing:</b> ${esc(text)}</p><p><b>Operational review:</b> ${esc(review)}</p></div>`;
}

function renderEvidence() {
  const readings=eventRows(currentEvent()).filter(r=>$('evidence-parameter').value==='all'||r.parameter===$('evidence-parameter').value);
  $('evidence-register').innerHTML=readings.length?`<table><thead><tr><th>Parameter / stage</th><th>Reading</th><th>Assessment</th><th>Source</th></tr></thead><tbody>${readings.map(r=>`<tr><td>${esc(r.parameter)}<small>${phaseLabels[r.phase]}</small></td><td>${esc(format(r))}<small>${esc(r.unit_assumed || (r.parameter==='pH'?'dimensionless':'unit unspecified'))}</small></td><td>${esc(r.status)}</td><td>${sourceLink(r)}</td></tr>`).join('')}</tbody></table>`:'<p class="empty">No measurements to display for this event.</p>';
}

function renderHistory() {
  const available=dataset.model.festivals;
  if($('festival').value!=='all')historyFestival=$('festival').value;
  if(!available.includes(historyFestival))historyFestival=available[0];
  $('detail-content').innerHTML=`<h3>Compare the same festival across years</h3><p class="muted">History shows all years in the loaded dataset, independently of the year filter above. Each phase is kept separate; lines stop at missing readings.</p><div class="trend-controls"><label>Parameter<select id="history-parameter">${core.map(p=>`<option ${p===historyParameter?'selected':''}>${esc(p)}</option>`).join('')}</select></label><label>Festival<select id="history-festival">${available.map(f=>`<option ${f===historyFestival?'selected':''}>${esc(f)}</option>`).join('')}</select></label></div><div id="history-chart"></div><div id="history-table" class="tablewrap"></div>`;
  $('history-parameter').onchange=()=>{historyParameter=$('history-parameter').value;renderChart();};
  $('history-festival').onchange=()=>{historyFestival=$('history-festival').value;renderChart();};
  renderChart();
}

function renderChart() {
  const years=dataset.model.years;
  const entries=years.map(year=>{
    const event=dataset.model.histories[selected].find(e=>e.year===year&&e.festival===historyFestival);
    const readings=event?eventRows(event):[];
    return {year,points:phases.map(phase=>readings.find(r=>r.parameter===historyParameter&&r.phase===phase))};
  });
  const limits=dataset.thresholds[historyParameter];
  const numeric=entries.flatMap(e=>e.points).filter(assessed).map(r=>r.value);
  const low=historyParameter==='pH'?Math.min(6,...numeric,...limits):0;
  const maximum=Math.max(...numeric,...limits,low+1);
  const high=Math.min(Number.MAX_VALUE,maximum+(historyParameter==='pH'?.5:maximum*.12));
  const width=680,height=245,left=48,right=22,top=25,bottom=35;
  const x=index=>years.length===1?width/2:left+index*(width-left-right)/(years.length-1);
  const y=value=>top+(high-value)/(high-low)*(height-top-bottom);
  const colors=['#477794','#b26047','#377459'];
  let svg=`<svg viewBox="0 0 ${width} ${height}" role="img" aria-label="${esc(historyParameter)} by year and sampling phase for ${esc(historyFestival)}. Exact values are in the following table.">`;
  for(let tick=0;tick<=4;tick++){
    const value=low+(high-low)*(tick/4);
    svg+=`<line x1="${left}" y1="${y(value)}" x2="${width-right}" y2="${y(value)}" stroke="#e1e8dc"/><text x="${left-9}" y="${y(value)+4}" text-anchor="end" fill="#738471" font-size="10">${number(value)}</text>`;
  }
  limits.forEach(value=>svg+=`<line x1="${left}" y1="${y(value)}" x2="${width-right}" y2="${y(value)}" stroke="#a58b47" stroke-dasharray="5 4"/><text x="${width-right}" y="${y(value)-5}" text-anchor="end" fill="#8c793c" font-size="9">reference ${value}</text>`);
  phases.forEach((phase,index)=>{
    let previous;
    entries.forEach((entry,i)=>{
      const point=entry.points[index];
      if(!assessed(point)){previous=undefined;return;}
      if(previous)svg+=`<line x1="${previous.x}" y1="${previous.y}" x2="${x(i)}" y2="${y(point.value)}" stroke="${colors[index]}" stroke-width="2"/>`;
      svg+=`<circle cx="${x(i)}" cy="${y(point.value)}" r="4" fill="${colors[index]}" stroke="white" stroke-width="1.5"><title>${entry.year} ${phaseLabels[phase]}: ${point.value}</title></circle>`;
      previous={x:x(i),y:y(point.value)};
    });
  });
  years.forEach((year,i)=>svg+=`<text x="${x(i)}" y="${height-10}" text-anchor="middle" fill="#657862" font-size="11">${year}</text>`);
  svg+='</svg>';
  $('history-chart').innerHTML=numeric.length?`<div class="chart">${svg}</div><div class="chart-legend">${phases.map((p,i)=>`<span><i style="background:${colors[i]}"></i>${phaseLabels[p]}</span>`).join('')}<span>Dashed: Class B reference</span></div>`:'<p class="empty">No numeric readings for this parameter and festival. No trend can be drawn.</p>';
  $('history-table').innerHTML=`<table><thead><tr><th>Year</th><th>Before</th><th>During</th><th>After</th></tr></thead><tbody>${entries.map(e=>`<tr><td>${e.year}</td>${e.points.map(p=>readingCell(p)).join('')}</tr>`).join('')}</tbody></table><p class="legend">${esc(historyParameter)}${historyParameter==='pH'?' · dimensionless':' · mg/l (assumed)'}. Click linked values to open the source PDF. Changes are observations, not a forecast.</p>`;
}

function siteBrief(g) {
  return {en:g.brief_en,hi:g.brief_hi};
}

function showBrief(siteOnly=false) {
  const brief=siteOnly?siteBrief(group()):{en:view().brief_en,hi:view().brief_hi};
  $('brief-title').textContent=siteOnly?'Site brief':'Officer brief · selected scope';
  $('brief-en').textContent=brief.en;$('brief-hi').textContent=brief.hi;
  currentBrief=brief.en+'\n\nहिंदी\n\n'+brief.hi;
  $('brief-dialog').showModal();
}

function exportRanks() {
  // rank_reason_* is the reading that produced the rank, matching the screen and the brief.
  // worst_deviation_* is the single largest deviation, which for a low-oxygen site is usually a different reading.
  const fields=['scope_year','scope_festival','method_version','reference_class','site','water_body','pollution_rank','testing_rank','assessed','expected','breaches','missing','coverage_percent','latest_evidence_year','after_breaches','after_assessed','rank_reason_parameter','rank_reason_value','rank_reason_year','rank_reason_festival','rank_reason_phase','rank_reason_source','worst_deviation_parameter','worst_deviation_value','worst_deviation_source','identity_needs_check'];
  const records=view().pollution_order.map(name=>{
    const g=view().sites.find(g=>g.site===name),reason=g.priority_reading,worst=g.worst_reading;
    return [view().year,view().festival,dataset.model.version,'B',g.site,g.water_body,g.pollution_rank??'',g.testing_rank,g.assessed,g.expected,g.breaches,g.missing,Math.round(g.coverage*100),g.latest_year??'',g.after_breaches,g.after_assessed,reason?.parameter??'',reason?.value??'',reason?.year??'',reason?.festival??'',reason?.phase??'',reason?sourceLabel(reason):'',worst?.parameter??'',worst?.value??'',worst?sourceLabel(worst):'',g.identity_uncertain?'yes':'no'];
  });
  download('\ufeff'+[fields,...records].map(values=>values.map(csvCell).join(',')).join('\r\n'),'ghat-priorities.csv','text/csv;charset=utf-8');
}

$('year').onchange=filterChanged;$('festival').onchange=filterChanged;
$('dataset').value=activeDataset;
$('dataset').onchange=()=>load(undefined,$('dataset').value);
$('reset').onclick=()=>load();
$('search').oninput=renderRanking;
$('pollution-tab').onclick=()=>{priority='pollution';renderRanking();};
$('testing-tab').onclick=()=>{priority='testing';renderRanking();};
$('open-brief').onclick=()=>showBrief();
$('export-ranks').onclick=exportRanks;
$('close-brief').onclick=()=>$('brief-dialog').close();
$('download-brief').onclick=()=>download(currentBrief,'visarjan-officer-brief.txt');
$('print-brief').onclick=()=>window.print();
let openedForPrint=false;
window.addEventListener('beforeprint',()=>{
  if(dataset && !$('brief-dialog').open){openedForPrint=true;showBrief();}
});
window.addEventListener('afterprint',()=>{
  if(openedForPrint){$('brief-dialog').close();openedForPrint=false;}
});
$('upload').onchange=async event=>{
  const file=event.target.files[0];event.target.value='';
  if(!file)return;
  if(file.size>2_000_000){$('error').textContent='Upload a CSV smaller than 2 MB. Your current dataset has not changed.';return;}
  await load(file);
};
load();
