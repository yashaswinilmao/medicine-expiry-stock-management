import os
import sqlite3
from datetime import date, timedelta
from flask import Flask, render_template, request, redirect, url_for, flash, g

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-this-secret-key")
DATABASE = os.environ.get("DB_PATH", os.path.join(os.path.dirname(__file__), "instance", "medicines.db"))
EXPIRY_WARNING_DAYS = int(os.environ.get("EXPIRY_WARNING_DAYS", "30"))

def get_db():
    if "db" not in g:
        os.makedirs(os.path.dirname(DATABASE) or ".", exist_ok=True)
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
        g.db.execute("""
            CREATE TABLE IF NOT EXISTS medicines (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                batch_number TEXT NOT NULL,
                category TEXT NOT NULL DEFAULT 'General',
                quantity INTEGER NOT NULL DEFAULT 0 CHECK(quantity >= 0),
                unit_price REAL NOT NULL DEFAULT 0 CHECK(unit_price >= 0),
                expiry_date TEXT NOT NULL,
                supplier TEXT DEFAULT '',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        g.db.commit()
    return g.db

@app.teardown_appcontext
def close_db(error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()

def medicine_status(expiry_date, quantity):
    today = date.today()
    try:
        expiry = date.fromisoformat(expiry_date)
    except (TypeError, ValueError):
        return "Unknown"
    if expiry < today:
        return "Expired"
    if expiry <= today + timedelta(days=EXPIRY_WARNING_DAYS):
        return "Expiring Soon"
    if quantity <= 10:
        return "Low Stock"
    return "In Stock"

@app.template_filter("status")
def status_filter(medicine):
    return medicine_status(medicine["expiry_date"], medicine["quantity"])

def fetch_medicines(search=""):
    db = get_db()
    if search:
        pattern = f"%{search}%"
        return db.execute("""SELECT * FROM medicines
            WHERE name LIKE ? OR batch_number LIKE ? OR category LIKE ?
            ORDER BY expiry_date ASC""", (pattern, pattern, pattern)).fetchall()
    return db.execute("SELECT * FROM medicines ORDER BY expiry_date ASC").fetchall()

@app.route("/")
def dashboard():
    medicines = fetch_medicines()
    today = date.today()
    total = len(medicines)
    expired = sum(date.fromisoformat(m["expiry_date"]) < today for m in medicines)
    expiring = sum(today <= date.fromisoformat(m["expiry_date"]) <= today + timedelta(days=EXPIRY_WARNING_DAYS) for m in medicines)
    low_stock = sum(int(m["quantity"]) <= 10 for m in medicines)
    total_units = sum(int(m["quantity"]) for m in medicines)
    alerts = [m for m in medicines if medicine_status(m["expiry_date"], m["quantity"]) in ("Expired", "Expiring Soon", "Low Stock")]
    return render_template("dashboard.html", total=total, expired=expired, expiring=expiring,
                           low_stock=low_stock, total_units=total_units, alerts=alerts[:6])

@app.route("/medicines")
def medicines():
    search = request.args.get("q", "").strip()
    return render_template("medicines.html", medicines=fetch_medicines(search), search=search)

@app.route("/medicines/add", methods=["GET", "POST"])
def add_medicine():
    if request.method == "POST":
        data = read_form()
        if not data:
            return render_template("medicine_form.html", medicine=None, today=date.today().isoformat())
        get_db().execute("""INSERT INTO medicines
            (name,batch_number,category,quantity,unit_price,expiry_date,supplier)
            VALUES (?,?,?,?,?,?,?)""", data)
        get_db().commit()
        flash("Medicine added successfully.", "success")
        return redirect(url_for("medicines"))
    return render_template("medicine_form.html", medicine=None, today=date.today().isoformat())

@app.route("/medicines/<int:medicine_id>/edit", methods=["GET", "POST"])
def edit_medicine(medicine_id):
    db = get_db()
    medicine = db.execute("SELECT * FROM medicines WHERE id=?", (medicine_id,)).fetchone()
    if medicine is None:
        flash("Medicine not found.", "error")
        return redirect(url_for("medicines"))
    if request.method == "POST":
        data = read_form()
        if not data:
            return render_template("medicine_form.html", medicine=medicine, today=date.today().isoformat())
        db.execute("""UPDATE medicines SET name=?,batch_number=?,category=?,quantity=?,
            unit_price=?,expiry_date=?,supplier=? WHERE id=?""", (*data, medicine_id))
        db.commit()
        flash("Medicine updated successfully.", "success")
        return redirect(url_for("medicines"))
    return render_template("medicine_form.html", medicine=medicine, today=date.today().isoformat())

@app.post("/medicines/<int:medicine_id>/delete")
def delete_medicine(medicine_id):
    db = get_db()
    db.execute("DELETE FROM medicines WHERE id=?", (medicine_id,))
    db.commit()
    flash("Medicine deleted.", "success")
    return redirect(url_for("medicines"))

def read_form():
    try:
        name = request.form.get("name", "").strip()
        batch = request.form.get("batch_number", "").strip()
        category = request.form.get("category", "General").strip() or "General"
        quantity = int(request.form.get("quantity", "0"))
        price = float(request.form.get("unit_price", "0"))
        expiry = request.form.get("expiry_date", "")
        supplier = request.form.get("supplier", "").strip()
        date.fromisoformat(expiry)
        if not name or not batch or quantity < 0 or price < 0:
            raise ValueError
        return (name, batch, category, quantity, price, expiry, supplier)
    except (ValueError, TypeError):
        flash("Please enter valid details. Quantity and price cannot be negative.", "error")
        return None

@app.route("/expiry")
def expiry():
    medicines = fetch_medicines()
    today = date.today()
    expired = [m for m in medicines if date.fromisoformat(m["expiry_date"]) < today]
    expiring = [m for m in medicines if today <= date.fromisoformat(m["expiry_date"]) <= today + timedelta(days=EXPIRY_WARNING_DAYS)]
    return render_template("expiry.html", expired=expired, expiring=expiring, warning_days=EXPIRY_WARNING_DAYS)

@app.route("/reports")
def reports():
    medicines = fetch_medicines()
    category_totals = {}
    for m in medicines:
        category_totals[m["category"]] = category_totals.get(m["category"], 0) + int(m["quantity"])
    return render_template("reports.html", medicines=medicines, category_totals=category_totals,
                           total_units=sum(int(m["quantity"]) for m in medicines),
                           stock_value=sum(int(m["quantity"]) * float(m["unit_price"]) for m in medicines))

@app.route("/health")
def health():
    return {"status": "ok"}, 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")), debug=os.environ.get("FLASK_DEBUG") == "1")
