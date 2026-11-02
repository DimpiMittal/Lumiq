/* ════════════════════════════════════════════════
   DataWise AI v5 — Core App
   ════════════════════════════════════════════════ */

const API = "/api";

/* ── State ── */
const S = {
  schema:    {},
  dbType:    null,
  dbLabel:   "",
  history:   JSON.parse(localStorage.getItem("dw_h") || "[]"),
  queries:   0,
  selDB:     "demo",
};
const ChartStore = {};  // stores {rows,cols,type} per chart id
const Charts     = {};  // Chart.js instances

/* ── DOM utils ── */
const $  = (s, c=document) => c.querySelector(s);
const $$ = (s, c=document) => [...c.querySelectorAll(s)];
const el = (tag, cls, html) => { const e = document.createElement(tag); if(cls) e.className=cls; if(html!==undefined) e.innerHTML=html; return e; };
const esc = s => String(s).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");

/* ════════════════════════════════════════════════
   THEME
   ════════════════════════════════════════════════ */
function initTheme() {
  const t = localStorage.getItem("dw_theme") || "dark";
  applyTheme(t, false);
}
function applyTheme(t, save=true) {
  document.documentElement.setAttribute("data-theme", t);
  const btn = $("#theme-btn");
  if (btn) btn.textContent = t === "dark" ? "☀️" : "🌙";
  if (save) localStorage.setItem("dw_theme", t);
}
window.toggleTheme = () => {
  const cur = document.documentElement.getAttribute("data-theme") || "dark";
  applyTheme(cur === "dark" ? "light" : "dark");
};

/* ════════════════════════════════════════════════
   TOAST
   ════════════════════════════════════════════════ */
window.toast = (msg, type="info", ms=4500) => {
  const icons = {ok:"✅",err:"❌",warn:"⚠️",info:"ℹ️"};
  const tray = $("#toast-tray");
  if (!tray) return;
  const d = el("div", `toast ${type}`, `<span>${icons[type]||"💬"}</span><span>${esc(msg)}</span>`);
  tray.appendChild(d);
  setTimeout(() => d.remove(), ms);
};

/* ════════════════════════════════════════════════
   PAGE ROUTER — loads HTML files into #page-area
   ════════════════════════════════════════════════ */
const PAGE_TITLES = {
  query:    "Ask AI Analyst",
  dashboard:"Dashboard",
  sql:      "SQL Editor",
  connect:  "Connect Database",
  upload:   "Upload CSV",
  history:  "Query History",
  settings: "Settings",
};

let currentPage = null;

async function navigate(page) {
  if (currentPage === page) return;
  currentPage = page;

  // Update nav active state
  $$(".nav-link").forEach(b => b.classList.remove("on"));
  $(`#nav-${page}`)?.classList.add("on");

  // Update topbar title
  const h = $("#pg-heading");
  if (h) h.textContent = PAGE_TITLES[page] || page;

  // Close sidebar on mobile
  $(".sidebar")?.classList.remove("open");

  // Load page HTML
  const area = $("#page-area");
  area.innerHTML = `<div style="display:flex;align-items:center;justify-content:center;height:200px;color:var(--t3);font-size:13px">Loading…</div>`;
  try {
    const resp = await fetch(`/pages/${page}.html`);
    area.innerHTML = await resp.text();
  } catch {
    area.innerHTML = `<div class="empty"><span class="empty-ico">😕</span><h3>Page not found</h3></div>`;
    return;
  }

  // Run page init
  const inits = {
    query:    initQueryPage,
    dashboard:initDashPage,
    sql:      initSqlPage,
    connect:  initConnectPage,
    upload:   initUploadPage,
    history:  initHistoryPage,
    settings: initSettingsPage,
  };
  if (inits[page]) inits[page]();

  // Update history badge
  const hb = $("#hist-badge");
  if (hb) hb.textContent = S.history.length;
}

window.navigate = navigate;
window.toggleSidebar = () => $(".sidebar")?.classList.toggle("open");

/* ════════════════════════════════════════════════
   DB STATUS
   ════════════════════════════════════════════════ */
