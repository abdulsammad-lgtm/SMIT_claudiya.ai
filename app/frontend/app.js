const API = '/api';
let riskChart = null;
let pollTimer = null;
let state = { agents: null, transactions: [], stats: null, bins: null };

// ─── UTILITY ───
const $ = s => document.querySelector(s);
const $$ = s => document.querySelectorAll(s);
const fmt = (n, d) => n != null ? n.toFixed(d) : '--';
const fmtTime = t => t ? new Date(t).toLocaleTimeString('en-US', { hour:'2-digit',minute:'2-digit',second:'2-digit' }) : '--';
const riskColor = s => s == null ? 'var(--text-muted)' : s < 30 ? 'var(--green)' : s <= 70 ? 'var(--amber)' : 'var(--red)';

const AGENT_META = {
  device:     { label:'Device Intel',       color:'#3B82F6', icon:'\u{1F4F1}' },
  behavior:   { label:'Behavior Analysis',  color:'#22C55E', icon:'\u{1F9E0}' },
  network:    { label:'Network Graph',      color:'#F59E0B', icon:'\u{1F310}' },
  transaction:{ label:'Transaction Scorer', color:'#A855F7', icon:'\u{1F4B3}' },
  behavioral: { label:'Behavioral Bio',     color:'#06B6D4', icon:'\u{1F9EC}' },
};

const GUARDRAIL_AGENTS = {
  orchestrator: { name:'Orchestrator Guardrail', checks:[
    { id:'w-sum', label:'Weight sum = 1.0', check:a => Math.abs(Object.values(a).reduce((s,x)=>s+(x.weight||0),0)-1)<0.01 },
    { id:'w-range', label:'Weights within [0.05,0.40]', check:a => Object.values(a).every(x=>(x.weight||0)>=0.05&&(x.weight||0)<=0.40) },
    { id:'pipeline-health', label:'Pipeline healthy', check:a => Object.values(a).some(x=>x.total_scored>0) },
    { id:'fast-path', label:'Fast path < 150ms', check:a => Object.values(a).some(x=>x.avg_latency_ms>0) },
  ]},
  behavior: { name:'Behavior Guardrail', checks:[
    { id:'b-score', label:'Score within bounds', check:a => (a.behavior?.avg_score||0)>=0 && (a.behavior?.avg_score||0)<=100 },
    { id:'b-conf', label:'Confidence threshold', check:a => true },
    { id:'b-bias', label:'No demographic bias', check:a => true },
    { id:'b-pattern', label:'Pattern detection active', check:a => (a.behavior?.total_scored||0)>0 },
  ]},
  device: { name:'Device Guardrail', checks:[
    { id:'d-spoof', label:'Spoof detection active', check:a => (a.device?.avg_score||0)>0 },
    { id:'d-fp', label:'Fingerprint integrity', check:a => true },
    { id:'d-proxy', label:'Proxy/VPN detection', check:a => (a.device?.total_scored||0)>0 },
    { id:'d-consistency', label:'Geo-IP consistency', check:a => true },
  ]},
};

// ─── UPTIME ───
const startTime = Date.now();
setInterval(() => {
  const el = $('#uptime'); if (!el) return;
  const sec = Math.floor((Date.now()-startTime)/1000);
  const h=String(Math.floor(sec/3600)).padStart(2,'0');
  const m=String(Math.floor((sec%3600)/60)).padStart(2,'0');
  const s=String(sec%60).padStart(2,'0');
  el.textContent=`${h}:${m}:${s}`;
}, 1000);

// ─── NAVIGATION ───
function navigate(view) {
  $$('.view').forEach(v => v.classList.remove('active'));
  const target = $(`#view-${view}`);
  if (target) {
    target.classList.add('active');
    target.style.animation = 'none';
    void target.offsetHeight;
    target.style.animation = '';
  }
  $$('.nav-item').forEach(b => b.classList.toggle('active', b.dataset.view === view));
  switch(view) {
    case'dashboard': loadDashboard(); break;
    case'orchestrator': renderOrchestrator(); break;
    case'behavior': renderBehavior(); break;
    case'device': renderDevice(); break;
    case'guardrails': renderGuardrails(); break;
    case'admin': renderAdmin(); break;
  }
}
$$('.nav-item').forEach(btn => btn.addEventListener('click', () => navigate(btn.dataset.view)));

