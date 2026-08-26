(function () {
  "use strict";

  var STORAGE_KEY = "predict_timestamp_notice_seen";

  function setupYoutubeWarning() {
    var links = document.querySelectorAll(".js-youtube-link");
    var modal = document.getElementById("youtube-warning-modal");
    if (!links.length || !modal) return;

    var continueBtn = document.getElementById("youtube-warning-continue");
    var pendingHref = null;

    function seen() {
      try { return window.localStorage.getItem(STORAGE_KEY) === "1"; }
      catch (e) { return true; }
    }
    function markSeen() {
      try { window.localStorage.setItem(STORAGE_KEY, "1"); } catch (e) {}
    }

    links.forEach(function (link) {
      link.addEventListener("click", function (evt) {
        if (seen()) return;
        evt.preventDefault();
        pendingHref = link.getAttribute("href");
        modal.classList.remove("hidden");
      });
    });

    if (continueBtn) {
      continueBtn.addEventListener("click", function () {
        markSeen();
        modal.classList.add("hidden");
        if (pendingHref) {
          window.open(pendingHref, "_blank", "noopener,noreferrer");
          pendingHref = null;
        }
      });
    }
  }

  var RESULT_COLORS = {
    right: "#22c55e",
    wrong: "#ef4444",
    ambiguous: "#d4c4a8",
    inconclusive: "#6b7280",
    unvalidated: "#94a3b8"
  };
  var RESOLVED_KEYS = ["right", "wrong"];
  var ALL_KEYS = ["right", "wrong", "ambiguous", "inconclusive"];

  function emptyBucket() {
    return { right: 0, wrong: 0, ambiguous: 0, inconclusive: 0, unvalidated: 0 };
  }

  function donutSvg(bucket, keys) {
    var size = 160, stroke = 22;
    var total = keys.reduce(function (sum, k) { return sum + (bucket[k] || 0); }, 0);
    var r = (size - stroke) / 2, cx = size / 2, cy = size / 2;
    var circumference = 2 * Math.PI * r;
    if (total === 0) {
      return '<svg width="' + size + '" height="' + size + '" viewBox="0 0 ' + size + ' ' + size +
        '" role="img" aria-label="No data"><circle cx="' + cx + '" cy="' + cy + '" r="' + r +
        '" fill="none" stroke="rgba(255,255,255,0.12)" stroke-width="' + stroke + '" /></svg>';
    }
    var offset = 0, segments = "";
    keys.forEach(function (key) {
      var val = bucket[key] || 0;
      if (val <= 0) return;
      var length = (val / total) * circumference;
      var dasharray = length.toFixed(2) + " " + (circumference - length).toFixed(2);
      var rotate = ((offset / total) * 360 - 90).toFixed(2);
      segments += '<circle cx="' + cx + '" cy="' + cy + '" r="' + r + '" fill="none" stroke="' +
        RESULT_COLORS[key] + '" stroke-width="' + stroke + '" stroke-dasharray="' + dasharray +
        '" transform="rotate(' + rotate + ' ' + cx + ' ' + cy + ')" />';
      offset += val;
    });
    return '<svg width="' + size + '" height="' + size + '" viewBox="0 0 ' + size + ' ' + size +
      '" role="img" aria-label="Accuracy chart">' + segments + "</svg>";
  }

  function stackedBarsHtml(groups, keys) {
    // groups: array of {label, bucket}, already sorted by caller.
    if (!groups.length) return '<p class="muted">No data for this filter.</p>';
    var html = '<div class="stacked-bars">';
    groups.forEach(function (g) {
      var total = keys.reduce(function (sum, k) { return sum + (g.bucket[k] || 0); }, 0);
      html += '<div class="stacked-bar-row"><div class="stacked-bar-label">' + g.label +
        ' <span class="muted">(' + total + ')</span></div><div class="stacked-bar-track">';
      if (total === 0) {
        html += '<div class="stacked-bar-seg" style="width:100%;background:rgba(255,255,255,0.08);"></div>';
      } else {
        keys.forEach(function (key) {
          var val = g.bucket[key] || 0;
          if (val <= 0) return;
          var pct = ((val / total) * 100).toFixed(2);
          html += '<div class="stacked-bar-seg" style="width:' + pct + '%;background:' +
            RESULT_COLORS[key] + ';" title="' + key + ": " + val + '"></div>';
        });
      }
      html += "</div></div>";
    });
    html += "</div>";
    return html;
  }

  function legendHtml(bucket, keys) {
    var html = '<table class="legend"><tbody>';
    keys.forEach(function (key) {
      html += "<tr><td><span class=\"dot dot-" + key + "\"></span>" +
        key.charAt(0).toUpperCase() + key.slice(1) + "</td><td class=\"num\">" +
        (bucket[key] || 0) + "</td></tr>";
    });
    html += "</tbody></table>";
    return html;
  }

  function setupHomeCharts() {
    var cards = document.querySelectorAll(".scorecard[data-who]");
    if (!cards.length) return;

    var resolvedToggle = document.getElementById("resolved-only-toggle");
    var topicFilter = document.getElementById("topic-filter");
    var viewToggle = document.getElementById("view-toggle");
    if (!resolvedToggle || !topicFilter || !viewToggle) return;

    var state = { resolvedOnly: true, topic: "", view: "total" };

    var cardData = [];
    cards.forEach(function (card) {
      var raw = card.getAttribute("data-entries");
      var entries = [];
      try { entries = JSON.parse(raw || "[]"); } catch (e) {}
      cardData.push({
        card: card,
        entries: entries,
        chartArea: card.querySelector(".chart-area"),
        countEl: card.querySelector(".scorecard-count")
      });
    });

    function filteredEntries(entries) {
      if (!state.topic) return entries;
      return entries.filter(function (e) { return (e.tags || []).indexOf(state.topic) !== -1; });
    }

    function bucketOf(entries) {
      var bucket = emptyBucket();
      entries.forEach(function (e) { bucket[e.result] = (bucket[e.result] || 0) + 1; });
      return bucket;
    }

    function render() {
      var keys = state.resolvedOnly ? RESOLVED_KEYS : ALL_KEYS;
      cardData.forEach(function (d) {
        var entries = filteredEntries(d.entries);
        var totalAll = entries.length;
        var totalResolved = entries.filter(function (e) { return e.result === "right" || e.result === "wrong"; }).length;
        if (d.countEl) d.countEl.textContent = totalResolved + " resolved · " + totalAll + " total";
        if (!d.chartArea) return;

        if (state.view === "total") {
          var bucket = bucketOf(entries);
          d.chartArea.innerHTML = '<div class="donut">' + donutSvg(bucket, keys) + "</div>" + legendHtml(bucket, keys);
          return;
        }

        var groupKey = state.view === "year" ? "year" : "tags";
        var groups = {};
        entries.forEach(function (e) {
          var labels = groupKey === "year" ? [e.year || "Unknown"] : (e.tags && e.tags.length ? e.tags : []);
          labels.forEach(function (label) {
            if (!groups[label]) groups[label] = emptyBucket();
            groups[label][e.result] = (groups[label][e.result] || 0) + 1;
          });
        });
        var groupList = Object.keys(groups).sort().map(function (label) {
          return { label: groupKey === "topic" ? label.charAt(0).toUpperCase() + label.slice(1) : label, bucket: groups[label] };
        });
        d.chartArea.innerHTML = stackedBarsHtml(groupList, keys);
      });
    }

    resolvedToggle.addEventListener("change", function () {
      state.resolvedOnly = resolvedToggle.checked;
      render();
    });
    topicFilter.addEventListener("change", function () {
      state.topic = topicFilter.value;
      render();
    });
    viewToggle.querySelectorAll("button[data-view]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        viewToggle.querySelectorAll("button").forEach(function (b) { b.classList.remove("active"); });
        btn.classList.add("active");
        state.view = btn.getAttribute("data-view");
        render();
      });
    });
  }

  function setupWelcomeBanner() {
    var STORAGE_KEY = "predict_welcome_banner_dismissed";
    var banner = document.getElementById("welcome-banner");
    var dismissBtn = document.getElementById("welcome-banner-dismiss");
    if (!banner) return;
    var dismissed = false;
    try { dismissed = window.localStorage.getItem(STORAGE_KEY) === "1"; } catch (e) {}
    if (!dismissed) banner.classList.remove("hidden");
    if (dismissBtn) {
      dismissBtn.addEventListener("click", function () {
        banner.classList.add("hidden");
        try { window.localStorage.setItem(STORAGE_KEY, "1"); } catch (e) {}
      });
    }
  }

  document.addEventListener("DOMContentLoaded", function () {
    setupYoutubeWarning();
    setupHomeCharts();
    setupWelcomeBanner();
  });
})();