function setDBStatus(connected, label, sub) {
  const dot   = $(".db-dot");
  const name  = $(".db-pill-label");
  const subEl = $(".db-pill-sub");
  if (dot)   dot.className   = "db-dot" + (connected ? " on" : "");
  if (name)  name.textContent = connected ? "Connected" : "Not Connected";
  if (subEl) subEl.textContent = sub || (connected ? label : "Connect a database to begin");
}

/* ════════════════════════════════════════════════
   SCHEMA PANEL
   ════════════════════════════════════════════════ */
function renderSchema(filter="") {
  const list = $("#schema-list");
  if (!list) return;
  const entries = Object.entries(S.schema).filter(([t]) => t.toLowerCase().includes(filter.toLowerCase()));
  if (!entries.length) {
    list.innerHTML = S.schema && Object.keys(S.schema).length
      ? `<div class="tsm tmuted" style="padding:8px">No matches</div>`
      : `<div class="empty" style="padding:22px 8px"><span class="empty-ico" style="font-size:26px">🔗</span><p style="font-size:12px">Connect a database</p></div>`;
    return;
  }
  list.innerHTML = entries.map(([t,i],index) => `
    <div class="sch-tbl">
      <div class="sch-tbl-hd" onclick="toggleSchemaTable(${index})">
        <span>📋</span><span>${esc(t)}</span>
        <span class="rc">${i.row_count.toLocaleString()}</span>
      </div>
      <div class="sch-cols" id="sc-${index}">
        ${i.columns.map(c=>`<div class="sch-col"><span class="sch-col-n">${esc(c.name)}</span><span class="sch-col-t">${esc(c.type)}</span></div>`).join("")}
      </div>
    </div>`).join("");
}
window.toggleSchemaTable = id => document.getElementById(`sc-${id}`)?.classList.toggle("open");
window.filterSchema = v => renderSchema(v);
window.renderSchema = renderSchema;

/* ════════════════════════════════════════════════
   CHARTS
   ════════════════════════════════════════════════ */
const PALETTE = [
  "rgba(57,255,133,.80)","rgba(56,189,248,.80)","rgba(167,139,250,.80)",
  "rgba(45,212,191,.80)","rgba(251,191,36,.80)","rgba(251,113,133,.80)",
  "rgba(99,102,241,.80)","rgba(249,115,22,.80)","rgba(34,211,238,.80)",
];

function renderChart(id, rows, cols, type="bar") {
  const canvas = document.getElementById(id);
  if (!canvas || !rows?.length || !cols?.length) return;

  const key = id === "ov-canvas" ? "__ov" : id;
  if (Charts[key]) { Charts[key].destroy(); delete Charts[key]; }

  // Save for fullscreen & tab switching
  if (id !== "ov-canvas") ChartStore[id] = { rows, cols, type };

  // Explicitly set canvas pixel size BEFORE creating Chart.js instance
  const wrap = canvas.parentElement;
  const W = wrap?.clientWidth  || 480;
  const H = wrap?.clientHeight || 185;
  canvas.width  = W;
  canvas.height = H;
  canvas.style.width  = W + "px";
  canvas.style.height = H + "px";

  const labels = rows.map(r => String(r[cols[0]]));
  const values = rows.map(r => parseFloat(r[cols[1]]) || 0);
  const flat   = ["pie","doughnut"].includes(type);

  const isDark = document.documentElement.getAttribute("data-theme") !== "light";
  const gridC  = isDark ? "rgba(255,255,255,0.05)" : "rgba(0,0,0,0.06)";
  const tickC  = isDark ? "#3d5069" : "#7e94b0";

  Charts[key] = new Chart(canvas.getContext("2d"), {
    type,
    data: {
      labels,
      datasets: [{
        label: cols[1] || "Value",
        data: values,
        backgroundColor: flat ? PALETTE : (type==="line" ? "rgba(57,255,133,0.12)" : PALETTE),
        borderColor:     flat ? PALETTE : (type==="line" ? "rgba(57,255,133,1)"    : PALETTE),
        borderWidth: 2, tension: 0.4, fill: type==="line",
        pointBackgroundColor: "rgba(57,255,133,1)",
        pointRadius: type==="line" ? 4 : 0,
        borderRadius: type==="bar" ? 6 : 0,
      }],
    },
    options: {
      responsive: false,           // ← NEVER auto-resize
      maintainAspectRatio: false,
      animation: { duration: 400 },
      plugins: {
        legend: { labels: { color: tickC, font: { family:"'DM Sans'", size: 11 } } },
      },
      scales: flat ? {} : {
        x: { ticks: { color: tickC, font: { family:"'DM Sans'", size: 10 }, maxRotation: 30 }, grid: { color: gridC } },
        y: { ticks: { color: tickC, font: { family:"'DM Sans'", size: 10 } }, grid: { color: gridC } },
      },
    },
  });
}
window.renderChart = renderChart;