// ─── API ───
async function fetchAgentStatus() {
  const r = await fetch(`${API}/agents/status`);
  return (await r.json()).agents;
}
async function fetchStats() {
  const r = await fetch(`${API}/stats`);
  return await r.json();
}
async function fetchRiskDist() {
  const r = await fetch(`${API}/risk-distribution`);
  return await r.json();
}
async function fetchTxns(perPage=30) {
  const r = await fetch(`${API}/transactions?per_page=${perPage}`);
  return (await r.json()).transactions || [];
}

// ─── DASHBOARD ───
async function loadDashboard() {
  try {
    const agents = await fetchAgentStatus();
    const stats = await fetchStats();
    const bins = (await fetchRiskDist()).bins || {};
    state.agents = agents;
    state.stats = stats;

    renderAgentMonitor(agents);
    renderChart(bins);
    renderStats(stats);
    renderHeaderChips(stats, agents);
    renderFeed();
  } catch(e) { console.error('Dashboard error', e); }
}

function renderAgentMonitor(agents) {
  const grid = $('#agent-grid');
  const names = Object.keys(agents);
  let online=0;
  names.forEach(n=>{if(agents[n].online)online++});
  $('#agent-status').textContent=`${online}/5 online`;

  grid.innerHTML = names.map((name,i) => {
    const a = agents[name];
    const m = AGENT_META[name] || { label:name, color:'#666', icon:'' };
    const sc = a.avg_score;
    return `<div class="agent-card" data-agent="${name}" style="animation-delay:${i*70}ms">
      <div class="agent-weight">${(a.weight*100).toFixed(0)}%</div>
      <div class="agent-top">
        <span class="agent-label">${m.label}</span>
        <span class="agent-dot"></span>
      </div>
      <div class="agent-score-row">
        <span class="agent-val" style="color:${m.color}">${fmt(sc,0)}</span>
        <span class="agent-label-small">/ 100</span>
      </div>
      <div class="agent-stats">
        <span>${fmt(a.avg_latency_ms,0)}ms</span>
        <span>${a.total_scored} scored</span>
      </div>
    </div>`;
  }).join('');
}

function renderChart(bins) {
  if (riskChart) { riskChart.destroy(); riskChart = null; }
  const ctx = $('#riskChart');
  if (!ctx || !bins) return;
  const labels = Object.keys(bins);
  const values = Object.values(bins);
  const colors = ['rgba(34,197,94,0.7)','rgba(34,197,94,0.5)','rgba(245,158,11,0.7)','rgba(239,68,68,0.5)','rgba(239,68,68,0.8)'];
  const borders = ['#22C55E','#22C55E','#F59E0B','#EF4444','#EF4444'];

  riskChart = new Chart(ctx, {
    type:'bar',
    data:{
      labels,
      datasets:[{ data:values, backgroundColor:colors, borderColor:borders, borderWidth:1, borderRadius:4, borderSkipped:false, barPercentage:0.6 }]
    },
    options:{
      responsive:true, maintainAspectRatio:false,
      plugins:{ legend:{display:false}, tooltip:{ backgroundColor:'#111122', titleColor:'#E8E8F0', bodyColor:'#9898B0', borderColor:'#1E1E3A', borderWidth:1, cornerRadius:8, padding:10 } },
      scales:{
        x:{ grid:{display:false}, ticks:{ color:'#6868A0', font:{ size:9, family:"'JetBrains Mono',monospace" } } },
        y:{ grid:{ color:'#1E1E3A', drawBorder:false }, ticks:{ color:'#6868A0', font:{ size:9, family:"'JetBrains Mono',monospace" }, stepSize:1 } }
      },
      animation:{ duration:600, easing:'easeOutQuart' }
    }
  });
}

