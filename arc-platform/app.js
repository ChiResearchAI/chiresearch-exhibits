/* ChiResearch — ARC RFP 828 working demonstration
   Three applications, one platform. The engine below is shared; each application
   is a configuration of it. That is the architecture the proposal describes. */

const cssv = n => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
const RAMP = () => ['--seq-2','--seq-3','--seq-4','--seq-5','--seq-7'].map(cssv);

const BAND = [
  { k:'reliable',   lab:'Reliable (CV ≤ 15%)',       gly:'●', col:()=>cssv('--good') },
  { k:'caution',    lab:'Use with caution (15–30%)', gly:'◐', col:()=>cssv('--warning') },
  { k:'unreliable', lab:'Unreliable (CV > 30%)',     gly:'○', col:()=>cssv('--critical') },
  { k:'none',       lab:'No reliable estimate',      gly:'×', col:()=>cssv('--nodata') },
];
const bandOf = cv => cv == null ? BAND[3] : cv <= 15 ? BAND[0] : cv <= 30 ? BAND[1] : BAND[2];
const cvOf = (e, m) => (e == null || m == null || e <= 0) ? null : +(((m/1.645)/e)*100).toFixed(1);

const APPS = {
  explorer: {
    title: 'Regional Data Explorer',
    sub: 'DataNexus replacement — Exhibit A, Application 1',
    geos: ['county','city','tract'], defaultGeo: 'county',
    defaultInd: 'housing_afford.pGRAPI30PctPlus_e23',
    defaultInd2: 'income.pHHIncLt10k_e23',
    region: 'all',
  },
  housing: {
    title: 'Regional Housing Dashboard',
    sub: 'Exhibit A, Application 2 — Housing Forward 2035 implementation tracking',
    geos: ['county','city'], defaultGeo: 'county',
    defaultInd: 'housing_afford.pHousingCost30PctPlus_e23',
    defaultInd2: 'housing_value.pVal300_500k_e23',
    region: 'arc',
    datasets: ['housing_afford','housing_value'],
  },
  mobility: {
    title: 'Economic Mobility Dashboard',
    sub: 'Exhibit A, Application 3 — framework',
    geos: ['county','tract'], defaultGeo: 'tract',
    defaultInd: 'income.pHHIncLt10k_e23',
    defaultInd2: 'commuting.pPublicTrans_e23',
    region: 'arc',
    datasets: ['income','commuting'],
  },
};

const S = {
  app: 'explorer', geo: 'county', ind: null, ind2: null,
  bin: 'quantile', flag: true, sel: null, q: '', region: 'all',
  sortK: 'val', sortDir: -1,
};

let CAT = [], cache = {}, rows = [], breaks = [], layer = null, refLayer = null, map = null;
const tip = document.getElementById('tip');

/* ─── data ─────────────────────────────────────────────────────────── */
async function load(geo) {
  if (cache[geo]) return cache[geo];
  setBusy(true);
  const [g, v] = await Promise.all([
    fetch(`geom_${geo}.json`).then(r => r.json()),
    fetch(`vals_${geo}.json`).then(r => r.json()),
  ]);
  cache[geo] = { geom: g, vals: v };
  setBusy(false);
  return cache[geo];
}
const setBusy = b => document.getElementById('busy').style.display = b ? 'flex' : 'none';

/* ARC publishes its region flag on counties. Tract GEOIDs nest inside county GEOIDs
   (state 2 + county 3 + tract 6), so the region extends to tracts by prefix. Place
   codes do not nest in counties, so city extent is statewide and is labelled as such
   rather than implied to be regional. */
let ARC_FIPS = null;
async function arcFips() {
  if (ARC_FIPS) return ARC_FIPS;
  const c = await load('county');
  ARC_FIPS = new Set(c.geom.features
    .filter(f => f.properties.PlanningRegion === 'Atlanta Regional Commission')
    .map(f => f.properties.GEOID));
  return ARC_FIPS;
}
function inRegion(props) {
  if (S.region !== 'arc') return true;
  if (S.geo === 'county') return props.PlanningRegion === 'Atlanta Regional Commission';
  if (S.geo === 'tract' && ARC_FIPS) return ARC_FIPS.has(String(props.GEOID).slice(0, 5));
  return true;
}