window.switchChartTab = (id, type, btn) => {
  btn.closest(".chart-bar")?.querySelectorAll(".ct-btn").forEach(b => b.classList.remove("on"));
  btn.classList.add("on");
  const d = ChartStore[id];
  if (!d) return;
  d.type = type;
  renderChart(id, d.rows, d.cols, type);
};

/* Overlay */
window.openChartOverlay = (cid) => {
  const d = ChartStore[cid];
  if (!d) return;
  const ov = $("#chart-overlay");
  ov._cid = cid;
  $("#ov-title").textContent = `📊 ${d.cols?.[1] || "Chart"}`;
  const tabs = $("#ov-tabs");
  tabs.innerHTML = ["bar","line","pie","doughnut"].map(t =>
    `<button class="ct-btn${d.type===t?" on":""}" onclick="switchOvTab('${t}',this)">${t[0].toUpperCase()+t.slice(1)}</button>`
  ).join("");
  ov.classList.add("open");
  document.body.style.overflow = "hidden";
  requestAnimationFrame(() => setTimeout(() => renderChart("ov-canvas", d.rows, d.cols, d.type||"bar"), 60));
};
window.switchOvTab = (type, btn) => {
  btn.closest(".flex")?.querySelectorAll(".ct-btn").forEach(b => b.classList.remove("on"));
  btn.classList.add("on");
  const d = ChartStore[$("#chart-overlay")._cid];
  if (d) renderChart("ov-canvas", d.rows, d.cols, type);
};
window.closeChartOverlay = e => { if (!e || e.target === $("#chart-overlay")) _closeOv(); };
window.closeChartOverlayDirect = _closeOv;
function _closeOv() {
  $("#chart-overlay")?.classList.remove("open");
  document.body.style.overflow = "";
  if (Charts.__ov) { Charts.__ov.destroy(); delete Charts.__ov; }
}
document.addEventListener("keydown", e => { if (e.key==="Escape") _closeOv(); });

/* ════════════════════════════════════════════════
   BUILD TABLE
   ════════════════════════════════════════════════ */
function buildTable(rows, cols) {
  if (!rows?.length) return "";
  const isNum = v => typeof v==="number" || (typeof v==="string" && v!=="" && !isNaN(+v));
  return `<div class="tbl-wrap"><table class="dtbl">
    <thead><tr>${cols.map(c=>`<th>${esc(c)}</th>`).join("")}</tr></thead>
    <tbody>${rows.map(r=>`<tr>${cols.map(c=>`<td class="${isNum(r[c])?"num":""}">${esc(r[c]??'—')}</td>`).join("")}</tr>`).join("")}</tbody>
  </table></div>`;
}
window.buildTable = buildTable;

/* ════════════════════════════════════════════════
   QUERY PAGE
   ════════════════════════════════════════════════ */
function initQueryPage() {
  renderSchema();
  loadSuggestions();

  // Expose globals for inline handlers in query.html
  window.handleKey = e => { if (e.key==="Enter" && !e.shiftKey) { e.preventDefault(); askQuery(); } };
  window.addChip   = txt => { const i = $("#q-inp"); i.value = (i.value ? i.value+" " : "") + txt; i.focus(); };
  window.fillQuery = el  => { $("#q-inp").value = el.textContent.trim(); askQuery(); };
}

async function loadSuggestions() {
  try {
    const r = await fetch(`${API}/suggest`, {credentials:"include"});
    const d = await r.json();
    const w = $("#sugg-list");
    if (w && d.suggestions?.length) {
      w.innerHTML = d.suggestions.map(s=>
        `<span class="sugg-pill" onclick="fillQuery(this)">${esc(s)}</span>`
      ).join("");
    }
  } catch {}
}

