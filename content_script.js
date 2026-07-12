// content_script.js — ScamShield Crawler
// Extracts all interactive elements from the current page and sends them to the background service worker.

(function () {
  'use strict';

  try {
    // ─── Helper: resolve any URL to absolute ───
    const toAbsolute = (url) => {
      if (!url || url.startsWith('javascript:') || url.startsWith('data:') || url === '#') return null;
      try {
        return new URL(url, location.href).href;
      } catch {
        return null;
      }
    };

    // ─── 1) Extract Links (<a> tags) ───
    const pageHost = location.hostname;
    const linkNodes = document.querySelectorAll('a[href]');
    const links = [];
    const seenLinks = new Set();

    // Helper: extract the best visible text for a link element
    const getLinkText = (a) => {
      // 1) Try innerText (visible text)
      let text = (a.innerText || '').trim();

      // 2) If empty/too short, check for heading children (e.g., Google uses <h3> for result titles)
      if (!text || text.length < 2) {
        const heading = a.querySelector('h1, h2, h3, h4, span[class], div[class]');
        if (heading) text = (heading.innerText || '').trim();
      }

      // 3) Try title attribute
      if (!text || text.length < 2) text = (a.getAttribute('title') || '').trim();

      // 4) Try aria-label
      if (!text || text.length < 2) text = (a.getAttribute('aria-label') || '').trim();

      // 5) Try alt text of child images
      if (!text || text.length < 2) {
        const img = a.querySelector('img[alt]');
        if (img) text = (img.alt || '').trim();
      }

      return text.substring(0, 150) || '[no text]';
    };

    // ─── Search Engine Detection ───
    // When on a search engine, ALL links to the engine's own domains are navigation/UI.
    // Only truly external domains are actual search results.
    const searchEnginePatterns = [
      { host: /google\./i, family: /\.google\.|\.google$/i },
      { host: /bing\./i, family: /\.bing\.|\.bing$|\.microsoft\./i },
      { host: /yahoo\./i, family: /\.yahoo\.|\.yahoo$/i },
      { host: /duckduckgo\./i, family: /\.duckduckgo\.|\.duckduckgo$/i },
      { host: /yandex\./i, family: /\.yandex\.|\.yandex$/i },
      { host: /baidu\./i, family: /\.baidu\.|\.baidu$/i },
    ];

    // Check if we're on a search engine page
    const searchEngine = searchEnginePatterns.find((se) => se.host.test(pageHost));
    const isOnSearchEngine = !!searchEngine;

    // Check if a hostname belongs to the search engine's domain family
    const isSearchEngineDomain = (hostname) => {
      if (!searchEngine) return false;
      return searchEngine.family.test(hostname) || searchEngine.host.test(hostname);
    };

    linkNodes.forEach((a) => {
      const href = toAbsolute(a.getAttribute('href'));
      if (!href || seenLinks.has(href)) return;
      seenLinks.add(href);

      const target = a.getAttribute('target') || '';
      let linkHost = pageHost;
      try {
        linkHost = new URL(href).hostname;
      } catch { }

      // Determine external vs same-site
      let external = linkHost !== pageHost || target === '_blank';

      // Determine if this is a navigation/UI link to hide
      let navigation = false;

      if (isOnSearchEngine) {
        // ON A SEARCH ENGINE: any link to the engine's own domain family = navigation
        // e.g., support.google.com, accounts.google.com, maps.google.com, etc.
        if (isSearchEngineDomain(linkHost)) {
          navigation = true;
          external = false; // Don't analyze these at all
        }
      } else {
        // ON A NORMAL PAGE: same-site links and fragment-only links = navigation
        if (!external && (href === location.href || href === location.href + '#')) {
          navigation = true;
        }
      }

      links.push({
        href,
        text: getLinkText(a),
        rel: a.getAttribute('rel') || '',
        target: a.getAttribute('target') || '',
        external,
        navigation,
      });
    });

    // ─── 2) Extract Forms ───
    const formNodes = document.querySelectorAll('form');
    const forms = [];

    formNodes.forEach((f) => {
      const action = toAbsolute(f.getAttribute('action') || '') || location.href;
      const method = (f.getAttribute('method') || 'GET').toUpperCase();
      const inputs = Array.from(f.querySelectorAll('input, textarea, select')).map((el) => ({
        type: el.type || el.tagName.toLowerCase(),
        name: el.name || el.id || '',
      }));
      // Flag forms that collect sensitive data
      const hasSensitive = inputs.some(
        (i) =>
          i.type === 'password' ||
          /email|card|credit|ssn|social/i.test(i.name)
      );
      forms.push({ action, method, inputs, hasSensitive });
    });

    // ─── 3) Extract Clickable Images ───
    const imgNodes = document.querySelectorAll('img');
    const images = [];

    imgNodes.forEach((img) => {
      const src = toAbsolute(img.getAttribute('src'));
      if (!src) return;

      const anchor = img.closest('a');
      const onclickAttr = img.getAttribute('onclick') || (img.parentElement ? img.parentElement.getAttribute('onclick') : null);
      const isClickable = !!anchor || !!onclickAttr;
      if (!isClickable) return; // only track clickable images

      const destination = anchor ? toAbsolute(anchor.getAttribute('href')) : null;
      images.push({
        src,
        alt: (img.alt || '').trim().substring(0, 80),
        clickable: true,
        destination,
        onclick: onclickAttr || null,
      });
    });

    // ─── 4) Meta Refresh Redirects ───
    const metaRedirects = [];
    const metaRefresh = document.querySelector('meta[http-equiv="refresh"]');
    if (metaRefresh) {
      const content = metaRefresh.getAttribute('content') || '';
      const match = content.match(/url\s*=\s*['"]?([^'";\s]+)/i);
      if (match && match[1]) {
        const url = toAbsolute(match[1]);
        if (url) metaRedirects.push({ type: 'meta-refresh', url });
      }
    }

    // ─── 5) JS-Based Redirects (best-effort static scan) ───
    const jsRedirects = [];
    const inlineScripts = document.querySelectorAll('script:not([src])');
    const redirectPatterns = [
      /window\.location\s*=\s*['"]([^'"]+)['"]/g,
      /window\.location\.href\s*=\s*['"]([^'"]+)['"]/g,
      /window\.location\.replace\s*\(\s*['"]([^'"]+)['"]\s*\)/g,
      /document\.location\s*=\s*['"]([^'"]+)['"]/g,
    ];
    inlineScripts.forEach((script) => {
      const code = script.textContent || '';
      redirectPatterns.forEach((pattern) => {
        let m;
        const re = new RegExp(pattern.source, pattern.flags);
        while ((m = re.exec(code)) !== null) {
          const url = toAbsolute(m[1]);
          if (url) jsRedirects.push({ type: 'js-redirect', url });
        }
      });
    });

    // ─── 6) Extract Iframes ───
    const iframeNodes = document.querySelectorAll('iframe');
    const iframes = [];

    iframeNodes.forEach((frame) => {
      const src = toAbsolute(frame.getAttribute('src'));
      if (!src) return;
      iframes.push({
        src,
        sandbox: frame.getAttribute('sandbox') || null,
        width: frame.width || frame.style.width || 'auto',
        height: frame.height || frame.style.height || 'auto',
        hidden: frame.hidden || frame.style.display === 'none' || (parseInt(frame.width) === 0 || parseInt(frame.height) === 0),
      });
    });

    // ─── Build the crawl result payload ───
    const crawlResult = {
      pageUrl: location.href,
      pageTitle: document.title || '',
      timestamp: new Date().toISOString(),
      counts: {
        links: links.length,
        forms: forms.length,
        images: images.length,
        metaRedirects: metaRedirects.length,
        jsRedirects: jsRedirects.length,
        iframes: iframes.length,
      },
      links,
      forms,
      images,
      metaRedirects,
      jsRedirects,
      iframes,
    };

    // ─── Send to background service worker ───
    chrome.runtime.sendMessage({ type: 'PAGE_CRAWL', payload: crawlResult });

    // ─── Listen for scan results to show in-page visual indicators ───
    chrome.runtime.onMessage.addListener((msg) => {
      if (msg.type !== 'SCAN_RESULT' || !msg.payload) return;

      const data = msg.payload;
      const summary = data.summary || {};
      const risk = summary.overall_risk || 'safe';
      const score = summary.risk_score || 0;

      // Build a lookup map: URL -> scan result
      const urlRiskMap = {};
      const allLinks = data.links || [];
      allLinks.forEach((item) => {
        if (!item.navigation) urlRiskMap[item.url] = item;
      });

      // Inject CSS for visual indicators + modal (only once)
      if (!document.getElementById('scamshield-injected-css')) {
        const style = document.createElement('style');
        style.id = 'scamshield-injected-css';
        style.textContent = `
          /* ── Floating Badge ── */
          #scamshield-badge {
            position: fixed; bottom: 20px; right: 20px; z-index: 2147483647;
            font-family: 'Segoe UI', system-ui, sans-serif;
            border-radius: 12px; padding: 10px 16px; color: #fff;
            font-size: 13px; font-weight: 600;
            display: flex; align-items: center; gap: 8px; cursor: pointer;
            box-shadow: 0 4px 20px rgba(0,0,0,0.3);
            transition: all 0.3s ease; opacity: 0; transform: translateY(20px);
            animation: ss-slidein 0.5s ease 0.5s forwards;
          }
          #scamshield-badge:hover { transform: translateY(-2px) scale(1.02); }
          #scamshield-badge.ss-safe { background: linear-gradient(135deg, #059669, #10b981); }
          #scamshield-badge.ss-suspicious { background: linear-gradient(135deg, #d97706, #f59e0b); }
          #scamshield-badge.ss-malicious { background: linear-gradient(135deg, #dc2626, #ef4444); }
          #scamshield-badge .ss-icon { font-size: 18px; }
          #scamshield-badge .ss-info { display: flex; flex-direction: column; line-height: 1.3; }
          #scamshield-badge .ss-label { font-size: 11px; opacity: 0.85; font-weight: 400; }
          #scamshield-badge .ss-close { margin-left: 6px; opacity: 0.6; font-size: 16px; }
          #scamshield-badge .ss-close:hover { opacity: 1; }
          @keyframes ss-slidein { to { opacity: 1; transform: translateY(0); } }

          /* ── Link Highlights ── */
          a.scamshield-suspicious { outline: 2px solid #f59e0b !important; outline-offset: 2px; border-radius: 3px; }
          a.scamshield-malicious { outline: 2px solid #ef4444 !important; outline-offset: 2px; border-radius: 3px; }

          /* ── Click Interception Modal ── */
          #ss-modal-overlay {
            position: fixed; inset: 0; z-index: 2147483647;
            background: rgba(0,0,0,0.7); backdrop-filter: blur(4px);
            display: flex; align-items: center; justify-content: center;
            animation: ss-fadein 0.2s ease;
          }
          @keyframes ss-fadein { from { opacity: 0; } to { opacity: 1; } }
          #ss-modal {
            background: #1a1a2e; border-radius: 16px; padding: 24px;
            width: 420px; max-width: 92vw; max-height: 85vh; overflow-y: auto;
            color: #e2e8f0; font-family: 'Segoe UI', system-ui, sans-serif;
            box-shadow: 0 20px 60px rgba(0,0,0,0.5);
            border: 1px solid rgba(255,255,255,0.1);
          }
          #ss-modal .ss-modal-header {
            display: flex; align-items: center; gap: 10px; margin-bottom: 16px;
          }
          #ss-modal .ss-modal-header .ss-shield { font-size: 28px; }
          #ss-modal .ss-modal-header h3 { margin: 0; font-size: 16px; font-weight: 700; }
          #ss-modal .ss-risk-banner {
            padding: 12px 16px; border-radius: 10px; margin-bottom: 14px;
            display: flex; align-items: center; gap: 10px; font-weight: 600;
          }
          #ss-modal .ss-risk-banner.ss-r-safe { background: rgba(16,185,129,0.15); border: 1px solid #10b981; color: #6ee7b7; }
          #ss-modal .ss-risk-banner.ss-r-suspicious { background: rgba(245,158,11,0.15); border: 1px solid #f59e0b; color: #fcd34d; }
          #ss-modal .ss-risk-banner.ss-r-malicious { background: rgba(239,68,68,0.15); border: 1px solid #ef4444; color: #fca5a5; }
          #ss-modal .ss-risk-banner .ss-risk-icon { font-size: 22px; }
          #ss-modal .ss-risk-banner .ss-risk-score { margin-left: auto; font-size: 12px; opacity: 0.8; }
          #ss-modal .ss-url-box {
            background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1);
            border-radius: 8px; padding: 10px 12px; margin-bottom: 14px;
            font-size: 12px; word-break: break-all; color: #94a3b8;
          }
          #ss-modal .ss-preview-area {
            background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08);
            border-radius: 10px; padding: 12px; margin-bottom: 16px; text-align: center;
            min-height: 60px;
          }
          #ss-modal .ss-preview-area img {
            max-width: 100%; border-radius: 6px; margin-top: 8px;
          }
          #ss-modal .ss-actions {
            display: flex; gap: 10px; justify-content: flex-end;
          }
          #ss-modal .ss-btn {
            padding: 9px 20px; border-radius: 8px; border: none;
            font-size: 13px; font-weight: 600; cursor: pointer;
            transition: all 0.2s ease;
          }
          #ss-modal .ss-btn:hover { transform: translateY(-1px); }
          #ss-modal .ss-btn-back {
            background: rgba(255,255,255,0.1); color: #e2e8f0;
            border: 1px solid rgba(255,255,255,0.2);
          }
          #ss-modal .ss-btn-proceed-safe { background: #10b981; color: #fff; }
          #ss-modal .ss-btn-proceed-warn { background: #f59e0b; color: #1a1a2e; }
          #ss-modal .ss-btn-proceed-danger { background: #ef4444; color: #fff; }
          #ss-modal .ss-btn-preview {
            background: rgba(99,102,241,0.2); color: #a5b4fc;
            border: 1px solid rgba(99,102,241,0.3);
          }
        `;
        document.head.appendChild(style);
      }

      // ── Floating Badge ──
      const oldBadge = document.getElementById('scamshield-badge');
      if (oldBadge) oldBadge.remove();

      const riskConfig = {
        safe: { icon: '\u2705', label: 'Page Safe', cls: 'ss-safe' },
        suspicious: { icon: '\u26a0\ufe0f', label: 'Suspicious Activity', cls: 'ss-suspicious' },
        malicious: { icon: '\ud83d\udeab', label: 'DANGER - Malicious!', cls: 'ss-malicious' },
      };
      const cfg = riskConfig[risk] || riskConfig.safe;
      const threats = (summary.suspicious || 0) + (summary.malicious || 0);
      const subtitle = threats > 0
        ? `${threats} threat${threats > 1 ? 's' : ''} found (Score: ${score})`
        : `All clear (Score: ${score})`;

      const badge = document.createElement('div');
      badge.id = 'scamshield-badge';
      badge.className = cfg.cls;
      badge.innerHTML = `
        <span class="ss-icon">${cfg.icon}</span>
        <span class="ss-info">
          <span>ScamShield: ${cfg.label}</span>
          <span class="ss-label">${subtitle}</span>
        </span>
        <span class="ss-close" title="Dismiss">&times;</span>
      `;
      document.body.appendChild(badge);

      badge.querySelector('.ss-close').addEventListener('click', (e) => {
        e.stopPropagation();
        badge.style.opacity = '0';
        badge.style.transform = 'translateY(20px)';
        setTimeout(() => badge.remove(), 300);
      });

      if (risk === 'safe') {
        setTimeout(() => {
          if (badge.parentNode) {
            badge.style.opacity = '0';
            badge.style.transform = 'translateY(20px)';
            setTimeout(() => badge.remove(), 300);
          }
        }, 8000);
      }

      // ── Highlight + Click Interception on Links ──
      allLinks.forEach((item) => {
        if (item.navigation) return;

        // Find matching anchors on the page
        const matchAnchors = (selector) => {
          try { return Array.from(document.querySelectorAll(selector)); } catch { return []; }
        };

        let anchors = matchAnchors(`a[href="${CSS.escape(item.url)}"]`);
        if (anchors.length === 0) {
          // Fallback: match by full origin + pathname (not just hostname)
          // This prevents prise.academy/#services from matching app.prise.academy/login
          try {
            const u = new URL(item.url);
            const fullPath = CSS.escape(u.origin + u.pathname);
            anchors = matchAnchors(`a[href*="${fullPath}"]`);
          } catch { }
        }

        anchors.forEach((a) => {
          // Visual highlight for non-safe links
          if (item.classification !== 'safe') {
            a.classList.add(`scamshield-${item.classification}`);
          }
          a.title = `ScamShield: ${item.classification.toUpperCase()} (Risk: ${item.risk_score})`;

          // Attach click interceptor (only once per anchor)
          if (a.dataset.ssIntercepted) return;
          a.dataset.ssIntercepted = 'true';

          a.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            // Use the anchor's ACTUAL href, not the pre-matched scan result URL
            const actualUrl = a.href || item.url;
            // Look up scan data for this actual URL, fallback to the matched item
            const actualData = urlRiskMap[actualUrl] || item;
            showInterceptModal(actualUrl, actualData);
          });
        });
      });

      // ── Modal Function ──
      function showInterceptModal(url, itemData) {
        // Remove existing modal
        const old = document.getElementById('ss-modal-overlay');
        if (old) old.remove();

        const cls = itemData?.classification || 'safe';
        const scoreVal = itemData?.risk_score ?? 0;
        const rCfg = {
          safe: { icon: '\u2705', label: 'Safe', bannerCls: 'ss-r-safe', btnCls: 'ss-btn-proceed-safe', msg: 'This link appears to be safe.' },
          suspicious: { icon: '\u26a0\ufe0f', label: 'Suspicious', bannerCls: 'ss-r-suspicious', btnCls: 'ss-btn-proceed-warn', msg: 'This link has suspicious characteristics. Proceed with caution.' },
          malicious: { icon: '\ud83d\udeab', label: 'MALICIOUS', bannerCls: 'ss-r-malicious', btnCls: 'ss-btn-proceed-danger', msg: 'This link is likely dangerous! We strongly advise NOT visiting it.' },
        };
        const rc = rCfg[cls] || rCfg.safe;

        const overlay = document.createElement('div');
        overlay.id = 'ss-modal-overlay';
        overlay.innerHTML = `
          <div id="ss-modal">
            <div class="ss-modal-header">
              <span class="ss-shield">\ud83d\udee1\ufe0f</span>
              <h3>ScamShield Link Check</h3>
            </div>
            <div class="ss-risk-banner ${rc.bannerCls}">
              <span class="ss-risk-icon">${rc.icon}</span>
              <span>${rc.label}</span>
              <span class="ss-risk-score">Risk Score: ${scoreVal}</span>
            </div>
            <div class="ss-url-box">${url}</div>
            <p style="font-size:13px; margin:0 0 14px; color:#94a3b8;">${rc.msg}</p>
            <div class="ss-preview-area" id="ss-preview-area">
              <button class="ss-btn ss-btn-preview" id="ss-load-preview">\ud83d\udd0d Load Safe Preview</button>
            </div>
            <div class="ss-actions">
              <button class="ss-btn ss-btn-back" id="ss-go-back">\u2190 Go Back</button>
              <button class="ss-btn ${rc.btnCls}" id="ss-proceed">Proceed to Site \u2192</button>
            </div>
          </div>
        `;
        document.body.appendChild(overlay);

        // Go Back
        overlay.querySelector('#ss-go-back').addEventListener('click', () => overlay.remove());
        overlay.addEventListener('click', (e) => { if (e.target === overlay) overlay.remove(); });

        // Proceed
        overlay.querySelector('#ss-proceed').addEventListener('click', () => {
          overlay.remove();
          // Navigate to the URL — use location for same-origin, window.open for cross-origin
          try {
            const targetUrl = new URL(url);
            const currentUrl = new URL(window.location.href);
            if (targetUrl.hostname === currentUrl.hostname) {
              // Same-site link (e.g. Login) — navigate in same tab
              window.location.href = url;
            } else {
              // Cross-site link — open in new tab
              const newTab = window.open(url, '_blank');
              if (!newTab) {
                // Popup was blocked — fall back to same-tab navigation
                window.location.href = url;
              }
            }
          } catch {
            window.location.href = url;
          }
        });

        // Safe Preview
        overlay.querySelector('#ss-load-preview').addEventListener('click', () => {
          const area = overlay.querySelector('#ss-preview-area');
          area.innerHTML = '<p style="color:#a5b4fc; font-size:12px;">Loading safe preview… waiting for full page load</p>';
          fetch('http://localhost:5000/preview', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url, timeout: 30 }),
          })
            .then((r) => r.json())
            .then((result) => {
              if (result.success && result.screenshot_base64) {
                area.innerHTML = `
                  <p style="color:#6ee7b7; font-size:11px; margin-bottom:6px;">\u2705 Preview captured safely (${result.load_time}s)</p>
                  <img src="data:image/png;base64,${result.screenshot_base64}" alt="Safe Preview" />
                `;
              } else {
                area.innerHTML = `<p style="color:#fca5a5; font-size:12px;">\u274c ${result.error || 'Could not load preview'}</p>`;
              }
            })
            .catch(() => {
              area.innerHTML = '<p style="color:#fca5a5; font-size:12px;">\u274c Backend unavailable</p>';
            });
        });
      }
    });

  } catch (err) {
    console.error('[ScamShield] Crawler error:', err);
  }
})();