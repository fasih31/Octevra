/**
 * Orkavia AI-OS Nexus — Single Page Application
 * © 2026 Fasih ur Rehman. All Rights Reserved.
 *
 * Hash-based SPA router, API client, chat, sensors, memory, admin, audit
 */

// ============================================================
// UTILITIES
// ============================================================
function escapeHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;')
    .replace(/\n/g, '<br>');
}

// ============================================================
// API BASE URL
// ============================================================
const API = window.location.origin;

// ============================================================
// HTTP CLIENT
// ============================================================
const http = {
  async get(path) {
    const r = await fetch(API + path);
    if (!r.ok) throw new Error(`GET ${path} → ${r.status}: ${await r.text()}`);
    return r.json();
  },
  async post(path, body) {
    const r = await fetch(API + path, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (!r.ok) throw new Error(`POST ${path} → ${r.status}: ${await r.text()}`);
    return r.json();
  },
  async del(path) {
    const r = await fetch(API + path, { method: 'DELETE' });
    if (!r.ok) throw new Error(`DELETE ${path} → ${r.status}: ${await r.text()}`);
    return r.json();
  },
};

// ============================================================
// TOAST NOTIFICATIONS
// ============================================================
function toast(msg, type = 'info', duration = 4000) {
  const icons = { success: '✅', error: '❌', warning: '⚠️', info: 'ℹ️' };
  const el = document.createElement('div');
  el.className = `toast ${type}`;
  el.setAttribute('role', 'alert');
  const iconSpan = document.createElement('span');
  iconSpan.textContent = icons[type] || '';
  iconSpan.setAttribute('aria-hidden', 'true');
  const msgSpan = document.createElement('span');
  msgSpan.textContent = String(msg);
  el.appendChild(iconSpan);
  el.appendChild(msgSpan);
  document.getElementById('toastContainer').appendChild(el);
  setTimeout(() => el.remove(), duration);
}

// ============================================================
// ROUTER
// ============================================================
const sections = ['chat', 'memory', 'sensors', 'reports', 'admin', 'audit'];
const sectionTitles = {
  chat: 'Chat',
  memory: 'Memory Vault',
  sensors: 'Sensors',
  reports: 'Reports',
  admin: 'Admin',
  audit: 'Audit',
};

function showSection(name) {
  sections.forEach(s => {
    const el = document.getElementById(`section-${s}`);
    if (el) el.classList.toggle('hidden', s !== name);
  });
  document.querySelectorAll('.nav-item').forEach(a => {
    const isActive = a.dataset.section === name;
    a.classList.toggle('active', isActive);
    a.setAttribute('aria-current', isActive ? 'page' : 'false');
  });
  // Update top bar title
  const titleEl = document.getElementById('topBarTitle');
  if (titleEl) titleEl.textContent = sectionTitles[name] || '';

  if (name === 'admin') { App.admin.loadHealth(); App.admin.loadStats(); App.admin.loadDataset(); }
  if (name === 'sensors') { App.sensors.refresh(); }
}

function handleRoute() {
  const hash = window.location.hash.replace('#', '') || 'chat';
  showSection(sections.includes(hash) ? hash : 'chat');
}

window.addEventListener('hashchange', handleRoute);
document.querySelectorAll('.nav-item').forEach(a => {
  a.addEventListener('click', e => {
    e.preventDefault();
    const sec = a.dataset.section;
    window.location.hash = sec;
    showSection(sec);
    closeMobileMenu();
  });
});

// ============================================================
// MOBILE MENU
// ============================================================
function closeMobileMenu() {
  const sidebar = document.getElementById('sidebar');
  const overlay = document.getElementById('sidebarOverlay');
  const btn = document.getElementById('mobileMenuBtn');
  sidebar.classList.remove('open');
  if (overlay) overlay.classList.remove('active');
  if (btn) btn.setAttribute('aria-expanded', 'false');
}

function openMobileMenu() {
  const sidebar = document.getElementById('sidebar');
  const overlay = document.getElementById('sidebarOverlay');
  const btn = document.getElementById('mobileMenuBtn');
  sidebar.classList.add('open');
  if (overlay) overlay.classList.add('active');
  if (btn) btn.setAttribute('aria-expanded', 'true');
}

// Create overlay element
(function () {
  const overlay = document.createElement('div');
  overlay.id = 'sidebarOverlay';
  overlay.className = 'sidebar-overlay';
  overlay.addEventListener('click', closeMobileMenu);
  document.body.appendChild(overlay);
})();

const mobileMenuBtn = document.getElementById('mobileMenuBtn');
if (mobileMenuBtn) {
  mobileMenuBtn.addEventListener('click', () => {
    const sidebar = document.getElementById('sidebar');
    if (sidebar.classList.contains('open')) {
      closeMobileMenu();
    } else {
      openMobileMenu();
    }
  });
}

// Sidebar toggle (desktop)
const sidebarToggle = document.getElementById('sidebarToggle');
if (sidebarToggle) {
  sidebarToggle.addEventListener('click', () => {
    // On desktop this is handled by CSS transitions; just close mobile if open
    closeMobileMenu();
  });
}

// ============================================================
// HELP / ONBOARDING PANEL
// ============================================================
(function () {
  const panel = document.getElementById('helpPanel');
  const closeBtn = document.getElementById('helpClose');
  const dismissBtn = document.getElementById('helpDismiss');
  const helpBtn = document.getElementById('helpBtn');
  const welcomeHelpBtn = document.getElementById('welcomeHelpBtn');
  const dontShow = document.getElementById('dontShowHelp');

  function openHelp() {
    if (panel) panel.classList.remove('hidden');
  }

  function closeHelp() {
    if (panel) panel.classList.add('hidden');
    if (dontShow && dontShow.checked) {
      try { localStorage.setItem('nexus_help_seen', '1'); } catch (_) { /* ignore */ }
    }
  }

  if (closeBtn)    closeBtn.addEventListener('click', closeHelp);
  if (dismissBtn)  dismissBtn.addEventListener('click', closeHelp);
  if (helpBtn)     helpBtn.addEventListener('click', openHelp);
  if (welcomeHelpBtn) welcomeHelpBtn.addEventListener('click', openHelp);

  // Close on ESC
  document.addEventListener('keydown', e => {
    if (e.key === 'Escape' && panel && !panel.classList.contains('hidden')) {
      closeHelp();
    }
  });

  // Show automatically for first-time users
  let seen = false;
  try { seen = !!localStorage.getItem('nexus_help_seen'); } catch (_) { /* ignore */ }
  if (!seen && panel) panel.classList.remove('hidden');
})();

// ============================================================
// CHAT MODULE
// ============================================================
const Chat = (() => {
  let mode = 'public';
  let sending = false;

  function getMode()    { return mode; }
  function getConsent() { return document.getElementById('memoryConsent').value; }
  function getUserId()  { return document.getElementById('userId').value.trim() || 'anonymous'; }

  // Mode toggle
  document.querySelectorAll('.toggle-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.toggle-btn').forEach(b => {
        b.classList.remove('active');
        b.setAttribute('aria-checked', 'false');
      });
      btn.classList.add('active');
      btn.setAttribute('aria-checked', 'true');
      mode = btn.dataset.value;
    });
  });

  function appendBubble(html, cssClass) {
    const msgs = document.getElementById('chatMessages');
    // Remove welcome message on first message
    const welcome = msgs.querySelector('.welcome-msg');
    if (welcome) welcome.remove();
    const div = document.createElement('div');
    div.className = `chat-bubble ${cssClass}`;
    div.innerHTML = html;
    msgs.appendChild(div);
    msgs.scrollTop = msgs.scrollHeight;
    return div;
  }

  function showTyping() {
    return appendBubble(
      '<div class="typing-dots" aria-label="Thinking…"><span></span><span></span><span></span></div>',
      'bubble-typing'
    );
  }

  function addFeedbackButtons(bubbleEl) {
    const fbDiv = document.createElement('div');
    fbDiv.className = 'bubble-feedback';
    fbDiv.setAttribute('aria-label', 'Rate this response');

    const upBtn = document.createElement('button');
    upBtn.className = 'feedback-btn';
    upBtn.textContent = '👍';
    upBtn.setAttribute('aria-label', 'Thumbs up — helpful response');
    upBtn.addEventListener('click', function () {
      upBtn.classList.add('voted');
      downBtn.disabled = true;
      upBtn.disabled = true;
    });

    const downBtn = document.createElement('button');
    downBtn.className = 'feedback-btn';
    downBtn.textContent = '👎';
    downBtn.setAttribute('aria-label', 'Thumbs down — unhelpful response');
    downBtn.addEventListener('click', function () {
      downBtn.classList.add('voted');
      upBtn.disabled = true;
      downBtn.disabled = true;
    });

    fbDiv.appendChild(upBtn);
    fbDiv.appendChild(downBtn);
    bubbleEl.appendChild(fbDiv);
  }

  async function send() {
    if (sending) return;
    const input = document.getElementById('chatInput');
    const query = input.value.trim();
    if (!query) return;

    input.value = '';
    input.style.height = 'auto';
    sending = true;
    document.getElementById('sendBtn').disabled = true;

    appendBubble(escapeHtml(query), 'bubble-user');
    const typing = showTyping();
    document.getElementById('chatMeta').textContent = '';

    try {
      const res = await http.post('/ask', {
        query,
        user_id: getUserId(),
        mode: getMode(),
        memory_consent: getConsent(),
      });

      typing.remove();
      const sourcesHtml = res.sources && res.sources.length
        ? `<div class="bubble-sources">📚 Sources: ${res.sources.slice(0, 3).map(s => escapeHtml(s.source)).join(', ')}</div>`
        : '';
      const aiBubble = appendBubble(escapeHtml(res.response) + sourcesHtml, 'bubble-ai');
      addFeedbackButtons(aiBubble);

      const memNote = res.memory_stored ? '💾 Memory stored' : '';
      document.getElementById('chatMeta').textContent =
        `⚡ ${res.latency_ms}ms | Mode: ${res.mode} ${memNote}`.trim();

    } catch (err) {
      typing.remove();
      appendBubble(`⚠️ Error: ${escapeHtml(err.message)}`, 'bubble-ai');
      toast(err.message, 'error');
    } finally {
      sending = false;
      document.getElementById('sendBtn').disabled = false;
      input.focus();
    }
  }

  // Events
  document.getElementById('sendBtn').addEventListener('click', send);
  document.getElementById('chatInput').addEventListener('keydown', e => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); }
  });
  document.getElementById('chatInput').addEventListener('input', function () {
    this.style.height = 'auto';
    this.style.height = Math.min(this.scrollHeight, 160) + 'px';
  });

  return { send };
})();