async function askQuery() {
  const inp = $("#q-inp");
  const q   = inp?.value.trim();
  if (!q) { toast("Type a question first","warn"); return; }

  const btn = $("#ask-btn");
  if (btn) { btn.disabled=true; btn.textContent="Analyzing…"; }
  $("#chat-empty")?.classList.add("hidden");

  // User bubble
  const feed = $("#chat-feed");
  appendBubble(feed, `<div class="msg msg-u">${esc(q)}</div>`);
  inp.value = "";
  feed.scrollTop = feed.scrollHeight;

  // Loader
  const loader = el("div","msg msg-loading",
    `<div class="ai-avatar">D</div>
     <div><div class="txs tmuted fw7 mb1">DataWise AI</div>
     <div class="dots"><span></span><span></span><span></span></div></div>`);
  feed.appendChild(loader);
  feed.scrollTop = feed.scrollHeight;

  try {
    const resp = await fetch(`${API}/query`, {
      method:"POST", credentials:"include",
      headers:{"Content-Type":"application/json"},
      body: JSON.stringify({question:q})
    });
    const data = await resp.json();
    loader.remove();

    if (data.ok) {
      renderAIResult(feed, data, q);
      S.queries++;
      document.getElementById("d-queries") && (document.getElementById("d-queries").textContent = S.queries);
      S.history.unshift({q, sql:data.sql, rows:data.row_count, time:new Date().toLocaleTimeString()});
      if (S.history.length > 100) S.history.pop();
      localStorage.setItem("dw_h", JSON.stringify(S.history));
      const hb = $("#hist-badge");
      if (hb) hb.textContent = S.history.length;
    } else {
      appendBubble(feed, `<div class="msg msg-a"><div style="color:var(--rose)">❌ ${esc(data.error||"Query failed")}</div></div>`);
    }
  } catch {
    loader.remove();
    appendBubble(feed, `<div class="msg msg-a"><div style="color:var(--rose)">❌ Cannot reach server. Is app.py running?</div></div>`);
  }

  if (btn) { btn.disabled=false; btn.textContent="Ask AI ✨"; }
  feed.scrollTop = feed.scrollHeight;
}
window.askQuery = askQuery;

function appendBubble(feed, html) {
  const d = el("div","msg");
  d.innerHTML = html;
  feed.appendChild(d);
}

function renderAIResult(feed, data, q) {
  const showSQL   = !$("#tog-sql")   || $("#tog-sql").classList.contains("on");
  const showChart = !$("#tog-chart") || $("#tog-chart").classList.contains("on");
  const cid = "c" + Date.now();

  const sqlHtml = showSQL ? `
    <div class="sql-blk">
      <div class="sql-blk-hd">
        <span class="sql-lang">SQL</span>
        <button class="btn btn-outline btn-sm" onclick="copySql(this,'${btoa(unescape(encodeURIComponent(data.sql)))}')">Copy</button>
      </div>
      <pre class="sql-code">${esc(data.sql)}</pre>
    </div>` : "";

  const insightHtml = data.insight
    ? `<div class="insight">${esc(data.insight).replace(/\n/g,"<br>")}</div>` : "";

  const chartHtml = (showChart && data.rows?.length >= 2) ? `
    <div class="chart-box">
      <div class="chart-bar" id="cb-${cid}">
        <button class="ct-btn on"  onclick="switchChartTab('${cid}','bar',this)">Bar</button>
        <button class="ct-btn"     onclick="switchChartTab('${cid}','line',this)">Line</button>
        <button class="ct-btn"     onclick="switchChartTab('${cid}','pie',this)">Pie</button>
        <button class="ct-btn"     onclick="switchChartTab('${cid}','doughnut',this)">Donut</button>
        <button class="ct-expand"  onclick="openChartOverlay('${cid}')">⛶ Fullscreen</button>
      </div>
      <div class="ct-wrap" id="cw-${cid}">
        <canvas id="${cid}"></canvas>
      </div>
    </div>` : "";

  const tableHtml = data.rows?.length ? buildTable(data.rows.slice(0,25), data.columns) : "";

  const wrap = el("div","msg");
  wrap.innerHTML = `
    <div class="msg msg-a">
      <div class="msg-a-hd">
        <div class="ai-avatar">D</div>
        <span>DataWise AI</span>
        <span class="row-pill">📊 ${data.row_count} rows</span>
      </div>
      ${sqlHtml}${insightHtml}${chartHtml}${tableHtml}
    </div>`;
  feed.appendChild(wrap);

  if (showChart && data.rows?.length >= 2) {
    requestAnimationFrame(() => {
      setTimeout(() => renderChart(cid, data.rows, data.columns, data.chart_type||"bar"), 60);
    });
  }
}

