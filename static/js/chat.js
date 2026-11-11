/* AI chat UI shared by the website Design Assistant and the internal Studio Assistant. No dependencies.
   The server returns answer HTML that is already sanitised (bleach); everything else is inserted as text. */
(function () {
  "use strict";

  function csrf() {
    var m = document.querySelector('meta[name="csrf-token"]');
    return m ? m.getAttribute("content") : "";
  }
  function el(tag, cls, text) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text != null) e.textContent = text;
    return e;
  }
  function store(key, val) {
    try { if (val === undefined) return window.localStorage.getItem(key); window.localStorage.setItem(key, val); }
    catch (e) { return null; }
  }

  function Chat(root) {
    this.root = root;
    this.endpoint = root.getAttribute("data-endpoint");
    this.leadEndpoint = root.getAttribute("data-lead-endpoint");
    this.public = root.getAttribute("data-channel") === "public";
    this.storeKey = "chat_session_" + (root.getAttribute("data-channel") || "public");
    this.session = store(this.storeKey) || "";
    this.log = root.querySelector(".chat-log");
    this.form = root.querySelector(".chat-form");
    this.input = this.form.querySelector("textarea, input");
    this.answers = 0;
    this.leadShown = false;
    var self = this;
    this.form.addEventListener("submit", function (e) { e.preventDefault(); self.send(self.input.value); });
    this.input.addEventListener("keydown", function (e) {
      if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); self.send(self.input.value); }
    });
    root.querySelectorAll("[data-ask]").forEach(function (b) {
      b.addEventListener("click", function () { self.send(b.getAttribute("data-ask")); });
    });
  }

  Chat.prototype.scroll = function () { this.log.scrollTop = this.log.scrollHeight; };

  Chat.prototype.bubble = function (who, content, isHtml) {
    var b = el("div", "chat-msg " + who);
    var body = el("div", "chat-bubble-body");
    if (isHtml) body.innerHTML = content; else body.textContent = content;
    b.appendChild(body);
    this.log.appendChild(b);
    this.scroll();
    return b;
  };

  Chat.prototype.typing = function () {
    var t = el("div", "chat-msg assistant typing");
    t.innerHTML = '<div class="chat-bubble-body"><span class="dot"></span><span class="dot"></span><span class="dot"></span></div>';
    this.log.appendChild(t);
    this.scroll();
    return t;
  };

  Chat.prototype.extras = function (bubble, data) {
    if (data.sources && data.sources.length) {
      var src = el("div", "chat-sources");
      src.appendChild(el("span", "chat-sources-label", "Sources"));
      data.sources.forEach(function (s) {
        var item = s.url ? el("a", "chat-source") : el("span", "chat-source");
        item.textContent = "[" + s.n + "] " + s.title.replace(/^(FAQ|Service|Project): /, "");
        if (s.url) { item.href = s.url; }
        src.appendChild(item);
      });
      bubble.appendChild(src);
    }
    if (data.projects && data.projects.length) {
      var row = el("div", "chat-projects");
      data.projects.forEach(function (p) {
        var a = el("a", "chat-project");
        a.href = p.url;
        if (p.cover) { var img = el("img"); img.src = p.cover; img.alt = ""; img.loading = "lazy"; a.appendChild(img); }
        var t = el("span", "chat-project-body");
        t.appendChild(el("strong", null, p.title));
        t.appendChild(el("small", null, p.meta || ""));
        a.appendChild(t);
        row.appendChild(a);
      });
      bubble.appendChild(row);
    }
    if (this.public && data.mode !== "lead") {
      var ctas = el("div", "chat-ctas");
      var book = el("a", "btn btn-accent btn-sm", "Book a free consultation"); book.href = "/book/";
      var est = el("a", "btn btn-outline-ink btn-sm", "Get an estimate"); est.href = "/estimate/";
      ctas.appendChild(book); ctas.appendChild(est);
      bubble.appendChild(ctas);
    }
    this.scroll();
  };

  Chat.prototype.leadForm = function () {
    if (!this.public || this.leadShown || !this.leadEndpoint) return;
    this.leadShown = true;
    var self = this;
    var box = el("form", "chat-lead");
    box.innerHTML = '<div class="small fw-semibold mb-1">Want our designer to call you?</div>' +
      '<div class="d-flex gap-2"><input class="form-control form-control-sm" name="name" placeholder="Your name" maxlength="100" required>' +
      '<input class="form-control form-control-sm" name="mobile" placeholder="Mobile" inputmode="numeric" maxlength="14" required></div>' +
      '<button class="btn btn-ink btn-sm w-100 mt-2" type="submit">Request a call back</button>';
    box.addEventListener("submit", function (e) {
      e.preventDefault();
      var btn = box.querySelector("button"); btn.disabled = true;
      fetch(self.leadEndpoint, { method: "POST", credentials: "same-origin",
        headers: { "Content-Type": "application/json", "X-CSRFToken": csrf() },
        body: JSON.stringify({ name: box.name.value, mobile: box.mobile.value, session: self.session }) })
        .then(function (r) { return r.json().then(function (j) { return { ok: r.ok, j: j }; }); })
        .then(function (res) {
          if (!res.ok) { btn.disabled = false; self.note(res.j.error || "Please check your details."); return; }
          if (res.j.session) { self.session = res.j.session; store(self.storeKey, self.session); }
          box.replaceWith(el("div", "chat-lead done", res.j.message));
        })
        .catch(function () { btn.disabled = false; self.note("Network problem — please try again."); });
    });
    this.log.appendChild(box);
    this.scroll();
  };

  Chat.prototype.note = function (msg) {
    var n = el("div", "chat-note", msg);
    this.log.appendChild(n);
    this.scroll();
  };

  Chat.prototype.send = function (text) {
    text = (text || "").trim();
    if (!text || this.busy) return;
    var max = parseInt(this.input.getAttribute("maxlength") || "500", 10);
    if (text.length > max) { this.note("Please keep it under " + max + " characters."); return; }
    this.busy = true;
    this.input.value = "";
    var chips = this.root.querySelector(".chat-suggestions");
    if (chips) chips.remove();
    this.bubble("user", text, false);
    var typing = this.typing(), self = this;
    fetch(this.endpoint, { method: "POST", credentials: "same-origin",
      headers: { "Content-Type": "application/json", "X-CSRFToken": csrf() },
      body: JSON.stringify({ message: text, session: this.session, audience: this.root.getAttribute("data-audience") || "" }) })
      .then(function (r) { return r.json().then(function (j) { return { ok: r.ok, j: j }; }); })
      .then(function (res) {
        typing.remove();
        if (res.j.session) { self.session = res.j.session; store(self.storeKey, self.session); }
        if (!res.ok) { self.note(res.j.error || "Something went wrong. Please try again."); return; }
        var b = self.bubble("assistant", res.j.html, true);   // sanitised server-side
        self.extras(b, res.j);
        self.answers += 1;
        if (self.answers === 2 && !res.j.lead) self.leadForm();
        if (res.j.lead) self.leadShown = true;
        var badge = self.root.querySelector("[data-mode]");
        if (badge) badge.textContent = (res.j.mode === "claude") ? "Powered by Claude" : "Offline demo answers";
      })
      .catch(function () { typing.remove(); self.note("Network problem — please check your connection."); })
      .then(function () { self.busy = false; self.input.focus(); });
  };

  document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll("[data-chat]").forEach(function (root) { root._chat = new Chat(root); });
    var panel = document.getElementById("chatPanel");
    if (!panel) return;
    function open() {
      panel.classList.add("open");
      document.body.classList.add("chat-open");
      setTimeout(function () { var i = panel.querySelector("textarea"); if (i) i.focus(); }, 50);
    }
    function close() { panel.classList.remove("open"); document.body.classList.remove("chat-open"); }
    document.querySelectorAll("[data-open-chat]").forEach(function (b) {
      b.addEventListener("click", function (e) { e.preventDefault(); open(); });
    });
    panel.querySelectorAll("[data-close-chat]").forEach(function (b) { b.addEventListener("click", close); });
    document.addEventListener("keydown", function (e) { if (e.key === "Escape") close(); });
  });
})();