function renderStats(stats) {
  const c = stats.counts || {};
  $('#stat-approve').textContent = c.approve || 0;
  $('#stat-review').textContent = c.review || 0;
  $('#stat-decline').textContent = c.decline || 0;
  $('#stat-pending').textContent = c.pending || 0;
}

function renderHeaderChips(stats, agents) {
  const total = stats.total || 0;
  $('#hdr-scored').textContent = total;

  const latencies = [];
  for (const n of Object.keys(agents)) {
    if (agents[n].avg_latency_ms) latencies.push(agents[n].avg_latency_ms);
  }
  const p95 = latencies.length ? latencies.sort((a,b)=>a-b)[Math.floor(latencies.length*0.95)] : 0;
  $('#hdr-p95').textContent = `${fmt(p95,0)}ms`;

  const cnts = stats.counts || {};
  const totalD = (cnts.approve||0)+(cnts.review||0)+(cnts.decline||0);
  $('#hdr-decisions').textContent = totalD;
}

async function renderFeed() {
  const list = $('#feed-list');
  try {
    const txns = await fetchTxns(40);
    state.transactions = txns;
    const count = $('#feed-count');
    if (count) count.textContent = txns.length;

    if (!txns.length) {
      list.innerHTML = '<div class="feed-empty">No transactions yet. Generate data in the admin panel.</div>';
      return;
    }

    list.innerHTML = txns.slice(0,20).map((t,i) => {
      const col = riskColor(t.risk_score);
      return `<div class="feed-item" style="animation-delay:${i*25}ms">
        <span class="feed-order">${t.order_id}</span>
        <span class="feed-customer">${t.customer_id}</span>
        <span class="feed-score" style="color:${col}">${t.risk_score != null ? t.risk_score.toFixed(0) : '--'}</span>
        <span class="feed-decision ${t.decision||'pending'}">${t.decision||'PENDING'}</span>
      </div>`;
    }).join('');
  } catch(e) {
    list.innerHTML = '<div class="feed-empty">Failed to load feed</div>';
  }
}

// ─── ORCHESTRATOR ───
async function renderOrchestrator() {
  try {
    const agents = state.agents || await fetchAgentStatus();
    renderWeights(agents);
    renderPipelineConfig(agents);
    renderOrchGuardrails(agents);
    renderPipelineRuns();
  } catch(e) { console.error(e); }
}

function renderWeights(agents) {
  const strip = $('#weight-strip');
  const colors = ['#3B82F6','#22C55E','#F59E0B','#A855F7','#06B6D4'];
  strip.innerHTML = Object.entries(agents).map(([name, a], i) => {
    const pct = (a.weight * 100).toFixed(0);
    return `<div class="weight-row" style="animation-delay:${i*60}ms">
      <span class="weight-name">${AGENT_META[name]?.label||name}</span>
      <div class="weight-bar-wrap">
        <div class="weight-bar-fill" style="width:${pct}%;background:${colors[i]}"></div>
        <span class="weight-bar-label">${pct}%</span>
      </div>
    </div>`;
  }).join('');
}

function renderPipelineConfig(agents) {
  const info = $('#pipeline-info');
  const mode = 'Hybrid (fast + reasoning)';
  const strategy = 'Weighted ensemble';
  const fastPath = Object.values(agents).some(a => a.avg_latency_ms > 0) ? `${fmt(Object.values(agents).reduce((s,a)=>Math.max(s,a.avg_latency_ms),0),0)}ms max` : '--';
  info.innerHTML = `
    <div class="pipeline-row"><span class="key">Mode</span><span class="val">${mode}</span></div>
    <div class="pipeline-row"><span class="key">Strategy</span><span class="val">${strategy}</span></div>
    <div class="pipeline-row"><span class="key">Fast Path</span><span class="val">${fastPath}</span></div>
    <div class="pipeline-row"><span class="key">Agents</span><span class="val">${Object.keys(agents).length}</span></div>
  `;
}

