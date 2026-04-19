/**
 * AI-OS Nexus — Single Page Application
 * Hash-based SPA router, API client, chat, sensors, memory, admin
 */

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
  el.innerHTML = `<span>${icons[type] || ''}</span><span>${msg}</span>`;
  document.getElementById('toastContainer').appendChild(el);
  setTimeout(() => el.remove(), duration);
}

// ============================================================
// ROUTER
// ============================================================
const sections = ['chat', 'memory', 'sensors', 'reports', 'admin'];

function showSection(name) {
  sections.forEach(s => {
    const el = document.getElementById(`section-${s}`);
    if (el) el.classList.toggle('hidden', s !== name);
  });
  document.querySelectorAll('.nav-item').forEach(a => {
    a.classList.toggle('active', a.dataset.section === name);
  });
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
  });
});

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
      document.querySelectorAll('.toggle-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
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
      '<div class="typing-dots"><span></span><span></span><span></span></div>',
      'bubble-typing'
    );
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
        ? `<div class="bubble-sources">📚 Sources: ${res.sources.slice(0, 3).map(s => s.source).join(', ')}</div>`
        : '';
      appendBubble(escapeHtml(res.response) + sourcesHtml, 'bubble-ai');

      const memNote = res.memory_stored ? '💾 Memory stored' : '';
      document.getElementById('chatMeta').textContent =
        `⚡ ${res.latency_ms}ms | Mode: ${res.mode} ${memNote}`.trim();

    } catch (err) {
      typing.remove();
      appendBubble(`Error: ${escapeHtml(err.message)}`, 'bubble-ai');
      toast(err.message, 'error');
    } finally {
      sending = false;
      document.getElementById('sendBtn').disabled = false;
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
    try {
      const data = await http.get(`/memory/${userId}`);
      renderMemories(data, userId);
    } catch (err) {
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
        `<div class="stat-chip"><div class="stat-value">${c}</div><div class="stat-label">${m}</div></div>`
      ).join('')}
    `;

    if (!entries.length) {
      list.innerHTML = '<div class="empty-state">No memories found for this user.</div>';
      return;
    }

    list.innerHTML = entries.map(e => `
      <div class="memory-card">
        <button class="mem-delete-btn" onclick="App.memory.deleteOne('${userId}','${e.id}')">✕</button>
        <div class="mem-content">${escapeHtml(e.content.substring(0, 300))}${e.content.length > 300 ? '…' : ''}</div>
        <div class="mem-meta">
          <span class="mode-badge mode-${e.mode}">${e.mode}</span>
          <span>🕐 ${new Date(e.created_at * 1000).toLocaleString()}</span>
          ${e.expires_at ? `<span>Expires: ${new Date(e.expires_at * 1000).toLocaleDateString()}</span>` : ''}
        </div>
      </div>
    `).join('');
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

  const demoData = {
    irrigation: {
      sensor_id: 'irr-001',
      data: {
        soil_moisture: +(Math.random() * 60 + 20).toFixed(1),
        temperature: +(Math.random() * 20 + 18).toFixed(1),
        rain_probability: +(Math.random() * 0.8).toFixed(2),
        pressure: +(Math.random() * 3 + 2).toFixed(2),
        flow_rate: +(Math.random() * 20 + 8).toFixed(1),
        humidity: +(Math.random() * 40 + 40).toFixed(1),
        status: 'OK',
      },
      source: 'demo',
    },
    hospital: {
      sensor_id: 'hosp-001',
      data: {
        heart_rate: Math.floor(Math.random() * 40 + 65),
        bp_systolic: Math.floor(Math.random() * 30 + 110),
        bp_diastolic: Math.floor(Math.random() * 20 + 70),
        oxygen: +(Math.random() * 4 + 96).toFixed(1),
        temperature: +(Math.random() * 1 + 36.5).toFixed(1),
        respiratory_rate: Math.floor(Math.random() * 6 + 14),
        alert_type: 'NORMAL',
      },
      source: 'demo',
    },
    industrial: {
      sensor_id: 'ind-001',
      data: {
        pressure: +(Math.random() * 4 + 3).toFixed(2),
        temperature: +(Math.random() * 30 + 50).toFixed(1),
        vibration: +(Math.random() * 1.5 + 0.3).toFixed(3),
        flow_rate: +(Math.random() * 20 + 85).toFixed(1),
        rpm: Math.floor(Math.random() * 400 + 2800),
        status: 'OK',
      },
      source: 'demo',
    },
  };

  async function injectDemo(type) {
    const payload = JSON.parse(JSON.stringify(demoData[type]));
    // Refresh values each time
    if (type === 'irrigation') {
      payload.data.soil_moisture = +(Math.random() * 60 + 20).toFixed(1);
      payload.data.temperature   = +(Math.random() * 20 + 18).toFixed(1);
    } else if (type === 'hospital') {
      payload.data.heart_rate = Math.floor(Math.random() * 40 + 65);
      payload.data.oxygen     = +(Math.random() * 4 + 96).toFixed(1);
    } else if (type === 'industrial') {
      payload.data.pressure = +(Math.random() * 4 + 3).toFixed(2);
      payload.data.rpm      = Math.floor(Math.random() * 400 + 2800);
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
          '<div class="empty-state">No sensor data yet. Click an inject button above.</div>';
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
      grid.innerHTML = '<div class="empty-state">No sensor readings available.</div>';
      return;
    }
    grid.innerHTML = readings.map(r => {
      const status = getSensorStatus(r);
      const fields = Object.entries(r.data).slice(0, 8);
      return `
        <div class="sensor-card status-${status}">
          <div class="sensor-card-header">
            <span class="sensor-id">📡 ${escapeHtml(r.sensor_id)}</span>
            <span class="sensor-badge ${status}">${status.toUpperCase()}</span>
          </div>
          <div class="sensor-readings">
            ${fields.map(([k, v]) => `
              <div class="sensor-reading">
                <div class="reading-field">${escapeHtml(k.replace(/_/g, ' '))}</div>
                <div class="reading-value">${formatValue(k, v)}</div>
              </div>
            `).join('')}
          </div>
          <div class="sensor-timestamp">🕐 ${new Date(r.timestamp * 1000).toLocaleTimeString()}</div>
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
      result.innerHTML = `<div style="color:var(--danger)">Error: ${escapeHtml(err.message)}</div>`;
      toast(err.message, 'error');
    }
  }

  function renderReport(res) {
    const result = document.getElementById('reportResult');
    result.classList.add('visible');
    result.innerHTML = `
      <h3>📋 ${escapeHtml(res.topic)} <small style="color:var(--text-muted);font-size:0.8rem">[${res.report_type}]</small></h3>
      <div style="margin:0.5rem 0 1rem;font-size:0.78rem;color:var(--text-muted)">
        ID: ${res.report_id} | ⚡ ${res.latency_ms}ms
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
    el.innerHTML = '<h3 style="margin-bottom:0.75rem">Recent Reports</h3>' +
      history.slice(0, 10).map(r => `
        <div class="report-item" onclick="App.reports.showReport('${r.report_id}')">
          <span>📋 ${escapeHtml(r.topic)}</span>
          <span style="font-size:0.78rem;color:var(--text-muted)">${r.report_type}</span>
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
        <div class="health-row"><span>Status</span><span class="health-val">${d.status}</span></div>
        <div class="health-row"><span>Uptime</span><span class="health-val">${d.uptime_human}</span></div>
        <div class="health-row"><span>Version</span><span class="health-val">${d.version}</span></div>
        <div class="health-row"><span>Python</span><span class="health-val">${d.python_version}</span></div>
        ${Object.entries(d.components).map(([k, v]) =>
          `<div class="health-row"><span>${k}</span><span class="health-val ${v !== 'ok' ? 'warn' : ''}">${v}</span></div>`
        ).join('')}
      `;
    } catch (err) {
      document.getElementById('healthContent').innerHTML = `<span style="color:var(--danger)">Error: ${err.message}</span>`;
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
      document.getElementById('statsContent').innerHTML = `<span style="color:var(--danger)">${err.message}</span>`;
    }
  }

  async function loadDataset() {
    try {
      const d = await http.get('/admin/dataset/stats');
      const cats = Object.entries(d.by_category || {});
      document.getElementById('datasetContent').innerHTML = `
        <div class="stat-row"><span>Total Entries</span><span class="stat-num">${d.total_entries}</span></div>
        ${cats.map(([c, n]) =>
          `<div class="stat-row"><span>${c}</span><span class="stat-num">${n}</span></div>`
        ).join('')}
      `;
    } catch (err) {
      document.getElementById('datasetContent').innerHTML = `<span style="color:var(--danger)">${err.message}</span>`;
    }
  }

  async function safetyOverride() {
    const actionId = document.getElementById('overrideActionId').value.trim();
    const adminId  = document.getElementById('overrideAdminId').value.trim();
    const reason   = document.getElementById('overrideReason').value.trim();
    if (!actionId || !reason) { toast('Fill in Action ID and Reason', 'warning'); return; }
    try {
      const res = await http.post('/admin/safety/override', { action_id: actionId, admin_id: adminId, reason });
      toast(`Override applied for ${res.action_id}`, 'success');
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
// GLOBAL App OBJECT
// ============================================================
const App = {
  chat:    Chat,
  memory:  Memory,
  sensors: Sensors,
  reports: Reports,
  admin:   Admin,
};

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
// HEALTH CHECK & STATUS DOT
// ============================================================
async function checkHealth() {
  const dot  = document.getElementById('statusDot');
  const text = document.getElementById('statusText');
  try {
    await http.get('/admin/health');
    dot.className  = 'status-dot online';
    text.textContent = 'Online';
  } catch {
    dot.className  = 'status-dot offline';
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
