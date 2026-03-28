// background.js — ScamShield Service Worker
// Stores crawl data per tab, sends data to backend for analysis, handles messaging.

'use strict';

const BACKEND_URL = 'http://localhost:5000';

// ─── Store crawl results per tab ───
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (!message || !message.type) return;

  // Content script finished crawling — store raw data and send to backend
  if (message.type === 'PAGE_CRAWL') {
    const tabId = sender?.tab?.id ? String(sender.tab.id) : 'unknown';
    const rawKey = `raw_${tabId}`;
    const scanKey = `scan_${tabId}`;

    // Store raw crawl data immediately (so popup can show something fast)
    chrome.storage.local.set({ [rawKey]: message.payload });

    // Send to backend for analysis
    sendToBackend(message.payload)
      .then((analysisResult) => {
        // Store the full analysis result
        chrome.storage.local.set({ [scanKey]: analysisResult });
        // Update badge based on overall risk
        updateBadge(Number(tabId), analysisResult.summary?.overall_risk);
      })
      .catch((err) => {
        console.warn('[ScamShield] Backend unavailable, using raw data:', err.message);
        // Store raw data as fallback
        chrome.storage.local.set({ [scanKey]: { ...message.payload, backend_offline: true } });
        updateBadge(Number(tabId), 'offline');
      });
    return;
  }

  // Popup requests stored scan data for the active tab
  if (message.type === 'REQUEST_SCAN') {
    const tabId = String(message.tabId || 'unknown');
    const scanKey = `scan_${tabId}`;
    const rawKey = `raw_${tabId}`;
    // Try analysis result first, fall back to raw data
    chrome.storage.local.get([scanKey, rawKey], (result) => {
      sendResponse({
        data: result[scanKey] || result[rawKey] || null,
        analyzed: !!result[scanKey] && !result[scanKey].backend_offline,
      });
    });
    return true;
  }

  // Popup requests a fresh re-crawl of the active tab
  if (message.type === 'RE_CRAWL') {
    const tabId = message.tabId;
    if (!tabId) return;
    chrome.scripting.executeScript(
      {
        target: { tabId: Number(tabId) },
        files: ['content_script.js'],
      },
      () => {
        if (chrome.runtime.lastError) {
          console.warn('[ScamShield] Re-crawl failed:', chrome.runtime.lastError.message);
          sendResponse({ success: false, error: chrome.runtime.lastError.message });
        } else {
          setTimeout(() => {
            sendResponse({ success: true });
          }, 500);
        }
      }
    );
    return true;
  }
});

// ─── Send crawl data to backend for analysis ───
async function sendToBackend(pageData) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 30000);

  try {
    const response = await fetch(`${BACKEND_URL}/analyze`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(pageData),
      signal: controller.signal,
    });
    clearTimeout(timeout);

    if (!response.ok) {
      throw new Error(`Backend returned ${response.status}`);
    }
    return await response.json();
  } catch (err) {
    clearTimeout(timeout);
    throw err;
  }
}

// ─── Update extension badge based on risk ───
function updateBadge(tabId, risk) {
  const config = {
    safe: { text: '✓', color: '#10b981' },
    suspicious: { text: '!', color: '#f59e0b' },
    malicious: { text: '✗', color: '#ef4444' },
    offline: { text: '?', color: '#6b7280' },
  };

  const c = config[risk] || config.offline;
  chrome.action.setBadgeText({ text: c.text, tabId });
  chrome.action.setBadgeBackgroundColor({ color: c.color, tabId });

  // Trigger browser notification for malicious sites
  if (risk === 'malicious') {
    chrome.notifications.create({
      type: 'basic',
      iconUrl: 'icons/icon128.png',
      title: 'ScamShield Security Alert!',
      message: 'Malicious content detected on this page. High risk of phishing!',
      priority: 2
    });
  }
}

// ─── Clean up storage when a tab is closed ───
chrome.tabs.onRemoved.addListener((tabId) => {
  chrome.storage.local.remove([`scan_${tabId}`, `raw_${tabId}`]);
});