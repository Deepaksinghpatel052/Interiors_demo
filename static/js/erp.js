/* Studio ERP: dashboard charts, Kanban boards, bookings calendar. jQuery + Bootstrap. */
(function ($) {
  "use strict";
  var toast = function (m, t) { window.Studio.toast(m, t); };
  var csrf = function () { return window.Studio.csrfToken(); };
  var css = getComputedStyle(document.documentElement);
  var ACCENT = (css.getPropertyValue("--accent") || "#0081F6").trim();
  var DEEP = (css.getPropertyValue("--deep") || "#111212").trim();
  var MUTED = (css.getPropertyValue("--muted") || "#5B6470").trim();
  var GRID = "#EEF1F5";
  var SURFACE = "#FFFFFF";
  var ACCENT2 = (css.getPropertyValue("--accent-2") || "#2474F8").trim();
  function rgba(hex, a) {
    var m = /^#?([0-9a-f]{2})([0-9a-f]{2})([0-9a-f]{2})$/i.exec(hex) || [0, "00", "81", "f6"];
    return "rgba(" + parseInt(m[1], 16) + "," + parseInt(m[2], 16) + "," + parseInt(m[3], 16) + "," + a + ")";
  }
  var PALETTE = [ACCENT, DEEP, ACCENT2, "#5B6470", "#A9B2BE", "#C9D3DF", "#E4E9F0"];

  function postJSON(url, data) {
    return $.ajax({ url: url, method: "POST", contentType: "application/json", data: JSON.stringify(data),
                    headers: { "X-CSRFToken": csrf() } });
  }

  $(function () {
    // ======================================================== Charts
    var $cd = $("#chartData");
    if ($cd.length && window.Chart) {
      var d = JSON.parse($cd.text());
      Chart.defaults.font.family = "Inter, system-ui, sans-serif";
      Chart.defaults.color = MUTED;
      Chart.defaults.borderColor = GRID;
      Chart.defaults.plugins.legend.labels.boxWidth = 10;
      var lbl = function (rows) { return rows.map(function (r) { return r[0]; }); };
      var val = function (rows) { return rows.map(function (r) { return r[1]; }); };
      var src = d.sources.filter(function (r) { return r[1] > 0; });
      new Chart(document.getElementById("chartSources"), {
        type: "doughnut",
        data: { labels: lbl(src), datasets: [{ data: val(src), backgroundColor: PALETTE, borderWidth: 3, borderColor: SURFACE }] },
        options: { maintainAspectRatio: false, cutout: "62%", plugins: { legend: { position: "bottom" } } }
      });
      new Chart(document.getElementById("chartFunnel"), {
        type: "bar",
        data: { labels: lbl(d.funnel), datasets: [{ data: val(d.funnel), backgroundColor: d.funnel.map(function (_, i) {
          return i === d.funnel.length - 1 ? DEEP : ACCENT; }), borderRadius: 6, barThickness: 18 }] },
        options: { indexAxis: "y", maintainAspectRatio: false, plugins: { legend: { display: false } },
                   scales: { x: { grid: { display: false }, ticks: { precision: 0 } }, y: { grid: { display: false } } } }
      });
      if (d.revenue && document.getElementById("chartRevenue")) {
        var ctx = document.getElementById("chartRevenue").getContext("2d");
        var grad = ctx.createLinearGradient(0, 0, 0, 220);
        grad.addColorStop(0, rgba(ACCENT, .28)); grad.addColorStop(1, rgba(ACCENT, 0));
        new Chart(ctx, {
          type: "line",
          data: { labels: lbl(d.revenue), datasets: [{ data: val(d.revenue), borderColor: ACCENT, backgroundColor: grad, fill: true,
                  tension: .35, pointRadius: 4, pointBackgroundColor: "#fff", pointBorderColor: ACCENT, pointBorderWidth: 2 }] },
          options: { maintainAspectRatio: false, plugins: { legend: { display: false }, tooltip: { callbacks: {
                       label: function (c) { return " ₹" + Number(c.parsed.y).toLocaleString("en-IN"); } } } },
                     scales: { y: { grid: { color: GRID }, ticks: { callback: function (v) {
                       return v >= 100000 ? "₹" + (v / 100000).toFixed(v % 100000 ? 1 : 0) + "L" : "₹" + Number(v).toLocaleString("en-IN"); } } },
                               x: { grid: { display: false } } } }
        });
      }
      new Chart(document.getElementById("chartStages"), {
        type: "bar",
        data: { labels: lbl(d.stages), datasets: [{ data: val(d.stages), backgroundColor: DEEP, borderRadius: 6, barThickness: 22 }] },
        options: { maintainAspectRatio: false, plugins: { legend: { display: false } },
                   scales: { y: { ticks: { precision: 0 }, grid: { color: GRID } }, x: { grid: { display: false } } } }
      });
    }

    // ======================================================== Kanban (leads & projects)
    function kanban($board, idKey) {
      if (!$board.length || !$.fn.sortable) return;
      var url = $board.data("move-url");
      var fromStage = null;
      $board.find(".kanban-list").sortable({
        connectWith: $board.find(".kanban-list"),
        items: ".kcard",
        placeholder: "kcard-placeholder",
        cancel: "a, button",
        distance: 6,
        tolerance: "pointer",
        start: function (e, ui) { fromStage = ui.item.closest(".kanban-list").data("stage"); },
        update: function (e, ui) {
          // fires for both lists; only handle the list that now contains the item
          if (ui.item.parent()[0] !== this) return;
          var $list = $(this), stage = $list.data("stage");
          var order = $list.children(".kcard").map(function () { return $(this).data("id"); }).get();
          var payload = { stage: stage, order: order };
          payload[idKey] = ui.item.data("id");
          postJSON(url, payload).done(function (r) {
            if (stage !== fromStage) toast((ui.item.find(".kname").text() || "Card") + " moved to " + r.stage_label);
            $board.find(".kanban-col").each(function () {
              $(this).find(".kanban-count").text($(this).find(".kcard").length);
            });
          }).fail(function () {
            toast("Could not save that move. Please refresh and try again.", "error");
          });
        }
      });
    }
    kanban($("#leadBoard"), "lead");
    kanban($("#projectBoard"), "project");

    // ======================================================== Calendar
    var calEl = document.getElementById("calendar");
    if (calEl && window.FullCalendar) {
      var $m = $("#bookingModal"), modal = new bootstrap.Modal($m[0]), current = null;
      var mobile = window.matchMedia("(max-width: 767.98px)").matches;
      var cal = new FullCalendar.Calendar(calEl, {
        initialView: mobile ? "listWeek" : "timeGridWeek",
        headerToolbar: mobile ? { left: "prev,next", center: "title", right: "listWeek,dayGridMonth" }
                              : { left: "prev,next today", center: "title", right: "dayGridMonth,timeGridWeek,listWeek" },
        buttonText: { today: "Today", month: "Month", week: "Week", list: "List" },
        firstDay: 1, slotMinTime: "08:00:00", slotMaxTime: "21:00:00", allDaySlot: false,
        height: "auto", nowIndicator: true, editable: true, eventDurationEditable: false,
        locale: "en-gb", timeZone: "local",
        eventTimeFormat: { hour: "numeric", minute: "2-digit", meridiem: "short" },
        slotLabelFormat: { hour: "numeric", meridiem: "short" },
        events: $(calEl).data("events-url"),
        noEventsContent: "No bookings in this period",
        eventClick: function (info) {
          if (info.event.display === "background") return;
          current = info.event;
          var p = current.extendedProps;
          $("#bmRef").text(p.reference);
          $("#bmTitle").text(p.name);
          $("#bmWhen").text(p.when);
          $("#bmMode").text(p.mode);
          $("#bmMobile").text(p.mobile);
          $("#bmStatus").text(p.statusLabel);
          $("#bmAddress").text(p.address); $("#bmAddressWrap").toggle(!!p.address);
          $("#bmNotes").text(p.notes); $("#bmNotesWrap").toggle(!!p.notes);
          var digits = String(p.mobile).replace(/\D/g, ""); if (digits.length === 10) digits = "91" + digits;
          $("#bmCall").attr("href", "tel:+" + digits);
          $("#bmWa").attr("href", "https://wa.me/" + digits + "?text=" + encodeURIComponent(
            "Hi " + p.name + ", this is " + $("#studioWa").data("name") + " about your consultation on " + p.when + "."));
          $("#bmLead").toggle(!!p.leadUrl).attr("href", p.leadUrl || "#");
          modal.show();
        },
        eventDrop: function (info) {
          var url = $(calEl).data("move-url-template").replace("/0/", "/" + info.event.id + "/");
          var s = info.event.start, pad = function (n) { return String(n).padStart(2, "0"); };
          var local = s.getFullYear() + "-" + pad(s.getMonth() + 1) + "-" + pad(s.getDate()) + "T" + pad(s.getHours()) + ":" + pad(s.getMinutes()) + ":00";
          var off = -s.getTimezoneOffset(), sign = off >= 0 ? "+" : "-";
          local += sign + pad(Math.floor(Math.abs(off) / 60)) + ":" + pad(Math.abs(off) % 60);
          postJSON(url, { start: local }).done(function (r) {
            info.event.setExtendedProp("when", r.when);
            toast("Rescheduled to " + r.when);
          }).fail(function (x) {
            info.revert();
            toast((x.responseJSON && x.responseJSON.error) || "Could not reschedule.", "error");
          });
        }
      });
      cal.render();
      $m.on("click", ".bm-status", function () {
        if (!current) return;
        var url = $("#bmStatusUrl").data("template").replace("/0/", "/" + current.id + "/");
        $.ajax({ url: url, method: "POST", data: { status: $(this).data("status") },
                 headers: { "X-CSRFToken": csrf(), "X-Requested-With": "XMLHttpRequest" } })
          .done(function (r) { modal.hide(); toast("Marked " + r.label.toLowerCase()); cal.refetchEvents(); })
          .fail(function () { toast("Could not update the booking.", "error"); });
      });
    }
  });
})(jQuery);
