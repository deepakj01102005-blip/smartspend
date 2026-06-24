from datetime import datetime
import calendar


def get_this_month():
    # Returns current month in YYYY-MM format, e.g. "2026-05"
    return datetime.now().strftime("%Y-%m")


# ── 1. Summary numbers for the top cards ─────────────────────────────────────

def get_summary(db):
    month = get_this_month()

    row = db.execute("""
        SELECT
            SUM(CASE WHEN type = 'income'  THEN amount ELSE 0 END) AS income,
            SUM(CASE WHEN type = 'expense' THEN amount ELSE 0 END) AS expenses,
            COUNT(*) AS total_transactions
        FROM transactions
        WHERE strftime('%Y-%m', date) = ?
    """, (month,)).fetchone()

    income   = row["income"]   or 0
    expenses = row["expenses"] or 0
    savings  = income - expenses

    # Savings rate = what % of income did you save
    savings_rate = round((savings / income) * 100, 1) if income > 0 else 0

    return {
        "income":   round(income, 0),
        "expenses": round(expenses, 0),
        "savings":  round(savings, 0),
        "savings_rate": savings_rate,
        "total_transactions": row["total_transactions"]
    }


# ── 2. Spending per category (for the donut chart) ───────────────────────────

def get_category_breakdown(db):
    month = get_this_month()

    rows = db.execute("""
        SELECT
            category,
            SUM(amount) AS total,
            COUNT(*)    AS num_transactions
        FROM transactions
        WHERE type = 'expense'
          AND strftime('%Y-%m', date) = ?
        GROUP BY category
        ORDER BY total DESC
    """, (month,)).fetchall()

    # Calculate total spending so we can show percentages
    grand_total = sum(r["total"] for r in rows) or 1

    result = []
    for r in rows:
        result.append({
            "category":        r["category"],
            "total":           round(r["total"], 0),
            "num_transactions": r["num_transactions"],
            "percentage":      round((r["total"] / grand_total) * 100, 1)
        })

    return result


# ── 3. Last 6 months income vs expenses (for the line chart) ─────────────────

def get_monthly_trend(db):
    rows = db.execute("""
        SELECT
            strftime('%Y-%m', date) AS month,
            SUM(CASE WHEN type = 'income'  THEN amount ELSE 0 END) AS income,
            SUM(CASE WHEN type = 'expense' THEN amount ELSE 0 END) AS expenses
        FROM transactions
        WHERE date >= date('now', '-6 months')
        GROUP BY month
        ORDER BY month ASC
    """).fetchall()

    result = []
    for r in rows:
        result.append({
            "month":    r["month"],
            "income":   round(r["income"], 0),
            "expenses": round(r["expenses"], 0),
            "savings":  round(r["income"] - r["expenses"], 0)
        })

    return result


# ── 4. Budget vs actual spending ─────────────────────────────────────────────

def get_budget_status(db):
    month = get_this_month()

    # First get how much was spent per category this month
    spending = db.execute("""
        SELECT category, SUM(amount) AS spent
        FROM transactions
        WHERE type = 'expense'
          AND strftime('%Y-%m', date) = ?
        GROUP BY category
    """, (month,)).fetchall()

    # Turn the spending results into a simple dict for easy lookup
    # e.g. {"Food & Dining": 3200, "Transport": 1500}
    spent_per_category = {}
    for row in spending:
        spent_per_category[row["category"]] = row["spent"]

    # Now get all the budget limits
    budgets = db.execute("SELECT * FROM budgets ORDER BY category").fetchall()

    result = []
    for b in budgets:
        cat   = b["category"]
        limit = b["monthly_limit"]
        spent = spent_per_category.get(cat, 0)  # if no spending, default to 0

        pct_used = round((spent / limit) * 100, 1) if limit > 0 else 0

        # Decide the status color
        if pct_used >= 100:
            status = "danger"
        elif pct_used >= 80:
            status = "warning"
        else:
            status = "safe"

        result.append({
            "category":  cat,
            "limit":     round(limit, 0),
            "spent":     round(spent, 0),
            "remaining": round(limit - spent, 0),
            "pct_used":  pct_used,
            "over":      spent > limit,
            "status":    status
        })

    return result


# ── 5. All transactions (for the table) ──────────────────────────────────────

def get_transactions(db, category=None, limit=30):
    if category:
        rows = db.execute("""
            SELECT * FROM transactions
            WHERE category = ?
            ORDER BY date DESC, id DESC
            LIMIT ?
        """, (category, limit)).fetchall()
    else:
        rows = db.execute("""
            SELECT * FROM transactions
            ORDER BY date DESC, id DESC
            LIMIT ?
        """, (limit,)).fetchall()

    # Convert each row to a plain dict so Flask can convert it to JSON
    return [dict(r) for r in rows]