function build(d) {
  let ind = CAT.find(c => c.id === S.ind);
  if (!ind) { ind = CAT[0]; S.ind = ind.id; }
  const i2 = S.ind2 ? CAT.find(c => c.id === S.ind2) : null;
  rows = d.geom.features.filter(f => inRegion(f.properties)).map(f => {
    const g = f.properties.GEOID;
    const rec = d.vals[g] || {};
    const pair = rec[ind.id], pair2 = i2 ? rec[i2.id] : null;
    const e = pair ? pair[0] : null, m = pair ? pair[1] : null;
    return {
      geoid: g, name: (rec.name || f.properties.NAME || '(unnamed)'),
      val: e, moe: m, cv: cvOf(e, m),
      val2: pair2 ? pair2[0] : null, f,
    };
  });
}

function computeBreaks() {
  const v = rows.filter(r => r.val != null).map(r => r.val).sort((a,b) => a-b);
  if (!v.length) { breaks = []; return; }
  if (S.bin === 'quantile') breaks = [.2,.4,.6,.8].map(q => v[Math.floor(q*(v.length-1))]);
  else if (S.bin === 'equal') {
    const lo = v[0], hi = v[v.length-1], s = (hi-lo)/5;
    breaks = [1,2,3,4].map(i => +(lo+s*i).toFixed(1));
  } else {
    const mu = v.reduce((a,b)=>a+b,0)/v.length;
    const sd = Math.sqrt(v.reduce((a,b)=>a+(b-mu)**2,0)/v.length);
    breaks = [-1.5,-.5,.5,1.5].map(z => +(mu+z*sd).toFixed(1));
  }
}
const binOf = v => { let i=0; while (i<breaks.length && v>breaks[i]) i++; return i; };

/* ─── map ──────────────────────────────────────────────────────────── */
function styleFor(r) {
  const ramp = RAMP();
  if (!r || r.val == null) return { fillColor: cssv('--nodata'), fillOpacity:.45,
    color: cssv('--rule'), weight:.5 };
  const unrel = S.flag && bandOf(r.cv).k === 'unreliable';
  const b = binOf(r.val);
  return {
    fillColor: unrel ? cssv('--nodata') : ramp[b],
    fillOpacity: unrel ? .4 : .85,
    color: r.geoid === S.sel ? cssv('--text-primary')
         : (unrel ? cssv('--text-muted') : ramp[Math.min(4, b+1)]),
    weight: r.geoid === S.sel ? 2.6 : (S.geo === 'county' ? .7 : 1.05),
    dashArray: unrel ? '2 2' : null,
  };
}

function tipHtml(r) {
  const ind = CAT.find(c => c.id === S.ind), b = bandOf(r.cv);
  if (r.val == null) return `<b>${r.name}</b><span class="r">No reliable estimate published</span>`;
  return `<b>${r.name}</b>${ind.label}<br><strong>${r.val}%</strong>` +
    (r.moe != null ? ` ± ${r.moe}` : '') +
    `<br><span class="r"><span style="color:${b.col()}">${b.gly}</span> ${b.lab}` +
    (r.val2 != null ? `<br>${CAT.find(c=>c.id===S.ind2).label}: <strong>${r.val2}%</strong>` : '') +
    `</span>`;
}

function showTip(html, ev) {
  tip.innerHTML = html; tip.style.opacity = 1;
  const p = 12, w = tip.offsetWidth, h = tip.offsetHeight;
  let x = ev.clientX + p, y = ev.clientY + p;
  if (x + w > innerWidth - 8) x = ev.clientX - w - p;
  if (y + h > innerHeight - 8) y = ev.clientY - h - p;
  tip.style.left = (x + scrollX) + 'px'; tip.style.top = (y + scrollY) + 'px';
}
const hideTip = () => tip.style.opacity = 0;

function drawMap(d) {
  if (layer) { layer.remove(); layer = null; }
  const by = {}; rows.forEach(r => by[r.geoid] = r);
  const keep = new Set(rows.map(r => r.geoid));
  layer = L.geoJSON(d.geom, {
    filter: f => keep.has(f.properties.GEOID),
    style: f => styleFor(by[f.properties.GEOID]),
    onEachFeature: (f, lyr) => {
      const r = by[f.properties.GEOID]; if (!r) return;
      lyr.on('mouseover', e => { showTip(tipHtml(r), e.originalEvent);
        lyr.setStyle({ weight:2.2, color: cssv('--text-primary') }); });
      lyr.on('mousemove', e => showTip(tipHtml(r), e.originalEvent));
      lyr.on('mouseout', () => { hideTip(); lyr.setStyle(styleFor(r)); });
      lyr.on('click', () => select(r.geoid));
    }
  }).addTo(map);
  map.invalidateSize(false);
  requestAnimationFrame(() => {
    map.invalidateSize(false);
    try { map.fitBounds(layer.getBounds(), { padding:[10,10] }); } catch(e) {}
  });
}

