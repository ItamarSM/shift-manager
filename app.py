from flask import Flask, redirect, render_template, session, url_for, request
from werkzeug.security import generate_password_hash, check_password_hash
from db import get_conn, get_cursor, init_db
import datetime
import requests
import os
from zoneinfo import ZoneInfo

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "Itush0374")
app.permanent_session_lifetime = datetime.timedelta(days=30)

init_db()

def get_shabbat_times(city):
    start = None
    end = None
    try:
        data = requests.get(f"https://www.hebcal.com/shabbat?cfg=json&city={city}&M=on").json()
        for i in data["items"]:
            if i["category"] == "candles":
                start = i["date"]
            elif i["category"] == "havdalah":
                end = i["date"]
        if start and end:
            return (datetime.datetime.fromisoformat(start).replace(tzinfo=None), datetime.datetime.fromisoformat(end).replace(tzinfo=None))
    except:
        return (None, None)

def calculate_earnings(clock_in, clock_out, shabbat_start, shabbat_end, regular_rate, shabbat_rate):
    if shabbat_start and shabbat_end:
        if min(clock_in, shabbat_start) == clock_in and min(clock_out, shabbat_start) == clock_out:
            return (clock_out - clock_in).total_seconds() / 3600 * regular_rate
        elif max(clock_in, shabbat_end) == clock_in:
            return (clock_out - clock_in).total_seconds() / 3600 * regular_rate
        elif min(clock_in, shabbat_start) == clock_in and max(clock_out, shabbat_start) == clock_out:
            weekday_time = (shabbat_start - clock_in).total_seconds() / 3600
            shabbat_time = (clock_out - shabbat_start).total_seconds() / 3600
            return weekday_time*regular_rate + shabbat_time*shabbat_rate
        elif max(shabbat_start, clock_in) == clock_in and min(shabbat_end, clock_out) == clock_out:
            return (clock_out - clock_in).total_seconds() / 3600 * shabbat_rate
        elif min(clock_in, shabbat_end) == clock_in and max(clock_out, shabbat_end) == clock_out:
            weekday_time = (shabbat_end - clock_in).total_seconds() / 3600
            shabbat_time = (clock_out - shabbat_end).total_seconds() / 3600
            return weekday_time*regular_rate + shabbat_time*shabbat_rate
        else:
            return (clock_out - clock_in).total_seconds() / 3600 * regular_rate
    return (clock_out - clock_in).total_seconds() / 3600 * regular_rate


@app.route("/register", methods=["GET", "POST"])
def register():
    conn = get_conn()
    cursor = get_cursor(conn)
    if request.method == "GET":
        return render_template("register.html")
    else:
        hashed_p = generate_password_hash(request.form["password"])
        username = request.form["username"]
        cursor.execute("INSERT INTO users (username, password_hash) VALUES (%s, %s)", (username, hashed_p))
        conn.commit()
        conn.close()
    return redirect(url_for("login"))

@app.route("/login", methods=["GET", "POST"])
def login():
    conn = get_conn()
    cursor = get_cursor(conn)
    if request.method == "GET":
        return render_template("login.html", wrong_un=False, wrong_pw=False)
    username = request.form["username"]
    password = request.form["password"]
    try:
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()
        if check_password_hash(user["password_hash"], password):
            session.permanent = True
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            return redirect("/")
        else:
            return render_template("login.html", wrong_pw=True)
    except:
        return render_template("login.html", wrong_un=True, wrong_pw=False)

