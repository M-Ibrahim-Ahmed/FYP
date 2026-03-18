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
    const linkNodes = document.querySelectorAll('a[href]');
    const links = [];
    const seenLinks = new Set();

    linkNodes.forEach((a) => {
      const href = toAbsolute(a.getAttribute('href'));
      if (!href || seenLinks.has(href)) return;
      seenLinks.add(href);
      links.push({
        href,
        text: (a.innerText || '').trim().substring(0, 120) || '[no text]',
        rel: a.getAttribute('rel') || '',
        target: a.getAttribute('target') || '',
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
  } catch (err) {
    console.error('[ScamShield] Crawler error:', err);
  }
})();