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

  let activeTabId = null;
  let activeTabUrl = null;
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

  // ─── Initialize: get active tab and request data ───
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
    requestScanData(activeTabId);
  });

  // ─── Request stored scan data from background ───
  function requestScanData(tabId) {
    setStatus('loading');
    chrome.runtime.sendMessage({ type: 'REQUEST_SCAN', tabId: String(tabId) }, (response) => {
      if (chrome.runtime.lastError) {
        setStatus('error');
        return;
      }
      const data = response?.data;
      if (!data) {
        // No crawl data — page might be blocked by Chrome. Try analyzing the URL directly.
        checkPageUrlDirectly(activeTabUrl);
        return;
      }

      const isAnalyzed = response?.analyzed === true;
      if (isAnalyzed) {
        renderAnalyzedDashboard(data);
        setStatus('ready');
      } else if (data.backend_offline) {
        renderRawDashboard(data);
        setStatus('offline');
      } else {
        renderRawDashboard(data);
        setStatus('no-backend');
      }
    });
  }

  // ─── Render: Analyzed dashboard (with risk scores from backend) ───
  function renderAnalyzedDashboard(data) {
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
    panel.innerHTML = links.map((item, i) => `
      <div class="item-card card-${item.classification}" style="animation-delay:${i * 25}ms">
        <div class="item-header">
          <span class="item-icon">${riskIcon(item.classification)}</span>
          <span class="item-title">${escapeHtml(item.text || '[no text]')}</span>
          ${riskBadge(item.classification, item.risk_score)}
          ${item.blacklisted?.is_blacklisted ? '<span class="badge badge-danger">BLACKLISTED</span>' : ''}
        </div>
        <div class="item-url">${escapeHtml(truncate(item.url, 65))}</div>
      </div>
    `).join('');
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

  function truncate(str, max) {
    return str.length > max ? str.substring(0, max) + '…' : str;
  }

  function emptyState(message) {
    return `<div class="empty-state"><span class="empty-icon">📂</span><p>${message}</p></div>`;
  }
});
