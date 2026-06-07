# CLAUDE.md

This file provides guidance to Claude Code when working in this folder.

## Context

This is a personal Python learning project — project 20. A Flask web app that works as a personal shift manager. Users register, create jobs, configure salary rates per job, clock in and out of shifts, and view earnings summaries with graphs. Designed to be used on a phone and added to the home screen as a PWA.

## Running the app

```powershell
python app.py
```

Requires:
```powershell
pip install flask werkzeug
```

## File structure

```
shift_manager/
    app.py                   ← all Flask routes
    db.py                    ← database setup and helper functions
    templates/
        base.html            ← shared layout, nav bar, PWA meta tags
        index.html           ← dashboard: clock in/out, active shift status
        jobs.html            ← manage jobs (add, list)
        setup.html           ← salary config per job (rates for weekday/friday/saturday)
        history.html         ← table of past shifts per job
        stats.html           ← monthly earnings graph (Chart.js)
        register.html
        login.html
    static/
        style.css            ← mobile-first responsive styles
        manifest.json        ← PWA manifest (name, icon, display: standalone)
        icon.png             ← app icon for home screen (user provides)
```

## Database — 4 tables

```
users         → id, username, password_hash, city
jobs          → id, user_id (FK→users), name
salary_config → id, job_id (FK→jobs), user_id (FK→users), regular_rate, shabbat_rate
shifts        → id, job_id (FK→jobs), user_id (FK→users), clock_in, clock_out, hours_worked, earnings, day_of_week
```

## Routes

```
GET/POST /register
GET/POST /login
POST     /logout
GET/POST /settings            → set user's city (used for Shabbat times API)
GET      /                    → dashboard: pick job, clock in/out, show active shift
POST     /clock-in            → insert shift row with clock_in = now, clock_out = NULL
POST     /clock-out           → fill in clock_out, calculate hours and earnings, save
GET      /jobs                → list user's jobs
POST     /jobs/add            → create a new job
GET/POST /jobs/<id>/setup     → salary config form for that job (regular_rate, shabbat_rate)
GET      /history             → past shifts (all jobs or filtered by job)
GET      /stats               → monthly earnings graph
```

## Salary calculation logic (clock-out)

Salary is split by Shabbat boundaries, not by weekday. Two rates: `regular_rate` and `shabbat_rate`.

1. Load the shift's `clock_in` from DB
2. Fetch Shabbat times from Hebcal API using the user's city: `https://www.hebcal.com/shabbat?cfg=json&city=CITY&M=on`
   - Parse `"Candle lighting"` event → Shabbat start
   - Parse `"Havdalah"` event → Shabbat end
   - Dates are ISO format strings, parse with `datetime.datetime.fromisoformat()`
3. Split the shift `[clock_in, clock_out]` into up to 3 segments against `[shabbat_start, shabbat_end]`
4. Multiply each segment's hours by its rate and sum for total earnings
5. Save `clock_out`, `hours_worked`, `earnings`, `day_of_week` to the shift row

## New concepts being introduced

- `datetime.datetime` — timestamps with both date AND time; `datetime.datetime.now()` for current time
- `datetime.timedelta` — result of subtracting two datetimes; `.total_seconds() / 3600` gives hours
- `.weekday()` — method on a datetime object; returns int 0 (Mon) to 6 (Sun)
- `strftime(format)` — formats a datetime as a string, e.g. `dt.strftime("%H:%M")` for "14:32", `"%B %Y"` for "June 2025"
- `strptime(string, format)` — parses a string back into a datetime object
- Chart.js — JavaScript charting library loaded from CDN; draws bar/line charts in the browser
- `| tojson` — Jinja2 filter; converts a Python list or dict to a safe JSON string inside a `<script>` tag so JavaScript can read it
- PWA manifest — `manifest.json` with `name`, `short_name`, `display: "standalone"`, `start_url`, `icons`; linked in `<head>` with `<link rel="manifest">`; tells the phone browser "this can be added to the home screen"
- `<meta name="viewport">` — makes the page scale correctly on mobile screens
- `<meta name="apple-mobile-web-app-capable" content="yes">` — enables add-to-home-screen on iOS Safari

## Build order

1. ✅ Auth — register/login/logout
2. ✅ Settings — city selector (dropdown of Israeli cities, saved to users.city)
3. ✅ Jobs — add jobs, list them, link to setup
4. ✅ Salary setup — regular_rate and shabbat_rate per job
5. ✅ Dashboard + Clock in/out — clock-in and clock-out routes done; earnings calculated with Shabbat API split (`get_shabbat_times`, `calculate_earnings` helpers); `day_of_week` saved; live JS timer in index.html using `setInterval` and template literals
6. ✅ History page — route and template done; filter by job via `request.args`; `selected` must be passed in both render_template calls
7. ✅ Stats page — monthly totals grouped by `strftime("%B %Y")`, passed to Chart.js as JSON via `| tojson`
8. ✅ PWA — manifest.json filled in, viewport/apple meta tags added to base.html, icon.png generated

## What the user knows

