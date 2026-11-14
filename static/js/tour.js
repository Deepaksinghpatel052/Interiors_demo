/* Guided demo tour: a lightweight jQuery overlay that walks across pages and demo roles.
   Steps come from core/tour.py (json_script #tourSteps). Progress lives in localStorage. */
(function ($) {
  "use strict";
  var KEY = "demoTour";
  var dataEl = document.getElementById("tourSteps");
  if (!dataEl || !$) return;
  var steps = [];
  try { steps = JSON.parse(dataEl.textContent) || []; } catch (e) { return; }
  if (!steps.length) return;
  var body = document.body;
  var role = body.getAttribute("data-role") || "visitor";

  function load() { try { return JSON.parse(localStorage.getItem(KEY) || "null"); } catch (e) { return null; } }
  function save(s) { try { if (s) localStorage.setItem(KEY, JSON.stringify(s)); else localStorage.removeItem(KEY); } catch (e) { /* private mode */ } }
  function samePath(url) { return location.pathname === url; }
  function roleOk(step) { return step.role === "visitor" || step.role === role; }

  // ---------------------------------------------------------------- navigation across pages / roles
  function goTo(i) {
    if (i < 0 || i >= steps.length) return end();
    save({ on: true, i: i });
    var step = steps[i];
    if (!roleOk(step)) {
      var f = document.createElement("form");
      f.method = "post";
      f.action = (body.getAttribute("data-role-url") || "").replace("ROLE", step.role);
      [["csrfmiddlewaretoken", ($('meta[name="csrf-token"]').attr("content") || "")], ["next", step.url], ["quiet", "1"]]
        .forEach(function (kv) { var inp = document.createElement("input"); inp.type = "hidden"; inp.name = kv[0]; inp.value = kv[1]; f.appendChild(inp); });
      document.body.appendChild(f);
      f.submit();
      return;
    }
    if (!samePath(step.url)) { location.href = step.url; return; }
    show(i);
  }

  function end() {
    save(null);
    teardown();
    $(".tour-resume").remove();
  }

  // ---------------------------------------------------------------- overlay
  var $spot, $card, $shades, current = -1;

  function teardown() {
    $(window).off(".tour"); $(document).off(".tour");
    if ($spot) $spot.remove();
    if ($card) $card.remove();
    if ($shades) $shades.remove();
    $spot = $card = $shades = null; current = -1;
  }

  function target(step) {
    if (!step.el) return null;
    var found = null;
    step.el.split(",").some(function (sel) {
      var $el = $(sel.trim()).filter(":visible").first();
      if ($el.length) { found = $el; return true; }
      return false;
    });
    return found;
  }

  function show(i) {
    teardown();
    current = i;
    var step = steps[i];
    $(".tour-resume").remove();
    $shades = $('<div class="tour-shade"></div><div class="tour-shade"></div><div class="tour-shade"></div><div class="tour-shade"></div>')
      .attr("aria-hidden", "true").appendTo(body);
    $spot = $('<div class="tour-spot" aria-hidden="true"></div>').appendTo(body);
    $card = $('<div class="tour-card" role="dialog" aria-modal="false" aria-live="polite"></div>').appendTo(body);
    var last = i === steps.length - 1;
    $card.append(
      $('<div class="tour-top"></div>').append(
        $('<span class="tour-count"></span>').text("Step " + (i + 1) + " of " + steps.length),
        $('<button type="button" class="tour-x" aria-label="Close tour"><i class="bi bi-x-lg"></i></button>')),
      $('<h3 class="tour-title"></h3>').text(step.title),
      $('<p class="tour-text"></p>').text(step.text),
      $('<p class="tour-benefit"><i class="bi bi-graph-up-arrow"></i> <span></span></p>').find("span").text(step.benefit).end(),
      $('<div class="tour-bar"><span></span></div>').find("span").css("width", ((i + 1) / steps.length * 100) + "%").end(),
      $('<div class="tour-actions"></div>').append(
        i > 0 ? $('<button type="button" class="btn btn-light btn-sm tour-back">Back</button>') : $("<span></span>"),
        step.open_chat ? $('<button type="button" class="btn btn-outline-ink btn-sm tour-try"><i class="bi bi-chat-dots me-1"></i>Try it</button>') : null,
        step.try === "tour360" ? $('<button type="button" class="btn btn-outline-ink btn-sm tour-try"><i class="bi bi-arrow-repeat me-1"></i>Try it</button>') : null,
        $('<button type="button" class="btn btn-accent btn-sm tour-next"></button>').text(last ? "Finish" : "Next →"))
    );
    var $el = target(step);
    if ($el) {
      var rect = $el[0].getBoundingClientRect();
      if (rect.height > window.innerHeight * 0.5) window.scrollTo({ top: Math.max(0, rect.top + window.pageYOffset - 110), behavior: "smooth" });
      else $el[0].scrollIntoView({ block: "center", behavior: "smooth" });
    }
    else { $spot.addClass("no-target"); }
    setTimeout(place, $el ? 380 : 0);
    $(window).on("resize.tour scroll.tour", place);
    $card.on("click", ".tour-next", function () { last ? end() : goTo(i + 1); })
         .on("click", ".tour-back", function () { goTo(i - 1); })
         .on("click", ".tour-x", end)
         .on("click", ".tour-try", function () {
           teardown(); pauseBadge(i + 1);
           if (step.try === "tour360") document.getElementById("tour360Open").click();   // 360° house tour
           else $(".chat-launcher").first().trigger("click");
         });
    $(document).on("keydown.tour", function (e) {
      if (e.key === "Escape") end();
      else if (e.key === "ArrowRight") last ? end() : goTo(i + 1);
      else if (e.key === "ArrowLeft" && i > 0) goTo(i - 1);
    });
    $card.find(".tour-next").trigger("focus");
  }

  function place() {
    if (!$card) return;
    var $el = target(steps[current]);
    var vw = window.innerWidth, vh = window.innerHeight, cw = $card.outerWidth(), ch = $card.outerHeight();
    var mobile = vw < 576;
    if (!$el) {
      shade(0, 0, 0, 0, vw, vh);
      $spot.css({ top: vh / 2, left: vw / 2, width: 0, height: 0 });
      $card.toggleClass("sheet", mobile).css(mobile ? { top: "", left: "" }
        : { top: clamp((vh - ch) / 2, 12, vh - ch - 12), left: clamp((vw - cw) / 2, 12, vw - cw - 12) });
      return;
    }
    var r = $el[0].getBoundingClientRect(), pad = 8;
    var top = Math.max(r.top - pad, 4), left = Math.max(r.left - pad, 4);
    var h = Math.min(r.height + pad * 2, vh - top - 4), w = Math.min(r.width + pad * 2, vw - left - 4);
    $spot.removeClass("no-target").css({ top: top, left: left, width: w, height: h });
    shade(top, left, w, h, vw, vh);
    if (mobile) { $card.addClass("sheet").css({ top: "", left: "" }); return; }
    $card.removeClass("sheet");
    var m = 12, gap = 14, x, y;
    var fitsBelow = top + h + gap + ch <= vh - m, fitsAbove = top - gap - ch >= m;
    if (fitsBelow || fitsAbove) {                       // below the highlight, else above it
      y = fitsBelow ? top + h + gap : top - ch - gap;
      x = left;
    } else if (left + w + gap + cw <= vw - m) {         // tall target: beside it, on the right
      x = left + w + gap; y = top;
    } else if (left - gap - cw >= m) {                  // ... or on the left
      x = left - cw - gap; y = top;
    } else {                                            // no free side: bottom-right corner
      x = vw - cw - 20; y = vh - ch - 20;
    }
    // Always keep the whole card (and its Next button) inside the visible window.
    $card.css({ top: clamp(y, m, vh - ch - m), left: clamp(x, m, vw - cw - m) });
  }

  function clamp(v, min, max) { return Math.max(min, Math.min(v, Math.max(min, max))); }

  // four dim panels around the highlighted box (more reliable than a huge box-shadow)
  function shade(t, l, w, h, vw, vh) {
    if (!$shades) return;
    var b = t + h, r = l + w;
    var boxes = w && h ? [[0, 0, vw, t], [b, 0, vw, Math.max(0, vh - b)], [t, 0, l, h], [t, r, Math.max(0, vw - r), h]]
                       : [[0, 0, vw, vh], [0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]];
    $shades.each(function (k) { $(this).css({ top: boxes[k][0], left: boxes[k][1], width: boxes[k][2], height: boxes[k][3] }); });
  }

  function pauseBadge(i) {
    $(".tour-resume").remove();
    var step = steps[i]; if (!step) return;
    save({ on: true, i: i });
    $('<button type="button" class="tour-resume"><i class="bi bi-signpost-2 me-1"></i></button>')
      .append($("<span></span>").text("Continue tour · step " + (i + 1)))
      .append('<span class="tour-resume-x" aria-label="End tour" role="button">&times;</span>')
      .appendTo(body)
      .on("click", function (e) { if ($(e.target).hasClass("tour-resume-x")) { end(); } else { goTo(i); } });
  }

  // ---------------------------------------------------------------- boot
  $(document).on("click", "[data-tour-start]", function (e) { e.preventDefault(); goTo(0); });
  $(function () {
    if (/[?&]tour=1\b/.test(location.search)) { goTo(0); return; }
    var s = load();
    if (!s || !s.on || !steps[s.i]) return;
    var step = steps[s.i];
    if (samePath(step.url) && roleOk(step)) show(s.i);
    else pauseBadge(s.i);
  });
})(window.jQuery);
