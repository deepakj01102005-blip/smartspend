from flask import Flask, render_template, request, jsonify
from database import get_db, init_db
from analytics import (
    get_summary,
    get_category_breakdown,
    get_monthly_trend,
    get_budget_status,
    get_transactions,
    get_insights
)

app = Flask(__name__)
app.secret_key = "smartspend-2026"

# Run this when the app starts
with app.app_context():
    init_db()


# ── Page route ────────────────────────────────────────────────────────────────

@app.route("/")
def home():
    return render_template("index.html")


# ── API routes (these return JSON data, not pages) ────────────────────────────

@app.route("/api/summary")
def api_summary():
    db = get_db()
    return jsonify(get_summary(db))


@app.route("/api/categories")
def api_categories():
    db = get_db()
    return jsonify(get_category_breakdown(db))


@app.route("/api/trend")
def api_trend():
    db = get_db()
    return jsonify(get_monthly_trend(db))


@app.route("/api/budgets")
def api_budgets():
    db = get_db()
    return jsonify(get_budget_status(db))


@app.route("/api/transactions")
def api_transactions():
    db = get_db()
    category = request.args.get("category")  # optional filter
    return jsonify(get_transactions(db, category=category))


@app.route("/api/insights")
def api_insights():
    db = get_db()
    return jsonify(get_insights(db))


# ── Add a transaction ─────────────────────────────────────────────────────────

@app.route("/api/transactions/add", methods=["POST"])
def add_transaction():
    db   = get_db()
    data = request.get_json()

    db.execute(
        "INSERT INTO transactions (type, category, amount, description, date) VALUES (?, ?, ?, ?, ?)",
        (data["type"], data["category"], float(data["amount"]), data["description"], data["date"])
    )
    db.commit()

    return jsonify({"success": True})


# ── Delete a transaction ──────────────────────────────────────────────────────

@app.route("/api/transactions/delete/<int:txn_id>", methods=["DELETE"])
def delete_transaction(txn_id):
    db = get_db()
    db.execute("DELETE FROM transactions WHERE id = ?", (txn_id,))
    db.commit()
    return jsonify({"success": True})


# ── Set a budget ──────────────────────────────────────────────────────────────

@app.route("/api/budgets/set", methods=["POST"])
def set_budget():
    db   = get_db()
    data = request.get_json()

    # If a budget for this category already exists, update it. Otherwise create it.
    db.execute("""
        INSERT INTO budgets (category, monthly_limit)
        VALUES (?, ?)
        ON CONFLICT(category) DO UPDATE SET monthly_limit = excluded.monthly_limit
    """, (data["category"], float(data["limit"])))

    db.commit()
    return jsonify({"success": True})


if __name__ == "__main__":
    app.run(debug=True, port=5000)
