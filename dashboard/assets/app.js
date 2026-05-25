(function () {
  const data = window.DASHBOARD_DATA;
  const state = {
    start: data.summary.dateStart,
    end: data.summary.dateEnd,
    category: "All",
    region: "All",
    channel: "All",
  };

  const palette = {
    blue: "#255e91",
    teal: "#0c7c7a",
    green: "#2f7d4f",
    amber: "#a76600",
    coral: "#b74d3f",
    ink: "#17202a",
    muted: "#667085",
    line: "#d9dee7",
  };

  const $ = (id) => document.getElementById(id);
  const money = (value) =>
    new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
      maximumFractionDigits: 0,
    }).format(value || 0);
  const number = (value) => new Intl.NumberFormat("en-US").format(Math.round(value || 0));
  const pct = (value) => `${((value || 0) * 100).toFixed(1)}%`;
  const escapeHtml = (value) =>
    String(value).replace(/[&<>"']/g, (match) => {
      const replacements = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;" };
      return replacements[match];
    });

  function uniqueValues(key) {
    return [...new Set(data.breakdown.map((row) => row[key]))].sort();
  }

  function fillSelect(id, values, label) {
    const select = $(id);
    select.innerHTML = "";
    const all = document.createElement("option");
    all.value = "All";
    all.textContent = label;
    select.appendChild(all);
    values.forEach((value) => {
      const option = document.createElement("option");
      option.value = value;
      option.textContent = value;
      select.appendChild(option);
    });
  }

  function setupFilters() {
    $("startDate").value = state.start;
    $("endDate").value = state.end;
    fillSelect("categoryFilter", uniqueValues("category"), "All categories");
    fillSelect("regionFilter", uniqueValues("region"), "All regions");
    fillSelect("channelFilter", uniqueValues("channel"), "All channels");

    ["startDate", "endDate", "categoryFilter", "regionFilter", "channelFilter"].forEach((id) => {
      $(id).addEventListener("change", () => {
        state.start = $("startDate").value;
        state.end = $("endDate").value;
        state.category = $("categoryFilter").value;
        state.region = $("regionFilter").value;
        state.channel = $("channelFilter").value;
        render();
      });
    });

    $("resetFilters").addEventListener("click", () => {
      state.start = data.summary.dateStart;
      state.end = data.summary.dateEnd;
      state.category = "All";
      state.region = "All";
      state.channel = "All";
      $("startDate").value = state.start;
      $("endDate").value = state.end;
      $("categoryFilter").value = "All";
      $("regionFilter").value = "All";
      $("channelFilter").value = "All";
      render();
    });
  }

  function dateInRange(dateValue, start, end) {
    return dateValue >= start && dateValue <= end;
  }

  function filteredBreakdown(custom = {}) {
    const start = custom.start || state.start;
    const end = custom.end || state.end;
    const category = custom.category || state.category;
    const region = custom.region || state.region;
    const channel = custom.channel || state.channel;
    return data.breakdown.filter((row) => {
      if (!dateInRange(row.date, start, end)) return false;
      if (category !== "All" && row.category !== category) return false;
      if (region !== "All" && row.region !== region) return false;
      if (channel !== "All" && row.channel !== channel) return false;
      return true;
    });
  }

  function filteredDaily(custom = {}) {
    const start = custom.start || state.start;
    const end = custom.end || state.end;
    return data.daily.filter((row) => dateInRange(row.date, start, end));
  }

  function filteredMarketing(custom = {}) {
    const start = custom.start || state.start;
    const end = custom.end || state.end;
    const channel = custom.channel || state.channel;
    return (data.marketingDaily || []).filter((row) => {
      if (!dateInRange(row.date, start, end)) return false;
      if (channel !== "All" && row.channel !== channel) return false;
      return true;
    });
  }

  function aggregateRows(rows) {
    const totals = rows.reduce(
      (acc, row) => {
        acc.orders += row.orders || 0;
        acc.units += row.units || 0;
        acc.revenue += row.net_revenue || 0;
        acc.profit += row.gross_profit || 0;
        return acc;
      },
      { orders: 0, units: 0, revenue: 0, profit: 0 }
    );
    totals.aov = totals.orders ? totals.revenue / totals.orders : 0;
    totals.margin = totals.revenue ? totals.profit / totals.revenue : 0;
    return totals;
  }

  function aggregateMarketing(rows) {
    return rows.reduce(
      (acc, row) => {
        acc.spend += row.spend || 0;
        acc.clicks += row.clicks || 0;
        acc.impressions += row.impressions || 0;
        return acc;
      },
      { spend: 0, clicks: 0, impressions: 0 }
    );
  }

  function groupBy(rows, key) {
    const map = new Map();
    rows.forEach((row) => {
      const name = row[key];
      const bucket = map.get(name) || { name, net_revenue: 0, gross_profit: 0, orders: 0 };
      bucket.net_revenue += row.net_revenue || 0;
      bucket.gross_profit += row.gross_profit || 0;
      bucket.orders += row.orders || 0;
      map.set(name, bucket);
    });
    return [...map.values()].sort((a, b) => b.net_revenue - a.net_revenue);
  }

  function aggregateDaily(rows) {
    const map = new Map();
    rows.forEach((row) => {
      const bucket = map.get(row.date) || { date: row.date, net_revenue: 0, gross_profit: 0, orders: 0 };
      bucket.net_revenue += row.net_revenue || 0;
      bucket.gross_profit += row.gross_profit || 0;
      bucket.orders += row.orders || 0;
      map.set(row.date, bucket);
    });
    return [...map.values()].sort((a, b) => a.date.localeCompare(b.date));
  }

  function setupCanvas(canvas) {
    const rect = canvas.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;
    canvas.width = Math.max(1, Math.floor(rect.width * dpr));
    canvas.height = Math.max(1, Math.floor(rect.height * dpr));
    const ctx = canvas.getContext("2d");
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    return { ctx, width: rect.width, height: rect.height };
  }

  function drawEmpty(canvas, label) {
    const { ctx, width, height } = setupCanvas(canvas);
    ctx.clearRect(0, 0, width, height);
    ctx.fillStyle = palette.muted;
    ctx.font = "600 14px Inter, sans-serif";
    ctx.textAlign = "center";
    ctx.fillText(label, width / 2, height / 2);
  }

  function drawLineChart(canvas, series) {
    const points = series.flatMap((item) => item.points);
    if (!points.length) {
      drawEmpty(canvas, "No data");
      return;
    }
    const { ctx, width, height } = setupCanvas(canvas);
    const pad = { left: 60, right: 18, top: 18, bottom: 42 };
    const chartWidth = width - pad.left - pad.right;
    const chartHeight = height - pad.top - pad.bottom;
    const xValues = points.map((point) => new Date(`${point.date}T00:00:00`).getTime());
    const yValues = points.map((point) => point.value);
    const xMin = Math.min(...xValues);
    const xMax = Math.max(...xValues);
    const yMax = Math.max(...yValues) * 1.12 || 1;
    const xScale = (dateValue) =>
      pad.left + ((new Date(`${dateValue}T00:00:00`).getTime() - xMin) / Math.max(1, xMax - xMin)) * chartWidth;
    const yScale = (value) => pad.top + chartHeight - (value / yMax) * chartHeight;

    ctx.clearRect(0, 0, width, height);
    ctx.strokeStyle = palette.line;
    ctx.lineWidth = 1;
    ctx.fillStyle = palette.muted;
    ctx.font = "12px Inter, sans-serif";
    ctx.textAlign = "right";

    for (let i = 0; i <= 4; i += 1) {
      const value = (yMax / 4) * i;
      const y = yScale(value);
      ctx.beginPath();
      ctx.moveTo(pad.left, y);
      ctx.lineTo(width - pad.right, y);
      ctx.stroke();
      ctx.fillText(money(value), pad.left - 8, y + 4);
    }

    series.forEach((item) => {
      if (!item.points.length) return;
      ctx.beginPath();
      ctx.strokeStyle = item.color;
      ctx.lineWidth = 2.6;
      ctx.setLineDash(item.dashed ? [6, 5] : []);
      item.points.forEach((point, index) => {
        const x = xScale(point.date);
        const y = yScale(point.value);
        if (index === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      });
      ctx.stroke();
      ctx.setLineDash([]);
    });

    const labelDates = [points[0].date, points[Math.floor(points.length / 2)].date, points[points.length - 1].date];
    ctx.fillStyle = palette.muted;
    ctx.textAlign = "center";
    labelDates.forEach((dateValue) => {
      ctx.fillText(dateValue.slice(5), xScale(dateValue), height - 14);
    });

    let legendX = pad.left;
    series.forEach((item) => {
      ctx.fillStyle = item.color;
      ctx.fillRect(legendX, 8, 12, 3);
      ctx.fillStyle = palette.ink;
      ctx.textAlign = "left";
      ctx.fillText(item.label, legendX + 18, 12);
      legendX += ctx.measureText(item.label).width + 46;
    });
  }

  function drawBarChart(canvas, rows, key = "net_revenue") {
    if (!rows.length) {
      drawEmpty(canvas, "No data");
      return;
    }
    const { ctx, width, height } = setupCanvas(canvas);
    const topRows = rows.slice(0, 8);
    const pad = { left: 118, right: 24, top: 14, bottom: 22 };
    const chartWidth = width - pad.left - pad.right;
    const barGap = 9;
    const barHeight = Math.max(16, (height - pad.top - pad.bottom - barGap * (topRows.length - 1)) / topRows.length);
    const maxValue = Math.max(...topRows.map((row) => row[key])) || 1;

    ctx.clearRect(0, 0, width, height);
    ctx.font = "12px Inter, sans-serif";
    topRows.forEach((row, index) => {
      const y = pad.top + index * (barHeight + barGap);
      const barWidth = Math.max(2, (row[key] / maxValue) * chartWidth);
      ctx.fillStyle = ["#255e91", "#0c7c7a", "#2f7d4f", "#a76600", "#b74d3f"][index % 5];
      ctx.fillRect(pad.left, y, barWidth, barHeight);
      ctx.fillStyle = palette.ink;
      ctx.textAlign = "right";
      ctx.fillText(row.name, pad.left - 9, y + barHeight * 0.66);
      ctx.textAlign = "left";
      ctx.fillStyle = palette.muted;
      ctx.fillText(money(row[key]), pad.left + barWidth + 8, y + barHeight * 0.66);
    });
  }

  function renderKpis(rows) {
    const metrics = aggregateRows(rows);
    const marketing = aggregateMarketing(filteredMarketing());
    const roas = marketing.spend ? metrics.revenue / marketing.spend : 0;
    $("kpiRevenue").textContent = money(metrics.revenue);
    $("kpiRoas").textContent = `${roas.toFixed(2)}x ROAS`;
    $("kpiProfit").textContent = money(metrics.profit);
    $("kpiMargin").textContent = `${pct(metrics.margin)} margin`;
    $("kpiOrders").textContent = number(metrics.orders);
    $("kpiAov").textContent = `${money(metrics.aov)} AOV`;
    $("kpiForecast").textContent = money(data.summary.forecastNext30);
  }

  function renderAnomalies() {
    const rows = data.anomalies
      .filter((row) => dateInRange(row.date, state.start, state.end))
      .sort((a, b) => b.date.localeCompare(a.date))
      .slice(0, 8);
    $("anomalyCount").textContent = `${rows.length} shown`;
    $("anomalyList").innerHTML =
      rows
        .map(
          (row) => `
          <div class="anomaly ${String(row.severity).toLowerCase()}">
            <strong>${row.date} · ${row.metric} · ${row.severity}</strong>
            <span>${money(row.value)} vs ${money(row.expected)} expected (${pct(row.deviation_pct)})</span>
            <p>${escapeHtml(row.action_hint)}</p>
          </div>
        `
        )
        .join("") || '<div class="anomaly low"><strong>No anomalies in this range</strong></div>';
  }

  function renderCharts(rows) {
    const daily = aggregateDaily(rows);
    const actualPoints = daily.map((row) => ({ date: row.date, value: row.net_revenue }));
    const forecastPoints = data.forecast.map((row) => ({ date: row.date, value: row.forecast_revenue }));
    drawLineChart($("revenueChart"), [
      { label: "Actual", color: palette.blue, points: actualPoints },
      { label: "Forecast", color: palette.coral, points: forecastPoints, dashed: true },
    ]);
    drawBarChart($("categoryChart"), groupBy(rows, "category"));
    drawBarChart($("channelChart"), groupBy(rows, "channel"));
    drawBarChart($("regionChart"), groupBy(rows, "region"));
  }

  function questionBounds(question) {
    const normalized = question.toLowerCase();
    const clamp = (bounds) => ({
      start: bounds.start < data.summary.dateStart ? data.summary.dateStart : bounds.start,
      end: bounds.end > data.summary.dateEnd ? data.summary.dateEnd : bounds.end,
    });
    const dayMatch = normalized.match(/(?:last|past)\s+(\d+)\s+day/);
    if (dayMatch) {
      const days = Number(dayMatch[1]);
      const end = new Date(`${data.summary.dateEnd}T00:00:00`);
      const start = new Date(end);
      start.setDate(end.getDate() - days + 1);
      return clamp({ start: start.toISOString().slice(0, 10), end: data.summary.dateEnd });
    }
    const yearMatch = normalized.match(/\b(2024|2025|2026)\b/);
    if (yearMatch) return clamp({ start: `${yearMatch[1]}-01-01`, end: `${yearMatch[1]}-12-31` });
    return { start: state.start, end: state.end };
  }

  function questionFilters(question) {
    const normalized = question.toLowerCase();
    const category = uniqueValues("category").find((value) => normalized.includes(value.toLowerCase())) || state.category;
    const region = uniqueValues("region").find((value) => normalized.includes(value.toLowerCase())) || state.region;
    const channel = uniqueValues("channel").find((value) => normalized.includes(value.toLowerCase())) || state.channel;
    return { category, region, channel };
  }

  function answerQuestion(question) {
    const normalized = question.toLowerCase();
    if (/(forecast|predict|projection|next)/.test(normalized)) {
      const dayMatch = normalized.match(/(\d+)\s+day/);
      const days = dayMatch ? Math.min(90, Math.max(1, Number(dayMatch[1]))) : 30;
      const rows = data.forecast.slice(0, days);
      const total = rows.reduce((sum, row) => sum + row.forecast_revenue, 0);
      const lower = rows.reduce((sum, row) => sum + row.lower_bound, 0);
      const upper = rows.reduce((sum, row) => sum + row.upper_bound, 0);
      return `Forecast revenue for the next ${days} days is ${money(total)}, with an expected range of ${money(lower)} to ${money(upper)}. Holdout MAPE is ${pct(data.forecastSummary.holdout_mape)}.`;
    }

    if (/(anomaly|anomalies|outlier|unusual|spike|drop)/.test(normalized)) {
      const bounds = questionBounds(question);
      const rows = data.anomalies
        .filter((row) => dateInRange(row.date, bounds.start, bounds.end))
        .sort((a, b) => b.date.localeCompare(a.date));
      if (!rows.length) return "No anomalies were flagged for that range.";
      const top = rows[0];
      return `${rows.length} anomalies were flagged. Most recent: ${top.date} ${top.metric} at ${money(top.value)} vs expected ${money(top.expected)} (${top.severity} severity).`;
    }

    const rows = filteredBreakdown({ ...questionBounds(question), ...questionFilters(question) });
    const metrics = aggregateRows(rows);

    if (/top category|best category/.test(normalized)) {
      const top = groupBy(rows, "category")[0];
      return top
        ? `Top category is ${top.name}, with ${money(top.net_revenue)} revenue across ${number(top.orders)} orders.`
        : "No matching rows were found.";
    }
    if (/top region|best region/.test(normalized)) {
      const top = groupBy(rows, "region")[0];
      return top
        ? `Top region is ${top.name}, with ${money(top.net_revenue)} revenue across ${number(top.orders)} orders.`
        : "No matching rows were found.";
    }
    if (/top channel|best channel/.test(normalized)) {
      const top = groupBy(rows, "channel")[0];
      return top
        ? `Top channel is ${top.name}, with ${money(top.net_revenue)} revenue across ${number(top.orders)} orders.`
        : "No matching rows were found.";
    }
    if (/(marketing|roas|spend|cpc)/.test(normalized)) {
      const marketing = aggregateMarketing(filteredMarketing(questionBounds(question)));
      const roas = marketing.spend ? metrics.revenue / marketing.spend : 0;
      const cpc = marketing.clicks ? marketing.spend / marketing.clicks : 0;
      return `Marketing spend is ${money(marketing.spend)} with ${roas.toFixed(2)}x ROAS and ${money(cpc)} CPC.`;
    }
    if (/(profit|margin)/.test(normalized)) {
      return `Gross profit is ${money(metrics.profit)} on ${money(metrics.revenue)} revenue, for a ${pct(metrics.margin)} margin rate.`;
    }
    if (/(orders|aov|average order)/.test(normalized)) {
      return `${number(metrics.orders)} orders generated ${money(metrics.revenue)} revenue, with ${money(metrics.aov)} average order value.`;
    }
    return `Net revenue is ${money(metrics.revenue)} from ${number(metrics.orders)} orders, with ${money(metrics.aov)} average order value.`;
  }

  function addMessage(kind, text) {
    const node = document.createElement("div");
    node.className = `message ${kind}`;
    node.innerHTML = escapeHtml(text);
    $("chatLog").appendChild(node);
    $("chatLog").scrollTop = $("chatLog").scrollHeight;
  }

  function setupChat() {
    $("sampleQuestions").innerHTML = data.qaSamples
      .slice(0, 4)
      .map((item) => `<button type="button">${escapeHtml(item.question)}</button>`)
      .join("");
    $("sampleQuestions").querySelectorAll("button").forEach((button) => {
      button.addEventListener("click", () => {
        const question = button.textContent;
        addMessage("user", question);
        addMessage("bot", answerQuestion(question));
      });
    });
    $("chatForm").addEventListener("submit", (event) => {
      event.preventDefault();
      const question = $("chatInput").value.trim();
      if (!question) return;
      $("chatInput").value = "";
      addMessage("user", question);
      addMessage("bot", answerQuestion(question));
    });
    addMessage("bot", data.qaSamples[0]?.answer || "Data is ready.");
  }

  function render() {
    const rows = filteredBreakdown();
    $("dateRange").textContent = `${data.summary.dateStart} to ${data.summary.dateEnd}`;
    $("modelScore").textContent = `MAPE ${pct(data.forecastSummary.holdout_mape)}`;
    $("trendNote").textContent = `${number(rows.length)} grouped rows`;
    renderKpis(rows);
    renderCharts(rows);
    renderAnomalies();
  }

  setupFilters();
  setupChat();
  render();
  window.addEventListener("resize", render);
})();