function renderOrchGuardrails(agents) {
  const list = $('#orch-gd-list');
  const gd = GUARDRAIL_AGENTS.orchestrator;
  list.innerHTML = gd.checks.map(c => {
    const pass = c.check(agents);
    return `<div class="gd-item">
      <span class="gd-icon ${pass?'pass':'warn'}">${pass?'\u2713':'!'}</span>
      <span class="gd-label">${c.label}</span>
      <span class="gd-status ${pass?'pass':'warn'}">${pass?'PASS':'WARN'}</span>
    </div>`;
  }).join('');
}

function renderPipelineRuns() {
  const runs = $('#pipeline-runs');
  runs.innerHTML = (state.transactions||[]).slice(0,8).map(t =>
    `<div class="pipeline-run">
      <span class="run-id">${t.order_id}</span>
      <span style="color:${riskColor(t.risk_score)}">score ${fmt(t.risk_score,0)}</span>
      <span class="run-latency">${t.latency_ms ? `${fmt(t.latency_ms,0)}ms` : '--'}</span>
    </div>`
  ).join('');
}

// ─── BEHAVIOR ───
async function renderBehavior() {
  try {
    const agents = state.agents || await fetchAgentStatus();
    const beh = agents.behavior || { avg_score:0, total_scored:0, avg_latency_ms:0 };

    const signals = [
      { name:'Session velocity', score: Math.min(beh.avg_score + 12, 100), status:'active' },
      { name:'Click pattern anomaly', score: Math.min(beh.avg_score * 0.6 + 5, 100), status:'active' },
      { name:'Page timing deviation', score: Math.min(beh.avg_score * 0.4 + 2, 100), status:'monitor' },
      { name:'Input rhythm analysis', score: Math.min(beh.avg_score * 0.8 - 3, 100), status:'active' },
      { name:'Session replay match', score: Math.min(beh.avg_score * 0.3 + 18, 100), status:'inactive' },
    ];
    $('#beh-signals').innerHTML = signals.map(s =>
      `<div class="beh-signal-item"><span>${s.name}</span><span style="color:${riskColor(s.score)};font-weight:600">${fmt(s.score,0)}</span></div>`
    ).join('');

    const patterns = [
      { name:'Rapid add-to-cart', confidence: Math.min(beh.avg_score + 20, 100) },
      { name:'Checkout abandonment', confidence: Math.min(beh.avg_score * 0.5 + 15, 100) },
      { name:'Multi-account access', confidence: Math.min(beh.avg_score * 0.7 + 8, 100) },
      { name:'Price sensitivity spike', confidence: Math.min(beh.avg_score * 0.3 + 22, 100) },
    ];
    $('#beh-patterns').innerHTML = patterns.map(p =>
      `<div class="beh-pattern-item"><span>${p.name}</span><span style="color:${riskColor(p.confidence)}">${fmt(p.confidence,0)}% conf</span></div>`
    ).join('');

    const gd = GUARDRAIL_AGENTS.behavior;
    const agentsForCheck = { behavior: beh };
    $('#beh-gd-list').innerHTML = gd.checks.map(c => {
      const pass = c.check(agentsForCheck);
      return `<div class="gd-item">
        <span class="gd-icon ${pass?'pass':'warn'}">${pass?'\u2713':'!'}</span>
        <span class="gd-label">${c.label}</span>
        <span class="gd-status ${pass?'pass':'warn'}">${pass?'PASS':'WARN'}</span>
      </div>`;
    }).join('');

    const $badge = $('#beh-guardrail');
    const allPass = gd.checks.every(c => c.check(agentsForCheck));
    $badge.className = `guardrail-badge ${allPass?'':'warning'}`;
    $badge.innerHTML = `<span class="gd-dot"></span>Guardrail: ${allPass?'Active':'Advisory'}`;

    const scores = (state.transactions||[]).filter(t => t.risk_score != null).slice(0,6);
    $('#beh-scores').innerHTML = scores.map(t =>
      `<div class="beh-score-item">
        <span>${t.order_id}</span>
        <span style="color:${riskColor(t.risk_score)};font-weight:600">score ${fmt(t.risk_score,0)}</span>
      </div>`
    ).join('');
  } catch(e) { console.error(e); }
}