async function drawRef() {
  if (refLayer) { refLayer.remove(); refLayer = null; }
  if (S.geo === 'county') return;
  const c = await load('county');
  refLayer = L.geoJSON(c.geom, { interactive:false,
    filter: f => S.region !== 'arc' || f.properties.PlanningRegion === 'Atlanta Regional Commission',
    style: { fill:false, color: cssv('--text-muted'), weight:.8, opacity:.5 } }).addTo(map);
  refLayer.bringToBack();
}

/* ─── charts ───────────────────────────────────────────────────────── */
function drawScatter() {
  const svg = document.getElementById('scatter');
  const host = document.getElementById('scatterWrap');
  if (!S.ind2) { host.style.display = 'none'; return; }
  host.style.display = '';
  const W=430,H=250,L=48,R=12,T=14,B=38;
  const pts = rows.filter(r => r.val != null && r.val2 != null);
  if (!pts.length) { svg.innerHTML = ''; return; }
  const mxX = Math.max(...pts.map(p=>p.val)), mxY = Math.max(...pts.map(p=>p.val2));
  const x = v => L + (v/mxX)*(W-L-R), y = v => H-B - (v/mxY)*(H-T-B);
  let s = '<g class="ax">';
  for (let i=0;i<=4;i++){ const v=mxY*i/4, yy=y(v);
    s += `<line class="grid-l" x1="${L}" x2="${W-R}" y1="${yy}" y2="${yy}"/>
          <text x="${L-7}" y="${yy+3.5}" text-anchor="end">${v.toFixed(0)}</text>`; }
  for (let i=0;i<=4;i++){ const v=mxX*i/4;
    s += `<text x="${x(v)}" y="${H-B+15}" text-anchor="middle">${v.toFixed(0)}</text>`; }
  s += `<line x1="${L}" x2="${W-R}" y1="${H-B}" y2="${H-B}"/></g>`;
  const rad = S.geo==='tract' ? 2.1 : S.geo==='city' ? 2.8 : 3.6;
  s += pts.map(p => {
    const b = bandOf(p.cv), sel = p.geoid === S.sel;
    return `<circle class="dot${sel?' sel':''}" data-id="${p.geoid}"
      cx="${x(p.val).toFixed(1)}" cy="${y(p.val2).toFixed(1)}" r="${sel?rad+2.2:rad}"
      fill="${b.k==='unreliable'?'none':b.col()}"
      stroke="${b.k==='unreliable'?b.col():cssv('--surface-1')}"
      stroke-width="${b.k==='unreliable'?1.4:1}" opacity=".82"/>`; }).join('');
  svg.innerHTML = s;
  svg.querySelectorAll('.dot').forEach(c => {
    const r = rows.find(z => z.geoid === c.dataset.id);
    c.addEventListener('mousemove', e => showTip(tipHtml(r), e));
    c.addEventListener('mouseleave', hideTip);
    c.addEventListener('click', () => select(r.geoid));
  });
  document.getElementById('sxLab').textContent = CAT.find(c=>c.id===S.ind).label;
  document.getElementById('syLab').textContent = CAT.find(c=>c.id===S.ind2).label;
}

