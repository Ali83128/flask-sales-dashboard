(function () {
  "use strict";
  var el = document.getElementById("stats-data");
  if (!el || typeof Chart === "undefined") return;
  var stats = JSON.parse(el.textContent);

  var palette = ["#2563eb", "#0d9488", "#d97706", "#7c3aed", "#db2777", "#64748b"];
  var money = function (v) {
    return "$" + Number(v).toLocaleString("en-US", { maximumFractionDigits: 0 });
  };

  Chart.defaults.font.family = 'Inter, "Segoe UI", system-ui, sans-serif';
  Chart.defaults.color = "#64748b";
  Chart.defaults.animation = false;
  Chart.defaults.plugins.tooltip.backgroundColor = "#0f172a";
  Chart.defaults.plugins.tooltip.padding = 10;

  var lastIndex = stats.revenue_series.values.length - 1;
  var periodWord = { "30d": "day", "90d": "week", "12m": "month" }[stats.range];

  new Chart(document.getElementById("revenueChart"), {
    type: "line",
    data: {
      labels: stats.revenue_series.labels,
      datasets: [{
        label: "Revenue",
        data: stats.revenue_series.values,
        borderColor: palette[0],
        backgroundColor: "rgba(37, 99, 235, 0.10)",
        fill: true,
        tension: 0.35,
        borderWidth: 2,
        pointRadius: stats.revenue_series.values.length > 40 ? 0 : 3,
        pointHoverRadius: 5,
        segment: {
          borderDash: function (ctx) { return ctx.p1DataIndex === lastIndex ? [5, 5] : undefined; }
        }
      }]
    },
    options: {
      maintainAspectRatio: false,
      interaction: { mode: "index", intersect: false },
      plugins: {
        legend: { display: false },
        tooltip: { callbacks: { label: function (c) {
          var note = c.dataIndex === lastIndex ? " (" + periodWord + " in progress)" : "";
          return " " + money(c.parsed.y) + note;
        } } }
      },
      scales: {
        x: { grid: { display: false }, ticks: { maxRotation: 0, autoSkipPadding: 14 } },
        y: { beginAtZero: true, grid: { color: "#eef2f7" }, border: { display: false },
             ticks: { callback: function (v) { return money(v); } } }
      }
    }
  });

  new Chart(document.getElementById("regionChart"), {
    type: "doughnut",
    data: {
      labels: stats.by_region.map(function (r) { return r.region; }),
      datasets: [{
        data: stats.by_region.map(function (r) { return r.revenue; }),
        backgroundColor: palette,
        borderColor: "#ffffff",
        borderWidth: 2
      }]
    },
    options: {
      maintainAspectRatio: false,
      cutout: "62%",
      plugins: {
        legend: { position: "right", labels: { boxWidth: 10, boxHeight: 10, usePointStyle: true, padding: 12 } },
        tooltip: { callbacks: { label: function (c) { return " " + c.label + ": " + money(c.parsed); } } }
      }
    }
  });

  new Chart(document.getElementById("productChart"), {
    type: "bar",
    data: {
      labels: stats.top_products.map(function (p) { return p.name; }),
      datasets: [{
        label: "Revenue",
        data: stats.top_products.map(function (p) { return p.revenue; }),
        backgroundColor: palette[0],
        borderRadius: 4,
        barThickness: 22
      }]
    },
    options: {
      indexAxis: "y",
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: { callbacks: { label: function (c) { return " " + money(c.parsed.x); } } }
      },
      scales: {
        x: { beginAtZero: true, grid: { color: "#eef2f7" }, border: { display: false },
             ticks: { callback: function (v) { return money(v); } } },
        y: { grid: { display: false }, ticks: { color: "#334155" } }
      }
    }
  });
  document.body.setAttribute("data-charts-ready", "1");
})();
