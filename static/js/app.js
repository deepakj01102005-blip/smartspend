// ── Helpers ───────────────────────────────────────────────────────────────────

// Format a number as rupees, e.g. 54000 → ₹54,000
function rupees(n) {
  return "₹" + Number(n).toLocaleString("en-IN", { maximumFractionDigits: 0 });
}

// Fetch JSON from a URL — returns the parsed data
async function getData(url) {
  const res = await fetch(url);
  return res.json();
}

// Show a small popup message at the bottom right
function showToast(msg) {
  const t = document.getElementById("toast");
  t.textContent = msg;
  t.classList.add("show");
  setTimeout(() => t.classList.remove("show"), 2500);
}


// ── Navigation ────────────────────────────────────────────────────────────────

// When a nav link is clicked, show that page and hide the others
document.querySelectorAll(".nav-link").forEach(link => {
  link.addEventListener("click", () => {
    const page = link.dataset.page;

    // Update active nav link
    document.querySelectorAll(".nav-link").forEach(l => l.classList.remove("active"));
    link.classList.add("active");

    // Show the right page, hide the rest
    document.querySelectorAll(".page").forEach(p => p.classList.remove("active"));
    document.getElementById("page-" + page).classList.add("active");

    // Update the title in the topbar
    document.getElementById("page-title").textContent =
      page.charAt(0).toUpperCase() + page.slice(1);

    // Load data for that page
    if (page === "transactions") loadTransactions();
    if (page === "budgets")      loadBudgets();
    if (page === "insights")     loadInsights();
  });
});


// ── Dashboard ─────────────────────────────────────────────────────────────────

async function loadDashboard() {
  // Fetch all dashboard data at the same time (parallel)
  const [summary, trend, cats] = await Promise.all([
    getData("/api/summary"),
    getData("/api/trend"),
    getData("/api/categories")
  ]);

  // Fill in the summary cards
  document.getElementById("val-income").textContent   = rupees(summary.income);
  document.getElementById("val-expenses").textContent = rupees(summary.expenses);
  document.getElementById("val-savings").textContent  = rupees(summary.savings);
  document.getElementById("val-txns").textContent     = summary.total_transactions;

  // Draw the line chart
  drawTrendChart(trend);

  // Draw the donut chart
  drawDonutChart(cats);
}


// ── Charts ────────────────────────────────────────────────────────────────────

let trendChart = null;
let donutChart = null;

function drawTrendChart(data) {
  const ctx = document.getElementById("chart-trend").getContext("2d");

  // Format month labels nicely, e.g. "2026-05" → "May 26"
  const labels = data.map(d => {
    const [year, month] = d.month.split("-");
    return new Date(year, month - 1).toLocaleString("en-IN", { month: "short", year: "2-digit" });
  });

  if (trendChart) trendChart.destroy(); // destroy old chart before making a new one

  trendChart = new Chart(ctx, {
    type: "line",
    data: {
      labels: labels,
      datasets: [
        {
          label: "Income",
          data: data.map(d => d.income),
          borderColor: "#60d0a0",
          backgroundColor: "rgba(96,208,160,0.08)",
          borderWidth: 2,
          pointRadius: 4,
          fill: true,
          tension: 0.4
        },
        {
          label: "Expenses",
          data: data.map(d => d.expenses),
          borderColor: "#f06060",
          backgroundColor: "rgba(240,96,96,0.06)",
          borderWidth: 2,
          pointRadius: 4,
          fill: true,
          tension: 0.4
        }
      ]
    },
    options: {
      responsive: true,
      plugins: {
        legend: { position: "top" }
      },
      scales: {
        x: { grid: { color: "rgba(255,255,255,0.04)" } },
        y: {
          grid: { color: "rgba(255,255,255,0.04)" },
          ticks: {
            callback: v => "₹" + (v / 1000).toFixed(0) + "k"
          }
        }
      }
    }
  });
}


function drawDonutChart(data) {
  const ctx = document.getElementById("chart-donut").getContext("2d");

  const colors = ["#f0d060","#60d0a0","#f06060","#6090f0","#d060f0","#60d0d0","#f09060"];

  if (donutChart) donutChart.destroy();

  donutChart = new Chart(ctx, {
    type: "doughnut",
    data: {
      labels: data.map(d => d.category),
      datasets: [{
        data: data.map(d => d.total),
        backgroundColor: colors.slice(0, data.length),
        borderWidth: 0
      }]
    },
    options: {
      responsive: true,
      cutout: "65%",
      plugins: {
        legend: { position: "bottom" }
      }
    }
  });
}


// ── Transactions ──────────────────────────────────────────────────────────────

