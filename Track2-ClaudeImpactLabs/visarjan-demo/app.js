let dataset, selected, currentBrief = '', requestVersion = 0, pendingRequest;
let uploadedDataset;
let locations = [];
const scopeRows = v => dataset.rows.filter(r=>(v.year==='all'||r.year===v.year)&&(v.festival==='all'||r.festival===v.festival));
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
  renderBreakdown(v);
  if(!v.sites.some(g=>g.site===selected))selected=v[`${priority}_order`][0];
  renderRanking();
  renderDetail();
}

// Per-parameter counts for the selected scope, matching the guide's own framing
// ("42 of 116 dissolved-oxygen readings below 5 mg/l").
function renderBreakdown(v) {
  const rows=scopeRows(v).filter(assessed);
  const wording={'Dissolved oxygen':'below 5 mg/l','BOD':'above 3 mg/l','pH':'outside 6.5–8.5'};
  $('breach-breakdown').innerHTML=core.map(p=>{
    const all=rows.filter(r=>r.parameter===p), bad=all.filter(r=>r.severity>0);
    return `<li><span>${esc(p)} ${wording[p]}</span><b class="${bad.length?'bad':''}">${bad.length} / ${all.length}</b></li>`;
  }).join('');
}

const MAP_BOUNDS={west:77.272,east:77.535,north:23.292,south:23.183};
const tierColor=['#a33b2d','#d08a2b','#2f6f9f','#9aa5b3'];
function markerColor(g) {
  if(priority==='pollution')return tierColor[g.assessed?g.priority_tier:3];
  return g.coverage<.5?tierColor[0]:g.coverage<.9?tierColor[1]:tierColor[2];
}

// Schematic SVG map. Equirectangular projection over a fixed Bhopal window; lakes are
// drawn from their OpenStreetMap bounding boxes as simple shapes, not surveyed outlines.
function renderMap() {
  const v=view(); if(!v)return;
  const W=320,H=175,pad=10;
  const kx=Math.cos(23.24*Math.PI/180);
  const x=lon=>pad+(lon-MAP_BOUNDS.west)/(MAP_BOUNDS.east-MAP_BOUNDS.west)*(W-2*pad);
  const y=lat=>pad+(MAP_BOUNDS.north-lat)/(MAP_BOUNDS.north-MAP_BOUNDS.south)*(H-2*pad);
  const lakes=[
    {name:'Upper Lake (Bhojtal)',west:77.2657,east:77.3982,south:23.2084,north:23.2716,rx:1,ry:.78},
    {name:'Lower Lake',west:77.3975,east:77.4138,south:23.2425,north:23.2545},
    {name:'',cx:77.4212,cy:23.2067,r:.0045},
    {name:'',cx:77.4888,cy:23.2581,r:.006},
  ];
  let svg=`<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Schematic map of Bhopal immersion ghats, coloured by the current priority list">`;
  for(const lake of lakes){
    if(lake.r){svg+=`<ellipse class="lake" cx="${x(lake.cx)}" cy="${y(lake.cy)}" rx="${(x(lake.cx+lake.r)-x(lake.cx))*kx}" ry="${y(lake.cy)-y(lake.cy+lake.r)}"/><text class="lake-label" x="${x(lake.cx)}" y="${y(lake.cy)+22}" text-anchor="middle">${esc(lake.name)}</text>`;}
    else{const cx=(lake.west+lake.east)/2,cy=(lake.south+lake.north)/2;svg+=`<ellipse class="lake" cx="${x(cx)}" cy="${y(cy)}" rx="${(x(lake.east)-x(lake.west))/2*(lake.rx??1)}" ry="${(y(lake.south)-y(lake.north))/2*(lake.ry??1)}"/><text class="lake-label" x="${x(cx)}" y="${y(cy)+(lake.rx?4:18)}" text-anchor="middle">${esc(lake.name)}</text>`;}
  }
  const unplaced=[];
  const placed=v.sites.map(g=>({g,loc:locations.find(l=>l.site===g.site)})).filter(({g,loc})=>{if(!loc)unplaced.push(g.site);return Boolean(loc);});
  // Draw the selected marker last so it stays on top.
  placed.sort((a,b)=>(a.g.site===selected)-(b.g.site===selected));
  for(const {g,loc} of placed){
    const px=x(loc.lon),py=y(loc.lat),rank=g[`${priority}_rank`];
    const title=`${g.site}: ${priority==='pollution'?(rank?`pollution rank ${rank}`:'unranked, no assessable reading'):`testing rank ${rank}`} · ${Math.round(g.coverage*100)}% coverage · position ${loc.confidence}`;
    const short=g.site.replace(' (Sant Hirdaram)','').replace(' / Kamla Park kund','').replace(' / kund','').replace(' ghat','').replace(' kund','').replace(' lake','');
    const anchor={above:[px,py-12,'middle'],below:[px,py+18,'middle'],left:[px-11,py+3,'end']}[loc.anchor]||[px+11,py+3,'start'];
    svg+=`<g class="marker ${loc.confidence} ${g.site===selected?'active':''}" tabindex="0" role="button" data-site="${esc(g.site)}" aria-label="${esc(title)}"><title>${esc(title)}</title><circle cx="${px}" cy="${py}" r="8.5" fill="${markerColor(g)}"/><text x="${px}" y="${py+3}">${rank??'–'}</text><text class="name" x="${anchor[0]}" y="${anchor[1]}" text-anchor="${anchor[2]}">${esc(short)}</text></g>`;
  }
  svg+='</svg>';
  const legend=priority==='pollution'
    ?`<span><i style="background:${tierColor[0]}"></i>Oxygen below 5 mg/l</span><span><i style="background:${tierColor[1]}"></i>pH or BOD breach only</span><span><i style="background:${tierColor[2]}"></i>No breach assessed</span><span><i style="background:${tierColor[3]}"></i>Unranked</span>`
    :`<span><i style="background:${tierColor[0]}"></i>Under 50% coverage</span><span><i style="background:${tierColor[1]}"></i>50–89%</span><span><i style="background:${tierColor[2]}"></i>90% or more</span>`;
  $('map').innerHTML=svg;
  $('map-note').innerHTML=`<span class="map-legend">${legend}<span><i class="dashed"></i>Approximate position</span></span>`+(unplaced.length?`<span class="map-off">Not on map (no public position on file): ${esc(unplaced.join(', '))}.</span><br>`:'')+`Schematic map. Positions are public, approximate placements for orientation only and play no part in any ranking. Edit <code>ghat_locations.csv</code> to correct them.`;
  $('map').querySelectorAll('.marker').forEach(m=>{
    const pick=()=>{const site=m.dataset.site;if(site!==selected){selected=site;selectedEvent=undefined;}renderRanking();renderDetail();};
    m.onclick=pick; m.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();pick();}};
  });
}