// ============================================================
// MEMORY MODULE
// ============================================================
const Memory = (() => {
  async function load() {
    const userId = document.getElementById('memUserId').value.trim();
    if (!userId) { toast('Enter a User ID first', 'warning'); return; }
    const list = document.getElementById('memoryList');
    list.innerHTML = '<div class="skeleton-loader" style="padding:2rem;text-align:center">⏳ Loading memories…</div>';
    try {
      const data = await http.get(`/memory/${userId}`);
      renderMemories(data, userId);
    } catch (err) {
      list.innerHTML = `<div class="empty-state"><span>❌</span><p>${escapeHtml(err.message)}</p></div>`;
      toast(err.message, 'error');
    }
  }

  function renderMemories(entries, userId) {
    const list = document.getElementById('memoryList');
    const stats = document.getElementById('memoryStats');

    // Stats
    const counts = entries.reduce((acc, e) => { acc[e.mode] = (acc[e.mode] || 0) + 1; return acc; }, {});
    stats.innerHTML = `
      <div class="stat-chip"><div class="stat-value">${entries.length}</div><div class="stat-label">Total</div></div>
      ${Object.entries(counts).map(([m, c]) =>
        `<div class="stat-chip"><div class="stat-value">${c}</div><div class="stat-label">${escapeHtml(m)}</div></div>`
      ).join('')}
    `;

    if (!entries.length) {
      list.innerHTML = '<div class="empty-state"><span>📭</span><p>No memories found for this user.</p></div>';
      return;
    }

    list.innerHTML = entries.map(e => {
      const safeId = escapeHtml(e.id);
      const safeUserId = escapeHtml(userId);
      const safeMode = escapeHtml(e.mode);
      const safeContent = escapeHtml(e.content.substring(0, 300)) + (e.content.length > 300 ? '…' : '');
      const created = new Date(e.created_at * 1000).toLocaleString();
      const expires = e.expires_at
        ? `<span>Expires: ${escapeHtml(new Date(e.expires_at * 1000).toLocaleDateString())}</span>`
        : '';
      return `
      <div class="memory-card" role="listitem">
        <button class="mem-delete-btn" onclick="App.memory.deleteOne('${safeUserId}','${safeId}')" aria-label="Delete this memory">✕</button>
        <div class="mem-content">${safeContent}</div>
        <div class="mem-meta">
          <span class="mode-badge mode-${safeMode}">${safeMode}</span>
          <span>🕐 ${escapeHtml(created)}</span>
          ${expires}
        </div>
      </div>
      `;
    }).join('');
  }

  async function deleteOne(userId, memId) {
    if (!confirm('Delete this memory?')) return;
    try {
      await http.del(`/memory/${userId}/${memId}`);
      toast('Memory deleted', 'success');
      load();
    } catch (err) { toast(err.message, 'error'); }
  }

  async function deleteAll() {
    const userId = document.getElementById('memUserId').value.trim();
    if (!userId) { toast('Enter a User ID first', 'warning'); return; }
    if (!confirm(`Delete ALL memories for ${userId}? This cannot be undone.`)) return;
    try {
      const res = await http.del(`/memory/${userId}`);
      toast(`Deleted ${res.deleted} memories`, 'success');
      load();
    } catch (err) { toast(err.message, 'error'); }
  }

  async function exportData() {
    const userId = document.getElementById('memUserId').value.trim();
    if (!userId) { toast('Enter a User ID first', 'warning'); return; }
    try {
      const data = await http.get(`/memory/${userId}/export`);
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = `nexus-memory-${userId}.json`;
      a.click();
      toast('Export downloaded', 'success');
    } catch (err) { toast(err.message, 'error'); }
  }

  return { load, deleteOne, deleteAll, exportData };
})();

