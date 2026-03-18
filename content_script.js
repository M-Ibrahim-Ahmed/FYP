// content_script.js
(function() {
  try {
    // Helper: absolute URL resolver
    const toAbsolute = (url) => {
      try {
        return new URL(url, location.href).href;
      } catch (e) {
        return url;
      }
    };

    // 1) Links
    const linkNodes = Array.from(document.querySelectorAll('a'));
    const links = linkNodes
      .map(a => ({ href: a.href || toAbsolute(a.getAttribute('href') || ''), text: a.innerText?.trim() || '' }))
      .filter(l => l.href);

    // 2) Forms
    const formNodes = Array.from(document.querySelectorAll('form'));
    const forms = formNodes.map(f => ({
      action: f.action || toAbsolute(f.getAttribute('action') || ''),
      method: (f.method || 'GET').toUpperCase(),
      inputs: Array.from(f.querySelectorAll('input,textarea,select')).map(i => i.name || i.id || i.type || '')
    }));

    // 3) Images (and clickable images)
    const imgNodes = Array.from(document.querySelectorAll('img'));
    const images = imgNodes.map(img => {
      // check if wrapped in anchor
      const anchor = img.closest('a');
      const onclick = img.getAttribute('onclick') || (img.parentElement ? img.parentElement.getAttribute('onclick') : null);
      return {
        src: toAbsolute(img.src || img.getAttribute('src') || ''),
        alt: img.alt || '',
        clickable: !!anchor || !!onclick,
        redirect: anchor ? (anchor.href || toAbsolute(anchor.getAttribute('href') || '')) : (onclick || null),
        onclick: onclick || null
      };
    });

    // 4) Meta refresh redirects
    const meta = document.querySelector('meta[http-equiv="refresh"]');
    const metaRedirects = [];
    if (meta) {
      const content = meta.getAttribute('content') || '';
      // common format "5; url=http://example.com"
      const m = content.match(/url=(.*)/i);
      if (m && m[1]) metaRedirects.push(m[1].trim());
    }

    // 5) Try to detect window.location assignments (best-effort: override assign if page hasn't completed)
    // NOTE: we only capture such redirects if they happen while our script runs. We don't override built-in behavior here.
    // This is a passive prototype.

    const crawlResult = {
      page_url: location.href,
      timestamp: new Date().toISOString(),
      links,
      forms,
      images,
      metaRedirects
    };

    // send to background
    chrome.runtime.sendMessage({ type: 'PAGE_CRAWL', payload: crawlResult });
  } catch (err) {
    console.error('ScamShield crawler error:', err);
  }
})();