const RELAY_URL = "http://localhost:18321";
const POLL_INTERVAL_MS = 500;
const KEEPALIVE_INTERVAL_MS = 20000;

let polling = false;
const activePorts = new Set();

async function pollForCommand() {
  if (polling) return;
  polling = true;

  try {
    const resp = await fetch(`${RELAY_URL}/command`, { method: "GET" });
    if (resp.status === 204) return;
    if (!resp.ok) return;

    const command = await resp.json();
    await executeCommand(command);
  } catch (_err) {
    // Relay server not running -- silently ignore
  } finally {
    polling = false;
  }
}

chrome.runtime.onConnect.addListener((port) => {
  if (port.name === "keepalive") {
    activePorts.add(port);
    port.onDisconnect.addListener(() => activePorts.delete(port));
  }
});

chrome.alarms.create("poll", { periodInMinutes: 0.5 });
chrome.alarms.onAlarm.addListener((alarm) => {
  if (alarm.name === "poll") {
    pollForCommand();
  }
});

async function executeCommand(command) {
  const { id, action, params } = command;

  try {
    if (action === "navigate") {
      const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
      if (!tab) throw new Error("No active tab");
      await chrome.tabs.update(tab.id, { url: params.url });
      await waitForTabLoad(tab.id, params.timeout || 30000);
      await postResult(id, { ok: true, url: params.url });
      return;
    }

    if (action === "tab_info") {
      const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
      await postResult(id, { ok: true, tab: tab ? { id: tab.id, url: tab.url, title: tab.title } : null });
      return;
    }

    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (!tab) {
      await postResult(id, { ok: false, error: "No active tab" });
      return;
    }

    const result = await chrome.tabs.sendMessage(tab.id, { id, action, params });
    await postResult(id, result);
  } catch (err) {
    await postResult(id, { ok: false, error: err.message });
  }
}

function waitForTabLoad(tabId, timeout) {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => {
      chrome.tabs.onUpdated.removeListener(listener);
      reject(new Error("Navigation timeout"));
    }, timeout);

    function listener(updatedTabId, changeInfo) {
      if (updatedTabId === tabId && changeInfo.status === "complete") {
        clearTimeout(timer);
        chrome.tabs.onUpdated.removeListener(listener);
        resolve();
      }
    }
    chrome.tabs.onUpdated.addListener(listener);
  });
}

async function postResult(commandId, result) {
  try {
    await fetch(`${RELAY_URL}/result`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id: commandId, ...result }),
    });
  } catch (_err) {
    // Relay server gone -- drop the result
  }
}

setInterval(pollForCommand, POLL_INTERVAL_MS);

chrome.runtime.onInstalled.addListener(() => {
  console.log("[browser-relay] Extension installed");
});
