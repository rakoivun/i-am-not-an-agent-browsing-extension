let keepalivePort = null;
const elementRefs = new Map();

function connectKeepalive() {
  keepalivePort = chrome.runtime.connect({ name: "keepalive" });
  keepalivePort.onDisconnect.addListener(() => {
    setTimeout(connectKeepalive, 1000);
  });
}
connectKeepalive();

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  handleMessage(message).then(sendResponse);
  return true;
});

async function handleMessage(message) {
  const { action, params } = message;

  try {
    switch (action) {
      case "click":
        return doClick(params);
      case "type":
        return doType(params);
      case "select":
        return doSelect(params);
      case "snapshot":
        return doSnapshot(params);
      case "wait":
        return doWait(params);
      case "evaluate":
        return doEvaluate(params);
      case "scroll":
        return doScroll(params);
      case "get_text":
        return doGetText(params);
      case "get_html":
        return doGetHtml(params);
      case "get_attr":
        return doGetAttr(params);
      case "get_value":
        return doGetValue(params);
      case "count":
        return doCount(params);
      case "hover":
        return doHover(params);
      case "focus":
        return doFocus(params);
      case "press":
        return doPress(params);
      case "dblclick":
        return doDblclick(params);
      case "check":
        return doCheck(params);
      case "uncheck":
        return doUncheck(params);
      case "fingerprint":
        return doFingerprint();
      case "ping":
        return { ok: true, url: window.location.href, title: document.title };
      default:
        return { ok: false, error: `Unknown action: ${action}` };
    }
  } catch (err) {
    return { ok: false, error: err.message };
  }
}

function resolveElement(target) {
  if (!target || typeof target !== "string") {
    throw new Error("Missing element target");
  }

  if (/^e\d+$/.test(target)) {
    const refEl = elementRefs.get(target);
    if (!refEl || !refEl.isConnected) {
      throw new Error(`Element ref not found or stale: ${target}`);
    }
    return refEl;
  }

  const el = document.querySelector(target);
  if (!el) throw new Error(`Element not found: ${target}`);
  return el;
}

function doClick(params) {
  const el = resolveElement(getTarget(params));
  el.scrollIntoView({ block: "center", behavior: "instant" });
  el.click();
  return { ok: true };
}

function doType(params) {
  const el = resolveElement(getTarget(params));
  el.scrollIntoView({ block: "center", behavior: "instant" });
  el.focus();

  if (params.clear) {
    el.value = "";
    el.dispatchEvent(new Event("input", { bubbles: true }));
  }

  for (const char of params.text) {
    el.dispatchEvent(new KeyboardEvent("keydown", { key: char, bubbles: true }));
    el.dispatchEvent(new KeyboardEvent("keypress", { key: char, bubbles: true }));
    if ("value" in el) {
      el.value += char;
    }
    el.dispatchEvent(new Event("input", { bubbles: true }));
    el.dispatchEvent(new KeyboardEvent("keyup", { key: char, bubbles: true }));
  }
  el.dispatchEvent(new Event("change", { bubbles: true }));

  return { ok: true };
}

function doSelect(params) {
  const el = resolveElement(getTarget(params));
  el.value = params.value;
  el.dispatchEvent(new Event("change", { bubbles: true }));
  return { ok: true };
}

function doSnapshot(params) {
  const interactiveOnly = params && params.interactive_only;
  const elements = [];

  const selectors = interactiveOnly
    ? "a, button, input, select, textarea, [role='button'], [role='link'], [tabindex], [contenteditable]"
    : "*";

  const nodes = document.querySelectorAll(selectors);
  const limit = (params && params.limit) || 500;

  let count = 0;
  elementRefs.clear();
  for (const node of nodes) {
    if (count >= limit) break;
    if (!isVisible(node)) continue;

    const rect = node.getBoundingClientRect();
    const info = {
      ref: `e${count}`,
      tag: node.tagName.toLowerCase(),
      text: (node.textContent || "").trim().slice(0, 120),
      selector: buildSelector(node),
    };

    if (node.id) info.id = node.id;
    if (node.name) info.name = node.name;
    if (node.type) info.type = node.type;
    if (node.href) info.href = node.href;
    if (node.value) info.value = node.value;
    if (node.placeholder) info.placeholder = node.placeholder;
    if (node.getAttribute("role")) info.role = node.getAttribute("role");
    if (node.getAttribute("aria-label")) info.ariaLabel = node.getAttribute("aria-label");

    info.rect = {
      x: Math.round(rect.x),
      y: Math.round(rect.y),
      w: Math.round(rect.width),
      h: Math.round(rect.height),
    };

    elements.push(info);
    elementRefs.set(info.ref, node);
    count++;
  }

  return {
    ok: true,
    url: window.location.href,
    title: document.title,
    elements,
  };
}

function doWait(params) {
  const target = getTarget(params);
  if (target) {
    const timeoutMs = params.timeout_ms || params.timeout || 10000;
    const start = Date.now();
    return new Promise((resolve) => {
      const timer = setInterval(() => {
        try {
          const el = resolveElement(target);
          if (el) {
            clearInterval(timer);
            resolve({ ok: true, selector: target });
            return;
          }
        } catch (_err) {
          // Keep polling until timeout.
        }
        if (Date.now() - start > timeoutMs) {
          clearInterval(timer);
          resolve({ ok: false, error: `Timeout waiting for element: ${target}` });
        }
      }, 100);
    });
  }

  const ms = params.ms || 1000;
  return new Promise((resolve) => {
    setTimeout(() => resolve({ ok: true }), ms);
  });
}

