(function () {
  // ---------- servings scaler ----------
  var UNICODE = { "¼": 0.25, "½": 0.5, "¾": 0.75, "⅓": 1 / 3, "⅔": 2 / 3, "⅛": 0.125 };
  var NUM = "(?:\\d+\\s+\\d+\\/\\d+|\\d+\\s*[¼½¾⅓⅔⅛]|\\d+\\/\\d+|\\d+(?:\\.\\d+)?|[¼½¾⅓⅔⅛])";
  var LEAD = new RegExp("^(" + NUM + ")(?:(\\s*[-–]\\s*)(" + NUM + "))?");
  var METRIC = /\((\d+(?:\.\d+)?)\s?(g|ml)\)/g;

  function parseQty(s) {
    s = s.trim();
    var m;
    if ((m = s.match(/^(\d+)\s+(\d+)\/(\d+)$/))) return +m[1] + m[2] / m[3];
    if ((m = s.match(/^(\d+)\s*([¼½¾⅓⅔⅛])$/))) return +m[1] + UNICODE[m[2]];
    if ((m = s.match(/^(\d+)\/(\d+)$/))) return m[1] / m[2];
    if (UNICODE[s] !== undefined) return UNICODE[s];
    return parseFloat(s);
  }

  var FRACS = [[0, ""], [1 / 8, "⅛"], [1 / 4, "¼"], [1 / 3, "⅓"], [1 / 2, "½"], [2 / 3, "⅔"], [3 / 4, "¾"], [1, ""]];
  function formatQty(n) {
    var whole = Math.floor(n + 1e-9), frac = n - whole, best = FRACS[0], bestD = 9;
    FRACS.forEach(function (f) {
      var d = Math.abs(frac - f[0]);
      if (d < bestD) { bestD = d; best = f; }
    });
    if (best[0] === 1) { whole += 1; best = FRACS[0]; }
    if (bestD > 0.04 && n >= 10) return String(Math.round(n));
    if (bestD > 0.04) return String(Math.round(n * 10) / 10);
    if (whole === 0 && best[1] === "") return "0";
    return (whole ? whole + (best[1] ? " " : "") : "") + best[1];
  }

  function escapeHtml(s) {
    return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }

  function scaleLine(raw, factor) {
    var text = raw;
    var m = raw.match(LEAD);
    var head = "", rest = raw;
    if (m) {
      var a = formatQty(parseQty(m[1]) * factor);
      head = m[3] ? a + m[2] + formatQty(parseQty(m[3]) * factor) : a;
      rest = raw.slice(m[0].length);
    }
    rest = rest.replace(METRIC, function (_, n, unit) {
      var v = parseFloat(n) * factor;
      return "(" + (v >= 10 ? Math.round(v) : Math.round(v * 10) / 10) + unit + ")";
    });
    text = head + rest;
    // Re-apply bold/italic/link markup used in recipe text.
    return escapeHtml(text)
      .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
      .replace(/\[([^\]]+)\]\((https?:\/\/[^)\s]+)\)/g, '<a href="$2" rel="noopener">$1</a>');
  }

  var ctl = document.querySelector(".servings");
  var items = Array.prototype.slice.call(document.querySelectorAll(".ingredients li"));
  if (ctl) {
    var base = parseInt(ctl.dataset.base, 10), current = base;
    var out = document.getElementById("servings-out");
    function render() {
      out.textContent = current;
      var f = current / base;
      items.forEach(function (li) {
        li.innerHTML = f === 1 ? li.dataset.html : scaleLine(li.dataset.raw, f);
      });
    }
    items.forEach(function (li) { li.dataset.html = li.innerHTML; });
    document.getElementById("minus").addEventListener("click", function () {
      if (current > 1) { current--; render(); }
    });
    document.getElementById("plus").addEventListener("click", function () {
      if (current < 99) { current++; render(); }
    });
  }

  // ---------- tap a step or ingredient to mark it done ----------
  Array.prototype.forEach.call(document.querySelectorAll(".steps li, .ingredients li"), function (li) {
    li.addEventListener("click", function (e) {
      if (e.target.tagName === "A") return;
      li.classList.toggle("done");
    });
  });

  // ---------- cook mode: keep the screen awake ----------
  var btn = document.getElementById("cook-mode");
  var lock = null;
  async function setCooking(on) {
    document.body.classList.toggle("cooking", on);
    btn.setAttribute("aria-pressed", String(on));
    btn.textContent = on ? "Exit cook mode" : "Cook mode";
    try {
      if (on && "wakeLock" in navigator) lock = await navigator.wakeLock.request("screen");
      else if (lock) { await lock.release(); lock = null; }
    } catch (err) { /* wake lock is a nice-to-have */ }
  }
  btn.addEventListener("click", function () {
    setCooking(!document.body.classList.contains("cooking"));
  });
  document.addEventListener("visibilitychange", function () {
    if (document.visibilityState === "visible" && document.body.classList.contains("cooking")) setCooking(true);
  });
})();