window.copySql = (btn, b64) => {
  try { navigator.clipboard?.writeText(decodeURIComponent(escape(atob(b64)))); } catch {}
  btn.textContent = "Copied!";
  setTimeout(() => btn.textContent = "Copy", 2000);
};

/* ════════════════════════════════════════════════
   DASHBOARD PAGE
   ════════════════════════════════════════════════ */
async function initDashPage() {
  try {
    const r = await fetch(`${API}/schema`, {credentials:"include"});
    const d = await r.json();
    if (!d.schema) return;
    S.schema = d.schema; S.dbType = d.db_type;
    const tables = Object.entries(d.schema);
    const totalR = tables.reduce((s,[,t]) => s+t.row_count, 0);
    const totalC = tables.reduce((s,[,t]) => s+t.columns.length, 0);
    setText("d-tables",  tables.length);
    setText("d-rows",    totalR.toLocaleString());
    setText("d-cols",    totalC);
    setText("d-queries", S.queries);
    setText("d-q2",      S.queries);
    setText("d-hist",    S.history.length);
    setText("d-insights",S.queries);
    renderTableList(tables);
    renderDashChart(tables);
  } catch {}
}
function setText(id, val) { const e=document.getElementById(id); if(e) e.textContent=val; }
window.loadDashboard = initDashPage;

function renderTableList(tables) {
  const el2 = document.getElementById("dash-table-list");
  if (!el2) return;
  const max = Math.max(...tables.map(([,t])=>t.row_count), 1);
  el2.innerHTML = tables.map(([n,i]) => `
    <div style="margin-bottom:13px">
      <div class="flex ic jb mb1">
        <span class="fw7 tsm">📋 ${esc(n)}</span>
        <span class="txs tmuted">${i.row_count.toLocaleString()} rows · ${i.columns.length} cols</span>
      </div>
      <div class="prog"><div class="prog-fill" style="width:${Math.round(i.row_count/max*100)}%"></div></div>
    </div>`).join("");
}

function renderDashChart(tables) {
  const canvas = document.getElementById("dash-chart");
  if (!canvas) return;
  if (Charts.__dash) { Charts.__dash.destroy(); delete Charts.__dash; }
  const W = canvas.parentElement?.clientWidth || 480;
  canvas.width=W; canvas.height=240;
  canvas.style.width=W+"px"; canvas.style.height="240px";
  const isDark = document.documentElement.getAttribute("data-theme") !== "light";
  const tickC  = isDark ? "#3d5069" : "#7e94b0";
  Charts.__dash = new Chart(canvas.getContext("2d"), {
    type:"bar",
    data:{ labels:tables.map(([n])=>n), datasets:[{label:"Rows",data:tables.map(([,t])=>t.row_count),backgroundColor:PALETTE,borderRadius:6}] },
    options:{ responsive:false, maintainAspectRatio:false,
      plugins:{legend:{display:false}},
      scales:{
        x:{ticks:{color:tickC,font:{family:"'DM Sans'",size:10}},grid:{display:false}},
        y:{ticks:{color:tickC,font:{family:"'DM Sans'",size:10}},grid:{color:isDark?"rgba(255,255,255,0.05)":"rgba(0,0,0,0.06)"}},
      }
    }
  });
}

/* ════════════════════════════════════════════════
   SQL EDITOR PAGE
   ════════════════════════════════════════════════ */