function drawHist() {
  const svg = document.getElementById('hist');
  const W=430,H=170,L=42,R=12,T=12,B=32,NB=20;
  const v = rows.filter(r => r.val != null).map(r => r.val);
  if (!v.length) { svg.innerHTML=''; return; }
  const mn=0, mx=Math.max(...v), w=(mx-mn)/NB, cnt=new Array(NB).fill(0);
  v.forEach(d => { let i=Math.floor((d-mn)/w); if(i>=NB)i=NB-1; if(i<0)i=0; cnt[i]++; });
  const mxC = Math.max(...cnt);
  const x = i => L + (i/NB)*(W-L-R), bw = (W-L-R)/NB - 2, y = c => H-B - (c/mxC)*(H-T-B);
  let s = '<g class="ax">';
  for (let i=0;i<=3;i++){ const c=Math.round(mxC*i/3), yy=y(c);
    s += `<line class="grid-l" x1="${L}" x2="${W-R}" y1="${yy}" y2="${yy}"/>
          <text x="${L-7}" y="${yy+3.5}" text-anchor="end">${c}</text>`; }
  for (let i=0;i<=4;i++){ const vv=mn+(mx-mn)*i/4;
    s += `<text x="${x(NB*i/4)}" y="${H-B+14}" text-anchor="middle">${vv.toFixed(0)}</text>`; }
  s += `<line x1="${L}" x2="${W-R}" y1="${H-B}" y2="${H-B}"/></g>`;
  s += cnt.map((c,i) => `<rect class="bar" x="${x(i)+1}" y="${y(c)}" width="${bw}"
        height="${Math.max(0,H-B-y(c))}" rx="3" ry="3"/>`).join('');
  svg.innerHTML = s;
  svg.querySelectorAll('.bar').forEach((b,i) => {
    const a = mn+i*w, bb = a+w;
    b.addEventListener('mousemove', e => showTip(
      `<b>${a.toFixed(1)}–${bb.toFixed(1)}%</b><span class="r">${cnt[i]} geograph${cnt[i]===1?'y':'ies'}</span>`, e));
    b.addEventListener('mouseleave', hideTip);
  });
}

/* ─── KPIs (dashboard apps) ────────────────────────────────────────── */
function drawKpis() {
  const host = document.getElementById('kpis');
  if (S.app === 'explorer') { host.style.display = 'none'; return; }
  host.style.display = '';
  const cfg = APPS[S.app];
  const picks = CAT.filter(c => cfg.datasets.includes(c.dataset_key)).slice(0, 4);
  const d = cache[S.geo];
  host.innerHTML = picks.map(ind => {
    const vals = rows.map(r => (d.vals[r.geoid]||{})[ind.id]).filter(Boolean).map(p => p[0]);
    if (!vals.length) return '';
    const med = vals.slice().sort((a,b)=>a-b)[Math.floor(vals.length/2)];
    const lo = Math.min(...vals), hi = Math.max(...vals);
    return `<div class="kpi"><div class="kn">${med.toFixed(1)}%</div>
      <div class="kl">${ind.label.replace(/^% /,'').replace(/, 2023$/,'')}</div>
      <div class="ks">median across ${vals.length} ${S.geo === 'county' ? 'counties' : S.geo+'s'} ·
      range ${lo.toFixed(1)}–${hi.toFixed(1)}%</div></div>`;
  }).join('');
}

function drawGoal() {
  const host = document.getElementById('goal');
  if (S.app !== 'housing') { host.style.display = 'none'; return; }
  host.style.display = '';
  host.innerHTML = `
    <h3>Housing Forward 2035 — implementation tracking</h3>
    <p class="muted" style="margin:0 0 12px">ARC's adopted regional target is
      <strong>367,000 additional homes by 2035</strong>, measured from a 2020 baseline using Census
      Housing Unit Estimates as the official county production measure. The tracking structure below
      is live; the county target column is deliberately empty, because ARC's county targets were
      scheduled for Board adoption on 12 November 2026 and are not ours to assume. They populate
      from the administrative interface without a code change.</p>
    <div class="goalbar">
      <div class="gb"><div class="gbf" style="width:0%"></div></div>
      <div class="gbl"><span>2020 baseline</span>
        <span><strong>Progress to be computed on ARC's delivered baseline</strong></span>
        <span>367,000 by 2035</span></div>
    </div>`;
}

/* ─── table ────────────────────────────────────────────────────────── */
function drawTable() {
  const tb = document.querySelector('#tbl tbody');
  const ind = CAT.find(c => c.id === S.ind);
  document.getElementById('colVal').textContent = ind.label.replace(/^% /,'').slice(0,46);
  const k = S.sortK, dir = S.sortDir;
  const list = rows.slice().sort((p,q) => {
    let A,B;
    if (k === 'name') { A=p.name; B=q.name; }
    else if (k === 'rel') { A=p.cv==null?999:p.cv; B=q.cv==null?999:q.cv; }
    else { A = p[k]==null?-1:p[k]; B = q[k]==null?-1:q[k]; }
    return A<B?-dir:A>B?dir:0;
  });
  tb.innerHTML = list.map(r => {
    const b = bandOf(r.cv);
    return `<tr data-id="${r.geoid}" class="${r.geoid===S.sel?'sel':''}">
      <td>${r.name}</td>
      <td class="num">${r.val==null?'—':r.val.toFixed(1)}</td>
      <td class="num">${r.moe==null?'—':'± '+r.moe.toFixed(1)}</td>
      <td><span class="gly" style="color:${b.col()}">${b.gly}</span> ${b.lab.replace(/ \(.*\)/,'')}</td>
    </tr>`; }).join('');
  tb.querySelectorAll('tr').forEach(tr => tr.addEventListener('click', () => select(tr.dataset.id)));
  document.getElementById('tblCount').textContent =
    `${list.length.toLocaleString()} geographies`;
}