// ============================================================
// SENSORS MODULE
// ============================================================
const Sensors = (() => {
  let autoRefreshTimer = null;

  // Pseudorandom value for non-security demo sensor data simulation only
  function rnd(min, max) { return Math.random() * (max - min) + min; }
  function rndInt(min, max) { return Math.floor(rnd(min, max + 1)); }

  const demoData = {
    irrigation: {
      sensor_id: 'irr-001',
      data: {
        soil_moisture: +rnd(20, 80).toFixed(1),
        temperature: +rnd(18, 38).toFixed(1),
        rain_probability: +rnd(0, 0.8).toFixed(2),
        pressure: +rnd(2, 5).toFixed(2),
        flow_rate: +rnd(8, 28).toFixed(1),
        humidity: +rnd(40, 80).toFixed(1),
        status: 'OK',
      },
      source: 'demo',
    },
    hospital: {
      sensor_id: 'hosp-001',
      data: {
        heart_rate: rndInt(65, 105),
        bp_systolic: rndInt(110, 140),
        bp_diastolic: rndInt(70, 90),
        oxygen: +rnd(96, 100).toFixed(1),
        temperature: +rnd(36.5, 37.5).toFixed(1),
        respiratory_rate: rndInt(14, 20),
        alert_type: 'NORMAL',
      },
      source: 'demo',
    },
    industrial: {
      sensor_id: 'ind-001',
      data: {
        pressure: +rnd(3, 7).toFixed(2),
        temperature: +rnd(50, 80).toFixed(1),
        vibration: +rnd(0.3, 1.8).toFixed(3),
        flow_rate: +rnd(85, 105).toFixed(1),
        rpm: rndInt(2800, 3200),
        status: 'OK',
      },
      source: 'demo',
    },
  };

  async function injectDemo(type) {
    const payload = JSON.parse(JSON.stringify(demoData[type]));
    // Refresh with new non-security pseudorandom demo values each time
    if (type === 'irrigation') {
      payload.data.soil_moisture = +rnd(20, 80).toFixed(1);
      payload.data.temperature   = +rnd(18, 38).toFixed(1);
    } else if (type === 'hospital') {
      payload.data.heart_rate = rndInt(65, 105);
      payload.data.oxygen     = +rnd(96, 100).toFixed(1);
    } else if (type === 'industrial') {
      payload.data.pressure = +rnd(3, 7).toFixed(2);
      payload.data.rpm      = rndInt(2800, 3200);
    }
    try {
      await http.post('/sensor/ingest', payload);
      toast(`${type} sensor data injected ✓`, 'success');
      refresh();
    } catch (err) { toast(err.message, 'error'); }
  }

  async function refresh() {
    try {
      const { sensors } = await http.get('/sensor/');
      if (!sensors.length) {
        document.getElementById('sensorGrid').innerHTML =
          '<div class="empty-state"><span>📡</span><p>No sensor data yet. Click an inject button above.</p></div>';
        return;
      }
      const readings = await Promise.all(
        sensors.map(sid => http.get(`/sensor/${sid}/latest`).catch(() => null))
      );
      renderSensors(readings.filter(Boolean));
    } catch (err) {
      console.error('Sensor refresh error:', err);
    }
  }

  function renderSensors(readings) {
    const grid = document.getElementById('sensorGrid');
    if (!readings.length) {
      grid.innerHTML = '<div class="empty-state"><span>📡</span><p>No sensor readings available.</p></div>';
      return;
    }
    grid.innerHTML = readings.map(r => {
      const status = getSensorStatus(r);
      const fields = Object.entries(r.data).slice(0, 8);
      return `
        <div class="sensor-card status-${status}" role="listitem" aria-label="Sensor ${escapeHtml(r.sensor_id)} — status ${status}">
          <div class="sensor-card-header">
            <span class="sensor-id">📡 ${escapeHtml(r.sensor_id)}</span>
            <span class="sensor-badge ${status}" aria-label="Status: ${status}">${status.toUpperCase()}</span>
          </div>
          <div class="sensor-readings">
            ${fields.map(([k, v]) => `
              <div class="sensor-reading">
                <div class="reading-field">${escapeHtml(k.replace(/_/g, ' '))}</div>
                <div class="reading-value">${formatValue(k, v)}</div>
              </div>
            `).join('')}
          </div>
          <div class="sensor-timestamp">🕐 ${escapeHtml(new Date(r.timestamp * 1000).toLocaleTimeString())}</div>
        </div>
      `;
    }).join('');
  }

  function getSensorStatus(r) {
    const d = r.data;
    if (r.sensor_id.startsWith('hosp')) {
      if (d.oxygen < 90 || d.heart_rate > 150 || d.heart_rate < 40) return 'critical';
      if (d.oxygen < 94 || d.heart_rate > 100) return 'warning';
    } else if (r.sensor_id.startsWith('irr')) {
      if (d.pressure > 8 || d.flow_rate > 50) return 'critical';
      if (d.soil_moisture < 25) return 'warning';
    } else if (r.sensor_id.startsWith('ind')) {
      if (d.pressure > 14 || d.temperature > 140) return 'critical';
      if (d.vibration > 3.0) return 'warning';
    }
    return 'ok';
  }

  function formatValue(key, v) {
    if (typeof v === 'number') {
      if (key.includes('pressure'))      return `${v.toFixed(2)} bar`;
      if (key.includes('temperature'))   return `${v.toFixed(1)}°C`;
      if (key.includes('moisture'))      return `${v.toFixed(1)}%`;
      if (key.includes('humidity'))      return `${v.toFixed(1)}%`;
      if (key.includes('oxygen'))        return `${v.toFixed(1)}%`;
      if (key.includes('probability'))   return `${(v * 100).toFixed(0)}%`;
      if (key.includes('flow_rate'))     return `${v.toFixed(1)} L/m`;
      if (key.includes('vibration'))     return `${v.toFixed(3)} mm/s`;
      if (key.includes('heart'))         return `${v} bpm`;
      if (key.includes('rpm'))           return `${v} rpm`;
      return v.toString();
    }
    return escapeHtml(String(v));
  }

  function toggleAutoRefresh(enabled) {
    if (autoRefreshTimer) { clearInterval(autoRefreshTimer); autoRefreshTimer = null; }
    if (enabled) autoRefreshTimer = setInterval(refresh, 5000);
  }

  return { injectDemo, refresh, toggleAutoRefresh };
})();

