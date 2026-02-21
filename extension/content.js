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
      case "ping":
        return { ok: true, url: window.location.href, title: document.title };
      default:
        return { ok: false, error: `Unknown action: ${action}` };
    }
  } catch (err) {
    return { ok: false, error: err.message };
  }
}

function resolveElement(selector) {
  const el = document.querySelector(selector);
  if (!el) throw new Error(`Element not found: ${selector}`);
  return el;
}

function doClick(params) {
  const el = resolveElement(params.selector);
  el.scrollIntoView({ block: "center", behavior: "instant" });
  el.click();
  return { ok: true };
}

function doType(params) {
  const el = resolveElement(params.selector);
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
  const el = resolveElement(params.selector);
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
  for (const node of nodes) {
    if (count >= limit) break;
    if (!isVisible(node)) continue;

    const rect = node.getBoundingClientRect();
    const info = {
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
  const ms = params.ms || 1000;
  return new Promise((resolve) => {
    setTimeout(() => resolve({ ok: true }), ms);
  });
}

function doEvaluate(params) {
  const fn = new Function(params.expression);
  const result = fn();
  return { ok: true, result: result !== undefined ? String(result) : null };
}

function doScroll(params) {
  if (params.selector) {
    const el = resolveElement(params.selector);
    el.scrollIntoView({ block: "center", behavior: "smooth" });
  } else {
    window.scrollBy({ top: params.y || 300, left: params.x || 0, behavior: "smooth" });
  }
  return { ok: true };
}

function doGetText(params) {
  const el = resolveElement(params.selector);
  return { ok: true, text: (el.textContent || "").trim() };
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