let liveMap, liveLayer, liveFitted=false;
// Real tile map (Leaflet + OpenStreetMap). Falls back to the schematic SVG when the
// library or the tiles cannot load, e.g. offline. Marker colours mirror the list.
function renderLiveMap() {
  const v=view(); const host=$('live-map');
  if(!v||!host)return;
  if(typeof L==='undefined'){
    document.body.classList.remove('has-live-map');
    host.style.display='none';
    $('live-map-note').textContent='Interactive map unavailable (offline or blocked). The schematic map below is shown instead.';
    return;
  }
  document.body.classList.add('has-live-map');
  host.style.display='';
  if(!liveMap){
    liveMap=L.map(host,{scrollWheelZoom:false,zoomSnap:.5}).setView([23.24,77.40],12);
    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:19,attribution:'&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap</a> contributors'}).addTo(liveMap);
    liveLayer=L.layerGroup().addTo(liveMap);
    host.addEventListener('click',e=>{
      const button=e.target.closest('[data-open-site]');
      if(!button)return;
      const site=button.dataset.openSite;
      if(site!==selected){selected=site;selectedEvent=undefined;}
      renderRanking();renderDetail();
      $('detail').scrollIntoView({behavior:'smooth',block:'start'});
    });
  }
  liveLayer.clearLayers();
  const points=[]; const unplaced=[];
  for(const g of v.sites){
    const loc=locations.find(l=>l.site===g.site);
    if(!loc){unplaced.push(g.site);continue;}
    const rank=g[`${priority}_rank`], color=markerColor(g), reason=g.priority_reading;
    const icon=L.divIcon({className:'',html:`<div class="ghat-pin ${loc.confidence} ${g.site===selected?'active':''}" style="background:${color}" title="${esc(g.site)}">${rank??'–'}</div>`,iconSize:[30,30],iconAnchor:[15,15],popupAnchor:[0,-16]});
    const why=reason?`${reason.parameter} ${reason.value}${reason.parameter==='pH'?'':' mg/l'} in ${reason.festival} ${reason.year} (${phaseLabels[reason.phase].toLowerCase()}), against ${dataset.limits[reason.parameter]}.`:g.assessed?'No breach among assessed core readings. Not proof of full compliance.':'No assessable core readings in this scope.';
    const source=reason&&reason.report&&reason.source_page?`<a href="/reports/${encodeURIComponent(reason.report)}#page=${reason.source_page}" target="_blank" rel="noopener">Report PDF p. ${reason.source_page}</a>`:'';
    const gmaps=`https://www.google.com/maps/search/?api=1&query=${loc.lat},${loc.lon}`;
    const popup=`<div class="ghat-popup"><h3>${esc(g.site)}</h3><span class="tag" style="background:${color}">${priority==='pollution'?(rank?`Pollution rank ${rank} of ${v.sites.filter(x=>x.pollution_rank).length}`:'Unranked'):`Testing rank ${rank}`}</span><p>${esc(why)}</p><p>${g.breaches} of ${g.assessed} assessed readings outside reference · ${pct(g.coverage)} coverage${g.absent_events?` · ${g.absent_events} absent event${g.absent_events===1?'':'s'}`:''}</p>${g.identity_uncertain?'<p><b>Confirm site identity:</b> the name may cover two places.</p>':''}<div class="popup-actions"><button class="primary" data-open-site="${esc(g.site)}">Open details ↓</button>${source}<a href="${gmaps}" target="_blank" rel="noopener">Google Maps ↗</a></div><small>${esc(g.water_body)} · position ${esc(loc.confidence)}. ${esc(loc.source)}</small></div>`;
    const marker=L.marker([loc.lat,loc.lon],{icon,title:g.site,keyboard:true}).bindPopup(popup,{maxWidth:320});
    marker.on('click',()=>{if(g.site!==selected){selected=g.site;selectedEvent=undefined;renderRanking();renderDetail();marker.openPopup();}});
    marker.addTo(liveLayer);
    points.push([loc.lat,loc.lon]);
  }
  if(points.length&&!liveFitted){liveMap.fitBounds(points,{padding:[40,40],maxZoom:13});liveFitted=true;}
  $('live-map-note').textContent=(unplaced.length?`Not on map (no public position on file): ${unplaced.join(', ')}. `:'')+'Dashed rings mark approximate positions. Positions come from ghat_locations.csv and never affect a rank. Markers scroll the page to that ghat\'s evidence.';
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
  renderMap();
  renderLiveMap();
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
  $('detail').innerHTML=`<div class="detail-heading"><div><p class="water-body">${esc(g.water_body)} · ${g.events.length} event${g.events.length===1?'':'s'} in selected scope</p><h2>${esc(g.site)}</h2><span class="badge ${!g.assessed?'neutral':!g.breaches?'green':''}">${g.breaches?'Recorded breaches':g.assessed?'No breaches in assessed readings':'Insufficient data'}</span></div><span class="detail-actions">${(()=>{const loc=locations.find(l=>l.site===g.site);return loc?`<a class="map-link" target="_blank" rel="noopener" title="Opens openstreetmap.org in a new tab (internet required). Position is ${esc(loc.confidence)}: ${esc(loc.source)}" href="https://www.openstreetmap.org/?mlat=${loc.lat}&amp;mlon=${loc.lon}#map=15/${loc.lat}/${loc.lon}">Map ↗</a>`:''})()}<button id="site-brief" class="quiet">Site brief ↗</button></span></div><p class="lead-reason">${esc(reason)}</p>${worst?sourceLink(worst):''}${g.identity_uncertain?'<div class="warning">Confirm this site identity. The dataset marks its site matching as uncertain; verify that these records refer to the same location before using cross-year comparisons.</div>':''}<div class="site-metrics"><div><span>Pollution / testing rank</span><b>${g.pollution_rank??'—'} / ${g.testing_rank}</b><span>Within this selected scope</span></div><div><span>Assessed / expected</span><b>${g.assessed} / ${g.expected}</b><span>${pct(g.coverage)} core coverage</span></div><div><span>After-immersion breaches</span><b>${g.after_breaches} / ${g.after_assessed}</b><span>Assessed after readings only</span></div></div><nav class="detail-tabs" role="tablist" aria-label="Ghat detail views">${[['overview','Readings'],['recovery','Recovery'],['history','Across years'],['evidence','All evidence']].map(([id,label])=>`<button id="tab-${id}" role="tab" aria-selected="${activeTab===id}" aria-controls="detail-content" data-tab="${id}">${label}</button>`).join('')}</nav><div id="detail-content" role="tabpanel" aria-labelledby="tab-${activeTab}"></div>`;
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
  const colors=['#6aa5d8','#b26047','#1d5a8a'];
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
(async()=>{
  try{
    const response=await fetch('/api/locations',{signal:AbortSignal.timeout(5000)});
    if(response.ok)locations=await response.json();
  }catch{ /* The map is optional; rankings and briefs do not depend on it. */ }
  await load();
})();