// ============================================================
// REPORTS MODULE
// ============================================================
const Reports = (() => {
  const history = [];

  async function generate() {
    const topic = document.getElementById('reportTopic').value.trim();
    const type  = document.getElementById('reportType').value;
    if (!topic) { toast('Enter a report topic', 'warning'); return; }

    const result = document.getElementById('reportResult');
    result.innerHTML = '<div class="skeleton-loader">⏳ Generating report…</div>';
    result.classList.add('visible');

    try {
      const res = await http.post('/report/generate', { topic, report_type: type });
      renderReport(res);
      history.unshift(res);
      renderHistory();
      toast('Report generated ✓', 'success');
    } catch (err) {
      result.innerHTML = `<div style="color:var(--danger)">⚠️ Error: ${escapeHtml(err.message)}</div>`;
      toast(err.message, 'error');
    }
  }

  function renderReport(res) {
    const result = document.getElementById('reportResult');
    result.classList.add('visible');
    result.innerHTML = `
      <h2 class="card-title">📋 ${escapeHtml(res.topic)} <small style="color:var(--text-muted);font-size:0.8rem">[${escapeHtml(res.report_type)}]</small></h2>
      <div style="margin:0.5rem 0 1rem;font-size:0.78rem;color:var(--text-muted)">
        ID: ${escapeHtml(res.report_id)} | ⚡ ${res.latency_ms}ms
      </div>
      ${res.sections.map(s => `
        <div class="report-section">
          <h4>${escapeHtml(s.title)}</h4>
          <p>${escapeHtml(s.content)}</p>
        </div>
      `).join('')}
    `;
  }

  function renderHistory() {
    const el = document.getElementById('reportHistory');
    if (!history.length) return;
    el.innerHTML = '<h2 class="card-title" style="margin-bottom:0.75rem">Recent Reports</h2>' +
      history.slice(0, 10).map(r => `
        <div class="report-item" role="button" tabindex="0" onclick="App.reports.showReport('${escapeHtml(r.report_id)}')"
             onkeydown="if(event.key==='Enter')App.reports.showReport('${escapeHtml(r.report_id)}')">
          <span>📋 ${escapeHtml(r.topic)}</span>
          <span style="font-size:0.78rem;color:var(--text-muted)">${escapeHtml(r.report_type)}</span>
        </div>
      `).join('');
  }

  function showReport(id) {
    const r = history.find(x => x.report_id === id);
    if (r) renderReport(r);
  }

  return { generate, showReport };
})();

