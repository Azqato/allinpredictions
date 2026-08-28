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

  // Keep in sync with TAG_DISPLAY_OVERRIDES in scripts/generate_site.py.
  var TAG_DISPLAY_OVERRIDES = { "ai": "AI", "ipo": "IPO" };
  function tagDisplay(tag) {
    if (Object.prototype.hasOwnProperty.call(TAG_DISPLAY_OVERRIDES, tag)) return TAG_DISPLAY_OVERRIDES[tag];
    return tag.split("-").map(function (word) {
      if (Object.prototype.hasOwnProperty.call(TAG_DISPLAY_OVERRIDES, word)) return TAG_DISPLAY_OVERRIDES[word];
      return word.charAt(0).toUpperCase() + word.slice(1);
    }).join(" ");
  }

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
    var total = keys.reduce(function (sum, k) { return sum + (bucket[k] || 0); }, 0);
    var html = '<table class="legend"><tbody>';
    keys.forEach(function (key) {
      var val = bucket[key] || 0;
      var pct = val > 0 && total > 0 ? ' <span class="muted">(' + ((val / total) * 100).toFixed(1) + '%)</span>' : '';
      html += "<tr><td><span class=\"dot dot-" + key + "\"></span>" +
        key.charAt(0).toUpperCase() + key.slice(1) + "</td><td class=\"num\">" +
        val + pct + "</td></tr>";
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
          return { label: state.view === "topic" ? tagDisplay(label) : label, bucket: groups[label] };
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

  function setupEpisodeYearFilter() {
    var select = document.getElementById("episode-year-filter");
    var grid = document.getElementById("episode-grid");
    var countEl = document.getElementById("episode-year-count");
    if (!select || !grid) return;
    var cards = grid.querySelectorAll(".episode-card");

    function render() {
      var year = select.value;
      var shown = 0;
      cards.forEach(function (card) {
        var match = !year || card.getAttribute("data-year") === year;
        card.style.display = match ? "" : "none";
        if (match) shown++;
      });
      if (countEl) {
        if (year) {
          countEl.style.display = "";
          countEl.textContent = shown + " episode" + (shown === 1 ? "" : "s") + " in " + year;
        } else {
          countEl.style.display = "none";
        }
      }
    }

    select.addEventListener("change", render);
    render();
  }

  function setupLedgerPage() {
    var container = document.getElementById("ledger-results");
    if (!container) return;
    var src = container.getAttribute("data-src");
    var searchInput = document.getElementById("ledger-search");
    var yearFilter = document.getElementById("ledger-year-filter");
    var topicFilter = document.getElementById("ledger-topic-filter");
    var resultFilter = document.getElementById("ledger-result-filter");
    var countEl = document.getElementById("ledger-count");
    var PAGE_SIZE = 50;
    var shownCount = PAGE_SIZE;
    var entries = [];

    function escapeHtml(s) {
      var div = document.createElement("div");
      div.textContent = s == null ? "" : String(s);
      return div.innerHTML;
    }

    function matches(e, q, year, topic, result) {
      if (year && e.year !== year) return false;
      if (result && e.result !== result) return false;
      if (topic && (e.tags || []).indexOf(topic) === -1) return false;
      if (q && (e.prediction || "").toLowerCase().indexOf(q) === -1 &&
        (e.who_display || "").toLowerCase().indexOf(q) === -1 &&
        (e.episode_title || "").toLowerCase().indexOf(q) === -1) return false;
      return true;
    }

    function render() {
      var q = (searchInput.value || "").trim().toLowerCase();
      var year = yearFilter.value;
      var topic = topicFilter.value;
      var result = resultFilter.value;
      var filtered = entries.filter(function (e) { return matches(e, q, year, topic, result); });

      if (countEl) countEl.textContent = filtered.length + " prediction" + (filtered.length === 1 ? "" : "s");

      var page = filtered.slice(0, shownCount);
      var html = page.map(function (e) {
        return '<a class="card prediction-card" href="episodes/' + e.episode_id + '.html#' + e.id + '">' +
          '<div class="flex-between">' +
          '<span class="who-badge">' + escapeHtml(e.who_display) + '</span>' +
          '<span class="badge badge-' + e.result + '">' + escapeHtml(e.result.charAt(0).toUpperCase() + e.result.slice(1)) + '</span>' +
          '</div>' +
          '<p style="margin:.5rem 0;">' + escapeHtml(e.prediction) + '</p>' +
          '<div class="muted">' + escapeHtml(e.episode_title) + (e.published ? ' &middot; ' + escapeHtml(e.published) : '') + '</div>' +
          '</a>';
      }).join("");

      if (filtered.length > shownCount) {
        html += '<button type="button" id="ledger-load-more" class="segmented" style="padding:.5rem 1rem;">Load more (' +
          (filtered.length - shownCount) + ' remaining)</button>';
      }
      container.innerHTML = html || '<p class="muted">No predictions match this filter.</p>';

      var loadMore = document.getElementById("ledger-load-more");
      if (loadMore) {
        loadMore.addEventListener("click", function () {
          shownCount += PAGE_SIZE;
          render();
        });
      }
    }

    function onFilterChange() {
      shownCount = PAGE_SIZE;
      render();
    }

    fetch(src).then(function (resp) { return resp.json(); }).then(function (data) {
      entries = data || [];
      render();
    }).catch(function () {
      container.innerHTML = '<p class="muted">Could not load the ledger data.</p>';
    });

    searchInput.addEventListener("input", onFilterChange);
    yearFilter.addEventListener("change", onFilterChange);
    topicFilter.addEventListener("change", onFilterChange);
    resultFilter.addEventListener("change", onFilterChange);
  }

  function setupLeaderboardSort() {
    var table = document.getElementById("leaderboard-table");
    if (!table) return;
    var headers = table.querySelectorAll("th[data-sort-key]");
    var tbody = table.querySelector("tbody");
    if (!headers.length || !tbody) return;

    function currentSort() {
      var active = table.querySelector("th.sort-active");
      return {
        key: active ? active.getAttribute("data-sort-key") : "accuracy",
        dir: active ? active.getAttribute("data-sort-dir") : "desc"
      };
    }

    function sortBy(key, dir, isText) {
      var rows = Array.prototype.slice.call(tbody.querySelectorAll("tr"));
      rows.sort(function (a, b) {
        var av = a.getAttribute("data-" + key), bv = b.getAttribute("data-" + key);
        var cmp;
        if (isText) {
          cmp = av.localeCompare(bv);
        } else {
          cmp = parseFloat(av) - parseFloat(bv);
        }
        return dir === "asc" ? cmp : -cmp;
      });
      rows.forEach(function (row) { tbody.appendChild(row); });
    }

    headers.forEach(function (th) {
      th.addEventListener("click", function () {
        var key = th.getAttribute("data-sort-key");
        var isText = th.getAttribute("data-sort-type") === "text";
        var prev = currentSort();
        var dir;
        if (prev.key === key) {
          dir = th.getAttribute("data-sort-dir") === "asc" ? "desc" : "asc";
        } else {
          // Numeric columns default to descending (biggest first) on first
          // click; the rank/speaker text columns default to ascending.
          dir = isText || key === "rank" ? "asc" : "desc";
        }
        headers.forEach(function (h) {
          h.classList.remove("sort-active");
          h.removeAttribute("data-sort-dir");
          h.textContent = h.textContent.replace(/ [↑↓]$/, "");
        });
        th.classList.add("sort-active");
        th.setAttribute("data-sort-dir", dir);
        th.textContent += dir === "asc" ? " ↑" : " ↓";
        sortBy(key, dir, isText);
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
    setupEpisodeYearFilter();
    setupLedgerPage();
    setupLeaderboardSort();
    setupWelcomeBanner();
  });
})();
