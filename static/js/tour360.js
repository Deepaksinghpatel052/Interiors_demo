/* 360° house tour on the portfolio page.
   The card shows a cheap animated preview; the Pannellum viewer (from the CDN) is only
   loaded when someone opens the tour. Rooms, info points and room links come from
   #tour360Data in the template. */
(function () {
  "use strict";
  var PANNELLUM = "https://cdn.jsdelivr.net/npm/pannellum@2.5.6/build/";

  var openBtn = document.getElementById("tour360Open");
  var overlay = document.getElementById("tour360");
  var dataEl = document.getElementById("tour360Data");
  if (!openBtn || !overlay || !dataEl) return;

  var data = JSON.parse(dataEl.textContent);
  var rooms = {};
  data.rooms.forEach(function (r) { rooms[r.id] = r; });
  var $ = function (id) { return document.getElementById(id); };
  var info = $("tour360Info"), loading = $("tour360Loading"), roomNav = $("tour360Rooms");
  var viewer = null, libPromise = null, lastFocus = null, activeSpot = null;

  function loadLib() {
    if (window.pannellum) return Promise.resolve();
    if (libPromise) return libPromise;
    libPromise = new Promise(function (resolve, reject) {
      var css = document.createElement("link");
      css.rel = "stylesheet"; css.href = PANNELLUM + "pannellum.css";
      document.head.appendChild(css);
      var s = document.createElement("script");
      s.src = PANNELLUM + "pannellum.js";
      s.onload = resolve;
      s.onerror = function () { libPromise = null; reject(new Error("load failed")); };
      document.head.appendChild(s);
    });
    return libPromise;
  }

  /* ---------- info dots ---------- */
  function makeDot(div, spot) {
    div.setAttribute("role", "button");
    div.setAttribute("tabindex", "0");
    div.setAttribute("aria-label", spot.title + " — details");
    div.innerHTML = '<span class="tour360-dot"><i class="bi bi-plus-lg"></i></span><span class="tour360-label"></span>';
    div.querySelector(".tour360-label").textContent = spot.title;
    div.addEventListener("keydown", function (e) {
      if (e.key === "Enter" || e.key === " ") { e.preventDefault(); showInfo(spot); }
    });
    spot._div = div;
  }

  function showInfo(spot) {
    if (activeSpot && activeSpot._div) activeSpot._div.classList.remove("is-active");
    activeSpot = spot;
    if (spot._div) spot._div.classList.add("is-active");
    $("tour360InfoTag").textContent = spot.tag || "";
    $("tour360InfoTitle").textContent = spot.title;
    $("tour360InfoText").textContent = spot.text || "";
    var ul = $("tour360InfoSpecs");
    ul.innerHTML = "";
    (spot.specs || []).forEach(function (t) {
      var li = document.createElement("li"); li.textContent = t; ul.appendChild(li);
    });
    info.hidden = false;
    if (viewer) {
      viewer.stopAutoRotate();
      viewer.lookAt(Math.max(-60, Math.min(60, spot.pitch)), spot.yaw, undefined, 700);
    }
  }

  function hideInfo() {
    info.hidden = true;
    if (activeSpot && activeSpot._div) activeSpot._div.classList.remove("is-active");
    activeSpot = null;
  }

  /* ---------- moving between rooms ---------- */
  function makeLink(div, link) {
    var room = rooms[link.to];
    div.setAttribute("role", "button");
    div.setAttribute("tabindex", "0");
    div.setAttribute("aria-label", "Go to " + room.title);
    div.innerHTML = '<span class="tour360-go-arrow"><i class="bi bi-arrow-up"></i></span><span class="tour360-go-label"></span>';
    div.querySelector(".tour360-go-label").textContent = room.title;
    div.addEventListener("keydown", function (e) {
      if (e.key === "Enter" || e.key === " ") { e.preventDefault(); goTo(link.to); }
    });
  }

  function goTo(id) {
    if (!viewer || viewer.getScene() === id) return;
    hideInfo();
    var s = rooms[id].start || {};
    viewer.loadScene(id, s.pitch || 0, s.yaw || 0, s.hfov || 105);
  }

  function buildRoomNav() {
    data.rooms.forEach(function (r, i) {
      var b = document.createElement("button");
      b.type = "button";
      b.className = "tour360-room";
      b.setAttribute("data-room", r.id);
      b.innerHTML = '<i class="bi ' + (r.icon || "bi-house") + '" aria-hidden="true"></i><span></span>';
      b.querySelector("span").textContent = r.title;
      b.addEventListener("click", function () { goTo(r.id); });
      roomNav.appendChild(b);
    });
  }

  function markRoom(id) {
    var room = rooms[id];
    $("tour360Title").textContent = (data.house ? data.house + " — " : "") + room.title;
    Array.prototype.forEach.call(roomNav.children, function (b) {
      var on = b.getAttribute("data-room") === id;
      b.classList.toggle("is-active", on);
      if (on) b.setAttribute("aria-current", "true"); else b.removeAttribute("aria-current");
    });
  }

  /* ---------- the viewer ---------- */
  function buildViewer() {
    var reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    var scenes = {};
    data.rooms.forEach(function (room) {
      var s = room.start || {};
      var hotSpots = (room.spots || []).map(function (spot) {
        return {
          pitch: spot.pitch, yaw: spot.yaw, cssClass: "tour360-spot",
          createTooltipFunc: makeDot, createTooltipArgs: spot,
          clickHandlerFunc: function (e, sp) { showInfo(sp); }, clickHandlerArgs: spot
        };
      }).concat((room.links || []).map(function (link) {
        return {
          pitch: link.pitch, yaw: link.yaw, cssClass: "tour360-go",
          createTooltipFunc: makeLink, createTooltipArgs: link,
          clickHandlerFunc: function (e, l) { goTo(l.to); }, clickHandlerArgs: link
        };
      }));
      scenes[room.id] = {
        title: room.title, type: "equirectangular", panorama: room.pano,
        yaw: s.yaw || 0, pitch: s.pitch || 0, hfov: s.hfov || 105,
        hotSpots: hotSpots
      };
    });

    viewer = window.pannellum.viewer("tour360Viewer", {
      "default": {
        firstScene: data.rooms[0].id,
        autoLoad: true,
        sceneFadeDuration: 900,
        autoRotate: reduce ? 0 : -2,
        autoRotateInactivityDelay: 8000,
        minHfov: 50, maxHfov: 120,
        showFullscreenCtrl: false,
        showControls: true,
        compass: false,
        friction: 0.12
      },
      scenes: scenes
    });
    markRoom(data.rooms[0].id);
    viewer.on("load", function () { loading.hidden = true; });
    viewer.on("scenechange", function (id) { hideInfo(); markRoom(id); });
    viewer.on("error", function () {
      loading.hidden = false;
      loading.textContent = "Sorry, the 360° view could not be loaded.";
    });
    startMouseLook();
  }

  // Look around just by moving the mouse (no click needed): the further the pointer is from the
  // centre of the screen, the faster the view turns that way. The middle of the screen is a calm
  // zone, and the view holds still while the pointer is on a dot, the details card or the menus.
  // Only for a real mouse — on touch screens visitors swipe as usual. Dragging still works too.
  var mouse = { x: 0, y: 0, inside: false, paused: false };
  var DEAD = 0.3, MAX_YAW = 70, MAX_PITCH = 40;   // calm zone (share of half-screen), degrees per second

  function startMouseLook() {
    if (!window.matchMedia("(hover: hover) and (pointer: fine)").matches) return;
    var box = $("tour360Viewer"), last = 0;

    overlay.addEventListener("mousemove", function (e) {
      var r = box.getBoundingClientRect();
      mouse.x = ((e.clientX - r.left) / r.width) * 2 - 1;
      mouse.y = ((e.clientY - r.top) / r.height) * 2 - 1;
      mouse.inside = true;
      if (viewer) viewer.stopAutoRotate();   // the visitor is in control now
      mouse.paused = e.buttons !== 0 ||
        !!e.target.closest(".tour360-spot, .tour360-go, .tour360-info, .tour360-bar, .tour360-rooms, .pnlm-controls-container");
    });
    overlay.addEventListener("mouseleave", function () { mouse.inside = false; });

    function speed(v) {   // 0 inside the calm zone, eases up to 1 at the screen edge
      var a = Math.abs(v);
      if (a <= DEAD) return 0;
      var t = Math.min(1, (a - DEAD) / (1 - DEAD));
      return (v < 0 ? -1 : 1) * t * t;
    }

    (function tick(now) {
      var dt = last ? Math.min(0.05, (now - last) / 1000) : 0;
      last = now;
      if (!overlay.hidden && viewer && mouse.inside && !mouse.paused) {
        var sx = speed(mouse.x), sy = speed(mouse.y);
        if (sx || sy) {
          viewer.stopAutoRotate();
          if (sx) viewer.setYaw(viewer.getYaw() + sx * MAX_YAW * dt, false);
          if (sy) viewer.setPitch(Math.max(-75, Math.min(75, viewer.getPitch() - sy * MAX_PITCH * dt)), false);
        }
      }
      requestAnimationFrame(tick);
    })(0);
  }

  /* ---------- open / close ---------- */
  function open() {
    lastFocus = document.activeElement;
    overlay.hidden = false;
    document.documentElement.classList.add("tour360-lock");
    $("tour360Close").focus();
    // Go truly full screen where the browser allows it (not iOS Safari — the overlay still fills the screen).
    if (overlay.requestFullscreen) overlay.requestFullscreen().catch(function () {});
    if (viewer) { viewer.resize(); return; }
    loading.hidden = false;
    loadLib().then(buildViewer).catch(function () {
      loading.textContent = "Sorry, the 360° view could not be loaded. Please check your connection.";
    });
  }

  function close() {
    if (overlay.hidden) return;
    hideInfo();
    mouse.inside = false;
    overlay.hidden = true;
    document.documentElement.classList.remove("tour360-lock");
    if (document.fullscreenElement === overlay && document.exitFullscreen) document.exitFullscreen().catch(function () {});
    if (lastFocus && lastFocus.focus) lastFocus.focus();
  }

  buildRoomNav();
  openBtn.addEventListener("click", open);
  $("tour360Close").addEventListener("click", close);
  $("tour360InfoClose").addEventListener("click", hideInfo);

  // Leaving browser full screen (Esc) closes the tour too, so one Esc gets the visitor out.
  document.addEventListener("fullscreenchange", function () {
    if (!document.fullscreenElement && !overlay.hidden) close();
    else if (viewer) viewer.resize();
  });

  document.addEventListener("keydown", function (e) {
    if (overlay.hidden || e.key !== "Escape") return;
    if (!info.hidden) hideInfo(); else close();
  });

  // Keep keyboard focus inside the dialog.
  overlay.addEventListener("keydown", function (e) {
    if (e.key !== "Tab") return;
    var items = Array.prototype.filter.call(
      overlay.querySelectorAll("button, a[href], [tabindex='0']"),
      function (el) { return el.offsetParent !== null; });
    if (!items.length) return;
    var first = items[0], last = items[items.length - 1];
    if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
    else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
  });
})();
