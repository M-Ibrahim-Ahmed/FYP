// popup.js — ScamShield Dashboard Controller
// Handles tab switching, data rendering with risk classification, and scan actions.

'use strict';

document.addEventListener('DOMContentLoaded', () => {
  // ─── Element references ───
  const statusEl      = document.getElementById('status');
  const scanBtn       = document.getElementById('scanBtn');
  const tabBtns       = document.querySelectorAll('.tab-btn');
  const tabPanels     = document.querySelectorAll('.tab-panel');
  const statLinks     = document.getElementById('stat-links');
  const statForms     = document.getElementById('stat-forms');
  const statImages    = document.getElementById('stat-images');
  const statRedirects = document.getElementById('stat-redirects');
  const statIframes   = document.getElementById('stat-iframes');
  const pageTitleEl   = document.getElementById('page-title');
  const pageUrlEl     = document.getElementById('page-url');
  const riskBanner    = document.getElementById('risk-banner');
  const riskLabel     = document.getElementById('risk-label');
  const riskScore     = document.getElementById('risk-score');
  const riskDetails   = document.getElementById('risk-details');
  const previewOverlay = document.getElementById('preview-overlay');
  const previewClose   = document.getElementById('preview-close');
  const previewUrlEl   = document.getElementById('preview-url');
  const previewBody    = document.getElementById('preview-body');
  const exportBtn      = document.getElementById('exportBtn');

  let activeTabId = null;
  let activeTabUrl = null;
  let currentScanData = null;  // Stores the latest scan data for export
  const BACKEND_URL = 'http://localhost:5000';

  // ─── Tab switching ───
  tabBtns.forEach((btn) => {
    btn.addEventListener('click', () => {
      tabBtns.forEach((b) => b.classList.remove('active'));
      tabPanels.forEach((p) => p.classList.remove('active'));
      btn.classList.add('active');
      const target = btn.dataset.tab;
      document.getElementById(`panel-${target}`).classList.add('active');
    });
  });

  // ─── Safe preview overlay close ───
  previewClose.addEventListener('click', () => {
    previewOverlay.style.display = 'none';
  });

  // ─── Export button ───
  exportBtn.addEventListener('click', () => exportCSV());

  // ─── Tab switching (load history when History tab is clicked) ───
  tabBtns.forEach((btn) => {
    btn.addEventListener('click', () => {
      const tab = btn.dataset.tab;
      tabBtns.forEach((b) => b.classList.remove('active'));
      tabPanels.forEach((p) => p.classList.remove('active'));
      btn.classList.add('active');
      document.getElementById(`panel-${tab}`).classList.add('active');
      if (tab === 'history') loadHistory();
    });
  });

  // ─── Scan button ───
  scanBtn.addEventListener('click', () => {
    if (!activeTabId) return;
    setStatus('scanning');
    chrome.runtime.sendMessage({ type: 'RE_CRAWL', tabId: activeTabId }, (resp) => {
      if (resp?.success) {
        setTimeout(() => requestScanData(activeTabId), 1200);
      } else {
        // Re-crawl failed (page blocked/restricted) — try URL-only check
        checkPageUrlDirectly(activeTabUrl);
      }
    });
  });

  // ─── Initialize: get active tab and auto-scan ───
  let pollTimer = null;
  let pollCount = 0;
  const MAX_POLLS = 15; // Poll up to 30 seconds (15 × 2s)

  chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
    if (!tabs || tabs.length === 0) {
      setStatus('error');
      return;
    }
    activeTabId = tabs[0].id;
    activeTabUrl = tabs[0].url || '';
    pageTitleEl.textContent = tabs[0].title || 'Unknown Page';
    pageUrlEl.textContent = truncate(activeTabUrl, 50);
    pageUrlEl.title = activeTabUrl;

    // Auto-scan: try to load existing data, if not analyzed yet start polling
    requestScanData(activeTabId, true);
  });

  // ─── Request stored scan data from background ───
  function requestScanData(tabId, autoRetry) {
    setStatus('loading');
    chrome.runtime.sendMessage({ type: 'REQUEST_SCAN', tabId: String(tabId) }, (response) => {
      if (chrome.runtime.lastError) {
        setStatus('error');
        return;
      }
      const data = response?.data;

      if (!data) {
        if (autoRetry) {
          // No data yet — trigger a crawl and start polling
          setStatus('scanning');
          chrome.runtime.sendMessage({ type: 'RE_CRAWL', tabId: activeTabId }, () => {
            startPolling();
          });
        } else {
          checkPageUrlDirectly(activeTabUrl);
        }
        return;
      }

      const isAnalyzed = response?.analyzed === true;
      if (isAnalyzed) {
        stopPolling();
        renderAnalyzedDashboard(data);
        setStatus('ready');
      } else if (data.backend_offline) {
        stopPolling();
        renderRawDashboard(data);
        setStatus('offline');
      } else {
        // Raw data available but not yet analyzed — show raw and keep polling
        renderRawDashboard(data);
        if (autoRetry && pollCount < MAX_POLLS) {
          setStatus('scanning');
          startPolling();
        } else {
          setStatus('no-backend');
        }
      }
    });
  }

  function startPolling() {
    if (pollTimer) return; // Already polling
    pollTimer = setInterval(() => {
      pollCount++;
      if (pollCount >= MAX_POLLS) {
        stopPolling();
        setStatus('no-backend');
        return;
      }
      requestScanData(activeTabId, false);
    }, 2000);
  }

  function stopPolling() {
    if (pollTimer) {
      clearInterval(pollTimer);
      pollTimer = null;
    }
  }

  // ─── Render: Analyzed dashboard (with risk scores from backend) ───
  function renderAnalyzedDashboard(data) {
    currentScanData = data;  // Store for export
    const summary = data.summary || {};

    // Show risk banner
    showRiskBanner(summary.overall_risk, summary.risk_score, summary);

    // Update stats
    statLinks.textContent     = (data.links || []).length;
    statForms.textContent     = (data.forms || []).length;
    statImages.textContent    = (data.images || []).length;
    statRedirects.textContent = (data.redirects || []).length;
    statIframes.textContent   = (data.iframes || []).length;

    // Render each panel with classification
    renderAnalyzedLinks(data.links || []);
    renderAnalyzedForms(data.forms || []);
    renderAnalyzedImages(data.images || []);
    renderAnalyzedRedirects(data.redirects || []);
    renderAnalyzedIframes(data.iframes || []);
  }

  // ─── Render: Raw dashboard (no backend, Phase 1 style) ───
  function renderRawDashboard(data) {
    hideRiskBanner();

    statLinks.textContent     = data.counts?.links ?? (data.links || []).length;
    statForms.textContent     = data.counts?.forms ?? (data.forms || []).length;
    statImages.textContent    = data.counts?.images ?? (data.images || []).length;
    statRedirects.textContent = (data.counts?.metaRedirects ?? 0) + (data.counts?.jsRedirects ?? 0);
    statIframes.textContent   = data.counts?.iframes ?? (data.iframes || []).length;

    renderRawLinks(data.links || []);
    renderRawForms(data.forms || []);
    renderRawImages(data.images || []);
    renderRawRedirects(data.metaRedirects || [], data.jsRedirects || []);
    renderRawIframes(data.iframes || []);
  }

  // ═══ ANALYZED RENDERERS (with risk classification) ═══

  function renderAnalyzedLinks(links) {
    const panel = document.getElementById('panel-links');
    if (links.length === 0) { panel.innerHTML = emptyState('No links found.'); return; }

    // Separate external and same-site links
    const external = links.filter((l) => l.external !== false);
    const sameSite = links.filter((l) => l.external === false);

    let html = '';

    // External links first (with full risk analysis)
    if (external.length > 0) {
      html += `<div class="item-meta" style="padding:6px 0 4px; color: var(--text-muted); font-size:10px; text-transform:uppercase; letter-spacing:0.5px;">🌐 External Links (${external.length})</div>`;
      html += external.map((item, i) => `
        <div class="item-card card-${item.classification}" style="animation-delay:${i * 25}ms">
          <div class="item-header">
            <span class="item-icon">${riskIcon(item.classification)}</span>
            <span class="item-title">${escapeHtml(item.text || '[no text]')}</span>
            ${riskBadge(item.classification, item.risk_score)}
            ${item.blacklisted?.is_blacklisted ? '<span class="badge badge-danger">BLACKLISTED</span>' : ''}
            ${item.classification !== 'safe' ? `<button class="btn-preview" data-url="${escapeAttr(item.url)}">🔍 Preview</button>` : ''}
          </div>
          <div class="item-url">${escapeHtml(truncate(item.url, 65))}</div>
        </div>
      `).join('');
    }

    // Same-site links (auto-safe, collapsed)
    if (sameSite.length > 0) {
      html += `<div class="item-meta" style="padding:10px 0 4px; color: var(--text-muted); font-size:10px; text-transform:uppercase; letter-spacing:0.5px;">🏠 Same-Site Links (${sameSite.length}) — auto safe</div>`;
      html += sameSite.slice(0, 10).map((item, i) => `
        <div class="item-card card-safe" style="animation-delay:${(external.length + i) * 15}ms; opacity: 0.7">
          <div class="item-header">
            <span class="item-icon">🏠</span>
            <span class="item-title">${escapeHtml(item.text || '[no text]')}</span>
            <span class="badge badge-safe">same-site</span>
          </div>
          <div class="item-url">${escapeHtml(truncate(item.url, 65))}</div>
        </div>
      `).join('');
      if (sameSite.length > 10) {
        html += `<div class="item-meta" style="padding:4px 22px; color:var(--text-muted); font-size:10px;">+ ${sameSite.length - 10} more same-site links (all safe)</div>`;
      }
    }

    panel.innerHTML = html;
    attachPreviewListeners(panel);
  }

  function renderAnalyzedForms(forms) {
    const panel = document.getElementById('panel-forms');
    if (forms.length === 0) { panel.innerHTML = emptyState('No forms found.'); return; }
    panel.innerHTML = forms.map((item, i) => `
      <div class="item-card card-${item.classification}" style="animation-delay:${i * 25}ms">
        <div class="item-header">
          <span class="item-icon">${riskIcon(item.classification)}</span>
          <span class="item-title">${escapeHtml(item.method || 'GET')} Form</span>
          ${riskBadge(item.classification, item.risk_score)}
          ${item.has_sensitive ? '<span class="badge badge-danger">sensitive data</span>' : ''}
        </div>
        <div class="item-url">Action: ${escapeHtml(truncate(item.url, 60))}</div>
        <div class="item-fields">
          ${(item.inputs || []).map((inp) => `<span class="field-tag">${escapeHtml(inp.name || inp.type)}</span>`).join('')}
        </div>
      </div>
    `).join('');
  }

  function renderAnalyzedImages(images) {
    const panel = document.getElementById('panel-images');
    if (images.length === 0) { panel.innerHTML = emptyState('No clickable images found.'); return; }
    panel.innerHTML = images.map((item, i) => `
      <div class="item-card card-${item.classification}" style="animation-delay:${i * 25}ms">
        <div class="item-header">
          <span class="item-icon">${riskIcon(item.classification)}</span>
          <span class="item-title">${escapeHtml(item.alt || 'Image')}</span>
          ${riskBadge(item.classification, item.risk_score)}
        </div>
        <div class="item-url">Links to: ${escapeHtml(truncate(item.url, 60))}</div>
      </div>
    `).join('');
  }

  function renderAnalyzedRedirects(redirects) {
    const panel = document.getElementById('panel-redirects');
    if (redirects.length === 0) { panel.innerHTML = emptyState('No redirects detected.'); return; }
    panel.innerHTML = redirects.map((item, i) => `
      <div class="item-card card-${item.classification}" style="animation-delay:${i * 25}ms">
        <div class="item-header">
          <span class="item-icon">${riskIcon(item.classification)}</span>
          <span class="item-title">${item.redirect_type === 'meta-refresh' ? 'Meta Refresh' : 'JavaScript'} Redirect</span>
          ${riskBadge(item.classification, item.risk_score)}
        </div>
        <div class="item-url">${escapeHtml(truncate(item.url, 65))}</div>
      </div>
    `).join('');
  }

  function renderAnalyzedIframes(iframes) {
    const panel = document.getElementById('panel-iframes');
    if (iframes.length === 0) { panel.innerHTML = emptyState('No iframes found.'); return; }
    panel.innerHTML = iframes.map((item, i) => `
      <div class="item-card card-${item.classification}" style="animation-delay:${i * 25}ms">
        <div class="item-header">
          <span class="item-icon">${riskIcon(item.classification)}</span>
          <span class="item-title">Iframe</span>
          ${riskBadge(item.classification, item.risk_score)}
          ${item.hidden ? '<span class="badge badge-danger">HIDDEN</span>' : ''}
          ${item.sandbox ? '<span class="badge badge-safe">sandboxed</span>' : ''}
        </div>
        <div class="item-url">${escapeHtml(truncate(item.url, 65))}</div>
      </div>
    `).join('');
  }

  // ═══ RAW RENDERERS (fallback when backend is offline) ═══

  function renderRawLinks(links) {
    const panel = document.getElementById('panel-links');
    if (links.length === 0) { panel.innerHTML = emptyState('No links found.'); return; }
    panel.innerHTML = links.map((link, i) => `
      <div class="item-card" style="animation-delay:${i * 25}ms">
        <div class="item-header">
          <span class="item-icon">🔗</span>
          <span class="item-title">${escapeHtml(link.text || '[no text]')}</span>
        </div>
        <div class="item-url">${escapeHtml(truncate(link.href, 65))}</div>
      </div>
    `).join('');
  }

  function renderRawForms(forms) {
    const panel = document.getElementById('panel-forms');
    if (forms.length === 0) { panel.innerHTML = emptyState('No forms found.'); return; }
    panel.innerHTML = forms.map((form, i) => `
      <div class="item-card ${form.hasSensitive ? 'card-warn' : ''}" style="animation-delay:${i * 25}ms">
        <div class="item-header">
          <span class="item-icon">📝</span>
          <span class="item-title">${escapeHtml(form.method || 'GET')} Form</span>
          ${form.hasSensitive ? '<span class="badge badge-danger">sensitive data</span>' : ''}
        </div>
        <div class="item-url">Action: ${escapeHtml(truncate(form.action, 60))}</div>
      </div>
    `).join('');
  }

  function renderRawImages(images) {
    const panel = document.getElementById('panel-images');
    if (images.length === 0) { panel.innerHTML = emptyState('No clickable images found.'); return; }
    panel.innerHTML = images.map((img, i) => `
      <div class="item-card" style="animation-delay:${i * 25}ms">
        <div class="item-header">
          <span class="item-icon">🖼️</span>
          <span class="item-title">${escapeHtml(img.alt || 'Image')}</span>
        </div>
        ${img.destination ? `<div class="item-url">Links to: ${escapeHtml(truncate(img.destination, 60))}</div>` : ''}
      </div>
    `).join('');
  }

  function renderRawRedirects(meta, js) {
    const panel = document.getElementById('panel-redirects');
    const all = [...meta.map(r => ({ ...r, type: 'meta-refresh' })), ...js.map(r => ({ ...r, type: 'js-redirect' }))];
    if (all.length === 0) { panel.innerHTML = emptyState('No redirects detected.'); return; }
    panel.innerHTML = all.map((r, i) => `
      <div class="item-card card-warn" style="animation-delay:${i * 25}ms">
        <div class="item-header">
          <span class="item-icon">↪️</span>
          <span class="item-title">${r.type === 'meta-refresh' ? 'Meta Refresh' : 'JavaScript'} Redirect</span>
        </div>
        <div class="item-url">${escapeHtml(truncate(r.url, 65))}</div>
      </div>
    `).join('');
  }

  function renderRawIframes(iframes) {
    const panel = document.getElementById('panel-iframes');
    if (iframes.length === 0) { panel.innerHTML = emptyState('No iframes found.'); return; }
    panel.innerHTML = iframes.map((frame, i) => `
      <div class="item-card ${frame.hidden ? 'card-danger' : ''}" style="animation-delay:${i * 25}ms">
        <div class="item-header">
          <span class="item-icon">📦</span>
          <span class="item-title">Iframe</span>
          ${frame.hidden ? '<span class="badge badge-danger">HIDDEN</span>' : ''}
        </div>
        <div class="item-url">${escapeHtml(truncate(frame.src, 65))}</div>
      </div>
    `).join('');
  }

  // ═══ RISK BANNER ═══

  function showRiskBanner(overallRisk, score, summary) {
    riskBanner.className = `risk-banner risk-${overallRisk}`;
    riskBanner.style.display = 'flex';

    const labels = { safe: '🛡️ Page is Safe', suspicious: '⚠️ Suspicious Activity', malicious: '🚨 Malicious Content Detected' };
    riskLabel.textContent = labels[overallRisk] || 'Unknown';
    riskScore.textContent = `Risk Score: ${score}/100`;
    riskDetails.textContent = `${summary.safe || 0} safe · ${summary.suspicious || 0} suspicious · ${summary.malicious || 0} malicious`;
  }

  function hideRiskBanner() {
    riskBanner.style.display = 'none';
  }

  // ═══ URL-ONLY DIRECT CHECK (when content script can't run) ═══

  function checkPageUrlDirectly(url) {
    if (!url || url.startsWith('chrome://') || url.startsWith('chrome-extension://') || url === 'about:blank') {
      setStatus('no-data');
      hideRiskBanner();
      return;
    }

    setStatus('scanning');
    fetch(`${BACKEND_URL}/check`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url }),
    })
      .then((res) => {
        if (!res.ok) throw new Error(`Backend ${res.status}`);
        return res.json();
      })
      .then((result) => {
        renderUrlOnlyResult(result);
        setStatus('ready');
      })
      .catch(() => {
        setStatus('no-backend');
        hideRiskBanner();
      });
  }

  function renderUrlOnlyResult(result) {
    // Show risk banner for the page URL itself
    const cls = result.classification || 'safe';
    const score = result.risk_score || 0;
    showRiskBanner(cls, score, { safe: cls === 'safe' ? 1 : 0, suspicious: cls === 'suspicious' ? 1 : 0, malicious: cls === 'malicious' ? 1 : 0 });

    // Update stats (only 1 URL — the page itself)
    statLinks.textContent = '1';
    statForms.textContent = '0';
    statImages.textContent = '0';
    statRedirects.textContent = '0';
    statIframes.textContent = '0';

    // Show the page URL as a single analyzed link in the Links tab
    const panel = document.getElementById('panel-links');
    const isBlacklisted = result.blacklisted?.is_blacklisted;
    const mlInfo = result.ml?.ml_available
      ? `<div class="item-meta">ML confidence: ${(result.ml.ml_confidence * 100).toFixed(1)}% | Phishing probability: ${(result.ml.ml_phishing_probability * 100).toFixed(1)}%</div>`
      : '';

    panel.innerHTML = `
      <div class="item-card card-${cls}" style="animation-delay:0ms">
        <div class="item-header">
          <span class="item-icon">${riskIcon(cls)}</span>
          <span class="item-title">Page URL</span>
          ${riskBadge(cls, score)}
          ${isBlacklisted ? '<span class="badge badge-danger">BLACKLISTED</span>' : ''}
        </div>
        <div class="item-url">${escapeHtml(result.url || activeTabUrl)}</div>
        ${mlInfo}
        <div class="item-meta">Content script could not run on this page (blocked or restricted)</div>
      </div>
    `;

    // Clear other panels
    ['forms', 'images', 'redirects', 'iframes'].forEach((id) => {
      document.getElementById(`panel-${id}`).innerHTML = emptyState('Page was blocked - only URL was analyzed.');
    });
  }

  // ═══ SAFE PREVIEW ═══

  function attachPreviewListeners(container) {
    container.querySelectorAll('.btn-preview').forEach((btn) => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const url = btn.dataset.url;
        if (url) openSafePreview(url);
      });
    });
  }

  function openSafePreview(url) {
    previewOverlay.style.display = 'flex';
    previewUrlEl.textContent = url;
    previewBody.innerHTML = '<div class="empty-state"><span class="empty-icon" style="animation: pulse 1.5s infinite">📸</span><p>Capturing safe screenshot…<br><small>This may take a few seconds</small></p></div>';

    fetch(`${BACKEND_URL}/preview`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url, timeout: 15 }),
    })
      .then((res) => res.json())
      .then((result) => {
        if (result.success && result.screenshot_base64) {
          previewBody.innerHTML = `
            <img src="data:image/png;base64,${result.screenshot_base64}" alt="Safe preview of ${escapeAttr(url)}" class="preview-img" title="Click to expand" />
            <div class="preview-info">
              📄 ${escapeHtml(result.page_title || 'Untitled')}<br>
              🔗 Final URL: ${escapeHtml(truncate(result.final_url || url, 60))}<br>
              ⏱️ Loaded in ${result.load_time || '?'}s
            </div>
          `;
          // Click image to toggle expanded view
          const img = previewBody.querySelector('.preview-img');
          if (img) {
            img.addEventListener('click', () => img.classList.toggle('expanded'));
          }
        } else {
          previewBody.innerHTML = `<div class="preview-error">❌ ${escapeHtml(result.error || 'Failed to capture preview')}</div>
            <div class="preview-info">Make sure the backend server is running.</div>`;
        }
      })
      .catch(() => {
        previewBody.innerHTML = `<div class="preview-error">❌ Could not connect to backend</div>
          <div class="preview-info">Make sure the backend is running on ${BACKEND_URL}</div>`;
      });
  }

  // ═══ HELPERS ═══

  function riskIcon(classification) {
    const icons = { safe: '✅', suspicious: '⚠️', malicious: '🚫' };
    return icons[classification] || '🔗';
  }

  function riskBadge(classification, score) {
    const cls = { safe: 'badge-safe', suspicious: 'badge-warn', malicious: 'badge-danger' };
    return `<span class="badge ${cls[classification] || ''}">${classification} (${score})</span>`;
  }

  function setStatus(state) {
    statusEl.className = `status status-${state}`;
    const messages = {
      loading: '⏳ Loading scan data…',
      scanning: '🔄 Scanning page…',
      ready: '✅ Analysis complete',
      'no-data': '⚠️ No data — click "Scan Page" to start',
      'no-backend': '📡 Backend offline — showing raw data',
      offline: '📡 Backend offline — showing raw data',
      error: '❌ Could not connect to the page',
    };
    statusEl.textContent = messages[state] || '';
  }

  function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }

  function escapeAttr(str) {
    return String(str).replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/'/g, '&#39;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }

  function truncate(str, max) {
    return str.length > max ? str.substring(0, max) + '…' : str;
  }

  function emptyState(message) {
    return `<div class="empty-state"><span class="empty-icon">📂</span><p>${message}</p></div>`;
  }

  // ═══ HISTORY TAB ═══

  function loadHistory() {
    const panel = document.getElementById('panel-history');
    panel.innerHTML = '<div class="empty-state"><span class="empty-icon" style="animation: pulse 1.5s infinite">📊</span><p>Loading history…</p></div>';

    // Fetch stats and history in parallel
    Promise.all([
      fetch(`${BACKEND_URL}/stats`).then((r) => r.json()),
      fetch(`${BACKEND_URL}/history?per_page=10`).then((r) => r.json()),
    ])
      .then(([stats, history]) => {
        let html = '';

        // Stats overview
        if (stats.available) {
          const cls = stats.classifications || {};
          html += `
            <div class="stats-overview">
              <div><div class="stat-big">${stats.total_scans || 0}</div><div class="stat-label-sm">Total Scans</div></div>
              <div><div class="stat-big">${stats.total_urls_analyzed || 0}</div><div class="stat-label-sm">URLs Analyzed</div></div>
              <div><div class="stat-big">${stats.blacklisted_urls || 0}</div><div class="stat-label-sm">Blacklisted</div></div>
            </div>
            <div class="stats-overview">
              <div><div class="stat-big" style="color:var(--safe)">${cls.safe || 0}</div><div class="stat-label-sm">Safe</div></div>
              <div><div class="stat-big" style="color:var(--warning)">${cls.suspicious || 0}</div><div class="stat-label-sm">Suspicious</div></div>
              <div><div class="stat-big" style="color:var(--danger)">${cls.malicious || 0}</div><div class="stat-label-sm">Malicious</div></div>
            </div>
          `;
        }

        // Recent scans
        const scans = history.scans || [];
        if (scans.length === 0) {
          html += '<div class="history-no-data">📂 No scan history yet.<br>Scan some pages to see history here.</div>';
        } else {
          html += '<div class="item-meta" style="padding:4px 0 6px; color:var(--text-muted); font-size:10px; text-transform:uppercase; letter-spacing:0.5px;">Recent Scans</div>';
          scans.forEach((scan) => {
            const s = scan.summary || {};
            const riskClass = s.overall_risk || 'safe';
            const time = scan.scanned_at ? new Date(scan.scanned_at).toLocaleString() : '';
            html += `
              <div class="history-card">
                <div class="history-url">${escapeHtml(truncate(scan.page_url || 'Unknown', 60))}</div>
                <div class="history-time">🕒 ${time}</div>
                <div class="history-stats">
                  <span class="badge badge-safe">✅ ${s.safe || 0} safe</span>
                  <span class="badge badge-warn">⚠️ ${s.suspicious || 0} suspicious</span>
                  <span class="badge badge-danger">🚫 ${s.malicious || 0} malicious</span>
                  ${riskBadge(riskClass, s.risk_score || 0)}
                </div>
              </div>
            `;
          });
          if (history.total > scans.length) {
            html += `<div class="history-no-data">Showing ${scans.length} of ${history.total} scans</div>`;
          }
        }

        panel.innerHTML = html;
      })
      .catch(() => {
        panel.innerHTML = '<div class="history-no-data">❌ Could not load history.<br>Make sure the backend is running.</div>';
      });
  }

  // ═══ EXPORT CSV ═══

  function exportCSV() {
    if (!currentScanData) {
      alert('No scan data to export. Scan a page first.');
      return;
    }

    const rows = [['Category', 'URL', 'Classification', 'Risk Score', 'Blacklisted', 'ML Prediction', 'ML Confidence', 'External']];

    for (const category of ['links', 'forms', 'images', 'redirects', 'iframes']) {
      const items = currentScanData[category] || [];
      items.forEach((item) => {
        rows.push([
          category,
          item.url || '',
          item.classification || 'unknown',
          item.risk_score ?? '',
          item.blacklisted?.is_blacklisted ? 'YES' : 'NO',
          item.ml?.ml_prediction || '',
          item.ml?.ml_confidence ?? '',
          item.external === false ? 'NO' : 'YES',
        ]);
      });
    }

    // Build CSV string
    const csv = rows.map((r) => r.map((v) => `"${String(v).replace(/"/g, '""')}"`).join(',')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);

    // Trigger download
    const a = document.createElement('a');
    a.href = url;
    const hostname = new URL(currentScanData.page_url || 'https://unknown').hostname;
    a.download = `scamshield_report_${hostname}_${Date.now()}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  }
});
