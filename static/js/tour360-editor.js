/* Studio CMS: place 360° tour info dots and room arrows by clicking on the photo.
   Reads #tourEdData (photo, start view, existing hotspots); writes the clicked angles into the
   dot/arrow form, and the current view into the room's start-view fields. */
(function () {
  "use strict";
  var PANNELLUM = "https://cdn.jsdelivr.net/npm/pannellum@2.5.6/build/";
  var dataEl = document.getElementById("tourEdData");
  var box = document.getElementById("tourEdView");
  if (!dataEl || !box) return;
  var data = JSON.parse(dataEl.textContent);
  var $ = function (id) { return document.getElementById(id); };
  var yawIn = $("id_spot-yaw"), pitchIn = $("id_spot-pitch"), spotForm = $("tourSpotForm");
  var viewer = null;

  function load(cb) {
    if (window.pannellum) return cb();
    var css = document.createElement("link");
    css.rel = "stylesheet"; css.href = PANNELLUM + "pannellum.css";
    document.head.appendChild(css);
    var s = document.createElement("script");
    s.src = PANNELLUM + "pannellum.js"; s.onload = cb;
    s.onerror = function () { box.innerHTML = '<div class="empty-mini py-5">The 360° viewer could not be loaded. Check the internet connection.</div>'; };
    document.head.appendChild(s);
  }

  function dot(div, spot) {
    var link = spot.kind === "link";
    div.innerHTML = link
      ? '<span class="tour360-go-arrow"><i class="bi bi-arrow-up"></i></span><span class="tour360-go-label"></span>'
      : '<span class="tour360-dot"><i class="bi bi-plus-lg"></i></span><span class="tour360-label"></span>';
    div.querySelector(link ? ".tour360-go-label" : ".tour360-label").textContent = spot.title || "New";
    if (spot.id === data.editing || spot.id === "new") div.classList.add("is-active");
  }

  function hs(spot) {
    return {
      id: String(spot.id), pitch: spot.pitch, yaw: spot.yaw,
      cssClass: (spot.kind === "link" ? "tour360-go" : "tour360-spot") + " tour-ed-spot",
      createTooltipFunc: dot, createTooltipArgs: spot,
      clickHandlerFunc: function () {
        if (spot.id !== "new" && spot.id !== data.editing) window.location.search = "?spot=" + spot.id;
      }
    };
  }

  function currentKind() {
    var r = spotForm && spotForm.querySelector("input[name='spot-kind']:checked");
    return r ? r.value : "info";
  }

  // Show only the fields that belong to the chosen type (info dot vs arrow).
  function syncKind() {
    if (!spotForm) return;
    var k = currentKind();
    Array.prototype.forEach.call(spotForm.querySelectorAll("[data-kind]"), function (el) {
      el.hidden = el.getAttribute("data-kind") !== k;
    });
  }

  // Put the marker being placed / moved at the clicked spot.
  function place(pitch, yaw) {
    if (!yawIn || !pitchIn) return;
    yawIn.value = yaw.toFixed(1);
    pitchIn.value = pitch.toFixed(1);
    var id = data.editing ? String(data.editing) : "new";
    var existing = data.spots.filter(function (s) { return String(s.id) === id; })[0];
    var titleIn = $("id_spot-title"), linkIn = $("id_spot-link_to");
    var spot = existing ? Object.assign({}, existing) : { id: "new", kind: currentKind() };
    spot.pitch = pitch; spot.yaw = yaw;
    if (!existing) {
      spot.kind = currentKind();
      spot.title = spot.kind === "link"
        ? (linkIn && linkIn.selectedIndex > 0 ? linkIn.options[linkIn.selectedIndex].text : "Room")
        : ((titleIn && titleIn.value) || "New info dot");
    }
    viewer.removeHotSpot(id);
    viewer.addHotSpot(hs(spot));
    var hint = $("posHint");
    if (hint) hint.innerHTML = '<i class="bi bi-check2 me-1"></i>Position set — fill in the details and save. Click again to move it.';
    if (!existing && titleIn && spot.kind === "info" && !titleIn.value) titleIn.focus({ preventScroll: true });
  }

  function init() {
    var s = data.start || {};
    viewer = window.pannellum.viewer("tourEdView", {
      type: "equirectangular", panorama: data.pano, autoLoad: true,
      yaw: s.yaw || 0, pitch: s.pitch || 0, hfov: s.hfov || 105, minHfov: 40, maxHfov: 120,
      showFullscreenCtrl: true, compass: false, friction: 0.15,
      hotSpots: data.spots.map(hs)
    });
    // If a dot is being edited, look at it.
    if (data.editing) {
      var e = data.spots.filter(function (sp) { return sp.id === data.editing; })[0];
      if (e) viewer.on("load", function () { viewer.lookAt(Math.max(-60, Math.min(60, e.pitch)), e.yaw, undefined, false); });
    }

    // A click (not a drag) on the photo sets the position.
    var down = null;
    box.addEventListener("pointerdown", function (ev) { down = { x: ev.clientX, y: ev.clientY }; });
    box.addEventListener("pointerup", function (ev) {
      if (!down || !yawIn) return;
      var moved = Math.abs(ev.clientX - down.x) + Math.abs(ev.clientY - down.y);
      down = null;
      if (moved > 6 || ev.target.closest(".pnlm-hotspot-base, .pnlm-controls-container")) return;
      var c = viewer.mouseEventToCoords(ev);   // [pitch, yaw]
      place(c[0], c[1]);
    });

    var useStart = $("tourEdUseStart");
    if (useStart) useStart.addEventListener("click", function () {
      $("id_start_yaw").value = viewer.getYaw().toFixed(1);
      $("id_start_pitch").value = viewer.getPitch().toFixed(1);
      $("id_start_hfov").value = viewer.getHfov().toFixed(0);
      useStart.innerHTML = '<i class="bi bi-check2 me-1"></i>Start view set — now “Save room”';
      var form = $("tourRoomForm");
      if (form) form.querySelector("button.btn-accent").classList.add("pulse-once");
    });
  }

  if (spotForm) {
    spotForm.addEventListener("change", function (e) {
      if (e.target.name === "spot-kind") syncKind();
    });
    syncKind();
  }
  load(init);
})();