// ============================================================
// ADMIN MODULE
// ============================================================
const Admin = (() => {
  async function loadHealth() {
    try {
      const d = await http.get('/admin/health');
      document.getElementById('healthContent').innerHTML = `
        <div class="health-row"><span>Status</span><span class="health-val">${escapeHtml(d.status)}</span></div>
        <div class="health-row"><span>Uptime</span><span class="health-val">${escapeHtml(d.uptime_human)}</span></div>
        <div class="health-row"><span>Version</span><span class="health-val">${escapeHtml(d.version)}</span></div>
        <div class="health-row"><span>Python</span><span class="health-val">${escapeHtml(d.python_version)}</span></div>
        ${Object.entries(d.components).map(([k, v]) =>
          `<div class="health-row"><span>${escapeHtml(k)}</span><span class="health-val ${v !== 'ok' ? 'warn' : ''}">${escapeHtml(v)}</span></div>`
        ).join('')}
      `;
    } catch (err) {
      document.getElementById('healthContent').innerHTML = `<span style="color:var(--danger)">⚠️ ${escapeHtml(err.message)}</span>`;
    }
  }

  async function loadStats() {
    try {
      const d = await http.get('/admin/stats');
      const s = d.sensors;
      document.getElementById('statsContent').innerHTML = `
        <div class="stat-row"><span>Sensor Readings</span><span class="stat-num">${s.total_readings}</span></div>
        <div class="stat-row"><span>Active Sensors</span><span class="stat-num">${s.sensor_count}</span></div>
        <div class="stat-row"><span>Triggers</span><span class="stat-num">${s.trigger_count}</span></div>
        <div class="stat-row"><span>Safety Overrides</span><span class="stat-num">${d.safety_overrides}</span></div>
      `;
    } catch (err) {
      document.getElementById('statsContent').innerHTML = `<span style="color:var(--danger)">⚠️ ${escapeHtml(err.message)}</span>`;
    }
  }

  async function loadDataset() {
    try {
      const d = await http.get('/admin/dataset/stats');
      const cats = Object.entries(d.by_category || {});
      document.getElementById('datasetContent').innerHTML = `
        <div class="stat-row"><span>Total Entries</span><span class="stat-num">${d.total_entries}</span></div>
        ${cats.map(([c, n]) =>
          `<div class="stat-row"><span>${escapeHtml(c)}</span><span class="stat-num">${n}</span></div>`
        ).join('')}
      `;
    } catch (err) {
      document.getElementById('datasetContent').innerHTML = `<span style="color:var(--danger)">⚠️ ${escapeHtml(err.message)}</span>`;
    }
  }

  async function safetyOverride() {
    const actionId = document.getElementById('overrideActionId').value.trim();
    const adminId  = document.getElementById('overrideAdminId').value.trim();
    const reason   = document.getElementById('overrideReason').value.trim();
    if (!actionId || !reason) { toast('Fill in Action ID and Reason', 'warning'); return; }
    if (reason.length < 10) { toast('Reason must be at least 10 characters', 'warning'); return; }
    try {
      const res = await http.post('/admin/safety/override', { action_id: actionId, admin_id: adminId, reason });
      toast(`Override applied for ${escapeHtml(res.action_id)}`, 'success');
    } catch (err) { toast(err.message, 'error'); }
  }

  async function purgeExpiredMemory() {
    try {
      const res = await http.del('/admin/memory/expired');
      document.getElementById('maintenanceMsg').textContent = `✅ Purged ${res.deleted} expired memories`;
      toast(`Purged ${res.deleted} expired memories`, 'success');
    } catch (err) { toast(err.message, 'error'); }
  }

  return { loadHealth, loadStats, loadDataset, safetyOverride, purgeExpiredMemory };
})();

