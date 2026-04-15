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
      { host: /google\./i,     family: /\.google\.|\.google$/i },
      { host: /bing\./i,       family: /\.bing\.|\.bing$|\.microsoft\./i },
      { host: /yahoo\./i,      family: /\.yahoo\.|\.yahoo$/i },
      { host: /duckduckgo\./i,  family: /\.duckduckgo\.|\.duckduckgo$/i },
      { host: /yandex\./i,     family: /\.yandex\.|\.yandex$/i },
      { host: /baidu\./i,      family: /\.baidu\.|\.baidu$/i },
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
      } catch {}

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

      // Inject CSS for visual indicators (only once)
      if (!document.getElementById('scamshield-injected-css')) {
        const style = document.createElement('style');
        style.id = 'scamshield-injected-css';
        style.textContent = `
          #scamshield-badge {
            position: fixed;
            bottom: 20px;
            right: 20px;
            z-index: 2147483647;
            font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
            border-radius: 12px;
            padding: 10px 16px;
            color: #fff;
            font-size: 13px;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 8px;
            cursor: pointer;
            box-shadow: 0 4px 20px rgba(0,0,0,0.3);
            transition: all 0.3s ease;
            opacity: 0;
            transform: translateY(20px);
            animation: scamshield-slidein 0.5s ease 0.5s forwards;
          }
          #scamshield-badge:hover { transform: translateY(-2px) scale(1.02); box-shadow: 0 6px 25px rgba(0,0,0,0.4); }
          #scamshield-badge.ss-safe { background: linear-gradient(135deg, #059669, #10b981); }
          #scamshield-badge.ss-suspicious { background: linear-gradient(135deg, #d97706, #f59e0b); }
          #scamshield-badge.ss-malicious { background: linear-gradient(135deg, #dc2626, #ef4444); }
          #scamshield-badge .ss-icon { font-size: 18px; }
          #scamshield-badge .ss-info { display: flex; flex-direction: column; line-height: 1.3; }
          #scamshield-badge .ss-label { font-size: 11px; opacity: 0.85; font-weight: 400; }
          #scamshield-badge .ss-close { margin-left: 6px; opacity: 0.6; font-size: 16px; cursor: pointer; }
          #scamshield-badge .ss-close:hover { opacity: 1; }
          @keyframes scamshield-slidein { to { opacity: 1; transform: translateY(0); } }
          a.scamshield-suspicious { outline: 2px solid #f59e0b !important; outline-offset: 2px; border-radius: 3px; }
          a.scamshield-malicious { outline: 2px solid #ef4444 !important; outline-offset: 2px; border-radius: 3px; }
          a.scamshield-malicious::after {
            content: ' \\26A0';
            color: #ef4444;
            font-size: 12px;
          }
        `;
        document.head.appendChild(style);
      }

      // Remove old badge if present (e.g., re-scan)
      const oldBadge = document.getElementById('scamshield-badge');
      if (oldBadge) oldBadge.remove();

      // Create floating badge
      const riskConfig = {
        safe:       { icon: '\u2705', label: 'Page Safe', cls: 'ss-safe' },
        suspicious: { icon: '\u26a0\ufe0f', label: 'Suspicious Activity', cls: 'ss-suspicious' },
        malicious:  { icon: '\ud83d\udeab', label: 'DANGER - Malicious!', cls: 'ss-malicious' },
      };
      const cfg = riskConfig[risk] || riskConfig.safe;

      // Count threats for the badge subtitle
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

      // Dismiss on close click
      badge.querySelector('.ss-close').addEventListener('click', (e) => {
        e.stopPropagation();
        badge.style.opacity = '0';
        badge.style.transform = 'translateY(20px)';
        setTimeout(() => badge.remove(), 300);
      });

      // Auto-dismiss safe pages after 8s
      if (risk === 'safe') {
        setTimeout(() => {
          if (badge.parentNode) {
            badge.style.opacity = '0';
            badge.style.transform = 'translateY(20px)';
            setTimeout(() => badge.remove(), 300);
          }
        }, 8000);
      }

      // Highlight suspicious/malicious links on the page
      const allLinks = data.links || [];
      allLinks.forEach((item) => {
        if (item.navigation) return; // Skip nav links
        if (item.classification === 'safe') return;

        // Find matching <a> on the page
        const anchors = document.querySelectorAll(`a[href="${CSS.escape(item.url)}"]`);
        if (anchors.length === 0) {
          // Try partial match (URL might have been resolved)
          try {
            const url = new URL(item.url);
            const partial = document.querySelectorAll(`a[href*="${CSS.escape(url.hostname)}"]`);
            partial.forEach((a) => {
              a.classList.add(`scamshield-${item.classification}`);
              a.title = `ScamShield: ${item.classification.toUpperCase()} (Risk: ${item.risk_score})`;
            });
          } catch {}
        }
        anchors.forEach((a) => {
          a.classList.add(`scamshield-${item.classification}`);
          a.title = `ScamShield: ${item.classification.toUpperCase()} (Risk: ${item.risk_score})`;
        });
      });
    });

  } catch (err) {
    console.error('[ScamShield] Crawler error:', err);
  }
})();