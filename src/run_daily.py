<!doctype html>
<html>
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>Stock Analysis Dashboard</title>
  <style>
    body{font-family:system-ui,-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;margin:24px;}
    h1{margin:0 0 10px 0;}
    .sub{color:#555;margin-bottom:14px;}
    .controls{display:flex;flex-wrap:wrap;gap:10px;align-items:center;margin-bottom:10px;}
    select,input{padding:6px 8px;border:1px solid #ccc;border-radius:8px;font-size:14px;}
    table{width:100%;border-collapse:collapse;font-size:14px;}
    th,td{border-bottom:1px solid #eee;padding:10px 8px;vertical-align:top;}
    th{color:#333;text-align:left;font-weight:600;background:#fafafa;position:sticky;top:0;}
    .pill{display:inline-block;padding:2px 10px;border-radius:999px;border:1px solid #ddd;font-size:12px;}
    .BUY{background:#f1fff1;border-color:#cce9cc;}
    .SELL{background:#fff1f1;border-color:#f1c1c1;}
    .HOLD{background:#f6f6f6;}
    .small{font-size:12px;color:#666;line-height:1.35;}
    a{color:#1a73e8;text-decoration:none;}
    a:hover{text-decoration:underline;}

    td.pos{color:#0a7a2f;}
    td.neg{color:#b00020;}
    td.hot{background:rgba(255,215,0,0.25);}
  </style>
</head>
<body>
  <h1>Stock Analysis Dashboard (Paper Trading)</h1>
  <div class="sub" id="asof">Loading…</div>

  <div class="controls">
    <label>Region
      <select id="region"></select>
    </label>
    <label>Category
      <select id="category"></select>
    </label>
    <label>Action
      <select id="action"></select>
    </label>
    <label>Search
      <input id="search" placeholder="ticker…" />
    </label>
  </div>

  <table>
    <thead>
      <tr>
        <th>Ticker</th>
        <th>Region</th>
        <th>Category</th>
        <th>Action</th>
        <th>Confidence</th>
        <th>Prev Close</th>
        <th>Last Close</th>
        <th>Change</th>
        <th>Pred Close (Tomorrow)</th>
        <th>Model Conf</th>
        <th>Ranges (approx)</th>
        <th>Notes</th>
      </tr>
    </thead>
    <tbody id="tbody"></tbody>
  </table>

<script>
const state = { region:'ALL', category:'ALL', action:'ALL', search:'' };

function uniq(arr){ return [...new Set(arr)].sort(); }
function optAll(id, items){
  const s = document.getElementById(id);
  s.innerHTML = '';
  const o0 = document.createElement('option');
  o0.value = 'ALL'; o0.textContent = 'All';
  s.appendChild(o0);
  for(const it of items){
    const o = document.createElement('option');
    o.value = it; o.textContent = it;
    s.appendChild(o);
  }
}

function fmtPctRange(r){
  if(!r || typeof r.low !== 'number' || typeof r.high !== 'number') return '—';
  const lo = (r.low*100).toFixed(1);
  const hi = (r.high*100).toFixed(1);
  return `${lo}% to ${hi}%`;
}

function fmtNum(x){
  return (typeof x === 'number' && isFinite(x)) ? x.toFixed(2) : '';
}
function fmtPct(x){
  if(typeof x !== 'number' || !isFinite(x)) return '';
  const s = (x*100).toFixed(1) + '%';
  return (x>0?'+':'') + s;
}
function rowChangePct(r){
  if(typeof r.prev_close !== 'number' || typeof r.last_close !== 'number' || r.prev_close === 0) return null;
  return (r.last_close - r.prev_close) / r.prev_close;
}
function sortRowsPinned(rows){
  // Top 5 winners + top 5 losers (by daily % change) pinned above everything else.
  const withChg = rows.map(r=>{
    const cp = rowChangePct(r);
    return {...r, _chgPct: cp};
  });
  const valid = withChg.filter(r=> typeof r._chgPct === 'number');
  const winners = [...valid].sort((a,b)=>b._chgPct-a._chgPct).slice(0,5);
  const losers  = [...valid].sort((a,b)=>a._chgPct-b._chgPct).slice(0,5);
  const pinnedTickers = new Set([...winners, ...losers].map(r=>r.ticker));
  const rest = withChg.filter(r=> !pinnedTickers.has(r.ticker))
                      .sort((a,b)=> (b.confidence||0)-(a.confidence||0));
  return [...winners, ...losers, ...rest];
}

function render(){
  const tb = document.getElementById('tbody');
  tb.innerHTML = '';

  let rows = window.SNAP.rows.filter(r=>{
    if(r.status !== 'OK') return false;
    if(state.region !== 'ALL' && r.region.toUpperCase() !== state.region) return false;
    if(state.category !== 'ALL' && r.category !== state.category) return false;
    if(state.action !== 'ALL' && r.action !== state.action) return false;
    if(state.search && !r.ticker.toLowerCase().includes(state.search.toLowerCase())) return false;
    return true;
  });
  rows = sortRowsPinned(rows);

  for(const r of rows){
    const tr = document.createElement('tr');
    const chgPct = rowChangePct(r);
    const chgAbs = (typeof r.prev_close==='number' && typeof r.last_close==='number') ? (r.last_close - r.prev_close) : null;
    const predPct = (typeof r.pred_close_1d==='number' && typeof r.last_close==='number' && r.last_close!==0) ? (r.pred_close_1d - r.last_close)/r.last_close : null;
    const chgClass = (chgPct==null) ? '' : (chgPct>0 ? 'pos' : (chgPct<0 ? 'neg' : ''));
    const predClass = (predPct==null) ? '' : (Math.abs(predPct) >= 0.02 ? 'hot' : (predPct>0 ? 'pos' : (predPct<0 ? 'neg' : '')));

    const pill = `<span class="pill ${r.action}">${r.action}</span>`;

    const notes = [];
    if(typeof r.trend === 'number'){
      notes.push(r.trend>0 ? 'Uptrend (MA50>MA200)' : (r.trend<0 ? 'Downtrend (MA50<MA200)' : 'Flat trend'));
    }
    if(typeof r.mom_6m === 'number'){
      notes.push(`6M mom: ${(r.mom_6m*100).toFixed(1)}%`);
    }
    if(typeof r.vol_20d_ann === 'number'){
      notes.push(`Vol: ${(r.vol_20d_ann*100).toFixed(0)}%`);
    }
    if(typeof r.rsi14 === 'number'){
      notes.push(`RSI: ${r.rsi14.toFixed(0)}`);
    }

    const news = (window.SNAP.news && window.SNAP.news[r.ticker]) ? window.SNAP.news[r.ticker] : [];
    const newsHtml = (news.length>0)
      ? `<div class="small">News: <a href="${news[0].link}" target="_blank" rel="noreferrer">${news[0].title}</a></div>`
      : '';

    tr.innerHTML = `
      <td><b>${r.ticker}</b>${newsHtml}</td>
      <td>${r.region.toUpperCase()}</td>
      <td>${r.category}</td>
      <td>${pill}</td>
      <td>${r.confidence}</td>
      <td class="${chgClass}">${fmtNum(r.prev_close)}</td>
      <td class="${chgClass}">${fmtNum(r.last_close)}</td>
      <td class="${chgClass}"><b>${fmtPct(chgPct)}</b><div class="small">${fmtNum(chgAbs)}</div></td>
      <td class="${predClass}">${fmtNum(r.pred_close_1d)}<div class="small">${fmtPct(predPct)}</div></td>
      <td class="${predClass}">${(typeof r.pred_confidence_1d === 'number') ? r.pred_confidence_1d : ''}</td>
      <td class="small">
        1D: ${fmtPctRange(r.range_1d)}<br/>
        1W: ${fmtPctRange(r.range_1w)}<br/>
        1M: ${fmtPctRange(r.range_1m)}
      </td>
      <td class="small">${notes.join(' • ')}</td>
    `;
    tb.appendChild(tr);
  }
}

function wire(){
  const r = document.getElementById('region');
  const c = document.getElementById('category');
  const a = document.getElementById('action');
  const s = document.getElementById('search');

  r.addEventListener('change', e=>{state.region=e.target.value; render();});
  c.addEventListener('change', e=>{state.category=e.target.value; render();});
  a.addEventListener('change', e=>{state.action=e.target.value; render();});
  s.addEventListener('input', e=>{state.search=e.target.value; render();});
}

async function boot(){
  const resp = await fetch('./data/snapshot.json', {cache:'no-store'});
  const snap = await resp.json();
  window.SNAP = snap;

  document.getElementById('asof').textContent =
    `As of (UTC): ${snap.asof_utc} • Rows: ${snap.rows.filter(r=>r.status==='OK').length}`;

  const regions = uniq(snap.rows.filter(r=>r.status==='OK').map(r=>r.region.toUpperCase()));
  const cats = uniq(snap.rows.filter(r=>r.status==='OK').map(r=>r.category));
  const acts = ['BUY','HOLD','SELL'];

  optAll('region', regions);
  optAll('category', cats);
  optAll('action', acts);

  wire();
  render();
}

boot().catch(err=>{
  document.getElementById('asof').textContent = 'Failed to load snapshot.json';
  console.error(err);
});
</script>
</body>
</html>