- Variables, `int()`, `float()`, `input()`
- `if / elif / else`
- `while True` loops with `break`
- `import random`, `random.randint()`
- Functions with parameters and `return`
- Classes: `__init__`, `self`, instance attributes, methods
- Lists: `append()`, `pop()`, indexing, `range(len(...))`
- Dictionaries: key-value pairs, access by key, list of dicts
- String methods: `.lower()`, `.strip()`, `.upper()`
- File I/O: `open()`, `read()`, `write()`, append mode (`"a"`), `with` statement
- Error handling: `try / except`, `FileNotFoundError`, `ValueError`, `KeyError`
- `datetime.date`: `date.today()`, converting to string with `str()`
- JSON: `json.load()`, `json.dump()`, saving/loading lists of dicts
- F-strings: `f"{variable}"`, float formatting `{value:.2f}`
- `for x in list` iteration, list comprehensions
- Built-in functions: `sum()`, `max()`, `sorted()` with `key=`, lambda functions
- Dict iteration: `.items()`, nested dicts
- `requests` library: `requests.get()`, `.json()` to parse response
- HTTP APIs: building URLs with query params, reading JSON responses, checking status codes, returning `None` on failure
- `os` module: `os.listdir()`, `os.path.splitext()`, `os.path.join()`, `os.makedirs()`, `os.rename()`
- SQLite3: `sqlite3.connect()`, cursor, `CREATE TABLE IF NOT EXISTS`, `INSERT INTO`, `INSERT OR IGNORE`, `SELECT`, `DELETE`, `WHERE`, `LIKE`, `fetchall()`, `fetchone()`, `conn.commit()`, `?` placeholders
- OOP inheritance: subclasses, `super().__init__()`, `__str__`, `isinstance()`
- Multi-file projects: `from filename import ClassName, function`
- Flask: `@app.route()`, `render_template()`, `request.form`, `request.args`, `redirect()`, `url_for()`, `methods=["POST"]`
- Jinja2: `{{ variable }}`, `{% for x in list %}` / `{% else %}` / `{% endfor %}`, `{% if condition %}` / `{% endif %}`
- Jinja2 template inheritance: `{% extends "base.html" %}`, `{% block content %}{% endblock %}`
- HTML: common tags, forms, hidden inputs, `<img src="">`, `<link rel="stylesheet">`
- CSS: external file via `url_for('static', ...)`, selectors, properties, classes, `input[type="text"]`
- GET vs POST: GET for reading, POST for writing
- URL variables in Flask routes: `@app.route("/post/<id>")`
- `session` — Flask dict stored in a signed cookie; persists login state across requests
- `app.secret_key` — signs and encrypts the session cookie
- `generate_password_hash()` / `check_password_hash()` from `werkzeug.security`
- Foreign keys in SQLite: `REFERENCES table(column)`, `PRAGMA foreign_keys = ON`
- `JOIN` / `LEFT JOIN` queries with `ON` to match foreign keys
- `COUNT()` + `GROUP BY` — SQL aggregate to count related rows per group
- `row_factory = sqlite3.Row` — access query results by column name instead of index
- Single-element tuples require a trailing comma: `(value,)` not `(value)`
- `"key" not in session` — checking if a user is logged in
- `datetime.datetime` — timestamps with both date and time; `datetime.datetime.now()` for current time
- `datetime.timedelta` — result of subtracting two datetimes; `.total_seconds() / 3600` gives hours
- `datetime.datetime.strptime(string, format)` — parses a string into a datetime object
- `datetime.datetime.fromisoformat(string)` — parses an ISO 8601 string into a datetime object
- `strftime(format)` — formats a datetime as a string, e.g. `dt.strftime("%A")` for weekday name
- `max(dt1, dt2)` / `min(dt1, dt2)` — comparing datetime objects works like numbers
- `required` attribute on `<select>` / `<input>` — browser blocks form submission if field is empty, no Python needed
- `|string` Jinja2 filter — converts a value to string so it can be compared with another string (e.g. `j['id']|string == selected`)
- JavaScript basics: `var`, `function`, `{}` blocks, `setInterval(fn, ms)` for repeating timers
- `new Date()` — JavaScript equivalent of `datetime.datetime.now()`; subtracting two Date objects gives milliseconds
- `Math.floor(n)` — JavaScript equivalent of `int(n)`
- Template literals — JavaScript f-strings: backticks and `${}` instead of quotes and `{}`
- `document.getElementById("id").textContent = ...` — updates the text of an HTML element by its id
- `<canvas>` — blank HTML drawing surface; Chart.js draws graphs onto it
- Chart.js — loaded from CDN; `new Chart(element, config)` draws a bar chart with `type`, `data.labels`, `data.datasets`
- `| tojson` — Jinja2 filter that converts a Python list/dict to a safe JSON string for use in `<script>` tags
- `datetime.replace(tzinfo=None)` — strips timezone info from a datetime to make it offset-naive
- PWA manifest — `manifest.json` with `name`, `short_name`, `display`, `start_url`, `icons`; linked via `<link rel="manifest">`
- `dict.keys()` / `dict.values()` — extract keys or values from a dict as a list

## Collaboration notes

- Always write responses in English
- Give the user the outline only — do not write the code for them
- When the user says they don't know something, ask if they want to learn about it
- Update this file whenever the user finishes a stage or exits a session