/* ─── catalogue ────────────────────────────────────────────────────── */
function drawCatalogue() {
  const host = document.getElementById('cat');
  const cfg = APPS[S.app];
  let items = CAT;
  if (cfg.datasets) items = items.filter(c => cfg.datasets.includes(c.dataset_key));
  if (S.q) {
    const q = S.q.toLowerCase();
    items = items.filter(c => c.label.toLowerCase().includes(q) ||
                              c.dataset.toLowerCase().includes(q));
  }
  const groups = {};
  items.forEach(c => (groups[c.dataset] = groups[c.dataset] || []).push(c));
  host.innerHTML = Object.entries(groups).map(([ds, list]) => `
    <div class="cg"><div class="cgh">${ds}<span>${list.length}</span></div>
    ${list.map(c => `<button class="ci${c.id===S.ind?' on':''}${c.id===S.ind2?' on2':''}"
        data-id="${c.id}" title="${c.label}">${c.label.replace(/^% /,'').replace(/, 2023$/,'')}</button>`).join('')}
    </div>`).join('') || '<p class="muted" style="padding:8px">No indicators match.</p>';
  host.querySelectorAll('.ci').forEach(b => {
    b.addEventListener('click', e => {
      if (e.shiftKey) { S.ind2 = (S.ind2 === b.dataset.id) ? null : b.dataset.id; }
      else { S.ind = b.dataset.id; }
      render(true);
    });
  });
  document.getElementById('catCount').textContent =
    `${items.length} of ${CAT.length} indicators · ${Object.keys(groups).length} datasets`;
}

function drawMeta() {
  const ind = CAT.find(c => c.id === S.ind);
  document.getElementById('meta').innerHTML = `
    <div><span>Indicator</span>${ind.label}</div>
    <div><span>Dataset</span>${ind.dataset}</div>
    <div><span>Source field</span><code>${ind.field}</code> · MOE <code>${ind.moe}</code></div>
    <div><span>Vintage</span>${ind.vintage} · ACS 5-year</div>
    <div><span>Service</span>ArcGIS Online, org <code>opendata@arc</code></div>`;
}

function drawLegend() {
  const ramp = RAMP(), v = rows.filter(r => r.val != null).map(r => r.val);
  if (!v.length) { document.getElementById('legend').innerHTML = ''; return; }
  const edges = [Math.min(...v), ...breaks, Math.max(...v)];
  document.getElementById('legend').innerHTML =
    ramp.map((c,i) => `<span class="lg"><span class="sw" style="background:${c}"></span>
      ${edges[i].toFixed(0)}–${edges[i+1].toFixed(0)}%</span>`).join('') +
    BAND.map(b => `<span class="lg"><span class="gly" style="color:${b.col()}">${b.gly}</span>${b.lab}</span>`).join('');
}

/* ─── orchestration ────────────────────────────────────────────────── */
function select(id) {
  S.sel = S.sel === id ? null : id;
  const r = rows.find(z => z.geoid === S.sel);
  document.getElementById('selname').textContent = r ? r.name : '— none —';
  if (layer) layer.eachLayer(l => {
    const rr = rows.find(z => z.geoid === l.feature.properties.GEOID);
    if (rr) l.setStyle(styleFor(rr));
  });
  drawScatter(); drawTable();
}

async function render(refetch = true) {
  const cfg = APPS[S.app];
  if (S.region === 'arc') await arcFips();
  const d = await load(S.geo);
  if (refetch) { build(d); computeBreaks(); }
  updateExtentNote();
  drawCatalogue(); drawMeta(); drawKpis(); drawGoal();
  drawMap(d); await drawRef(); drawLegend(); drawScatter(); drawHist(); drawTable();
}