# ── 6. AI Insights ───────────────────────────────────────────────────────────

def get_insights(db):
    month     = get_this_month()
    insights  = []

    # Get this month's total expenses
    this_month = db.execute("""
        SELECT SUM(amount) AS total
        FROM transactions
        WHERE type = 'expense' AND strftime('%Y-%m', date) = ?
    """, (month,)).fetchone()

    this_month_total = this_month["total"] or 0

    # Get last month's total expenses
    last_month = db.execute("""
        SELECT SUM(amount) AS total
        FROM transactions
        WHERE type = 'expense'
          AND strftime('%Y-%m', date) = strftime('%Y-%m', date('now', '-1 month'))
    """).fetchone()

    last_month_total = last_month["total"] or 0

    # ── Insight 1: Top spending category ─────────────────────────────────────
    top_cat = db.execute("""
        SELECT category, SUM(amount) AS total
        FROM transactions
        WHERE type = 'expense' AND strftime('%Y-%m', date) = ?
        GROUP BY category
        ORDER BY total DESC
        LIMIT 1
    """, (month,)).fetchone()

    if top_cat:
        insights.append({
            "icon":     "🏆",
            "title":    f"Top Spend: {top_cat['category']}",
            "message":  f"You spent ₹{top_cat['total']:,.0f} on {top_cat['category']} this month — your biggest expense.",
            "severity": "info"
        })

    # ── Insight 2: Spending went up or down vs last month ────────────────────
    if last_month_total > 0:
        change = ((this_month_total - last_month_total) / last_month_total) * 100

        if change > 10:
            insights.append({
                "icon":     "📈",
                "title":    f"Spending up {abs(change):.0f}% vs last month",
                "message":  f"You spent ₹{this_month_total:,.0f} this month vs ₹{last_month_total:,.0f} last month.",
                "severity": "warning"
            })
        elif change < -10:
            insights.append({
                "icon":     "📉",
                "title":    f"Spending down {abs(change):.0f}% — great job!",
                "message":  f"You spent ₹{abs(last_month_total - this_month_total):,.0f} less than last month.",
                "severity": "success"
            })

    # ── Insight 3: Categories over budget ────────────────────────────────────
    over_budget = db.execute("""
        SELECT b.category, b.monthly_limit, SUM(t.amount) AS spent
        FROM budgets b
        JOIN transactions t ON b.category = t.category
        WHERE t.type = 'expense' AND strftime('%Y-%m', t.date) = ?
        GROUP BY b.category
        HAVING SUM(t.amount) > b.monthly_limit
    """, (month,)).fetchall()

    for item in over_budget:
        excess = item["spent"] - item["monthly_limit"]
        insights.append({
            "icon":     "⚠️",
            "title":    f"Over budget: {item['category']}",
            "message":  f"You went ₹{excess:,.0f} over your {item['category']} budget this month.",
            "severity": "danger"
        })

    # ── Insight 4: Daily average spend ───────────────────────────────────────
    today        = datetime.now()
    days_so_far  = today.day
    daily_avg    = this_month_total / days_so_far if days_so_far > 0 else 0
    days_in_month = calendar.monthrange(today.year, today.month)[1]
    projected    = daily_avg * days_in_month

    insights.append({
        "icon":     "📊",
        "title":    f"Daily average: ₹{daily_avg:,.0f}",
        "message":  f"At this rate you'll spend ₹{projected:,.0f} total this month.",
        "severity": "info"
    })

    # ── Insight 5: Savings rate ───────────────────────────────────────────────
    both = db.execute("""
        SELECT
            SUM(CASE WHEN type = 'income'  THEN amount ELSE 0 END) AS income,
            SUM(CASE WHEN type = 'expense' THEN amount ELSE 0 END) AS expenses
        FROM transactions
        WHERE strftime('%Y-%m', date) = ?
    """, (month,)).fetchone()

    income   = both["income"]   or 0
    expenses = both["expenses"] or 0

    if income > 0:
        rate = ((income - expenses) / income) * 100
        if rate < 20:
            insights.append({
                "icon":     "💡",
                "title":    f"Savings rate is only {rate:.0f}%",
                "message":  "Try to save at least 20% of your income each month.",
                "severity": "warning"
            })
        else:
            insights.append({
                "icon":     "🎉",
                "title":    f"Good savings rate: {rate:.0f}%",
                "message":  f"You're saving {rate:.0f}% of your income. Keep it up!",
                "severity": "success"
            })

    return insights