async function loadTransactions() {
  const category = document.getElementById("filter-category").value;
  const url      = category ? `/api/transactions?category=${category}` : "/api/transactions";
  const data     = await getData(url);

  const tbody = document.getElementById("txn-list");

  if (data.length === 0) {
    tbody.innerHTML = `<tr><td colspan="6" style="text-align:center;padding:24px;color:#7a7a90">No transactions found</td></tr>`;
    return;
  }

  tbody.innerHTML = data.map(t => `
    <tr>
      <td style="color:#7a7a90;font-size:12px">${t.date}</td>
      <td>${t.description || "—"}</td>
      <td>${t.category}</td>
      <td><span class="tag ${t.type}">${t.type}</span></td>
      <td class="amount ${t.type}">
        ${t.type === "income" ? "+" : "−"}${rupees(t.amount)}
      </td>
      <td>
        <button class="del-btn" onclick="deleteTransaction(${t.id})">Delete</button>
      </td>
    </tr>
  `).join("");
}

// Reload transactions when category filter changes
document.getElementById("filter-category").addEventListener("change", loadTransactions);

async function deleteTransaction(id) {
  if (!confirm("Delete this transaction?")) return;

  await fetch(`/api/transactions/delete/${id}`, { method: "DELETE" });
  showToast("Transaction deleted");
  loadTransactions();
  loadDashboard(); // refresh the dashboard cards too
}


// ── Budgets ───────────────────────────────────────────────────────────────────

async function loadBudgets() {
  const data = await getData("/api/budgets");
  const grid = document.getElementById("budget-grid");

  grid.innerHTML = data.map(b => `
    <div class="budget-card">
      <div class="budget-card-top">
        <span class="budget-name">${b.category}</span>
        <span class="budget-badge ${b.status}">
          ${b.status === "danger" ? "Over" : b.status === "warning" ? "Near limit" : "On track"}
        </span>
      </div>
      <div class="progress-bg">
        <div class="progress-fill ${b.status}" style="width:${Math.min(b.pct_used, 100)}%"></div>
      </div>
      <div class="budget-amounts">
        <span><span class="budget-spent">${rupees(b.spent)}</span> spent</span>
        <span>of ${rupees(b.limit)}</span>
      </div>
    </div>
  `).join("");
}


// ── Insights ──────────────────────────────────────────────────────────────────

async function loadInsights() {
  const data = await getData("/api/insights");
  const list = document.getElementById("insights-list");

  list.innerHTML = data.map(i => `
    <div class="insight-card ${i.severity}">
      <span class="insight-icon">${i.icon}</span>
      <div>
        <div class="insight-title">${i.title}</div>
        <div class="insight-msg">${i.message}</div>
      </div>
    </div>
  `).join("");
}


// ── Add Transaction Modal ─────────────────────────────────────────────────────

document.getElementById("btn-add").addEventListener("click", () => {
  // Set today's date as the default
  document.getElementById("input-date").value = new Date().toISOString().slice(0, 10);
  document.getElementById("modal-add").classList.add("open");
});

document.getElementById("close-add").addEventListener("click", () => {
  document.getElementById("modal-add").classList.remove("open");
});

document.getElementById("submit-add").addEventListener("click", async () => {
  const payload = {
    type:        document.getElementById("input-type").value,
    category:    document.getElementById("input-category").value,
    amount:      document.getElementById("input-amount").value,
    description: document.getElementById("input-desc").value || "Transaction",
    date:        document.getElementById("input-date").value
  };

  if (!payload.amount || !payload.date) {
    showToast("Please fill all fields");
    return;
  }

  await fetch("/api/transactions/add", {
    method:  "POST",
    headers: { "Content-Type": "application/json" },
    body:    JSON.stringify(payload)
  });

  document.getElementById("modal-add").classList.remove("open");
  showToast("Transaction added!");
  loadDashboard();
});


// ── Set Budget Modal ──────────────────────────────────────────────────────────

document.getElementById("btn-set-budget").addEventListener("click", () => {
  document.getElementById("modal-budget").classList.add("open");
});

document.getElementById("close-budget").addEventListener("click", () => {
  document.getElementById("modal-budget").classList.remove("open");
});

document.getElementById("submit-budget").addEventListener("click", async () => {
  const payload = {
    category: document.getElementById("budget-cat").value,
    limit:    document.getElementById("budget-limit").value
  };

  if (!payload.limit) {
    showToast("Please enter a limit");
    return;
  }

  await fetch("/api/budgets/set", {
    method:  "POST",
    headers: { "Content-Type": "application/json" },
    body:    JSON.stringify(payload)
  });

  document.getElementById("modal-budget").classList.remove("open");
  showToast("Budget saved!");
  loadBudgets();
});


// ── Start the app ─────────────────────────────────────────────────────────────

// This runs when the page first loads
loadDashboard();