// ============================================================
// AUDIT MODULE
// ============================================================
const Audit = (() => {
  async function load() {
    const eventFilter = document.getElementById('auditEventFilter').value;
    const listEl = document.getElementById('auditList');
    listEl.innerHTML = '<div class="skeleton-loader" style="padding:2rem;text-align:center">⏳ Loading audit log…</div>';
    try {
      const path = eventFilter
        ? `/admin/audit?limit=100&event=${encodeURIComponent(eventFilter)}`
        : '/admin/audit?limit=100';
      const data = await http.get(path);
      renderAuditList(data.records);
      toast(`Loaded ${data.count} audit records`, 'info');
    } catch (err) {
      listEl.innerHTML = `<div class="empty-state"><span>❌</span><p>${escapeHtml(err.message)}</p></div>`;
      toast(err.message, 'error');
    }
  }

  async function loadCompliance() {
    const statsEl = document.getElementById('complianceStats');
    statsEl.innerHTML = '<div class="skeleton-loader" style="padding:1rem;text-align:center">⏳ Loading compliance stats…</div>';
    try {
      const data = await http.get('/admin/audit/compliance');
      renderComplianceStats(data);
    } catch (err) {
      statsEl.innerHTML = `<div class="empty-state"><span>❌</span><p>${escapeHtml(err.message)}</p></div>`;
      toast(err.message, 'error');
    }
  }

  function renderComplianceStats(data) {
    const statsEl = document.getElementById('complianceStats');
    statsEl.innerHTML = `
      <div class="compliance-card">
        <div class="comp-value">${data.total_events}</div>
        <div class="comp-label">Total Events</div>
      </div>
      <div class="compliance-card">
        <div class="comp-value">${data.events_last_24h}</div>
        <div class="comp-label">Last 24h</div>
      </div>
      ${Object.entries(data.by_event || {}).slice(0, 4).map(([ev, cnt]) => `
        <div class="compliance-card">
          <div class="comp-value">${cnt}</div>
          <div class="comp-label">${escapeHtml(ev)}</div>
        </div>
      `).join('')}
    `;
  }

  function renderAuditList(records) {
    const listEl = document.getElementById('auditList');
    if (!records.length) {
      listEl.innerHTML = '<div class="empty-state"><span>🔍</span><p>No audit records found.</p></div>';
      return;
    }
    listEl.innerHTML = records.map(r => {
      const ts = new Date(r.timestamp * 1000).toLocaleString();
      const statusClass = `audit-status-${(r.status || 'ok').replace(/[^a-z]/g, '')}`;
      return `
        <div class="audit-row" role="listitem">
          <div class="audit-row-header">
            <span class="audit-event-badge">${escapeHtml(r.event)}</span>
            <span class="${statusClass}">●  ${escapeHtml(r.status)}</span>
            <span style="font-size:0.78rem;color:var(--text-dim)">actor: ${escapeHtml(r.actor)}</span>
            ${r.target ? `<span style="font-size:0.78rem;color:var(--text-dim)">target: ${escapeHtml(r.target.substring(0, 32))}</span>` : ''}
          </div>
          <div class="audit-row-meta">🕐 ${escapeHtml(ts)}</div>
        </div>
      `;
    }).join('');
  }

  return { load, loadCompliance };
})();

// ============================================================
// GLOBAL App OBJECT
// ============================================================
const App = {
  chat:    Chat,
  memory:  Memory,
  sensors: Sensors,
  reports: Reports,
  admin:   Admin,
  audit:   Audit,
};

// ============================================================
// HEALTH CHECK & STATUS DOT
// ============================================================
async function checkHealth() {
  const dot  = document.getElementById('statusDot');
  const text = document.getElementById('statusText');
  try {
    await http.get('/admin/health');
    dot.className  = 'status-dot online';
    dot.setAttribute('aria-label', 'Online');
    text.textContent = 'Online';
  } catch {
    dot.className  = 'status-dot offline';
    dot.setAttribute('aria-label', 'Offline');
    text.textContent = 'Offline';
  }
}

// ============================================================
// INIT
// ============================================================
document.addEventListener('DOMContentLoaded', () => {
  handleRoute();
  checkHealth();
  setInterval(checkHealth, 30_000);
});