function doFingerprint() {
  const brands = navigator.userAgentData
    ? navigator.userAgentData.brands.map((b) => `${b.brand}/${b.version}`)
    : null;
  return {
    ok: true,
    webdriver: navigator.webdriver,
    userAgent: navigator.userAgent,
    brands,
    platform: navigator.platform,
    languages: navigator.languages,
    cookieEnabled: navigator.cookieEnabled,
    hardwareConcurrency: navigator.hardwareConcurrency,
  };
}

function doEvaluate(params) {
  let expr = params.expression;
  if (!expr.trimStart().startsWith("return ") && !expr.includes(";")) {
    expr = "return " + expr;
  }
  const fn = new Function(expr);
  const result = fn();
  return { ok: true, result: result !== undefined ? String(result) : null };
}

function doScroll(params) {
  const target = getTarget(params);
  if (target) {
    const el = resolveElement(target);
    el.scrollIntoView({ block: "center", behavior: "smooth" });
  } else {
    window.scrollBy({ top: params.y || 300, left: params.x || 0, behavior: "smooth" });
  }
  return { ok: true };
}

function doGetText(params) {
  const el = resolveElement(getTarget(params));
  return { ok: true, text: (el.textContent || "").trim() };
}

function doGetHtml(params) {
  const el = resolveElement(getTarget(params));
  return { ok: true, html: el.innerHTML };
}

function doGetAttr(params) {
  const el = resolveElement(getTarget(params));
  const name = params.name;
  if (!name) {
    throw new Error("Missing attribute name");
  }
  return { ok: true, value: el.getAttribute(name) };
}

function doGetValue(params) {
  const el = resolveElement(getTarget(params));
  return { ok: true, value: "value" in el ? el.value : null };
}

function doCount(params) {
  const selector = params.selector;
  if (!selector) throw new Error("Missing selector");
  return { ok: true, count: document.querySelectorAll(selector).length };
}

function doHover(params) {
  const el = resolveElement(getTarget(params));
  el.scrollIntoView({ block: "center", behavior: "instant" });
  el.dispatchEvent(new MouseEvent("mouseover", { bubbles: true }));
  el.dispatchEvent(new MouseEvent("mouseenter", { bubbles: true }));
  return { ok: true };
}

function doFocus(params) {
  const el = resolveElement(getTarget(params));
  el.focus();
  return { ok: true };
}

function doPress(params) {
  const key = params.key || "Enter";
  const target = getTarget(params);
  const el = target ? resolveElement(target) : document.activeElement || document.body;
  el.dispatchEvent(new KeyboardEvent("keydown", { key, bubbles: true }));
  el.dispatchEvent(new KeyboardEvent("keypress", { key, bubbles: true }));
  el.dispatchEvent(new KeyboardEvent("keyup", { key, bubbles: true }));
  if (key === "Enter" && typeof el.form?.requestSubmit === "function") {
    el.form.requestSubmit();
  }
  return { ok: true };
}

function doDblclick(params) {
  const el = resolveElement(getTarget(params));
  el.scrollIntoView({ block: "center", behavior: "instant" });
  el.dispatchEvent(new MouseEvent("dblclick", { bubbles: true }));
  return { ok: true };
}

function doCheck(params) {
  const el = resolveElement(getTarget(params));
  if (!("checked" in el)) throw new Error("Element is not checkable");
  el.checked = true;
  el.dispatchEvent(new Event("input", { bubbles: true }));
  el.dispatchEvent(new Event("change", { bubbles: true }));
  return { ok: true };
}

function doUncheck(params) {
  const el = resolveElement(getTarget(params));
  if (!("checked" in el)) throw new Error("Element is not checkable");
  el.checked = false;
  el.dispatchEvent(new Event("input", { bubbles: true }));
  el.dispatchEvent(new Event("change", { bubbles: true }));
  return { ok: true };
}

function getTarget(params = {}) {
  return params.ref || params.selector || params.target || null;
}

function isVisible(el) {
  if (!el.offsetParent && el.tagName !== "BODY" && el.tagName !== "HTML") return false;
  const style = window.getComputedStyle(el);
  return style.display !== "none" && style.visibility !== "hidden" && style.opacity !== "0";
}

function buildSelector(el) {
  if (el.id) return `#${CSS.escape(el.id)}`;

  const parts = [];
  let current = el;
  while (current && current !== document.body) {
    let selector = current.tagName.toLowerCase();
    if (current.id) {
      parts.unshift(`#${CSS.escape(current.id)}`);
      break;
    }
    const parent = current.parentElement;
    if (parent) {
      const siblings = Array.from(parent.children).filter(
        (c) => c.tagName === current.tagName
      );
      if (siblings.length > 1) {
        const index = siblings.indexOf(current) + 1;
        selector += `:nth-of-type(${index})`;
      }
    }
    parts.unshift(selector);
    current = current.parentElement;
  }
  return parts.join(" > ");
}
