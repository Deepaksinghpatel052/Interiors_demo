/* Live client activity for the studio: polls every 20 s and shows a toast with a link. No dependencies. */
(function () {
  "use strict";
  var el = document.getElementById("liveActivity");
  if (!el) return;
  var url = el.getAttribute("data-url");
  var since = el.getAttribute("data-since");
  var ICON = { approved: "patch-check-fill", changes: "pencil-square", comment: "chat-left-text", request: "flag", automation: "whatsapp" };

  function show(ev) {
    var stack = document.getElementById("toastStack");
    if (!stack || !window.bootstrap) return;
    var t = document.createElement("div");
    t.className = "toast live-toast " + (ev.kind === "approved" ? "success" : ev.kind === "automation" ? "info auto" : "info");
    t.setAttribute("role", "status");
    t.innerHTML = '<div class="toast-body"><i class="bi"></i><div class="flex-grow-1"><div class="fw-semibold small text-muted live-label"></div>' +
      '<a class="live-link"></a></div><button type="button" class="btn-close btn-sm ms-2" data-bs-dismiss="toast" aria-label="Close"></button></div>';
    t.querySelector(".live-label").textContent = ev.kind === "automation" ? "Automation" : "Client update";
    t.querySelector(".bi").className = "bi bi-" + (ICON[ev.kind] || "bell");
    var a = t.querySelector(".live-link");
    a.textContent = ev.text;          // text only: never inject HTML from the server
    a.href = ev.url;
    stack.appendChild(t);
    var toast = new window.bootstrap.Toast(t, { delay: 9000 });
    t.addEventListener("hidden.bs.toast", function () { t.remove(); });
    toast.show();
    var badge = document.getElementById("liveBadge");
    if (badge) { badge.textContent = String((parseInt(badge.textContent, 10) || 0) + 1); badge.hidden = false; }
  }

  function poll() {
    if (document.hidden) return;
    fetch(url + "?since=" + encodeURIComponent(since), { credentials: "same-origin", headers: { "Accept": "application/json" } })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (data) {
        if (!data) return;
        since = data.now;
        (data.events || []).slice().reverse().forEach(show);
      })
      .catch(function () { /* offline: try again next tick */ });
  }
  setInterval(poll, 20000);
  document.addEventListener("visibilitychange", function () { if (!document.hidden) poll(); });
})();
