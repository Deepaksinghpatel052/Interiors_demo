/* Public site behaviour. jQuery + Bootstrap 5 only. */
(function ($) {
  "use strict";

  // ---------- Toasts (also used by later phases via window.Studio.toast) ----------
  function toast(message, type) {
    type = type || "success";
    var icon = type === "error" ? "exclamation-circle" : (type === "info" ? "info-circle" : "check-circle");
    var $t = $('<div class="toast ' + type + '" role="status" aria-live="polite"><div class="toast-body">' +
      '<i class="bi bi-' + icon + '"></i><div class="flex-grow-1"></div>' +
      '<button type="button" class="btn-close btn-sm ms-2" data-bs-dismiss="toast" aria-label="Close"></button></div></div>');
    $t.find(".flex-grow-1").text(message);
    $("#toastStack").append($t);
    var t = new bootstrap.Toast($t[0], { delay: 4500 });
    $t.on("hidden.bs.toast", function () { $t.remove(); });
    t.show();
  }
  function getCookie(name) {
    var m = document.cookie.match(new RegExp("(?:^|; )" + name + "=([^;]*)"));
    return m ? decodeURIComponent(m[1]) : "";
  }
  window.Studio = window.Studio || {};
  window.Studio.toast = toast;
  window.Studio.getCookie = getCookie;
  function csrfToken() { return $('meta[name="csrf-token"]').attr("content") || getCookie("csrftoken"); }
  window.Studio.csrfToken = csrfToken;

  $(function () {
    // Django messages → toasts
    $("#djangoMessages [data-msg]").each(function () {
      var tag = $(this).data("tag") || "success";
      toast($(this).data("msg"), tag.indexOf("error") > -1 ? "error" : (tag.indexOf("info") > -1 ? "info" : "success"));
    });

    // Demo ribbon dismiss (remembered for 7 days)
    $(".ribbon-close").on("click", function () {
      $(".demo-ribbon").slideUp(150);
      document.cookie = "demo_ribbon=hidden; path=/; max-age=" + 60 * 60 * 24 * 7 + "; SameSite=Lax";
    });

    // Navbar border on scroll
    var $nav = $(".site-nav");
    var onScroll = function () { $nav.toggleClass("scrolled", window.scrollY > 8); };
    $(window).on("scroll", onScroll); onScroll();
    document.documentElement.style.setProperty("--nav-h", ($nav.outerHeight() || 72) + "px");

    // Reveal on scroll
    if ("IntersectionObserver" in window) {
      var io = new IntersectionObserver(function (entries) {
        entries.forEach(function (e) { if (e.isIntersecting) { e.target.classList.add("in"); io.unobserve(e.target); } });
      }, { rootMargin: "0px 0px -8% 0px" });
      $(".reveal").each(function () { io.observe(this); });
    } else { $(".reveal").addClass("in"); }

    // Submit buttons show a loading state and prevent double submits
    $("form[data-loading]").on("submit", function () {
      var $b = $(this).find("[type=submit]");
      if ($b.prop("disabled")) return false;
      $b.prop("disabled", true).data("label", $b.html())
        .html('<span class="spinner-border me-2" role="status" aria-hidden="true"></span>' + ($b.data("loading-text") || "Sending…"));
    });

    // ---------- Confirmation dialogs for forms with data-confirm ----------
    var $confirm = $('<div class="modal fade" tabindex="-1" aria-hidden="true"><div class="modal-dialog modal-dialog-centered modal-sm">' +
      '<div class="modal-content border-0" style="border-radius:16px"><div class="modal-body p-4"><p class="mb-4 confirm-text"></p>' +
      '<div class="d-flex gap-2 justify-content-end"><button type="button" class="btn btn-light btn-sm" data-bs-dismiss="modal">Cancel</button>' +
      '<button type="button" class="btn btn-accent btn-sm confirm-ok">Yes, continue</button></div></div></div></div></div>').appendTo("body");
    var pendingForm = null;
    $(document).on("submit", "form[data-confirm]", function (e) {
      if (this._confirmed) return;
      e.preventDefault();
      e.stopImmediatePropagation();
      pendingForm = this;
      $confirm.find(".confirm-text").text($(this).data("confirm"));
      bootstrap.Modal.getOrCreateInstance($confirm[0]).show();
    });
    $confirm.on("click", ".confirm-ok", function () {
      if (!pendingForm) return;
      pendingForm._confirmed = true;
      bootstrap.Modal.getInstance($confirm[0]).hide();
      if (pendingForm.requestSubmit) pendingForm.requestSubmit(); else pendingForm.submit();
    });

    // ---------- Locked “full version” features ----------
    var lockedData = {};
    try { lockedData = JSON.parse($("#lockedFeatures").text() || "{}"); } catch (e) { lockedData = {}; }
    var lockedKey = null;
    $(document).on("click", "[data-locked]", function (e) {
      e.preventDefault();
      lockedKey = $(this).data("locked");
      var f = lockedData[lockedKey];
      if (!f) return;
      $("#lockedTitle").text(f.title);
      $("#lockedWhat").text(f.what);
      $("#lockedBenefit").text(f.benefit);
      bootstrap.Modal.getOrCreateInstance(document.getElementById("lockedModal")).show();
    });
    $("#lockedWant").on("click", function () {
      if (!lockedKey) return;
      var $b = $(this).prop("disabled", true);
      // Open the tab synchronously so pop-up blockers allow it; point it at WhatsApp when the server replies.
      var win = window.open("about:blank", "_blank");
      $.ajax({ url: $b.data("url-template").replace("KEY", lockedKey), method: "POST",
               headers: { "X-CSRFToken": csrfToken() } })
        .done(function (r) {
          if (r.wa_url && win) { win.location = r.wa_url; } else if (win) { win.close(); }
          bootstrap.Modal.getInstance(document.getElementById("lockedModal")).hide();
          toast("Noted! We’ll show you how this works for your studio.");
        })
        .fail(function () { if (win) win.close(); toast("Could not record that just now. Please try again.", "error"); })
        .always(function () { $b.prop("disabled", false); });
    });

    // ---------- Portfolio: instant filtering ----------
    var $grid = $("#portfolioGrid");
    if ($grid.length) {
      var state = { room: $grid.data("room") || "", style: $grid.data("style") || "", budget: $grid.data("budget") || "" };
      var apply = function () {
        var shown = 0;
        $grid.find(".masonry-item").each(function () {
          var $i = $(this);
          var ok = (!state.room || $i.data("room") === state.room) &&
                   (!state.style || $i.data("style") === state.style) &&
                   (!state.budget || $i.data("budget") === state.budget);
          $i.toggleClass("is-hidden", !ok);
          if (ok) shown++;
        });
        $("#portfolioEmpty").toggleClass("d-none", shown > 0);
        $("#portfolioCount").text(shown + (shown === 1 ? " project" : " projects"));
        var qs = $.param(Object.fromEntries(Object.entries(state).filter(function (kv) { return kv[1]; })));
        history.replaceState(null, "", location.pathname + (qs ? "?" + qs : ""));
      };
      $(".filter-group .chip").on("click", function (e) {
        e.preventDefault();
        var $c = $(this), key = $c.data("key"), val = $c.data("val") || "";
        state[key] = val;
        $c.closest(".filter-group").find(".chip").removeClass("active");
        $c.addClass("active");
        apply();
      });
      $("#resetFilters").on("click", function (e) {
        e.preventDefault();
        state = { room: "", style: "", budget: "" };
        $(".filter-group").each(function () { $(this).find(".chip").removeClass("active").first().addClass("active"); });
        apply();
      });
      // Keep the active chip visible in horizontally-scrolling groups on phones.
      $(".filter-group .chip.active").each(function () {
        var g = this.parentNode;
        g.scrollLeft = this.offsetLeft - g.offsetLeft - 80;
      });
      apply();
    }

    // ---------- Lightbox ----------
    var $lb = $("#lightbox");
    if ($lb.length) {
      var items = [], idx = 0, modal = new bootstrap.Modal($lb[0]);
      var show = function (i) {
        idx = (i + items.length) % items.length;
        $lb.find("img").attr({ src: items[idx].src, alt: items[idx].caption });
        $lb.find(".lb-caption").text(items[idx].caption || "");
        $lb.find(".lb-count").text((idx + 1) + " / " + items.length);
      };
      $(document).on("click", "[data-lightbox]", function (e) {
        e.preventDefault();
        var group = $(this).data("lightbox");
        var $all = $('[data-lightbox="' + group + '"]');
        items = $all.map(function () { return { src: $(this).attr("href"), caption: $(this).data("caption") }; }).get();
        show($all.index(this));
        modal.show();
      });
      $lb.on("click", ".lb-prev", function () { show(idx - 1); });
      $lb.on("click", ".lb-next", function () { show(idx + 1); });
      $(document).on("keydown", function (e) {
        if (!$lb.hasClass("show")) return;
        if (e.key === "ArrowLeft") show(idx - 1);
        if (e.key === "ArrowRight") show(idx + 1);
      });
      // swipe on phones
      var x0 = null;
      $lb.on("touchstart", function (e) { x0 = e.originalEvent.touches[0].clientX; });
      $lb.on("touchend", function (e) {
        if (x0 === null) return;
        var dx = e.originalEvent.changedTouches[0].clientX - x0;
        if (Math.abs(dx) > 40) show(idx + (dx < 0 ? 1 : -1));
        x0 = null;
      });
    }

    // ---------- Before / after slider ----------
    $(".ba-slider").each(function () {
      var $s = $(this), $wrap = $s.find(".ba-after-wrap"), $h = $s.find(".ba-handle"), dragging = false;
      var set = function (clientX) {
        var r = $s[0].getBoundingClientRect();
        var p = Math.max(0, Math.min(100, ((clientX - r.left) / r.width) * 100));
        $wrap.css("clip-path", "inset(0 0 0 " + p + "%)");
        $h.css("left", p + "%");
        $s.attr("aria-valuenow", Math.round(p));
      };
      $s.on("mousedown touchstart", function (e) {
        dragging = true;
        set(e.type === "touchstart" ? e.originalEvent.touches[0].clientX : e.clientX);
      });
      $(window).on("mousemove touchmove", function (e) {
        if (!dragging) return;
        set(e.type === "touchmove" ? e.originalEvent.touches[0].clientX : e.clientX);
      }).on("mouseup touchend", function () { dragging = false; });
      $s.on("keydown", function (e) {
        var now = parseFloat($s.attr("aria-valuenow") || 50), r = $s[0].getBoundingClientRect();
        if (e.key === "ArrowLeft" || e.key === "ArrowRight") {
          e.preventDefault();
          set(r.left + r.width * (now + (e.key === "ArrowLeft" ? -5 : 5)) / 100);
        }
      });
    });
  });
})(jQuery);