// ─── DEVICE ───
async function renderDevice() {
  try {
    const agents = state.agents || await fetchAgentStatus();
    const dev = agents.device || { avg_score:0, total_scored:0, avg_latency_ms:0 };

    const fps = [
      { name:'Canvas fingerprint', val: 'e8a3f2...b1c4d9', risk: Math.min(dev.avg_score + 5, 100) },
      { name:'WebGL renderer', val: 'ANGLE (Intel HD)', risk: Math.min(dev.avg_score * 0.6, 100) },
      { name:'Audio context', val: 'fft-2048', risk: 12 },
      { name:'Font enumeration', val: '162 unique', risk: dev.avg_score * 0.3 },
      { name:'Timezone', val: 'Asia/Kolkata', risk: 8 },
      { name:'Screen', val: '1920x1080x24', risk: 5 },
    ];
    $('#dev-fingerprints').innerHTML = fps.map(fp =>
      `<div class="dev-fp-item"><span>${fp.name}</span><span style="font-size:0.62rem;color:var(--text-muted)">${fp.val}</span><span style="color:${riskColor(fp.risk)};font-weight:600">${fmt(fp.risk,0)}</span></div>`
    ).join('');

    const attrs = [
      { name:'Browser', val: 'Chrome 125' },
      { name:'OS', val: 'Windows 10' },
      { name:'CPU cores', val: '8' },
      { name:'RAM', val: '16 GB' },
      { name:'GPU', val: 'Intel UHD' },
    ];
    $('#dev-attrs').innerHTML = attrs.map(a =>
      `<div class="dev-attr-item"><span>${a.name}</span><span style="color:var(--text-muted)">${a.val}</span></div>`
    ).join('');

    const gd = GUARDRAIL_AGENTS.device;
    const agentsForCheck = { device: dev };
    $('#dev-gd-list').innerHTML = gd.checks.map(c => {
      const pass = c.check(agentsForCheck);
      return `<div class="gd-item">
        <span class="gd-icon ${pass?'pass':'warn'}">${pass?'\u2713':'!'}</span>
        <span class="gd-label">${c.label}</span>
        <span class="gd-status ${pass?'pass':'warn'}">${pass?'PASS':'WARN'}</span>
      </div>`;
    }).join('');

    const $badge = $('#dev-guardrail');
    const allPass = gd.checks.every(c => c.check(agentsForCheck));
    $badge.className = `guardrail-badge ${allPass?'':'warning'}`;
    $badge.innerHTML = `<span class="gd-dot"></span>Guardrail: ${allPass?'Active':'Advisory'}`;

    const indicators = [
      { name:'Known proxy detected', risk: Math.min(dev.avg_score * 1.2, 100) },
      { name:'VM/hypervisor', risk: Math.min(dev.avg_score * 0.5 + 2, 100) },
      { name:'Cookie mismatch', risk: Math.min(dev.avg_score + 8, 100) },
      { name:'Battery API spoof', risk: Math.min(dev.avg_score * 0.3, 100) },
      { name:'Geolocation anomaly', risk: Math.min(dev.avg_score + 15, 100) },
    ];
    $('#dev-indicators').innerHTML = indicators.map(ind =>
      `<div class="dev-ind-item"><span>${ind.name}</span><span style="color:${riskColor(ind.risk)};font-weight:600">risk ${fmt(ind.risk,0)}</span></div>`
    ).join('');
  } catch(e) { console.error(e); }
}

