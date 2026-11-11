/* Quotation builder: rooms -> line items, live GST totals, autosave (server recalculates authoritative totals). */
(function ($) {
  "use strict";
  var $root, state, catalogue, units, saveUrl, timer = null, saving = null, dirty = false;
  var GST = ["0", "5", "12", "18", "28"];

  function n(v) { var x = parseFloat(v); return isFinite(x) ? x : 0; }
  function r2(x) { return Math.round((x + Number.EPSILON) * 100) / 100; }
  function inr(x, dec) {
    var v = Number(x), d = dec === 0 ? 0 : 2;
    return (v < 0 ? "−" : "") + "₹" + Math.abs(v).toLocaleString("en-IN", { minimumFractionDigits: d, maximumFractionDigits: d });
  }
  function esc(s) { return $("<div>").text(s == null ? "" : String(s)).html(); }

  function lineCalc(it) {
    var amount = r2(n(it.quantity) * n(it.rate));
    var disc = r2(amount * n(it.discount_percent) / 100);
    var taxable = r2(amount - disc);
    var gst = r2(taxable * n(it.gst_percent) / 100);
    return { amount: amount, disc: disc, taxable: taxable, gst: gst };
  }

  function totals() {
    var t = { subtotal: 0, discount_total: 0, taxable_total: 0, gst_total: 0 };
    state.rooms.forEach(function (room) {
      room.items.forEach(function (it) {
        var c = lineCalc(it);
        t.subtotal += c.amount; t.discount_total += c.disc; t.taxable_total += c.taxable; t.gst_total += c.gst;
      });
    });
    Object.keys(t).forEach(function (k) { t[k] = r2(t[k]); });
    var exact = r2(t.taxable_total + t.gst_total);
    t.grand_total = Math.round(exact);
    t.round_off = r2(t.grand_total - exact);
    t.cgst = state.inter_state ? 0 : r2(t.gst_total / 2);
    t.sgst = state.inter_state ? 0 : r2(t.gst_total - t.cgst);
    t.igst = state.inter_state ? t.gst_total : 0;
    return t;
  }

  function showTotals(t) {
    $("[data-total]").each(function () {
      var k = $(this).data("total");
      if (t[k] !== undefined) $(this).text(inr(t[k], k === "grand_total" ? 0 : 2));
    });
    $(".igst-row").toggle(!!state.inter_state);
    $(".cgst-row").toggle(!state.inter_state);
    $("#taxMode").text(state.inter_state ? "IGST" : "CGST + SGST");
  }

  function unitOptions(sel) {
    return units.map(function (u) { return '<option value="' + u[0] + '"' + (u[0] === sel ? " selected" : "") + ">" + esc(u[1]) + "</option>"; }).join("");
  }
  function gstOptions(sel) {
    return GST.map(function (g) { return '<option value="' + g + '"' + (String(n(sel)) === g ? " selected" : "") + ">" + g + "%</option>"; }).join("");
  }
  function catalogueOptions() {
    var html = '<option value="">Add from catalogue…</option>', group = null;
    catalogue.forEach(function (c) {
      if (c.category !== group) { if (group !== null) html += "</optgroup>"; group = c.category; html += '<optgroup label="' + esc(group) + '">'; }
      html += '<option value="' + c.id + '">' + esc(c.name) + " — " + inr(c.rate) + "/" + esc(c.unit) + "</option>";
    });
    return html + (group !== null ? "</optgroup>" : "");
  }

  function render() {
    var html = "";
    state.rooms.forEach(function (room, ri) {
      var roomTotal = 0;
      var rows = room.items.map(function (it, ii) {
        var c = lineCalc(it); roomTotal += c.taxable;
        return '<tr data-ri="' + ri + '" data-ii="' + ii + '">' +
          '<td><input class="form-control form-control-sm" data-f="description" maxlength="240" value="' + esc(it.description) + '" placeholder="Item description" aria-label="Description"></td>' +
          '<td><input class="form-control form-control-sm text-end" data-f="quantity" inputmode="decimal" value="' + esc(it.quantity) + '" aria-label="Quantity"></td>' +
          '<td><select class="form-select form-select-sm" data-f="unit" aria-label="Unit">' + unitOptions(it.unit) + "</select></td>" +
          '<td><input class="form-control form-control-sm text-end" data-f="rate" inputmode="decimal" value="' + esc(it.rate) + '" aria-label="Rate"></td>' +
          '<td><input class="form-control form-control-sm text-end" data-f="discount_percent" inputmode="decimal" value="' + esc(it.discount_percent) + '" aria-label="Discount %"></td>' +
          '<td><select class="form-select form-select-sm" data-f="gst_percent" aria-label="GST %">' + gstOptions(it.gst_percent) + "</select></td>" +
          '<td class="text-end fw-semibold line-amount">' + inr(c.taxable) + "</td>" +
          '<td><button type="button" class="btn btn-sm btn-light del-item" aria-label="Remove item"><i class="bi bi-x-lg"></i></button></td></tr>';
      }).join("");
      html += '<div class="panel mb-3 qt-room" data-ri="' + ri + '">' +
        '<div class="panel-head gap-2"><input class="form-control form-control-sm room-name fw-semibold" value="' + esc(room.name) + '" maxlength="80" aria-label="Room name">' +
        '<span class="fw-semibold text-nowrap room-total">' + inr(r2(roomTotal)) + "</span>" +
        '<button type="button" class="btn btn-sm btn-light del-room" aria-label="Remove room"><i class="bi bi-trash3"></i></button></div>' +
        '<div class="table-responsive"><table class="table table-sm align-middle mb-0 qt-table qt-edit"><thead class="small text-muted"><tr>' +
        '<th>Item</th><th style="width:66px" class="text-end">Qty</th><th style="width:84px">Unit</th><th style="width:96px" class="text-end">Rate ₹</th>' +
        '<th style="width:58px" class="text-end">Disc %</th><th style="width:76px">GST</th><th style="width:108px" class="text-end">Amount</th><th style="width:34px"></th></tr></thead>' +
        "<tbody>" + (rows || '<tr><td colspan="8" class="text-muted small py-3 text-center">No items yet — add from the catalogue or a custom line.</td></tr>') + "</tbody></table></div>" +
        '<div class="panel-body d-flex flex-wrap gap-2 py-2"><select class="form-select form-select-sm add-cat" style="max-width:24rem" aria-label="Add from catalogue">' + catalogueOptions() + "</select>" +
        '<button type="button" class="btn btn-sm btn-light add-custom"><i class="bi bi-plus-lg me-1"></i>Custom line</button></div></div>';
    });
    if (!state.rooms.length) html = '<div class="panel mb-3"><div class="empty-mini py-5"><i class="bi bi-door-open"></i>Start by adding a room — Living room, Kitchen, Master bedroom…</div></div>';
    $root.html(html);
    showTotals(totals());
  }

  function markDirty() {
    dirty = true;
    $("#saveState").text("Saving…");
    clearTimeout(timer);
    timer = setTimeout(save, 900);
    showTotals(totals());
  }

  function save() {
    clearTimeout(timer);
    if (!dirty) return $.Deferred().resolve().promise();
    dirty = false;
    saving = $.ajax({ url: saveUrl, method: "POST", contentType: "application/json", data: JSON.stringify(state),
                      headers: { "X-CSRFToken": window.Studio.csrfToken() } })
      .done(function (r) {
        $("#saveState").text("All changes saved");
        if (r.totals) showTotals(r.totals);
      })
      .fail(function (x) {
        dirty = true;
        var msg = (x.responseJSON && x.responseJSON.error) || "Could not save. Check your connection.";
        $("#saveState").text("Not saved");
        window.Studio.toast(msg, "error");
      });
    return saving;
  }

  $(function () {
    $root = $("#quoteBuilder");
    if (!$root.length) return;
    state = JSON.parse($("#quotePayload").text());
    catalogue = JSON.parse($("#quoteCatalogue").text());
    units = JSON.parse($("#quoteUnits").text());
    saveUrl = $root.data("save-url");
    render();

    // Meta fields
    $("[data-meta]").each(function () {
      var k = $(this).data("meta");
      if (this.type === "checkbox") this.checked = !!state[k]; else $(this).val(state[k] || "");
    }).on("input change", function () {
      var k = $(this).data("meta");
      state[k] = this.type === "checkbox" ? this.checked : $(this).val();
      markDirty();
    });

    $("#addRoom").on("click", function () {
      var names = ["Living room", "Kitchen", "Master bedroom", "Kids' room", "Dining", "Pooja room", "Study"];
      state.rooms.push({ name: names[state.rooms.length] || "Room " + (state.rooms.length + 1), items: [] });
      render(); markDirty();
      $root.find(".room-name").last().trigger("focus").trigger("select");
    });
    $root.on("input", ".room-name", function () {
      state.rooms[$(this).closest(".qt-room").data("ri")].name = $(this).val(); markDirty();
    });
    $root.on("click", ".del-room", function () {
      var ri = $(this).closest(".qt-room").data("ri");
      if (state.rooms[ri].items.length && !window.confirm("Remove “" + state.rooms[ri].name + "” and its items?")) return;
      state.rooms.splice(ri, 1); render(); markDirty();
    });
    $root.on("change", ".add-cat", function () {
      var id = parseInt($(this).val(), 10), c = catalogue.find(function (x) { return x.id === id; });
      if (!c) return;
      state.rooms[$(this).closest(".qt-room").data("ri")].items.push({
        catalogue_id: c.id, description: c.name, hsn_code: c.hsn, unit: c.unit, quantity: "1", rate: c.rate,
        discount_percent: "0", gst_percent: c.gst });
      render(); markDirty();
      $root.find('.qt-room[data-ri="' + $(this).closest(".qt-room").data("ri") + '"] [data-f=quantity]').last().trigger("focus").trigger("select");
    });
    $root.on("click", ".add-custom", function () {
      var ri = $(this).closest(".qt-room").data("ri");
      state.rooms[ri].items.push({ catalogue_id: null, description: "", unit: "nos", quantity: "1", rate: "0", discount_percent: "0", gst_percent: "18" });
      render(); markDirty();
      $root.find('.qt-room[data-ri="' + ri + '"] [data-f=description]').last().trigger("focus");
    });
    $root.on("input change", "[data-f]", function () {
      var $tr = $(this).closest("tr"), it = state.rooms[$tr.data("ri")].items[$tr.data("ii")];
      it[$(this).data("f")] = $(this).val();
      // live line + room totals without re-rendering (keeps focus)
      $tr.find(".line-amount").text(inr(lineCalc(it).taxable));
      var room = state.rooms[$tr.data("ri")], rt = 0;
      room.items.forEach(function (x) { rt += lineCalc(x).taxable; });
      $tr.closest(".qt-room").find(".room-total").text(inr(r2(rt)));
      markDirty();
    });
    $root.on("click", ".del-item", function () {
      var $tr = $(this).closest("tr");
      state.rooms[$tr.data("ri")].items.splice($tr.data("ii"), 1);
      render(); markDirty();
    });

    // Make sure everything is saved before "Send to client" or leaving the page
    $("#sendBtn").on("click", function (e) {
      if (!dirty && !(saving && saving.state() === "pending")) return;
      e.preventDefault();
      var btn = this;
      $.when(save()).always(function () { if (!dirty) btn.click(); });
    });
    window.addEventListener("beforeunload", function (e) {
      if (dirty) { e.preventDefault(); e.returnValue = ""; }
    });
  });
})(jQuery);