// ---------- tag editor ----------
(function () {
  var dataEl = document.getElementById("tag-data");
  var editBtn = document.getElementById("edit-tags");
  if (!dataEl || !editBtn) return;

  var data = JSON.parse(dataEl.textContent);
  var list = document.getElementById("tag-list");
  var editor = document.getElementById("tag-editor");
  var notice = document.getElementById("tag-notice");
  var current = data.tags.slice();
  var draft = [];
  var input = null;

  function clean(t) {
    return t.toLowerCase().replace(/[^a-z0-9 -]/g, "").replace(/\s+/g, " ").trim().slice(0, 30);
  }
  function el(name, cls, text) {
    var e = document.createElement(name);
    if (cls) e.className = cls;
    if (text !== undefined) e.textContent = text;
    return e;
  }
  function button(cls, text, onClick, label) {
    var b = el("button", cls, text);
    b.type = "button";
    if (label) b.setAttribute("aria-label", label);
    b.addEventListener("click", onClick);
    return b;
  }

  function renderView() {
    list.textContent = "";
    current.forEach(function (t) {
      var a = el("a", "tag", t);
      a.href = "../../?tag=" + encodeURIComponent(t);
      list.appendChild(a);
    });
  }

  function addTag(raw) {
    var t = clean(raw);
    if (t && draft.indexOf(t) === -1) draft.push(t);
  }

  function renderEditor(focusInput) {
    editor.textContent = "";
    editor.appendChild(el("h3", "", "Edit tags"));

    editor.appendChild(el("p", "editor-label", "Current tags (click one to remove it)"));
    var row = el("div", "tag-chips");
    draft.forEach(function (t) {
      row.appendChild(button("tag-chip removable", t + "  ×", function () {
        draft = draft.filter(function (x) { return x !== t; });
        renderEditor();
      }, "Remove tag " + t));
    });
    if (!draft.length) row.appendChild(el("span", "muted", "No tags yet"));
    editor.appendChild(row);

    var available = data.allTags.filter(function (t) { return draft.indexOf(t) === -1; });
    if (available.length) {
      editor.appendChild(el("p", "editor-label", "Add from existing tags"));
      var pool = el("div", "tag-chips");
      available.forEach(function (t) {
        pool.appendChild(button("tag-chip addable", "+ " + t, function () {
          addTag(t);
          renderEditor();
        }, "Add tag " + t));
      });
      editor.appendChild(pool);
    }

    editor.appendChild(el("p", "editor-label", "Or add your own"));
    var form = el("div", "tag-add");
    input = el("input");
    input.type = "text";
    input.maxLength = 30;
    input.placeholder = "e.g. high protein";
    input.setAttribute("aria-label", "New tag");
    function submitNew() {
      if (input.value.trim()) { addTag(input.value); renderEditor(true); }
    }
    input.addEventListener("keydown", function (e) {
      if (e.key === "Enter") { e.preventDefault(); submitNew(); }
    });
    form.appendChild(input);
    form.appendChild(button("btn ghost small", "Add", submitNew));
    editor.appendChild(form);

    var actions = el("div", "tag-actions");
    actions.appendChild(button("btn small", "Save changes", save));
    actions.appendChild(button("btn ghost small", "Cancel", closeEditor));
    editor.appendChild(actions);

    if (focusInput) input.focus();
  }

  function openEditor() {
    draft = current.slice();
    notice.hidden = true;
    editor.hidden = false;
    editBtn.hidden = true;
    renderEditor();
  }
  function closeEditor() {
    editor.hidden = true;
    editBtn.hidden = false;
  }

  function showNotice(text) {
    notice.textContent = text;
    notice.hidden = false;
  }

  function save() {
    if (input && input.value.trim()) addTag(input.value);
    var same = draft.length === current.length &&
      draft.every(function (t) { return current.indexOf(t) !== -1; });
    if (same) { closeEditor(); return; }
    if (!data.repo) {
      showNotice("This site isn't linked to a GitHub repo yet, so tag changes can't be sent. Set \"repo\" in site.json.");
      closeEditor();
      return;
    }
    var url = "https://github.com/" + data.repo + "/issues/new?template=edit-tags.yml" +
      "&title=" + encodeURIComponent("Tag change: " + data.title) +
      "&recipe=" + encodeURIComponent(data.slug) +
      "&tags=" + encodeURIComponent(draft.join(", "));
    window.open(url, "_blank", "noopener");
    current = draft.slice();
    renderView();
    closeEditor();
    showNotice("Almost done: a GitHub page opened with your tag change filled in. Press \"Submit new issue\" there. The new tags go live once the change is approved.");
  }

  editBtn.addEventListener("click", openEditor);
})();