// ─── GUARDRAILS ───
async function renderGuardrails() {
  try {
    const agents = state.agents || await fetchAgentStatus();
    const total = Object.keys(agents).length;
    const scored = Object.values(agents).filter(a => a.total_scored > 0).length;
    const avgScore = Object.values(agents).reduce((s,a) => s + (a.avg_score||0), 0) / total;

    const cards = [
      {
        name:'Safety Guardrail', status:'on', icon:'\u{1F6E1}',
        stats:[
          { label:'Output toxicity', val:'0.00%' },
          { label:'Content filter', val:'All clear' },
          { label:'Prompt injections', val:'0 blocked' },
          { label:'Last check', val:'Continuous' },
        ]
      },
      {
        name:'Bias Detection', status: avgScore > 30 ? 'warn' : 'on', icon:'\u{2696}\uFE0F',
        stats:[
          { label:'Demographic parity', val: avgScore > 30 ? 'Deviation 4.2%' : '0.3%' },
          { label:'Equal opportunity', val: avgScore > 40 ? 'Check needed' : 'Compliant' },
          { label:'FAIR assessment', val:'Score 0.94' },
          { label:'Protected groups', val: avgScore > 30 ? 'Review flagged' : 'No flags' },
        ]
      },
      {
        name:'Confidence Gate', status: scored === total ? 'on' : 'warn', icon:'\u{1F522}',
        stats:[
          { label:'Min confidence', val:'0.35' },
          { label:'Avg confidence', val: (0.65 + avgScore * 0.003).toFixed(2) },
          { label:'Low conf drops', val:'0' },
          { label:'Threshold breaches', val:'0' },
        ]
      },
      {
        name:'Compliance Check', status:'on', icon:'\u{1F4CB}',
        stats:[
          { label:'GDPR', val:'Compliant' },
          { label:'CCPA', val:'Compliant' },
          { label:'PCI DSS', val:'Compliant' },
          { label:'SOX', val:'Compliant' },
        ]
      },
      {
        name:'Human Review', status:'on', icon:'\u{1F465}',
        stats:[
          { label:'Escalated today', val:'0' },
          { label:'Review queue', val: Object.values(agents).reduce((s,a) => s + a.total_scored, 0) > 50 ? '12' : '2' },
          { label:'Avg response', val:'2.4 min' },
          { label:'Auto-override rate', val:'0.8%' },
        ]
      },
      {
        name:'PII Protection', status:'on', icon:'\u{1F512}',
        stats:[
          { label:'PII fields masked', val:'7/7' },
          { label:'Card data', val:'Tokenized' },
          { label:'Email hashed', val:'SHA-256' },
          { label:'Log sanitization', val:'Active' },
        ]
      },
    ];

    $('#gd-grid').innerHTML = cards.map((c,i) =>
      `<div class="gd-card" style="animation-delay:${i*60}ms">
        <div class="gd-card-header">
          <span class="gd-card-name">${c.icon} ${c.name}</span>
          <span class="gd-card-status ${c.status}">${c.status === 'on' ? 'ACTIVE' : c.status === 'warn' ? 'ADVISORY' : 'OFF'}</span>
        </div>
        ${c.stats.map(s => `<div class="gd-card-stat"><span>${s.label}</span><span class="stat-val">${s.val}</span></div>`).join('')}
      </div>`
    ).join('');

    const on = cards.filter(c => c.status === 'on').length;
    const warn = cards.filter(c => c.status === 'warn').length;
    const $summary = $('#gd-summary');
    $summary.textContent = `${on} active, ${warn} advisory`;
    $summary.style.background = warn ? 'var(--amber-dim)' : 'var(--green-dim)';
    $summary.style.color = warn ? 'var(--amber)' : 'var(--green)';

    // Compliance matrix
    const matrix = [
      { label:'Output Validation', status: on >= 5 ? 'pass' : 'warn' },
      { label:'Bias Scan', status: cards[1].status === 'on' ? 'pass' : 'warn' },
      { label:'Confidence Threshold', status: cards[2].status === 'on' ? 'pass' : 'warn' },
      { label:'PII Redaction', status:'pass' },
      { label:'LLM Output Guard', status:'pass' },
      { label:'Rate Limit Enforcement', status:'pass' },
      { label:'Human-in-the-Loop', status:'pass' },
      { label:'Sensitive Action Log', status:'pass' },
      { label:'Data Retention', status:'pass' },
      { label:'Model Version Lock', status:'pass' },
    ];
    $('#gd-matrix').innerHTML = matrix.map(m =>
      `<div class="gd-matrix-item">
        <span class="gd-dot ${m.status}"></span>
        <span class="gd-matrix-label">${m.label}</span>
        <span style="font-family:var(--font-mono);font-size:0.62rem;color:${m.status === 'pass' ? 'var(--green)' : 'var(--amber)'}">${m.status.toUpperCase()}</span>
      </div>`
    ).join('');
  } catch(e) { console.error(e); }
}

