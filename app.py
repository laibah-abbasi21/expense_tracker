from flask import Flask, render_template, request, redirect, url_for, session, flash
import psycopg2
import psycopg2.extras
from werkzeug.security import generate_password_hash, check_password_hash
import bcrypt


app = Flask(__name__)
app.secret_key = "supersecretkey"   # change this for security

# Database connection
def get_db_connection():
    conn = psycopg2.connect(
        host="localhost",
        database="expense_tracker",
        user="postgres",
        password="venom"   # replace with your postgres password
    )
    return conn

# ------------------- ROUTES -------------------

@app.route("/")
def index():
    username = session.get("username")

    conn = get_db_connection()
    cur = conn.cursor()

    # Total spent
    cur.execute("SELECT COALESCE(SUM(amount), 0) FROM expenses")
    total = cur.fetchone()[0]

    # Expenses list
    cur.execute("SELECT * FROM expenses ORDER BY date DESC")
    expenses = cur.fetchall()

    # Category-wise data for doughnut chart
    cur.execute("SELECT category, SUM(amount) FROM expenses GROUP BY category")
    category_data = cur.fetchall()

    # Month-wise data for bar/line chart
    cur.execute("""
        SELECT 
            TO_CHAR(date, 'Mon YYYY') AS month,
            SUM(amount) AS total
        FROM expenses
        GROUP BY month, DATE_TRUNC('month', date)
        ORDER BY DATE_TRUNC('month', date)
    """)
    monthly_data = cur.fetchall()

    conn.close()

    # Prepare category chart data
    category_labels = [row[0] for row in category_data]
    category_values = [float(row[1]) for row in category_data]

    default_colors = [
        "#ff6384", "#36a2eb", "#ffcd56", "#4bc0c0",
        "#9966ff", "#ff9f40", "#c9cbcf", "#009688", "#795548"
    ]
    category_colors = default_colors[:len(category_labels)]

    chart_data = {
        "labels": category_labels,
        "values": category_values,
        "colors": category_colors
    }

    # Prepare monthly chart data
    month_labels = [row[0] for row in monthly_data]
    month_totals = [float(row[1]) for row in monthly_data]

    return render_template(
        "index.html",
        username=username,
        total=total,
        expenses=expenses,
        chart_data=chart_data,
        month_labels=month_labels,
        month_totals=month_totals
    )


@app.route("/register", methods=["POST"])
def register():
    username = request.form["username"]   # keep only username
    password = request.form["password"]
    confirm_password = request.form["confirm_password"]

    if password != confirm_password:
        flash("Passwords do not match!", "danger")
        return redirect(url_for("index"))

    # hash password
    hashed_pw = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        cur.execute(
            "INSERT INTO users (username, password) VALUES (%s, %s)",
            (username, hashed_pw),
        )
        conn.commit()
        flash("Registration successful! Please login.", "success")
    except psycopg2.Error:
        flash("Username already exists!", "danger")
    finally:
        cur.close()
        conn.close()

    return redirect(url_for("index"))


@app.route("/login", methods=["POST"])
def login():
    username = request.form["username"]
    password = request.form["password"]

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("SELECT id, username, password FROM users WHERE username = %s", (username,))
    user = cur.fetchone()

    cur.close()
    conn.close()

    if user and bcrypt.checkpw(password.encode("utf-8"), user[2].encode("utf-8")):
        # store username in session
        session["username"] = user[1]
        flash("Login successful!", "success")
        return redirect(url_for("index"))
    else:
        flash("Invalid credentials!", "danger")
        return redirect(url_for("index"))



@app.route("/logout")
def logout():
    session.pop("username", None)
    flash("You have been logged out.", "info")
    return redirect(url_for("index"))


@app.route("/add", methods=["POST"])
def add_expense():
    if "username" not in session:
        flash("Please login first.", "danger")
        return redirect(url_for("index"))

    title = request.form["title"]
    amount = request.form["amount"]
    category = request.form["category"]

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO expenses (title, amount, category, date) VALUES (%s, %s, %s, NOW())",
                (title, amount, category))
    conn.commit()
    conn.close()

    flash("Expense added successfully!", "success")
    return redirect(url_for("index"))


@app.route("/delete/<int:id>")
def delete_expense(id):
    if "username" not in session:
        flash("Please login first.", "danger")
        return redirect(url_for("index"))

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM expenses WHERE id = %s", (id,))
    conn.commit()
    conn.close()

    flash("Expense deleted successfully!", "info")
    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(debug=True)