function firstIndicatorFor(cfg) {
  const pool = cfg.datasets ? CAT.filter(c => cfg.datasets.includes(c.dataset_key)) : CAT;
  return pool.length ? pool[0].id : (CAT[0] && CAT[0].id);
}

function updateExtentNote() {
  const cfg = APPS[S.app];
  const el = document.getElementById('regionNote');
  if (cfg.region !== 'arc') { el.textContent = 'Statewide — all 159 Georgia counties'; return; }
  if (S.geo === 'county') el.textContent = "ARC 11-county region, from ARC's own PlanningRegion field";
  else if (S.geo === 'tract') el.textContent = "ARC 11-county region — tracts nested by county FIPS";
  else el.textContent = 'Statewide — place codes do not nest in counties';
}

function setApp(a) {
  S.app = a;
  const cfg = APPS[a];
  S.region = cfg.region; S.sel = null;
  S.ind2 = CAT.some(c => c.id === cfg.defaultInd2) ? cfg.defaultInd2 : null;
  S.geo = cfg.defaultGeo; S.q = '';
  S.ind = CAT.some(c => c.id === cfg.defaultInd) ? cfg.defaultInd : firstIndicatorFor(cfg);
  document.getElementById('search').value = '';
  document.getElementById('selname').textContent = '— none —';
  document.getElementById('appTitle').textContent = cfg.title;
  document.getElementById('appSub').textContent = cfg.sub;
  document.querySelectorAll('.tab').forEach(t => t.classList.toggle('on', t.dataset.app === a));
  const gs = document.getElementById('geo');
  gs.innerHTML = cfg.geos.map(g =>
    `<option value="${g}"${g===cfg.defaultGeo?' selected':''}>${
      g==='county'?'County':g==='city'?'City / town':'Census tract'}</option>`).join('');
  updateExtentNote();
  render(true);
}

async function boot() {
  CAT = await fetch('catalogue.json').then(r => r.json());
  map = L.map('map', { scrollWheelZoom: true, zoomControl: true }).setView([32.9,-83.4], 7);
  map.attributionControl.addAttribution(
    'Atlanta Regional Commission · ACS 2023 · ArcGIS Online org opendata@arc');

  document.querySelectorAll('.tab').forEach(t =>
    t.addEventListener('click', () => setApp(t.dataset.app)));
  document.getElementById('geo').onchange = e => { S.geo = e.target.value; S.sel = null; updateExtentNote(); render(true); };
  document.getElementById('bin').onchange = e => { S.bin = e.target.value; computeBreaks(); render(false); };
  document.getElementById('flag').onchange = e => { S.flag = e.target.checked; render(false); };
  document.getElementById('search').oninput = e => { S.q = e.target.value; drawCatalogue(); };
  document.querySelectorAll('#tbl th').forEach(th => th.onclick = () => {
    const k = th.dataset.k;
    S.sortDir = S.sortK === k ? -S.sortDir : (k === 'name' ? 1 : -1);
    S.sortK = k; drawTable();
  });
  addEventListener('load', () => map.invalidateSize(false));

  const btn = document.getElementById('csv');
  btn.onclick = () => {
    const ind = CAT.find(c => c.id === S.ind);
    const head = ['geoid','name','indicator','dataset','estimate_pct','moe_90pct','cv_pct','reliability'];
    const body = rows.map(r => [r.geoid, `"${(r.name||'').replace(/"/g,'""')}"`,
      `"${ind.label}"`, `"${ind.dataset}"`, r.val ?? '', r.moe ?? '', r.cv ?? '',
      bandOf(r.cv).lab.replace(/ \(.*\)/,'')]);
    const csv = [head.join(','), ...body.map(r => r.join(','))].join('\n');
    const was = btn.textContent; btn.disabled = true; btn.textContent = 'Preparing…';
    try { saveCsv(`arc_${S.app}_${S.geo}.csv`, csv); btn.textContent = 'Exported'; }
    catch(e) { btn.textContent = 'Export failed'; }
    setTimeout(() => { btn.textContent = was; btn.disabled = false; }, 1700);
  };

  setApp('explorer');
}
boot();

function saveCsv(filename, csv){
  var blob = new Blob([csv], {type:'text/csv;charset=utf-8'});
  var url = URL.createObjectURL(blob);
  var a = document.createElement('a');
  a.href = url; a.download = filename;
  document.body.appendChild(a); a.click(); document.body.removeChild(a);
  setTimeout(function(){ URL.revokeObjectURL(url); }, 1000);
}