function initSqlPage() {
  window.runSQL = async () => {
    const sql = $("#sql-ta")?.value.trim();
    if (!sql) { toast("Write a SELECT query","warn"); return; }
    try {
      const r = await fetch(`${API}/sql`,{method:"POST",credentials:"include",headers:{"Content-Type":"application/json"},body:JSON.stringify({sql})});
      const d = await r.json();
      const wrap = $("#sql-out");
      if (!wrap) return;
      wrap.classList.remove("hidden");
      if (d.ok) {
        setText("sql-badge","");
        const badge = document.getElementById("sql-badge");
        if (badge) badge.innerHTML = `<span class="row-pill">📊 ${d.row_count} rows</span>`;
        const body = document.getElementById("sql-body");
        if (body) body.innerHTML = buildTable(d.rows?.slice(0,200), d.columns) || `<p class="tmuted" style="padding:14px;font-size:13px">Query ran — no results.</p>`;
        toast(`${d.row_count} rows returned`,"ok");
      } else {
        const body = document.getElementById("sql-body");
        if (body) body.innerHTML = `<div style="color:var(--rose);padding:14px;font-size:13px">❌ ${esc(d.error)}</div>`;
      }
    } catch { toast("Server offline","err"); }
  };
  window.clearSQL = () => {
    const ta = $("#sql-ta"); if(ta) ta.value="";
    const out = $("#sql-out"); if(out) out.classList.add("hidden");
  };
  window.insertSQL = sql => { const ta=$("#sql-ta"); if(ta) ta.value=sql; };
}

/* ════════════════════════════════════════════════
   CONNECT PAGE
   ════════════════════════════════════════════════ */
function initConnectPage() {
  S.selDB = "demo";

  // Show connected banner if already connected
  if (S.dbType) {
    const banner = document.getElementById("conn-banner");
    if (banner) {
      banner.classList.remove("hidden");
      const lbl = document.getElementById("conn-banner-lbl");
      if (lbl) lbl.textContent = S.dbLabel || `${S.dbType} connected`;
    }
  }

  window.pickDB = (type, el2) => {
    S.selDB = type;
    $$(".db-opt").forEach(c => c.classList.remove("sel"));
    el2.classList.add("sel");
  };

  window.connNext = () => {
    document.getElementById("conn-step1")?.classList.add("hidden");
    document.getElementById("conn-step2")?.classList.remove("hidden");
    document.getElementById("ws2")?.classList.add("active");
    buildConnForm();
  };
  window.connBack = () => {
    document.getElementById("conn-step2")?.classList.add("hidden");
    document.getElementById("conn-step1")?.classList.remove("hidden");
    document.getElementById("ws2")?.classList.remove("active");
  };
  window.resetConn = () => {
    document.getElementById("conn-banner")?.classList.add("hidden");
    document.getElementById("conn-step1")?.classList.remove("hidden");
    document.getElementById("conn-step2")?.classList.add("hidden");
    document.getElementById("conn-step3")?.classList.add("hidden");
    document.getElementById("ws2")?.classList.remove("active");
    document.getElementById("ws3")?.classList.remove("active");
  };
  window.doConnect = async () => {
    document.getElementById("conn-step2")?.classList.add("hidden");
    document.getElementById("conn-step3")?.classList.remove("hidden");
    document.getElementById("ws3")?.classList.add("active");

    let cfg = {};
    if (S.selDB==="demo") cfg={type:"sqlite",path:""};
    else if (S.selDB==="sqlite") cfg={type:"sqlite",path:document.getElementById("f-path")?.value||""};
    else cfg={type:S.selDB,host:document.getElementById("f-host")?.value,port:document.getElementById("f-port")?.value,
               database:document.getElementById("f-db")?.value,username:document.getElementById("f-user")?.value,
               password:document.getElementById("f-pass")?.value};

    try {
      const r = await fetch(`${API}/connect`,{method:"POST",credentials:"include",headers:{"Content-Type":"application/json"},body:JSON.stringify({config:cfg})});
      const d = await r.json();
      const res = document.getElementById("conn-result");
      if (d.ok) {
        S.schema  = d.schema; S.dbType = d.db_type;
        S.dbLabel = `${d.db_type} · ${d.tables} tables · ${d.total_rows.toLocaleString()} records`;
        setDBStatus(true, S.dbLabel, S.dbLabel);
        loadSuggestions();
        if (res) res.innerHTML = `
          <div style="text-align:center;padding:24px 14px">
            <div style="font-size:52px;margin-bottom:12px">✅</div>
            <div class="fdisp fw8" style="font-size:19px;margin-bottom:8px">Connected!</div>
            <div class="tmuted tsm">${d.tables} tables · ${d.total_rows.toLocaleString()} records</div>
            <div class="flex gap2 mt3" style="justify-content:center;flex-wrap:wrap">
              <span class="tag tag-g">📦 ${d.tables} Tables</span>
              <span class="tag tag-t">📝 ${d.total_rows.toLocaleString()} Records</span>
              <span class="tag tag-p">🔒 Read-Only</span>
            </div>
            <div class="flex gap2 mt4" style="justify-content:center;flex-wrap:wrap">
              <button class="btn btn-green" onclick="navigate('query')">Start Analyzing →</button>
              <button class="btn btn-outline" onclick="resetConn()">🔄 Connect Different</button>
            </div>
          </div>`;
        toast("Database connected!","ok");
      } else { throw new Error(d.error); }
    } catch(e) {
      const res = document.getElementById("conn-result");
      if (res) res.innerHTML = `
        <div style="text-align:center;padding:24px 14px">
          <div style="font-size:52px;margin-bottom:12px">❌</div>
          <div class="fdisp fw8" style="font-size:17px;margin-bottom:8px">Connection Failed</div>
          <div class="tmuted tsm">${esc(e.message||"Unknown error")}</div>
          <button class="btn btn-outline mt3" onclick="resetConn()">← Try Again</button>
        </div>`;
    }
  };
}

