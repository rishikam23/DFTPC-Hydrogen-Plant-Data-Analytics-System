const token = localStorage.getItem("access_token");

if (!token) {
    window.location.href = "/";
}

let dashboardDate = null;
let h2Chart = null;
let powerChart = null;

// ================= COLOR =================

function setStatusColor(elementId, status) {
    const el = document.getElementById(elementId);
    if (!el || !status) return;

    el.classList.remove("text-success", "text-warning", "text-danger");

    if (status === "GREEN") el.classList.add("text-success");
    if (status === "AMBER") el.classList.add("text-warning");
    if (status === "RED") el.classList.add("text-danger");
}

// ================= DASHBOARD SUMMARY =================

async function loadDashboardSummary() {
    try {
        if (!dashboardDate) {
            const dateResponse = await fetch("/api/dashboard/latest-date", {
                headers: {
                    "Authorization": "Bearer " + token
                }
            });
            if (dateResponse.ok) {
                const dateData = await dateResponse.json();
                if (dateData.latest_date) {
                    dashboardDate = dateData.latest_date;
                }
            }
            if (!dashboardDate) {
                dashboardDate = "2025-10-31"; // Fallback default
            }
        }

        const subtitleEl = document.getElementById("dashboardSubtitle");
        if (subtitleEl) {
            subtitleEl.innerText = `Data for date: ${dashboardDate}`;
        }

        const response = await fetch(
            `/api/dashboard/summary?report_date=${dashboardDate}`,
            {
                headers: {
                    "Authorization": "Bearer " + token
                }
            }
        );

        if (response.status === 401 || response.status === 403) {
            localStorage.removeItem("access_token");
            window.location.href = "/";
            return;
        }

        const data = await response.json();

        document.getElementById("plantLoad").innerText =
            data.plant_load_percent != null
                ? data.plant_load_percent.toFixed(2)
                : "--";

        document.getElementById("psaRecovery").innerText =
            data.psa_recovery_percent != null
                ? data.psa_recovery_percent.toFixed(2)
                : "--";

        document.getElementById("h2Purity").innerText =
            data.h2_production_tday != null
                ? (data.h2_production_tday / 24).toFixed(2)
                : "--";

        document.getElementById("activeAlarms").innerText =
            data.active_pap_events ?? 0;

        if (data.status) {
            setStatusColor("plantLoad", data.status.plant_load);
            setStatusColor("psaRecovery", data.status.psa_recovery);
        }

    } catch (err) {
        console.error("Dashboard summary error:", err);
    }
}

// ================= DASHBOARD TRENDS =================

async function loadDashboardTrends() {
    try {
        const response = await fetch(
            `/api/dashboard/trends`,
            {
                headers: {
                    "Authorization": "Bearer " + token
                }
            }
        );

        const data = await response.json();

        if (!data.dates || data.dates.length === 0) {
            console.warn("No trend data available");
            return;
        }

        // 🔥 destroy old charts
        if (h2Chart) h2Chart.destroy();
        if (powerChart) powerChart.destroy();

        h2Chart = new Chart(
            document.getElementById("h2TrendChart"),
            {
                type: "line",
                data: {
                    labels: data.dates,
                    datasets: [{
                        label: "H2 Production (T/Day)",
                        data: data.h2,
                        tension: 0.3
                    }]
                }
            }
        );

        powerChart = new Chart(
            document.getElementById("powerChart"),
            {
                type: "line",
                data: {
                    labels: data.dates,
                    datasets: [{
                        label: "Power Consumption (MW)",
                        data: data.power,
                        tension: 0.3
                    }]
                }
            }
        );

    } catch (err) {
        console.error("Dashboard trends error:", err);
    }
}

// ================= LOGOUT =================

function logout() {
    localStorage.removeItem("access_token");
    window.location.href = "/";
}

// ================= LOAD =================

document.addEventListener("DOMContentLoaded", () => {
    loadDashboardSummary();
    loadDashboardTrends();
});

// ================= AUTO REFRESH =================

// Refresh KPIs every 30 seconds
setInterval(() => {
    loadDashboardSummary();
}, 30000);

// Refresh charts every 60 seconds
setInterval(() => {
    loadDashboardTrends();
}, 60000);