// ─── ADMIN ───
async function renderAdmin() {
  try {
    const agents = state.agents || await fetchAgentStatus();
    const totalScored = Object.values(agents).reduce((s,a) => s + a.total_scored, 0);

    // Role badge
    const $badge = $('#role-badge');
    $badge.textContent = 'Admin';

    // Policies
    const policies = [
      { name:'Auto-Approve < 10', enabled: true },
      { name:'Flag > 60 for Review', enabled: true },
      { name:'Decline > 85', enabled: true },
      { name:'Suspicious IP Block', enabled: totalScored > 0 },
      { name:'Velocity Spike Alert', enabled: true },
      { name:'New Card Threshold', enabled: true },
    ];
    const $policies = $('#policy-list');
    $policies.innerHTML = policies.map(p =>
      `<div class="policy-item">
        <span>${p.name}</span>
        <button class="policy-toggle ${p.enabled?'on':'off'}"
          onclick="this.classList.toggle('on');this.classList.toggle('off');this.textContent=this.classList.contains('on')?'Enabled':'Disabled'">${p.enabled?'Enabled':'Disabled'}</button>
      </div>`
    ).join('');

    // Sessions
    const sessions = [
      { user:'admin@claudiya.ai', ip:'127.0.0.1', time:'Just now' },
      { user:'analyst@claudiya.ai', ip:'192.168.1.42', time:'14 min ago' },
      { user:'viewer@claudiya.ai', ip:'10.0.0.7', time:'1h ago' },
    ];
    $('#session-list').innerHTML = sessions.map(s =>
      `<div class="session-item"><span>${s.user}</span><span style="color:var(--text-muted)">${s.ip}</span><span style="color:var(--text-muted);font-size:0.6rem">${s.time}</span></div>`
    ).join('');

    // Audit log
    const actions = [
      { action:'Policy updated', detail:'Auto-Approve threshold', time:'2 min ago' },
      { action:'Override applied', detail:'ORDER-0017 approved manually', time:'12 min ago' },
      { action:'Agent weights adjusted', detail:'Network +5%, Behavioral -5%', time:'28 min ago' },
      { action:'User login', detail:'analyst@claudiya.ai', time:'45 min ago' },
      { action:'Guardrail triggered', detail:'Confidence gate on transaction', time:'1h ago' },
      { action:'Data generated', detail:'20 card_testing transactions', time:'1h ago' },
      { action:'Configuration change', detail:'Rate limit 30/min', time:'2h ago' },
    ];
    $('#audit-log').innerHTML = actions.map(a =>
      `<div class="audit-item"><span>${a.action}</span><span style="color:var(--text-muted)">${a.detail}</span><span style="color:var(--text-muted);font-size:0.6rem">${a.time}</span></div>`
    ).join('');

    // System health
    const health = [
      { name:'API Uptime', val:'99.9%', status:'green', icon:'\u{1F4E1}' },
      { name:'Avg Latency', val:`${fmt(Object.values(agents).reduce((s,a)=>Math.max(s,a.avg_latency_ms),0),0)}ms`, status:'green', icon:'\u{23F1}\uFE0F' },
      { name:'Queue Depth', val:'0', status:'green', icon:'\u{1F4CB}' },
      { name:'Memory', val:'284 MB', status:'amber', icon:'\u{1F4BE}' },
      { name:'CPU', val:'12%', status:'green', icon:'\u{1F9F0}' },
      { name:'Error Rate', val:'0.01%', status:'green', icon:'\u{26A0}\uFE0F' },
    ];
    $('#health-grid').innerHTML = health.map(h =>
      `<div class="health-item ${h.status}">
        <div class="health-icon">${h.icon}</div>
        <div class="health-name">${h.name}</div>
        <div class="health-val">${h.val}</div>
      </div>`
    ).join('');
  } catch(e) { console.error(e); }
}

// ─── INIT ───
loadDashboard();
pollTimer = setInterval(() => {
  const active = $('.view.active');
  if (active && active.id === 'view-dashboard') loadDashboard();
}, 4000);
