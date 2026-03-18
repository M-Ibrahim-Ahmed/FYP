// background.js
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (!message || !message.type) return;
  if (message.type === 'PAGE_CRAWL') {
    const data = message.payload || {};
    // store last scan keyed by tabId if available
    const tabId = sender && sender.tab && sender.tab.id ? sender.tab.id.toString() : 'global';
    const key = `lastScan_${tabId}`;
    chrome.storage.local.set({ [key]: data }, () => {
      // console.log('ScamShield: stored crawl for', key);
    });
  }
});