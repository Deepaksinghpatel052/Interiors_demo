/* Booking slots, cost estimator and style quiz. jQuery only. */
(function ($) {
  "use strict";

  var MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  function fmtDate(iso) { // 2026-11-12 -> Thu, 12-11-2026
    var p = iso.split("-"), d = new Date(+p[0], +p[1] - 1, +p[2]);
    return d.toLocaleDateString("en-IN", { weekday: "short" }) + ", " + p[2] + "-" + p[1] + "-" + p[0];
  }
  function inr(n) { return "₹" + Number(n).toLocaleString("en-IN"); }

  $(function () {
    // =================================================== Booking
    var $bf = $("#bookingForm");
    if ($bf.length) {
      var $date = $bf.find("input[name=date]"), $time = $bf.find("input[name=time]");
      var $grid = $("#slotGrid"), $hint = $("#slotHint"), $btn = $("#bookBtn");

      var refresh = function () {
        var $mode = $bf.find("input[name=mode]:checked");
        $("#sumMode").text($mode.length ? $mode.closest("label").find(".fw-semibold").text() : "—");
        $("#sumDate").text($date.val() ? fmtDate($date.val()) : "—");
        $("#sumTime").text($time.val() ? $grid.find(".slot.active").text() || $time.val() : "—");
        $("#siteAddressWrap").toggle($mode.val() === "site_visit");
        $btn.prop("disabled", !($mode.length && $date.val() && $time.val()));
      };

      var loadSlots = function (iso, keepTime) {
        $hint.addClass("d-none");
        $grid.html(new Array(7).join('<span class="slot skeleton"></span>'));
        $.getJSON($bf.data("slots-url"), { date: iso })
          .done(function (r) {
            $grid.empty();
            var any = false;
            $.each(r.slots, function (_, s) {
              any = any || s.available;
              $("<button type='button' class='slot'>").text(s.label).attr("data-time", s.time)
                .prop("disabled", !s.available).attr("title", s.available ? "" : "Already booked")
                .toggleClass("active", keepTime === s.time && s.available).appendTo($grid);
            });
            if (!any) {
              $grid.html('<p class="text-muted small mb-0">No free times left on this day — please pick another.</p>');
            }
            if (!$grid.find(".slot.active").length) $time.val("");
            refresh();
          })
          .fail(function () {
            $grid.html('<p class="text-danger small mb-0">Could not load times. Please check your connection and try again.</p>');
          });
      };

      $bf.on("click", ".date-pill", function () {
        $(".date-pill").removeClass("active").attr("aria-selected", "false");
        $(this).addClass("active").attr("aria-selected", "true");
        $date.val($(this).data("date"));
        $time.val("");
        loadSlots($(this).data("date"));
        refresh();
      });
      $grid.on("click", ".slot:not(:disabled)", function () {
        $grid.find(".slot").removeClass("active");
        $(this).addClass("active");
        $time.val($(this).data("time"));
        refresh();
      });
      $bf.on("change", "input[name=mode]", refresh);

      // Restore a previous selection after a validation error.
      var selDate = $bf.data("selected-date"), selTime = $bf.data("selected-time");
      if (selDate) {
        var $pill = $('.date-pill[data-date="' + selDate + '"]');
        if ($pill.length) { $pill.addClass("active"); $date.val(selDate); loadSlots(selDate, String(selTime || "").slice(0, 5)); }
        else { $date.val(""); $time.val(""); }
      }
      if (!$bf.find("input[name=mode]:checked").length) $bf.find("input[name=mode]").first().prop("checked", true);
      refresh();
    }

    // =================================================== Estimator
    var $ef = $("#estimateForm");
    if ($ef.length) {
      var defaults = $ef.data("default-rooms"), areas = $ef.data("room-areas");
      var $area = $("#area"), areaTouched = !!$area.val(), timer = null;
      var officeRooms = ["workstations", "cabins", "reception", "conference"];

      var showRoomsFor = function (ptype, reset) {
        var isOffice = ptype === "office";
        $("#roomChoices [data-room]").each(function () {
          var key = $(this).data("room"), fits = (officeRooms.indexOf(key) > -1) === isOffice;
          $(this).toggleClass("d-none", !fits);
          if (!fits) $(this).find("input").prop("checked", false);
          if (reset) $(this).find("input").prop("checked", (defaults[ptype] || []).indexOf(key) > -1);
        });
      };
      var suggestArea = function () {
        if (areaTouched) return;
        var sum = 0;
        $ef.find("input[name=rooms]:checked").each(function () { sum += areas[this.value] || 0; });
        $area.val(sum || "");
      };
      var calc = function () {
        clearTimeout(timer);
        timer = setTimeout(function () {
          var q = $ef.find("input[name=property_type], input[name=rooms], input[name=finish], input[name=area]").serialize();
          $("#estimateCard").addClass("is-loading");
          $.getJSON($ef.data("api") + "?" + q)
            .done(function (r) {
              $("#estRange, #estRangeMini").text(inr(r.low) + " – " + inr(r.high));
              $("#estMeta").text(r.property_label + " · " + Number(r.area).toLocaleString("en-IN") + " sq ft · " + r.finish_label + " finish");
            })
            .fail(function (x) {
              $("#estRange, #estRangeMini").text("—");
              $("#estMeta").text((x.responseJSON && x.responseJSON.error) || "Choose your options to see a range.");
            })
            .always(function () { $("#estimateCard").removeClass("is-loading"); });
        }, 180);
      };

      $ef.on("change", "input[name=property_type]", function () { areaTouched = false; showRoomsFor(this.value, true); suggestArea(); calc(); });
      $ef.on("change", "input[name=rooms]", function () { suggestArea(); calc(); });
      $ef.on("change", "input[name=finish]", calc);
      $area.on("input", function () { areaTouched = true; calc(); });

      var start = $ef.find("input[name=property_type]:checked").val() || "2bhk";
      var hasPosted = $ef.find("input[name=rooms]:checked").length > 0;
      showRoomsFor(start, !hasPosted);
      suggestArea();
      calc();
    }

    // =================================================== Style quiz
    var $qf = $("#quizForm");
    if ($qf.length) {
      var $steps = $qf.find(".quiz-step"), total = $steps.length;
      var go = function (i) {
        $steps.addClass("d-none").eq(i).removeClass("d-none");
        $("#quizBar").css("width", ((i + 1) / total * 100) + "%");
        var top = $qf.offset().top - 110;
        if (window.scrollY > top) window.scrollTo({ top: top, behavior: "smooth" });
      };
      $qf.on("change", "input[type=radio]", function () {
        var $step = $(this).closest(".quiz-step"), i = $steps.index($step);
        if (i < total - 1) setTimeout(function () { go(i + 1); }, 260);
        else $qf.find(".quiz-submit").prop("disabled", false);
      });
      $qf.on("click", ".quiz-back", function () {
        var i = $steps.index($(this).closest(".quiz-step"));
        if (i > 0) go(i - 1);
      });
    }
  });
})(jQuery);
