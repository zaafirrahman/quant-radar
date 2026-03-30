/* execution.js — Alpha Execution Bot Chart Logic */
/* Depends on Chart.js 4.x loaded via CDN and DATA injected by Python */

(function () {
    "use strict";

    const { dates, equity, spy, rebalance_dates } = DATA;

    // ── Color palette ──────────────────────────────────────────────────────
    const ORANGE   = "#ff8c00";
    const GREEN    = "#00ff88";
    const RED      = "#ff4d4d";
    const DIM      = "#333333";
    const SPY_CLR  = "#4488ff";

    // ── Determine equity color per segment (green if up, red if down) ──────
    function buildGradientDataset(ctx, values) {
        // Solid orange line for portfolio
        return {
            label: "Portfolio Equity",
            data: values,
            borderColor: ORANGE,
            backgroundColor: "transparent",
            borderWidth: 2,
            pointRadius: 0,
            pointHoverRadius: 4,
            pointHoverBackgroundColor: ORANGE,
            tension: 0.15,
            order: 1,
        };
    }

    // ── Rebalance vertical line plugin ─────────────────────────────────────
    const rebalPlugin = {
        id: "rebalLines",
        afterDraw(chart) {
            const { ctx, scales: { x, y } } = chart;
            if (!rebalance_dates || rebalance_dates.length === 0) return;

            rebalance_dates.forEach((d) => {
                const idx = dates.indexOf(d);
                if (idx < 0) return;
                const xPos = x.getPixelForValue(idx);

                ctx.save();
                ctx.setLineDash([4, 4]);
                ctx.strokeStyle = "#ff8c0055";
                ctx.lineWidth = 1;
                ctx.beginPath();
                ctx.moveTo(xPos, y.top);
                ctx.lineTo(xPos, y.bottom);
                ctx.stroke();
                ctx.restore();

                // Label
                ctx.save();
                ctx.font = "9px 'IBM Plex Mono', monospace";
                ctx.fillStyle = "#ff8c0088";
                ctx.textAlign = "center";
                ctx.fillText("R", xPos, y.top + 10);
                ctx.restore();
            });
        },
    };

    // ── Build datasets ─────────────────────────────────────────────────────
    const canvas  = document.getElementById("equityChart");
    if (!canvas) return;
    const ctx     = canvas.getContext("2d");

    const datasets = [buildGradientDataset(ctx, equity)];

    // SPY overlay
    if (spy && spy.length > 0 && spy.some(v => v !== null)) {
        datasets.push({
            label: "SPY (rebased)",
            data: spy,
            borderColor: SPY_CLR,
            backgroundColor: "transparent",
            borderWidth: 1.5,
            borderDash: [6, 3],
            pointRadius: 0,
            tension: 0.1,
            order: 2,
        });
    }

    // ── Chart config ───────────────────────────────────────────────────────
    const chart = new Chart(ctx, {
        type: "line",
        data: {
            labels: dates,
            datasets,
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            animation: { duration: 600 },
            interaction: {
                mode: "index",
                intersect: false,
            },
            plugins: {
                legend: {
                    display: datasets.length > 1,
                    labels: {
                        color: "#888888",
                        font: { family: "'IBM Plex Mono', monospace", size: 11 },
                        boxWidth: 20,
                        padding: 16,
                    },
                },
                tooltip: {
                    backgroundColor: "#111111",
                    borderColor: "#333333",
                    borderWidth: 1,
                    titleColor: "#ffffff",
                    bodyColor: "#cccccc",
                    titleFont: { family: "'IBM Plex Mono', monospace", size: 12 },
                    bodyFont: { family: "'IBM Plex Mono', monospace", size: 12 },
                    padding: 12,
                    callbacks: {
                        title(items) {
                            return items[0].label;
                        },
                        label(item) {
                            const val = item.raw;
                            if (val === null || val === undefined) return null;
                            const prefix = item.dataset.label === "SPY (rebased)" ? "SPY  " : "Port ";
                            return `${prefix} ${val.toFixed(4)}`;
                        },
                        afterBody(items) {
                            // Show daily return for portfolio
                            const idx = items[0].dataIndex;
                            if (idx > 0) {
                                const prev = equity[idx - 1];
                                const curr = equity[idx];
                                if (prev && curr) {
                                    const dr = ((curr / prev) - 1) * 100;
                                    const sign = dr >= 0 ? "+" : "";
                                    return [`Daily: ${sign}${dr.toFixed(3)}%`];
                                }
                            }
                            return [];
                        },
                    },
                },
            },
            scales: {
                x: {
                    ticks: {
                        color: "#555555",
                        font: { family: "'IBM Plex Mono', monospace", size: 10 },
                        maxTicksLimit: 10,
                        maxRotation: 0,
                    },
                    grid: {
                        color: "#111111",
                    },
                    border: { color: "#222222" },
                },
                y: {
                    ticks: {
                        color: "#555555",
                        font: { family: "'IBM Plex Mono', monospace", size: 10 },
                        callback(val) {
                            return val.toFixed(2);
                        },
                    },
                    grid: {
                        color: "#111111",
                    },
                    border: { color: "#222222" },
                },
            },
        },
        plugins: [rebalPlugin],
    });

    // ── Highlight equity value on load (latest point) ─────────────────────
    const lastIdx = equity.length - 1;
    if (lastIdx >= 0) {
        chart.tooltip.setActiveElements(
            [{ datasetIndex: 0, index: lastIdx }],
            { x: 0, y: 0 }
        );
        chart.update();
    }

})();