/**
 * Orkavia AI-OS Nexus — SPA
 * © 2026 Fasih ur Rehman. All Rights Reserved.
 */

'use strict';

/* ================================================================
   UTILITIES
   ================================================================ */
const API = window.location.origin;

function escapeHtml(s) {
  return String(s)
    .replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')
    .replace(/"/g,'&quot;').replace(/'/g,'&#039;');
}

/** Very light Markdown → HTML (bold, italic, code, pre, ul, ol, headers) */
function renderMarkdown(text) {
  let h = escapeHtml(text);
  // Code blocks
  h = h.replace(/```[\w]*\n?([\s\S]*?)```/g, '<pre><code>$1</code></pre>');
  // Inline code
  h = h.replace(/`([^`]+)`/g, '<code>$1</code>');
  // Bold
  h = h.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
  // Italic
  h = h.replace(/\*(.+?)\*/g, '<em>$1</em>');
  // Headers
  h = h.replace(/^### (.+)$/gm, '<h4>$1</h4>');
  h = h.replace(/^## (.+)$/gm,  '<h3>$1</h3>');
  h = h.replace(/^# (.+)$/gm,   '<h2>$1</h2>');
  // Unordered list
  h = h.replace(/^[-*] (.+)$/gm, '<li>$1</li>');
  h = h.replace(/(<li>.*<\/li>(\n|$))+/g, m => `<ul>${m}</ul>`);
  // Ordered list
  h = h.replace(/^\d+\. (.+)$/gm, '<li>$1</li>');
  // Line breaks (non-block)
  h = h.replace(/\n/g, '<br>');
  return h;
}

function fmt(ts) {
  if (!ts) return '';
  const d = new Date(typeof ts === 'number' && ts < 1e12 ? ts * 1000 : ts);
  return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
}

function fmtDate(ts) {
  if (!ts) return '';
  const d = new Date(typeof ts === 'number' && ts < 1e12 ? ts * 1000 : ts);
  return d.toLocaleString();
}

/* ================================================================
   HTTP CLIENT
   ================================================================ */
const http = {
  async get(path) {
    const r = await fetch(API + path);
    if (!r.ok) throw new Error(await r.text());
    return r.json();
  },
  async post(path, body) {
    const r = await fetch(API + path, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (!r.ok) throw new Error(await r.text());
    return r.json();
  },
  async del(path) {
    const r = await fetch(API + path, { method: 'DELETE' });
    if (!r.ok) throw new Error(await r.text());
    return r.json();
  },
};

/* ================================================================
   TOAST
   ================================================================ */
function toast(msg, type = 'info', duration = 4200) {
  const icons = { success: '✅', error: '❌', warning: '⚠️', info: 'ℹ️' };
  const el = document.createElement('div');
  el.className = `toast ${type}`;
  el.setAttribute('role', 'alert');
  el.innerHTML = `<span class="toast-icon" aria-hidden="true">${icons[type] || ''}</span><span class="toast-msg">${escapeHtml(String(msg))}</span>`;
  const c = document.getElementById('toastContainer');
  c.appendChild(el);
  setTimeout(() => { el.style.opacity = '0'; el.style.transform = 'translateY(6px)'; el.style.transition = '.25s ease'; setTimeout(() => el.remove(), 280); }, duration);
}

/* ================================================================
   ROUTER
   ================================================================ */
const ALL_SECTIONS = ['chat', 'decide', 'sensors', 'memory', 'reports', 'admin', 'audit'];
const SECTION_TITLES = {
  chat: 'Chat', decide: 'Decision Engine', sensors: 'Sensors',
  memory: 'Memory Vault', reports: 'Reports', admin: 'Admin', audit: 'Audit',
};

function showSection(name) {
  if (!ALL_SECTIONS.includes(name)) name = 'chat';
  ALL_SECTIONS.forEach(s => {
    const el = document.getElementById(`section-${s}`);
    if (el) el.classList.toggle('hidden', s !== name);
  });
  document.querySelectorAll('.nav-item').forEach(a => {
    const active = a.dataset.section === name;
    a.classList.toggle('active', active);
    a.setAttribute('aria-current', active ? 'page' : 'false');
  });
  const t = document.getElementById('topBarTitle');
  if (t) t.textContent = SECTION_TITLES[name] || name;

  if (name === 'admin')   { App.admin.loadHealth(); App.admin.loadStats(); App.admin.loadDataset(); }
  if (name === 'sensors') App.sensors.refresh();
  if (name === 'decide')  App.decide.loadHistory();
}

function navigate() {
  const hash = window.location.hash.replace('#','') || 'chat';
  showSection(hash);
}

/* ================================================================
   STATUS INDICATOR
   ================================================================ */
async function checkApiStatus() {
  const dot  = document.getElementById('statusDot');
  const text = document.getElementById('statusText');
  const hbar = document.getElementById('topBarHealth');
  dot?.classList.add('pulse');
  try {
    const d = await http.get('/admin/health');
    dot?.classList.remove('pulse');
    dot?.classList.add('online');
    if (text) text.textContent = 'Online';
    if (hbar) hbar.textContent = `v${d.version || '2'} · ${d.status || 'OK'}`;
  } catch {
    dot?.classList.remove('pulse', 'online');
    dot?.classList.add('offline');
    if (text) text.textContent = 'Offline';
    if (hbar) hbar.textContent = 'API unavailable';
  }
}

/* ================================================================
   CHAT MODULE
   ================================================================ */
const App = {};

App.chat = (() => {
  const state = { loading: false };

  function getMode()    { return document.querySelector('.pill-btn.active')?.dataset.value || 'public'; }
  function getConsent() { return document.getElementById('memoryConsent')?.value || 'NONE'; }
  function getUserId()  { return document.getElementById('userId')?.value.trim() || 'user-001'; }

  function addBubble(role, htmlContent, meta = {}) {
    const box = document.getElementById('chatMessages');
    const welcome = document.getElementById('welcomeMsg');
    if (welcome) welcome.remove();

    const wrap = document.createElement('div');
    wrap.className = `chat-bubble bubble-${role}`;

    if (role === 'ai') {
      wrap.innerHTML = `
        <div class="bubble-ai-header">
          <div class="ai-avatar" aria-hidden="true">AI</div>
          <span class="ai-label">Nexus</span>
        </div>
        <div class="bubble-body">${htmlContent}</div>
        ${meta.sources ? `<div class="bubble-sources">📚 Sources: ${escapeHtml(meta.sources.slice(0,3).map(s => s.source||s.id||'kb').join(', '))}</div>` : ''}
        <div class="bubble-meta">${fmt(Date.now())}</div>
        <div class="bubble-feedback">
          <button class="feedback-btn" title="Helpful" onclick="this.classList.add('voted');this.disabled=true">👍</button>
          <button class="feedback-btn" title="Not helpful" onclick="this.classList.add('voted');this.disabled=true">👎</button>
        </div>`;
    } else {
      wrap.innerHTML = `
        <div class="bubble-body">${htmlContent}</div>
        <div class="bubble-meta">${fmt(Date.now())}</div>`;
    }
    box.appendChild(wrap);
    box.scrollTop = box.scrollHeight;
    return wrap;
  }

  function addTyping() {
    const box = document.getElementById('chatMessages');
    const el = document.createElement('div');
    el.className = 'chat-bubble bubble-ai bubble-typing';
    el.id = 'typingIndicator';
    el.innerHTML = `<div class="bubble-ai-header"><div class="ai-avatar" aria-hidden="true">AI</div><span class="ai-label">Nexus</span></div><div class="bubble-body"><div class="typing-dots"><span></span><span></span><span></span></div></div>`;
    box.appendChild(el);
    box.scrollTop = box.scrollHeight;
  }
  function removeTyping() { document.getElementById('typingIndicator')?.remove(); }

  async function send() {
    if (state.loading) return;
    const input = document.getElementById('chatInput');
    const query = input.value.trim();
    if (!query) return;

    input.value = '';
    input.style.height = 'auto';
    input.dispatchEvent(new Event('input'));
    addBubble('user', escapeHtml(query));
    state.loading = true;
    document.getElementById('sendBtn').disabled = true;
    addTyping();

    const meta = document.getElementById('chatMeta');
    if (meta) meta.textContent = 'Thinking…';

    try {
      const body = {
        query, mode: getMode(), memory_consent: getConsent(), user_id: getUserId(),
      };
      const d = await http.post('/ask', body);
      removeTyping();
      const answer = d.answer || d.response || JSON.stringify(d);
      addBubble('ai', renderMarkdown(answer), { sources: d.sources });
      if (meta) {
        const parts = [];
        if (d.mode)          parts.push(`Mode: ${d.mode}`);
        if (d.search_engine) parts.push(`Search: ${d.search_engine}`);
        if (d.sources?.length) parts.push(`${d.sources.length} source(s)`);
        meta.textContent = parts.join(' · ');
      }
    } catch(e) {
      removeTyping();
      addBubble('ai', `<span style="color:var(--danger)">Error: ${escapeHtml(e.message)}</span>`);
      if (meta) meta.textContent = '';
    } finally {
      state.loading = false;
      document.getElementById('sendBtn').disabled = false;
      input.focus();
    }
  }

  function inject(text) {
    const input = document.getElementById('chatInput');
    if (input) { input.value = text; input.dispatchEvent(new Event('input')); input.focus(); }
  }

  function clear() {
    const box = document.getElementById('chatMessages');
    box.innerHTML = '';
    const welcome = document.createElement('div');
    welcome.className = 'welcome-msg'; welcome.id = 'welcomeMsg';
    welcome.innerHTML = `
      <div class="welcome-visual">
        <div class="welcome-ring ring1"></div>
        <div class="welcome-ring ring2"></div>
        <div class="welcome-ring ring3"></div>
        <div class="welcome-core"><svg viewBox="0 0 60 60" fill="none" width="36" height="36"><circle cx="30" cy="18" r="5" fill="url(#wlg)"/><circle cx="18" cy="38" r="5" fill="url(#wlg)"/><circle cx="42" cy="38" r="5" fill="url(#wlg)"/><line x1="30" y1="23" x2="18" y2="33" stroke="url(#wlg)" stroke-width="1.8"/><line x1="30" y1="23" x2="42" y2="33" stroke="url(#wlg)" stroke-width="1.8"/><line x1="18" y1="38" x2="42" y2="38" stroke="url(#wlg)" stroke-width="1.8"/><defs><linearGradient id="wlg" x1="0" y1="0" x2="60" y2="60" gradientUnits="userSpaceOnUse"><stop stop-color="#a78bfa"/><stop offset="1" stop-color="#38bdf8"/></linearGradient></defs></svg></div>
      </div>
      <h2>Orkavia AI-OS Nexus</h2>
      <p>Ask me about science, programming, agriculture, medical monitoring, or anything in your knowledge base.</p>
      <div class="welcome-chips">
        <button class="chip" onclick="App.chat.inject('What is the optimal soil moisture for wheat crops?')">🌱 Irrigation query</button>
        <button class="chip" onclick="App.chat.inject('Explain patient vital signs monitoring')">🏥 Medical vitals</button>
        <button class="chip" onclick="App.chat.inject('How does industrial pressure monitoring work?')">🏭 Industrial</button>
        <button class="chip" onclick="App.chat.inject('How does the AES-256 memory encryption work?')">🔒 Privacy</button>
      </div>`;
    box.appendChild(welcome);
    const meta = document.getElementById('chatMeta');
    if (meta) meta.textContent = '';
  }

  function init() {
    const input = document.getElementById('chatInput');
    const btn   = document.getElementById('sendBtn');
    input?.addEventListener('keydown', e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); } });
    input?.addEventListener('input', () => { input.style.height = 'auto'; input.style.height = Math.min(input.scrollHeight, 160) + 'px'; });
    btn?.addEventListener('click', send);

    // Mode pill toggle
    document.querySelectorAll('.pill-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('.pill-btn').forEach(b => { b.classList.remove('active'); b.setAttribute('aria-checked','false'); });
        btn.classList.add('active');
        btn.setAttribute('aria-checked','true');
      });
    });
  }

  return { send, inject, clear, init };
})();

/* ================================================================
   DECISION ENGINE MODULE
   ================================================================ */
App.decide = (() => {
  let liveEventSource = null;

  const TEMPLATES = {
    irrigation: { soil_moisture: 28, temperature: 32, rain_probability: 0.15, pressure: 3.2, flow_rate: 14 },
    hospital:   { heart_rate: 92, systolic_bp: 142, diastolic_bp: 88, spo2: 96, temperature: 37.8, respiratory_rate: 18 },
    industrial: { pressure: 8.4, temperature: 89, vibration: 4.2, flow_rate: 62, rpm: 1450 },
    general:    { value: 42, threshold: 50, priority: 'medium' },
  };

  function updateContextTemplate() {
    const domain = document.getElementById('decideDomain')?.value || 'irrigation';
    const ta = document.getElementById('decideContext');
    if (ta) ta.value = JSON.stringify(TEMPLATES[domain] || TEMPLATES.irrigation, null, 2);
  }

  function actionClass(action) {
    if (!action) return 'action-info';
    const a = String(action).toLowerCase();
    if (a.includes('critical') || a.includes('emergency') || a.includes('stop') || a.includes('alarm')) return 'action-danger';
    if (a.includes('warn') || a.includes('caution') || a.includes('check') || a.includes('inspect')) return 'action-warn';
    if (a.includes('ok') || a.includes('normal') || a.includes('optimal') || a.includes('maintain') || a.includes('irrigat')) return 'action-ok';
    return 'action-info';
  }

  function actionEmoji(action) {
    const a = String(action || '').toLowerCase();
    if (a.includes('critical') || a.includes('emergency') || a.includes('stop')) return '🚨';
    if (a.includes('warn') || a.includes('caution')) return '⚠️';
    if (a.includes('ok') || a.includes('optimal') || a.includes('normal')) return '✅';
    if (a.includes('irrigat')) return '💧';
    return '⚡';
  }

  function simActionClass(action) {
    const a = String(action || '').toLowerCase();
    if (a.includes('critical') || a.includes('stop') || a.includes('emergency')) return 'danger';
    if (a.includes('warn') || a.includes('caution') || a.includes('check')) return 'warn';
    if (a.includes('ok') || a.includes('optimal') || a.includes('normal') || a.includes('maintain')) return 'ok';
    return 'info';
  }

  function renderDecisionResult(data, el) {
    // Endpoint returns a flat DecideResponse object
    const pct     = Math.round((data.confidence || 0) * 100);
    const cls     = actionClass(data.action);
    const emoji   = actionEmoji(data.action);
    const allowed = data.safety_allowed !== false;
    const safetyHtml = `
      <div class="safety-status ${allowed ? 'allowed' : 'blocked'}">
        <div class="safety-status-dot"></div>
        Safety: ${allowed ? 'Passed ✓' : 'Blocked ✗'} — ${escapeHtml(data.safety_reason || '')}
      </div>
      ${(data.safety_flags||[]).length ? `<div class="safety-flags">${(data.safety_flags||[]).map(f => `<span class="safety-flag-chip">${escapeHtml(f)}</span>`).join('')}</div>` : ''}`;

    el.innerHTML = `
      <div class="decision-display">
        <div class="decision-action-badge ${cls}">
          <span class="decision-action-icon">${emoji}</span>
          <span>${escapeHtml(data.action || 'Analysis complete')}</span>
        </div>
        <div class="decision-confidence-bar">
          <div class="confidence-label"><span>Confidence</span><span>${pct}%</span></div>
          <div class="confidence-track"><div class="confidence-fill" style="width:0%"></div></div>
        </div>
        <div class="decision-meta-grid">
          <div class="decision-meta-item"><label>Domain</label><span>${escapeHtml(data.domain || '—')}</span></div>
          <div class="decision-meta-item"><label>Latency</label><span>${data.latency_ms != null ? data.latency_ms.toFixed(1) + 'ms' : '—'}</span></div>
          <div class="decision-meta-item"><label>Risk Level</label><span>${escapeHtml(data.risk_level || '—')}</span></div>
          <div class="decision-meta-item"><label>Approval Req.</label><span>${data.requires_human_approval ? '⚠ Yes' : '✓ No'}</span></div>
        </div>
        ${data.reasoning ? `<div class="decision-reasoning">${escapeHtml(data.reasoning)}</div>` : ''}
        ${safetyHtml}
      </div>`;

    // Animate confidence bar
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        const fill = el.querySelector('.confidence-fill');
        if (fill) fill.style.width = pct + '%';
      });
    });
  }

  async function run() {
    const domain  = document.getElementById('decideDomain')?.value || 'irrigation';
    const ctxRaw  = document.getElementById('decideContext')?.value || '{}';
    const safety  = document.getElementById('decideSafety')?.checked ?? true;
    const resultEl = document.getElementById('decideResult');
    let context;
    try { context = JSON.parse(ctxRaw); }
    catch { toast('Invalid JSON in context field', 'error'); return; }

    resultEl.innerHTML = `<div class="typing-dots" style="margin:auto;padding:2rem"><span></span><span></span><span></span></div>`;
    try {
      const data = await http.post('/decide', { domain, context, apply_safety: safety });
      renderDecisionResult(data, resultEl);
      toast('Decision analysis complete', 'success', 2500);
      setTimeout(() => loadHistory(), 500);
    } catch(e) {
      resultEl.innerHTML = `<div class="decide-result-placeholder"><div class="placeholder-icon">❌</div><p style="color:var(--danger)">${escapeHtml(e.message)}</p></div>`;
      toast(`Decision error: ${e.message}`, 'error');
    }
  }

  async function simulate() {
    const type  = document.getElementById('simType')?.value || 'irrigation';
    const count = parseInt(document.getElementById('simCount')?.value) || 3;
    const box   = document.getElementById('simulateResults');
    box.innerHTML = `<div class="typing-dots" style="padding:1rem"><span></span><span></span><span></span></div>`;
    try {
      const data = await http.post('/sensor/simulate', { sensor_type: type, count });
      const readings = data.results || data.readings || [];
      if (!readings.length) { box.innerHTML = '<p style="color:var(--text-muted);font-size:.82rem;padding:.5rem">No readings returned.</p>'; return; }
      box.innerHTML = '';
      readings.forEach((r, i) => {
        const d = r.decision || {};
        const sd = r.data || r;
        const metrics = Object.entries(sd).filter(([k]) => !['sensor_id','sensor_type','timestamp','anomaly_score','status'].includes(k));
        const isAnomaly = r.is_anomaly || (sd.anomaly_score || 0) > 0.5;
        const aCls = simActionClass(d.action);
        const el = document.createElement('div');
        el.className = `simulate-reading${isAnomaly ? ' is-anomaly' : ''}`;
        el.innerHTML = `
          <div class="simulate-reading-header">
            <span>Reading #${i + 1} — ${escapeHtml(sd.sensor_id || type)}</span>
            <span>${isAnomaly ? `<span class="anomaly-badge">⚠ Anomaly ${((sd.anomaly_score||0)*100).toFixed(0)}%</span>` : `<span style="font-size:.72rem;color:var(--text-muted)">${fmt(sd.timestamp)}</span>`}</span>
          </div>
          <div class="sim-data-cols">${metrics.slice(0,6).map(([k,v]) => `<div class="sim-data-item"><span class="key">${escapeHtml(k)}</span><span class="val">${typeof v === 'number' ? v.toFixed(2) : escapeHtml(String(v))}</span></div>`).join('')}</div>
          <div class="sim-decision">
            <span class="sim-action ${aCls}">${escapeHtml(d.action || 'No decision')}</span>
            ${d.confidence != null ? `<span style="font-size:.72rem;color:var(--text-muted)">Confidence: ${Math.round((d.confidence||0)*100)}%</span>` : ''}
            ${d.reasoning ? `<span style="font-size:.72rem;color:var(--text-muted);margin-top:2px">${escapeHtml(d.reasoning.slice(0,80))}…</span>` : ''}
          </div>`;
        box.appendChild(el);
      });
      toast(`${readings.length} simulation(s) complete`, 'success', 2200);
    } catch(e) {
      box.innerHTML = `<p style="color:var(--danger);font-size:.82rem;padding:.5rem">Error: ${escapeHtml(e.message)}</p>`;
      toast(`Simulation error: ${e.message}`, 'error');
    }
  }

  function toggleLiveStream() {
    const btn = document.getElementById('liveStreamBtn');
    const box = document.getElementById('simulateResults');
    if (liveEventSource) {
      liveEventSource.close(); liveEventSource = null;
      btn?.classList.remove('streaming');
      btn.innerHTML = `<svg viewBox="0 0 16 16" fill="none" width="14" height="14"><circle cx="8" cy="8" r="3" fill="currentColor"/><circle cx="8" cy="8" r="6" stroke="currentColor" stroke-width="1.5"/></svg> Live Stream`;
      toast('Live stream stopped', 'info', 2000);
      return;
    }
    const type = document.getElementById('simType')?.value || 'irrigation';
    btn?.classList.add('streaming');
    btn.innerHTML = `<svg viewBox="0 0 16 16" fill="none" width="14" height="14"><rect x="4" y="3" width="3" height="10" fill="currentColor"/><rect x="9" y="3" width="3" height="10" fill="currentColor"/></svg> Stop Stream`;
    box.innerHTML = '';
    toast('Live stream started', 'success', 2000);
    liveEventSource = new EventSource(`${API}/sensor/live-stream?sensor_type=${encodeURIComponent(type)}`);
    liveEventSource.onmessage = e => {
      try {
        const r = JSON.parse(e.data);
        if (r.__done__) return;
        const d  = r.decision || {};
        const sd = r.data || r;
        const metrics = Object.entries(sd).filter(([k]) => !['sensor_id','sensor_type','timestamp','anomaly_score','status'].includes(k));
        const isAnomaly = (sd.anomaly_score || 0) > 0.5;
        const aCls = simActionClass(d.action);
        const el = document.createElement('div');
        el.className = `simulate-reading${isAnomaly ? ' is-anomaly' : ''}`;
        el.innerHTML = `
          <div class="simulate-reading-header">
            <span>LIVE — ${escapeHtml(r.sensor_id || type)}</span>
            <span style="font-size:.7rem;color:var(--text-muted)">${fmt(r.timestamp)}</span>
          </div>
          <div class="sim-data-cols">${metrics.slice(0,6).map(([k,v]) => `<div class="sim-data-item"><span class="key">${escapeHtml(k)}</span><span class="val">${typeof v === 'number' ? v.toFixed(2) : escapeHtml(String(v))}</span></div>`).join('')}</div>
          <div class="sim-decision"><span class="sim-action ${aCls}">${escapeHtml(d.action || '—')}</span>${d.confidence != null ? `<span style="font-size:.7rem;color:var(--text-muted)">Conf: ${Math.round((d.confidence||0)*100)}%</span>` : ''}</div>`;
        box.insertBefore(el, box.firstChild);
        if (box.children.length > 20) box.removeChild(box.lastChild);
      } catch { /* skip malformed frame */ }
    };
    liveEventSource.onerror = () => {
      liveEventSource?.close(); liveEventSource = null;
      btn?.classList.remove('streaming');
      btn.innerHTML = `<svg viewBox="0 0 16 16" fill="none" width="14" height="14"><circle cx="8" cy="8" r="3" fill="currentColor"/><circle cx="8" cy="8" r="6" stroke="currentColor" stroke-width="1.5"/></svg> Live Stream`;
    };
  }

  async function loadHistory() {
    const box = document.getElementById('decideHistory');
    if (!box) return;
    try {
      const data = await http.get('/decide/history?limit=10');
      const items = data.history || data.decisions || [];
      if (!items.length) { box.innerHTML = '<div class="empty-state"><span>⚡</span><p>No decisions yet.</p></div>'; return; }
      box.innerHTML = items.map(h => {
        const d = h.decision || h;
        const pct = Math.round((d.confidence || 0) * 100);
        return `<div class="history-item">
          <span class="history-action">${escapeHtml(d.action || '—')}</span>
          <span class="history-domain">${escapeHtml(d.domain || h.domain || '—')}</span>
          <span class="history-confidence">Conf: ${pct}%</span>
          <span style="font-size:.68rem;color:var(--text-muted)">${fmt(h.timestamp || h.ts)}</span>
        </div>`;
      }).join('');
    } catch(e) {
      box.innerHTML = `<div class="empty-state"><p style="color:var(--text-muted)">Could not load history.</p></div>`;
    }
  }

  return { run, simulate, toggleLiveStream, loadHistory, updateContextTemplate };
})();

/* ================================================================
   SENSORS MODULE
   ================================================================ */
App.sensors = (() => {
  let autoRefreshTimer = null;
  const state = { cards: {} };

  const SENSOR_CONFIGS = {
    irrigation: {
      sensor_id: 'irr-001', sensor_type: 'irrigation',
      readings: { soil_moisture: [20,60], temperature: [18,42], flow_rate: [5,25], pressure: [1.5,5.5], rain_probability: [0,1] },
    },
    hospital: {
      sensor_id: 'hosp-001', sensor_type: 'hospital',
      readings: { heart_rate: [55,120], systolic_bp: [100,180], diastolic_bp: [60,110], spo2: [88,100], temperature: [36,40], respiratory_rate: [10,24] },
    },
    industrial: {
      sensor_id: 'ind-001', sensor_type: 'industrial',
      readings: { pressure: [4,12], temperature: [60,120], vibration: [0.5,8], flow_rate: [30,90], rpm: [800,2000] },
    },
  };

  function rand(lo, hi) { return +(lo + Math.random() * (hi - lo)).toFixed(2); }

  function determineStatus(type, readings) {
    if (type === 'irrigation') {
      if (readings.soil_moisture < 25 || readings.soil_moisture > 55) return 'warning';
      return 'normal';
    }
    if (type === 'hospital') {
      if (readings.heart_rate > 110 || readings.spo2 < 92 || readings.systolic_bp > 160) return 'critical';
      if (readings.heart_rate > 95 || readings.spo2 < 96) return 'warning';
      return 'normal';
    }
    if (type === 'industrial') {
      if (readings.pressure > 10 || readings.temperature > 110) return 'critical';
      if (readings.pressure > 8 || readings.temperature > 95) return 'warning';
      return 'normal';
    }
    return 'normal';
  }

  function buildSensorCard(sensor) {
    const type    = sensor.sensor_type || 'unknown';
    const id      = sensor.sensor_id || 'sensor';
    const metrics = Object.entries(sensor).filter(([k]) => !['sensor_id','sensor_type','timestamp','anomaly_score','status','decision'].includes(k));
    const status  = sensor.status || determineStatus(type, sensor);
    const d       = sensor.decision || {};
    const aCls    = decisionCls(d.action);

    const metricHtml = metrics.slice(0,6).map(([k, v]) => {
      const num = parseFloat(v);
      let valCls = '';
      if (status === 'critical') valCls = 'crit';
      else if (status === 'warning') valCls = 'warn';
      return `<div class="sensor-metric"><div class="sensor-metric-key">${escapeHtml(k)}</div><div class="sensor-metric-val ${valCls}">${typeof v === 'number' ? v.toFixed(2) : escapeHtml(String(v))}</div></div>`;
    }).join('');

    const decHtml = d.action
      ? `<div class="sensor-decision-strip ${aCls}"><span>${escapeHtml(d.action)}</span>${d.confidence != null ? `<span class="decision-confidence-chip">${Math.round((d.confidence||0)*100)}%</span>` : ''}</div>`
      : '';

    return `<div class="sensor-card ${status}" role="listitem">
      <div class="sensor-card-header">
        <div><div class="sensor-id">${escapeHtml(id)}</div><div class="sensor-time">${fmt(sensor.timestamp)}</div></div>
        <span class="sensor-status-badge ${status}">${status}</span>
      </div>
      <div class="sensor-metrics">${metricHtml}</div>
      ${decHtml}
    </div>`;
  }

  function decisionCls(action) {
    const a = String(action || '').toLowerCase();
    if (a.includes('critical') || a.includes('stop') || a.includes('emergency') || a.includes('alarm')) return 'danger';
    if (a.includes('warn') || a.includes('caution') || a.includes('check')) return 'warning';
    if (a.includes('ok') || a.includes('optimal') || a.includes('normal') || a.includes('maintain') || a.includes('irrigat')) return 'ok';
    return 'info';
  }

  async function injectDemo(type) {
    const cfg = SENSOR_CONFIGS[type];
    if (!cfg) return;
    const readings = {};
    Object.entries(cfg.readings).forEach(([k, [lo, hi]]) => { readings[k] = rand(lo, hi); });
    const payload = { sensor_id: cfg.sensor_id, data: { sensor_type: cfg.sensor_type, ...readings }, source: 'demo' };
    try {
      await http.post('/sensor/ingest', payload);
      toast(`${type} sensor data injected`, 'success', 2000);
      refresh();
    } catch(e) {
      toast(`Inject error: ${e.message}`, 'error');
    }
  }

  async function refresh() {
    const grid = document.getElementById('sensorGrid');
    if (!grid) return;
    try {
      const data = await http.get('/sensor/latest-all');
      const sensors = data.sensors || [];
      if (!sensors.length) {
        grid.innerHTML = '<div class="empty-state col-span-all"><div class="empty-icon">📡</div><p>Inject sensor data above to see live readings here.</p></div>';
        return;
      }
      grid.innerHTML = sensors.map(buildSensorCard).join('');
    } catch(e) {
      grid.innerHTML = `<div class="empty-state col-span-all"><p style="color:var(--danger)">Error loading sensors: ${escapeHtml(e.message)}</p></div>`;
    }
  }

  function toggleAutoRefresh(enabled) {
    clearInterval(autoRefreshTimer);
    if (enabled) { autoRefreshTimer = setInterval(refresh, 5000); toast('Auto-refresh every 5s', 'info', 2000); }
    else { toast('Auto-refresh stopped', 'info', 2000); }
  }

  return { injectDemo, refresh, toggleAutoRefresh };
})();

/* ================================================================
   MEMORY MODULE
   ================================================================ */
App.memory = (() => {
  let _data = [];

  function getUserId() { return document.getElementById('memUserId')?.value.trim() || 'user-001'; }

  async function load() {
    const uid = getUserId();
    const list = document.getElementById('memoryList');
    const stats = document.getElementById('memoryStats');
    list.innerHTML = '<div class="skeleton-shimmer">Loading…</div>';
    try {
      const d = await http.get(`/memory/${encodeURIComponent(uid)}`);
      _data = d.memories || d.entries || d || [];
      renderList(_data);
      if (stats) {
        const total  = _data.length;
        const modes  = {};
        _data.forEach(m => { const md = m.mode || 'NONE'; modes[md] = (modes[md]||0)+1; });
        stats.innerHTML = `
          <div class="stat-chip"><span class="stat-value">${total}</span><span class="stat-label">Total</span></div>
          ${Object.entries(modes).map(([m,c]) => `<div class="stat-chip"><span class="stat-value">${c}</span><span class="stat-label">${m}</span></div>`).join('')}`;
      }
      if (!_data.length) toast('No memories found for this user', 'info');
      else toast(`Loaded ${_data.length} memory record(s)`, 'success', 2200);
    } catch(e) {
      list.innerHTML = `<div class="empty-state"><div class="empty-icon">⚠️</div><p style="color:var(--danger)">${escapeHtml(e.message)}</p></div>`;
      toast(`Error: ${e.message}`, 'error');
    }
  }

  function renderList(items) {
    const list = document.getElementById('memoryList');
    if (!items.length) { list.innerHTML = '<div class="empty-state"><div class="empty-icon">🔒</div><p>No memories found.</p></div>'; return; }
    list.innerHTML = items.map(m => {
      const mode = m.mode || 'NONE';
      return `<div class="memory-card" role="listitem">
        <div class="mem-content">${escapeHtml(m.content || m.text || JSON.stringify(m))}</div>
        <div class="mem-meta">
          <span class="mode-badge mode-${mode}">${mode}</span>
          <span>${fmtDate(m.timestamp || m.ts)}</span>
          ${m.id ? `<span style="font-family:monospace;font-size:.68rem">${escapeHtml(String(m.id).slice(0,8))}…</span>` : ''}
        </div>
        <button class="mem-delete-btn" aria-label="Delete memory" onclick="App.memory.deleteOne('${escapeHtml(String(m.id || ''))}')">
          <svg viewBox="0 0 16 16" fill="none" width="14" height="14"><path d="M2 4h12M5 4V3a1 1 0 011-1h4a1 1 0 011 1v1M13 4l-.87 9.13A1 1 0 0111.14 14H4.86a1 1 0 01-.99-.87L3 4" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/></svg>
        </button>
      </div>`;
    }).join('');
  }

  async function deleteOne(id) {
    if (!id) return;
    if (!confirm('Delete this memory entry?')) return;
    try {
      await http.del(`/memory/${encodeURIComponent(getUserId())}/${encodeURIComponent(id)}`);
      toast('Memory deleted', 'success');
      load();
    } catch(e) { toast(`Delete failed: ${e.message}`, 'error'); }
  }

  async function deleteAll() {
    const uid = getUserId();
    if (!confirm(`Delete ALL memories for "${uid}"? This cannot be undone.`)) return;
    try {
      await http.del(`/memory/${encodeURIComponent(uid)}`);
      toast('All memories deleted', 'success');
      _data = [];
      renderList([]);
      document.getElementById('memoryStats').innerHTML = '';
    } catch(e) { toast(`Delete all failed: ${e.message}`, 'error'); }
  }

  function exportData() {
    if (!_data.length) { toast('No data to export — load memories first', 'warning'); return; }
    const blob = new Blob([JSON.stringify(_data, null, 2)], { type: 'application/json' });
    const url  = URL.createObjectURL(blob);
    const a    = document.createElement('a');
    a.href = url; a.download = `memory-export-${getUserId()}.json`;
    document.body.appendChild(a); a.click();
    document.body.removeChild(a); URL.revokeObjectURL(url);
    toast('Memory exported as JSON', 'success');
  }

  return { load, deleteOne, deleteAll, exportData };
})();

/* ================================================================
   REPORTS MODULE
   ================================================================ */
App.reports = (() => {
  const history = [];

  async function generate() {
    const topic = document.getElementById('reportTopic')?.value.trim();
    const type  = document.getElementById('reportType')?.value || 'general';
    if (!topic) { toast('Enter a topic first', 'warning'); return; }

    const resultEl = document.getElementById('reportResult');
    resultEl.innerHTML = '<div class="skeleton-shimmer" style="min-height:120px">Generating report…</div>';
    try {
      const d = await http.post('/report/generate', { topic, report_type: type });
      const sections = d.sections || (typeof d.report === 'string' ? [{ title: 'Report', content: d.report }] : [{ title: 'Result', content: JSON.stringify(d, null, 2) }]);
      resultEl.innerHTML = `<div class="report-result-inner">${sections.map(s => `<div class="report-section"><h3>${escapeHtml(s.title || s.section || 'Section')}</h3><p>${escapeHtml(s.content || s.text || '')}</p></div>`).join('')}</div>`;
      history.unshift({ topic, type, ts: Date.now(), data: d });
      renderHistory();
      toast('Report generated', 'success');
    } catch(e) {
      resultEl.innerHTML = `<div class="empty-state"><div class="empty-icon">❌</div><p style="color:var(--danger)">${escapeHtml(e.message)}</p></div>`;
      toast(`Report error: ${e.message}`, 'error');
    }
  }

  function renderHistory() {
    const box = document.getElementById('reportHistory');
    if (!box) return;
    box.innerHTML = history.slice(0, 8).map((h, i) => `
      <div class="report-history-item" onclick="App.reports.showHistory(${i})">
        <span class="report-topic">${escapeHtml(h.topic)}</span>
        <span class="report-type-badge">${escapeHtml(h.type)}</span>
        <span style="font-size:.7rem;color:var(--text-muted)">${fmtDate(h.ts)}</span>
      </div>`).join('');
  }

  function showHistory(i) {
    const h = history[i];
    if (!h) return;
    const resultEl = document.getElementById('reportResult');
    const sections = h.data.sections || [{ title: 'Report', content: JSON.stringify(h.data, null, 2) }];
    resultEl.innerHTML = `<div class="report-result-inner">${sections.map(s => `<div class="report-section"><h3>${escapeHtml(s.title || 'Section')}</h3><p>${escapeHtml(s.content || s.text || '')}</p></div>`).join('')}</div>`;
  }

  return { generate, showHistory };
})();

/* ================================================================
   ADMIN MODULE
   ================================================================ */
App.admin = (() => {
  async function loadHealth() {
    const el = document.getElementById('healthContent');
    const badge = document.getElementById('healthBadge');
    if (el) el.className = 'skeleton-shimmer';
    try {
      const d = await http.get('/health');
      if (el) {
        el.className = '';
        el.innerHTML = [
          ['Status',    d.status || 'OK'],
          ['Version',   d.version || '—'],
          ['Uptime',    d.uptime ? `${Math.round(d.uptime)}s` : '—'],
          ['Memory OK', d.memory_ok !== false ? '✓' : '✗'],
          ['Search OK', d.search_ok !== false ? '✓' : '✗'],
        ].map(([k,v]) => `<div class="health-row"><span>${escapeHtml(k)}</span><span class="health-val">${escapeHtml(String(v))}</span></div>`).join('');
      }
      if (badge) {
        badge.textContent = d.status === 'ok' || d.status === 'healthy' ? 'Healthy' : 'Degraded';
        badge.className = `health-badge ${d.status === 'ok' || d.status === 'healthy' ? 'healthy' : 'degraded'}`;
      }
    } catch(e) {
      if (el) { el.className = ''; el.innerHTML = `<p style="color:var(--danger)">${escapeHtml(e.message)}</p>`; }
    }
  }

  async function loadStats() {
    const el = document.getElementById('statsContent');
    if (el) el.className = 'skeleton-shimmer';
    try {
      const d = await http.get('/admin/stats');  
      if (el) {
        el.className = '';
        const rows = Object.entries(d).filter(([,v]) => typeof v !== 'object');
        el.innerHTML = rows.map(([k,v]) => `<div class="stat-row"><span>${escapeHtml(k.replace(/_/g,' '))}</span><span class="stat-num">${escapeHtml(String(v))}</span></div>`).join('') || '<p style="color:var(--text-muted)">No stats</p>';
      }
    } catch(e) {
      if (el) { el.className = ''; el.innerHTML = `<p style="color:var(--danger)">${escapeHtml(e.message)}</p>`; }
    }
  }

  async function loadDataset() {
    const el = document.getElementById('datasetContent');
    if (el) el.className = 'skeleton-shimmer';
    try {
      const d = await http.get('/admin/dataset/stats');
      if (el) {
        el.className = '';
        el.innerHTML = Object.entries(d).map(([k,v]) => `<div class="stat-row"><span>${escapeHtml(k.replace(/_/g,' '))}</span><span class="stat-num">${escapeHtml(String(v))}</span></div>`).join('') || '<p style="color:var(--text-muted)">No info</p>';
      }
    } catch(e) {
      if (el) { el.className = ''; el.innerHTML = `<p style="color:var(--text-muted)">Dataset info unavailable</p>`; }
    }
  }

  async function safetyOverride() {
    const actionId = document.getElementById('overrideActionId')?.value.trim();
    const adminId  = document.getElementById('overrideAdminId')?.value.trim();
    const reason   = document.getElementById('overrideReason')?.value.trim();
    if (!actionId || !adminId || !reason || reason.length < 10) {
      toast('Fill all override fields (reason ≥ 10 chars)', 'warning'); return;
    }
    try {
      await http.post('/admin/safety/override', { action_id: actionId, admin_id: adminId, reason });
      toast('Safety override applied', 'success');
    } catch(e) { toast(`Override failed: ${e.message}`, 'error'); }
  }

  async function purgeExpiredMemory() {
    if (!confirm('Purge all expired memory entries?')) return;
    const msg = document.getElementById('maintenanceMsg');
    try {
      const d = await http.del('/admin/memory/expired');
      if (msg) msg.textContent = `Purged ${d.purged_count || 0} expired entries`;
      toast(`Purged ${d.purged_count || 0} entries`, 'success');
    } catch(e) {
      if (msg) msg.style.color = 'var(--danger)';
      if (msg) msg.textContent = e.message;
      toast(`Purge failed: ${e.message}`, 'error');
    }
  }

  return { loadHealth, loadStats, loadDataset, safetyOverride, purgeExpiredMemory };
})();

/* ================================================================
   AUDIT MODULE
   ================================================================ */
App.audit = (() => {
  async function load() {
    const filter = document.getElementById('auditEventFilter')?.value || '';
    const box = document.getElementById('auditList');
    box.innerHTML = '<div class="skeleton-shimmer">Loading audit log…</div>';
    try {
      const path = `/admin/audit?limit=50${filter ? `&event_type=${encodeURIComponent(filter)}` : ''}`;
      const d = await http.get(path);
      const entries = d.entries || d.logs || d || [];
      if (!entries.length) { box.innerHTML = '<div class="empty-state"><div class="empty-icon">🔍</div><p>No audit entries found.</p></div>'; return; }
      box.innerHTML = entries.map(e => {
        const statusCls = e.status === 'ok' ? 'audit-status-ok' : e.status === 'blocked' ? 'audit-status-blocked' : e.status === 'override' ? 'audit-status-override' : 'audit-status-error';
        return `<div class="audit-row">
          <div class="audit-row-header">
            <span class="audit-event-badge">${escapeHtml(e.event_type || e.event || '—')}</span>
            <span class="${statusCls}">${escapeHtml(e.status || '—')}</span>
            ${e.user_id ? `<span style="font-size:.72rem;color:var(--text-muted)">${escapeHtml(String(e.user_id).slice(0,12))}</span>` : ''}
          </div>
          <div class="audit-row-meta">${fmtDate(e.timestamp || e.ts)} ${e.details ? '· ' + escapeHtml(String(e.details).slice(0,80)) : ''}</div>
        </div>`;
      }).join('');
    } catch(e) {
      box.innerHTML = `<div class="empty-state"><p style="color:var(--danger)">${escapeHtml(e.message)}</p></div>`;
      toast(`Audit error: ${e.message}`, 'error');
    }
  }

  async function loadCompliance() {
    const box = document.getElementById('complianceStats');
    try {
      const d = await http.get('/admin/audit/compliance');
      const entries = Object.entries(d).filter(([,v]) => typeof v !== 'object');
      if (box) box.innerHTML = entries.map(([k,v]) => `<div class="compliance-card"><div class="comp-value">${escapeHtml(String(v))}</div><div class="comp-label">${escapeHtml(k.replace(/_/g,' '))}</div></div>`).join('');
    } catch { if (box) box.innerHTML = ''; }
  }

  return { load, loadCompliance };
})();

/* ================================================================
   SIDEBAR / MOBILE
   ================================================================ */
function initSidebar() {
  const sidebar  = document.getElementById('sidebar');
  const menuBtn  = document.getElementById('mobileMenuBtn');
  const collapse = document.getElementById('sidebarToggle');

  // Overlay for mobile
  const overlay = document.createElement('div');
  overlay.className = 'sidebar-overlay';
  document.body.appendChild(overlay);

  function closeSidebar() { sidebar.classList.remove('open'); overlay.classList.remove('active'); menuBtn?.setAttribute('aria-expanded','false'); }
  function openSidebar()  { sidebar.classList.add('open'); overlay.classList.add('active'); menuBtn?.setAttribute('aria-expanded','true'); }

  menuBtn?.addEventListener('click', () => { sidebar.classList.contains('open') ? closeSidebar() : openSidebar(); });
  overlay.addEventListener('click', closeSidebar);
  collapse?.addEventListener('click', closeSidebar);

  document.querySelectorAll('.nav-item').forEach(a => {
    a.addEventListener('click', e => {
      e.preventDefault();
      const section = a.dataset.section;
      window.location.hash = section;
      closeSidebar();
    });
  });
}

/* ================================================================
   HELP PANEL
   ================================================================ */
function initHelp() {
  const panel   = document.getElementById('helpPanel');
  const helpBtn = document.getElementById('helpBtn');
  const close   = document.getElementById('helpClose');
  const dismiss = document.getElementById('helpDismiss');
  const dontShow= document.getElementById('dontShowHelp');

  function showHelp()  { panel?.classList.remove('hidden'); }
  function closeHelp() { panel?.classList.add('hidden'); if (dontShow?.checked) localStorage.setItem('nexus-help-dismissed','1'); }

  helpBtn?.addEventListener('click', showHelp);
  close?.addEventListener('click', closeHelp);
  dismiss?.addEventListener('click', closeHelp);
  panel?.addEventListener('click', e => { if (e.target === panel) closeHelp(); });
  document.addEventListener('keydown', e => { if (e.key === 'Escape' && !panel?.classList.contains('hidden')) closeHelp(); });

  if (!localStorage.getItem('nexus-help-dismissed')) setTimeout(showHelp, 600);
}

/* ================================================================
   BOOT
   ================================================================ */
document.addEventListener('DOMContentLoaded', () => {
  App.chat.init();
  initSidebar();
  initHelp();
  navigate();
  window.addEventListener('hashchange', navigate);
  checkApiStatus();
  setInterval(checkApiStatus, 30000);
});
