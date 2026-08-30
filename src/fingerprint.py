"""
fingerprint.py — element identity capture.

One JavaScript description function is used everywhere: to record what an
element looked like on a green run, and to describe every candidate element on
a page after a break. Both sides must be captured identically or the scores
mean nothing.

Fingerprint shape (frozen with the rest of the contracts):

    {
      "step_id":   "login_submit",
      "tag":       "button",
      "text":      "Sign in",
      "attrs":     { "id": "btn-login", "class": "btn primary", "type": "submit" },
      "dom_path":  "form#login-form > div.actions > button",
      "neighbors": { "prev_label": "Password" },
      "geometry":  { "x": 420, "y": 380, "w": 120, "h": 40 }
    }
"""

# Attributes worth carrying. An id is recorded but deliberately carries no
# weight of its own during scoring — a renamed id is the break we heal.
KEPT_ATTRS = [
    "id", "class", "type", "name", "aria-label",
    "data-testid", "placeholder", "role", "href", "value",
]

# Everything a bot could plausibly interact with.
INTERACTIVE_SELECTOR = (
    "button, input, select, textarea, a[href], "
    "[role='button'], [onclick], table[id], [contenteditable='true']"
)

DESCRIBE_JS = """
(el) => {
  const KEPT = %s;

  const attrs = {};
  for (const name of KEPT) {
    const value = el.getAttribute(name);
    if (value !== null && value !== '') attrs[name] = value;
  }

  const domPath = (() => {
    const parts = [];
    let node = el;
    let hops = 0;
    while (node && node.nodeType === 1 && node.tagName !== 'BODY' && hops < 6) {
      let part = node.tagName.toLowerCase();
      // An ancestor id anchors the path, but the element's own id never does:
      // a renamed id is exactly the break this path has to survive.
      if (node.id && node !== el) {
        part += '#' + node.id;
        parts.unshift(part);
        break;
      }
      const classes = Array.from(node.classList).slice(0, 2).join('.');
      if (classes) part += '.' + classes;
      parts.unshift(part);
      node = node.parentElement;
      hops += 1;
    }
    return parts.join(' > ');
  })();

  const neighbors = (() => {
    const out = { prev_label: '', parent_text: '' };
    if (el.id) {
      const bound = document.querySelector('label[for="' + CSS.escape(el.id) + '"]');
      if (bound) out.prev_label = bound.textContent.trim().slice(0, 60);
    }
    if (!out.prev_label) {
      const prev = el.previousElementSibling;
      if (prev) out.prev_label = prev.textContent.trim().slice(0, 60);
    }
    if (!out.prev_label && el.parentElement) {
      const label = el.parentElement.querySelector('label');
      if (label) out.prev_label = label.textContent.trim().slice(0, 60);
    }
    if (el.parentElement) {
      out.parent_text = el.parentElement.textContent.trim().slice(0, 80);
    }
    return out;
  })();

  const rect = el.getBoundingClientRect();
  const geometry = {
    x: Math.round(rect.left + window.scrollX),
    y: Math.round(rect.top + window.scrollY),
    w: Math.round(rect.width),
    h: Math.round(rect.height),
  };

  let text = (el.innerText || el.textContent || '').trim().slice(0, 120);
  if (!text) {
    text = (el.getAttribute('value') || el.getAttribute('placeholder') || '').trim().slice(0, 120);
  }

  return {
    tag: el.tagName.toLowerCase(),
    text: text,
    attrs: attrs,
    dom_path: domPath,
    neighbors: neighbors,
    geometry: geometry,
    visible: !!(rect.width && rect.height),
  };
}
""" % (KEPT_ATTRS,)


def describe_locator(locator) -> dict:
    """Describe a single Playwright locator as a fingerprint dict."""
    return locator.evaluate(DESCRIBE_JS)


def collect_candidates(page) -> list[dict]:
    """
    Describe every interactive element on the page.

    Used after a break to build the candidate pool the ranker scores against
    the stored fingerprint. Invisible elements are dropped: a bot cannot click
    what a user cannot see.
    """
    described = page.evaluate(
        """
        ({selector, describeSource}) => {
          const describe = eval('(' + describeSource + ')');
          return Array.from(document.querySelectorAll(selector)).map(describe);
        }
        """,
        {"selector": INTERACTIVE_SELECTOR, "describeSource": DESCRIBE_JS},
    )
    return [element for element in described if element.get("visible")]


def css_escape(value: str) -> str:
    """Escape a value for use inside a CSS attribute selector."""
    return value.replace("\\", "\\\\").replace("'", "\\'")