function buildConnForm() {
  const wrap = document.getElementById("conn-form");
  if (!wrap) return;
  if (S.selDB==="demo") {
    wrap.innerHTML = `
      <div style="text-align:center;padding:22px">
        <span style="font-size:48px">🎯</span>
        <div class="fdisp fw7 mt2" style="font-size:16px">Demo Database Ready</div>
        <div class="tmuted tsm mt2">600 orders · 100 customers · 25 campaigns · 16 products</div>
      </div>`;
  } else if (S.selDB==="sqlite") {
    wrap.innerHTML = `
      <div class="field">
        <label class="field-lbl">SQLite File Path</label>
        <input id="f-path" class="field-inp" placeholder="C:/path/to/your.db" />
        <div class="field-hint">Leave blank to use the built-in demo database</div>
      </div>`;
  } else {
    const port = S.selDB==="postgresql"?"5432":"3306";
    wrap.innerHTML = `
      <div class="field-row">
        <div class="field"><label class="field-lbl">Host</label><input id="f-host" class="field-inp" placeholder="localhost" /></div>
        <div class="field"><label class="field-lbl">Port</label><input id="f-port" class="field-inp" placeholder="${port}" /></div>
      </div>
      <div class="field"><label class="field-lbl">Database Name</label><input id="f-db" class="field-inp" placeholder="my_database" /></div>
      <div class="field-row">
        <div class="field"><label class="field-lbl">Username</label><input id="f-user" class="field-inp" placeholder="readonly_user" /></div>
        <div class="field"><label class="field-lbl">Password</label><input id="f-pass" class="field-inp" type="password" placeholder="••••••••" /></div>
      </div>
      <div class="tag tag-a" style="display:block;padding:8px 12px;border-radius:8px;font-size:12px">💡 Use a read-only database user for safety</div>`;
  }
}

/* ════════════════════════════════════════════════
   UPLOAD PAGE
   ════════════════════════════════════════════════ */
function initUploadPage() {
  const dz = $(".drop-zone");
  if (dz) {
    dz.addEventListener("dragover", e => { e.preventDefault(); dz.classList.add("drag"); });
    dz.addEventListener("dragleave", () => dz.classList.remove("drag"));
    dz.addEventListener("drop", e => { e.preventDefault(); dz.classList.remove("drag"); const f=e.dataTransfer?.files[0]; if(f) uploadFile(f); });
  }
  window.onFileChange = inp => { if(inp.files[0]) uploadFile(inp.files[0]); };
}