@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/")
def index():
    conn = get_conn()
    cursor = get_cursor(conn)
    if "user_id" not in session:
        return redirect(url_for("login"))
    cursor.execute("SELECT * FROM jobs WHERE user_id=%s", (session["user_id"],))
    job_list = cursor.fetchall()
    cursor.execute("SELECT shifts.*, jobs.name FROM shifts JOIN jobs ON shifts.job_id=jobs.id WHERE shifts.user_id=%s AND clock_out IS NULL", (session["user_id"],))
    active_shift = cursor.fetchone()
    clock_in_iso = None
    if active_shift:
        clock_in_iso = datetime.datetime.strptime(active_shift["clock_in"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=ZoneInfo("Asia/Jerusalem")).isoformat()
    return render_template("index.html", jobs=job_list, active_shift=active_shift, clock_in_iso=clock_in_iso)

@app.route("/settings", methods=["POST", "GET"])
def settings():
    conn = get_conn()
    cursor = get_cursor(conn)
    if "user_id" not in session:
        return redirect(url_for("login"))
    if request.method == "GET":
        cursor.execute("SELECT * FROM users WHERE id = %s", (session["user_id"],))
        user = cursor.fetchone()
        return render_template("settings.html", city=user["city"])
    city = request.form["city"]
    cursor.execute("UPDATE users SET city = %s WHERE id = %s", (city, session["user_id"]))
    conn.commit()
    conn.close()
    return redirect(url_for("settings"))

@app.route("/jobs", methods=["GET"])
def jobs():
    conn = get_conn()
    cursor = get_cursor(conn)
    if "user_id" not in session:
        return redirect(url_for("login"))
    cursor.execute("SELECT * FROM jobs WHERE user_id = %s", (session["user_id"],))
    job_list = cursor.fetchall()
    return render_template("jobs.html", jobs=job_list)

@app.route("/jobs/add", methods=["POST"])
def add_job():
    conn = get_conn()
    cursor = get_cursor(conn)
    if "user_id" not in session:
        return redirect(url_for("login"))
    cursor.execute("INSERT INTO jobs (user_id, name) VALUES (%s, %s)", (session["user_id"], request.form["name"]))
    conn.commit()
    conn.close()
    return redirect(url_for("jobs"))

@app.route("/jobs/<id>/setup", methods=["GET", "POST"])
def setup_job(id):
    conn = get_conn()
    cursor = get_cursor(conn)
    if "user_id" not in session:
        return redirect(url_for("login"))
    cursor.execute("SELECT * FROM salary_config WHERE job_id = %s", (id,))
    salary = cursor.fetchone()
    if request.method == "GET":
        return render_template("setup.html", salary=salary, id=id)
    if salary:
        cursor.execute("UPDATE salary_config SET regular_rate=%s, shabbat_rate=%s WHERE job_id = %s", (request.form["regular"], request.form["shabbat"], id))
    else:
        cursor.execute("INSERT INTO salary_config (job_id, user_id, regular_rate, shabbat_rate) VALUES (%s, %s, %s, %s)", (id, session["user_id"], request.form["regular"], request.form["shabbat"]))
    conn.commit()
    conn.close()
    return redirect(url_for("setup_job", id=id))

@app.route("/clock-in", methods=["POST"])
def clock_in():
    conn = get_conn()
    cursor = get_cursor(conn)
    if "user_id" not in session:
        return redirect(url_for("login"))
    job_id = request.form["job_id"]
    current_time = datetime.datetime.now(ZoneInfo("Asia/Jerusalem")).strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("INSERT INTO shifts (job_id, user_id, clock_in) VALUES(%s, %s, %s)", (job_id, session["user_id"], current_time))
    conn.commit()
    conn.close()
    return redirect("/")

@app.route("/clock-out", methods=["POST"])
def clock_out():
    conn = get_conn()
    cursor = get_cursor(conn)
    if "user_id" not in session:
        return redirect(url_for("login"))
    cursor.execute("SELECT * FROM shifts WHERE user_id=%s AND clock_out IS NULL", (session["user_id"],))
    active = cursor.fetchone()
    cursor.execute("SELECT * FROM users WHERE id=%s", (session["user_id"],))
    city = cursor.fetchone()["city"]
    shabbat_times = get_shabbat_times(city)
    cursor.execute("SELECT * FROM salary_config WHERE job_id=%s", (active["job_id"],))
    config = cursor.fetchone()
    clockout = datetime.datetime.now(ZoneInfo("Asia/Jerusalem")).strftime("%Y-%m-%d %H:%M:%S")
    time = (datetime.datetime.now(ZoneInfo("Asia/Jerusalem")).replace(tzinfo=None) - datetime.datetime.strptime(active["clock_in"], "%Y-%m-%d %H:%M:%S")).total_seconds() / 3600
    cursor.execute("UPDATE shifts SET clock_out=%s, hours_worked=%s WHERE id=%s", (clockout, time, active["id"]))
    clockin = datetime.datetime.strptime(active["clock_in"], "%Y-%m-%d %H:%M:%S")
    earnings = calculate_earnings(clockin, datetime.datetime.now(ZoneInfo("Asia/Jerusalem")).replace(tzinfo=None), shabbat_times[0], shabbat_times[1], config["regular_rate"], config["shabbat_rate"])
    cursor.execute("UPDATE shifts SET earnings=%s, day_of_week=%s WHERE id=%s", (earnings, clockin.strftime("%A"), active["id"]))
    conn.commit()
    conn.close()
    return redirect("/")

@app.route("/history")
def history():
    conn = get_conn()
    cursor = get_cursor(conn)
    if "user_id" not in session:
        return redirect(url_for("login"))
    cursor.execute("SELECT * FROM jobs WHERE user_id=%s", (session["user_id"],))
    jobs = cursor.fetchall()
    if not request.args.get("job_id"):
        cursor.execute("SELECT * FROM shifts WHERE user_id=%s AND clock_out IS NOT NULL", (session["user_id"],))
        shifts = cursor.fetchall()
        return render_template("history.html", jobs=jobs, shifts=shifts)
    else:
        cursor.execute("SELECT * FROM shifts WHERE user_id=%s AND job_id=%s AND clock_out IS NOT NULL", (session["user_id"], request.args.get("job_id")))
        shifts = cursor.fetchall()
        return render_template("history.html", jobs=jobs, shifts=shifts, selected=request.args.get("job_id"))

@app.route("/stats", methods=["GET"])
def stats():
    conn = get_conn()
    cursor = get_cursor(conn)
    if "user_id" not in session:
        return redirect(url_for("login"))
    cursor.execute("SELECT * FROM shifts WHERE user_id=%s AND clock_in IS NOT NULL AND earnings IS NOT NULL", (session["user_id"],))
    shifts = cursor.fetchall()
    monthly = {}
    for shift in shifts:
        month = datetime.datetime.strptime(shift["clock_in"], "%Y-%m-%d %H:%M:%S").strftime("%B %Y")
        if month not in monthly:
            monthly[month] = 0
        monthly[month] += shift["earnings"]
    return render_template("stats.html", labels=list(monthly.keys()), totals=list(monthly.values()))


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5002))
    app.run(host="0.0.0.0", port=port, debug=False)