async function uploadFile(file) {
  if (!file.name.endsWith(".csv")) { toast("Please upload a .csv file","warn"); return; }
  const status = document.getElementById("upload-status");
  if (status) status.innerHTML = `<div class="tmuted tsm" style="padding:10px">⏳ Uploading ${esc(file.name)}…</div>`;
  const fd = new FormData(); fd.append("file", file);
  try {
    const r = await fetch(`${API}/upload-csv`,{method:"POST",credentials:"include",body:fd});
    const d = await r.json();
    if (d.ok) {
      if (status) status.innerHTML = `
        <div class="tag tag-t" style="display:block;padding:10px 14px;border-radius:10px;font-size:13px;margin-bottom:10px">
          ✅ ${esc(d.file)} → table <strong>${esc(d.table)}</strong> (${d.rows} rows)
        </div>
        <div class="flex gap2 flex-wrap">
          <span class="tag tag-g">📋 ${esc(d.table)}</span>
          <span class="tag tag-p">📝 ${d.rows} rows</span>
          <span class="tag tag-b">${d.columns.length} columns</span>
        </div>`;
      const sr = await fetch(`${API}/schema`,{credentials:"include"});
      const sd = await sr.json();
      if (sd.schema) { S.schema=sd.schema; setDBStatus(true,"CSV","CSV · "+d.rows+" rows"); }
      toast("CSV uploaded — ready to query!","ok");
      setTimeout(()=>navigate("query"),1400);
    } else throw new Error(d.error);
  } catch(e) {
    if (status) status.innerHTML = `<div style="color:var(--rose);font-size:13px">❌ ${esc(e.message)}</div>`;
  }
}

/* ════════════════════════════════════════════════
   HISTORY PAGE
   ════════════════════════════════════════════════ */
function initHistoryPage() {
  renderHistoryList();
  window.clearHistory = () => {
    S.history=[]; localStorage.removeItem("dw_h");
    const hb=$("#hist-badge"); if(hb) hb.textContent="0";
    renderHistoryList(); toast("History cleared","ok");
  };
}

function renderHistoryList() {
  const list = document.getElementById("hist-list");
  if (!list) return;
  if (!S.history.length) {
    list.innerHTML = `<div class="empty"><span class="empty-ico">📝</span><h3>No history yet</h3><p>Questions you ask will appear here.</p></div>`;
    return;
  }
  list.innerHTML = S.history.map((h,i) => `
    <div class="hist-item" onclick="replayQuery(${i})">
      <div class="hist-q">${esc(h.q)}</div>
      <div class="hist-meta"><span>🕒 ${h.time}</span><span>📊 ${h.rows} rows</span></div>
    </div>`).join("");
}

window.replayQuery = i => { navigate("query"); setTimeout(() => { const inp=$("#q-inp"); if(inp){inp.value=S.history[i].q; askQuery();} }, 200); };

/* ════════════════════════════════════════════════
   SETTINGS PAGE
   ════════════════════════════════════════════════ */
function initSettingsPage() {
  // toggles already work via inline onclick
}

/* ════════════════════════════════════════════════
   BOOT
   ════════════════════════════════════════════════ */
async function boot() {
  initTheme();

  // Update hist badge in sidebar
  const hb = $("#hist-badge");
  if (hb) hb.textContent = S.history.length;

  // Health check
  try {
    const r = await fetch(`${API}/health`);
    const d = await r.json();
    const badge = document.getElementById("ai-badge");
    if (badge) {
      badge.innerHTML = (d.groq||d.gemini)
        ? `<span class="tag tag-g">✅ AI Ready</span>`
        : `<span class="tag tag-a">⚠️ No API Key</span>`;
    }
    if (!d.groq && !d.gemini) toast("Add GROQ_API_KEY to .env then restart app.py","warn",7000);
  } catch {
    const badge = document.getElementById("ai-badge");
    if (badge) badge.innerHTML = `<span class="tag tag-r">❌ Offline</span>`;
    toast("Server offline — run: python app.py","err",8000);
  }

  // Try to restore schema from session
  try {
    const r = await fetch(`${API}/schema`,{credentials:"include"});
    const d = await r.json();
    if (d.schema && Object.keys(d.schema).length) {
      S.schema=d.schema; S.dbType=d.db_type;
      S.dbLabel=`${d.db_type} · ${Object.keys(d.schema).length} tables`;
      setDBStatus(true, S.dbLabel, S.dbLabel);
    }
  } catch {}

  // Load default page
  navigate("query");
}

document.addEventListener("DOMContentLoaded", boot);
