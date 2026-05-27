# 🌿 Carbon Footprint — Complete VS Code Setup Guide

## Step 0 — What You're Building

A Flask web app that:
1. **Login page** → email/password or Google OAuth
2. **Onboarding** → enter name, city, family size
3. **Motivational Feed** → InShorts-style cards about Pune's pollution
4. **Calculate** → input daily activities, see live CO2 meter
5. **Insights Feed** → personalised reduction tips
6. **Dashboard** → history chart from SQL Server

All data saved to **Microsoft SQL Server** via SQLAlchemy.

---

## Step 1 — Install Prerequisites (do this ONCE)

### 1A. Python
Download from https://python.org (get Python 3.11+).
During install: ✅ check **"Add Python to PATH"**

Verify: open a terminal and type:
```
python --version
```

### 1B. Visual Studio Code
Download from https://code.visualstudio.com

Install these VS Code extensions:
- **Python** (by Microsoft)
- **Pylance**
- **SQLTools** (to browse your SQL Server from VS Code)

### 1C. Microsoft SQL Server
Download **SQL Server 2022 Developer Edition** (free):
https://www.microsoft.com/en-us/sql-server/sql-server-downloads

Also install **SQL Server Management Studio (SSMS)**:
https://learn.microsoft.com/en-us/sql/ssms/download-sql-server-management-studio-ssms

### 1D. ODBC Driver 17 for SQL Server
Download from Microsoft:
https://learn.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server

---

## Step 2 — Create the Database in SQL Server

Open **SSMS** → connect to `localhost` → right-click **Databases** → **New Database**

Name it: `CarbonFootprintDB`

Click OK. The database now exists.
Flask will create all **tables** automatically in Step 6.

---

## Step 3 — Open Project in VS Code

1. Create a folder on your computer:
   ```
   C:\Projects\carbon_footprint\
   ```

2. Copy all the project files (from this zip) into that folder.

3. In VS Code: **File → Open Folder** → select `carbon_footprint`

Your VS Code Explorer should look like this:
```
carbon_footprint/
│
├── app.py              ← Main Flask application (all routes)
├── config.py           ← Database URL, CO2 factors, settings
├── models.py           ← Database table definitions (SQLAlchemy)
├── requirements.txt    ← Python libraries to install
├── .env.example        ← Template for your .env secrets file
│
├── templates/          ← HTML files (Jinja2 templates)
│   ├── base.html       ← Navbar, flash messages, footer (shared)
│   ├── login.html      ← Login + Register tabs
│   ├── onboarding.html ← Name, city, family size
│   ├── feed.html       ← Motivational card feed (pollution facts)
│   ├── calculate.html  ← Activity input form + live CO2 meter
│   ├── insights.html   ← Personalised reduction tips feed
│   └── dashboard.html  ← History chart + data table
│
└── static/             ← CSS and JavaScript files
    ├── css/
    │   ├── main.css        ← Global styles (navbar, buttons, forms)
    │   ├── feed.css        ← Card feed styles (used by feed + insights)
    │   └── calculate.css   ← Calculation form styles
    └── js/
        ├── main.js         ← Global JS (flash auto-dismiss)
        ├── feed.js         ← Scroll animations for card feeds
        └── calculate.js    ← Live CO2 meter on calculation form
```

---

## Step 4 — Create the Virtual Environment

In VS Code, open the **Terminal** (Ctrl + `) and run:

```bash
# Navigate to your project folder (if not already there)
cd C:\Projects\carbon_footprint

# Create a virtual environment named .venv
python -m venv .venv

# Activate it (Windows)
.venv\Scripts\activate

# You should see (.venv) at the start of your prompt
```

> **Why virtual environment?**
> It installs packages only for THIS project, not globally.
> This prevents version conflicts between projects.

---

## Step 5 — Install Python Libraries

With `.venv` activated, run:

```bash
pip install -r requirements.txt
```

This installs:
| Library | Purpose |
|---|---|
| Flask | Web framework — handles routes, templates, sessions |
| Flask-Login | User session management (login/logout, @login_required) |
| Flask-SQLAlchemy | ORM — write Python classes, it creates SQL tables |
| Flask-WTF | Form validation and CSRF protection |
| pyodbc | Python driver to connect to SQL Server |
| python-dotenv | Reads .env file for secrets |
| Authlib | Google OAuth (optional) |

---

## Step 6 — Configure the .env File

In your project folder, create a file called `.env` (copy from `.env.example`):

```bash
copy .env.example .env
```

Open `.env` and edit it:

```env
# Generate a real secret key:
# In Python: import secrets; print(secrets.token_hex(32))
SECRET_KEY=paste-your-generated-key-here

SQL_SERVER=localhost
SQL_DATABASE=CarbonFootprintDB
USE_WINDOWS_AUTH=1
```

If you're using **Windows Authentication** (recommended for local dev),
leave `USE_WINDOWS_AUTH=1` and you don't need a username/password.

If you're using **SQL Server Authentication**:
```env
USE_WINDOWS_AUTH=0
SQL_USERNAME=sa
SQL_PASSWORD=your_sql_password
```

---

## Step 7 — Create Database Tables

Flask will create all tables from `models.py` automatically.
Run this command once:

```bash
flask db-init
```

You should see:
```
✅ All database tables created successfully.
```

Open SSMS → refresh your database → you'll see 3 new tables:
- `users` — registered users
- `activity_logs` — daily activity inputs
- `calculations` — computed CO2 totals

---

## Step 8 — Run the App

```bash
flask run
```

Or:
```bash
python app.py
```

Open your browser: http://127.0.0.1:5000

---

## How Data Flows (End to End)

```
Browser (HTML form)
      │
      │  POST /calculate  (form data)
      ▼
  app.py → calculate() route
      │
      ├─→ Validates inputs (Python)
      │
      ├─→ Creates ActivityLog object (models.py)
      │     └─→ db.session.add() → SQL INSERT into activity_logs
      │
      ├─→ Computes CO2 (multiplication with CO2_FACTORS from config.py)
      │
      ├─→ Creates Calculation object
      │     └─→ db.session.add() → SQL INSERT into calculations
      │
      └─→ redirect to /insights
              │
              ▼
          insights() route → Calculation.query.get(id)
              │              (SQL SELECT from calculations)
              ▼
          render_template('insights.html', calc=calc, ...)
              │
              ▼
          Jinja2 fills {{ calc.total_co2 }} etc. → HTML sent to browser
```

---

## How Templates Work (Jinja2)

Every HTML file **extends base.html**:

```html
{% extends "base.html" %}          ← inherit navbar, footer, flash messages
{% block title %}My Page{% endblock %}  ← override the <title> tag

{% block content %}
  <h1>Hello {{ user.full_name }}</h1>   ← Python variable → HTML
  {% for card in cards %}               ← Python list → loop
    <div>{{ card.title }}</div>
  {% endfor %}
{% endblock %}
```

**How static files link to templates:**
```html
<!-- In any template — url_for generates the correct path -->
<link rel="stylesheet" href="{{ url_for('static', filename='css/main.css') }}" />
<script src="{{ url_for('static', filename='js/calculate.js') }}"></script>
```

Flask translates `url_for('static', filename='css/main.css')`
→ `/static/css/main.css` → serves from `static/css/main.css` on disk.

---

## How the Database Connection Works

```
.env file
  SQL_SERVER=localhost
  SQL_DATABASE=CarbonFootprintDB
        │
        ▼
config.py builds the connection string:
  "DRIVER={ODBC Driver 17};SERVER=localhost;DATABASE=CarbonFootprintDB;Trusted_Connection=yes;"
        │
        ▼
  SQLALCHEMY_DATABASE_URI = "mssql+pyodbc:///?odbc_connect=..."
        │
        ▼
app.py:  db.init_app(app)   ← connects SQLAlchemy to Flask
        │
        ▼
models.py defines tables as Python classes:
  class User(db.Model):
      id    = db.Column(db.Integer, primary_key=True)
      email = db.Column(db.String(120))
        │
        ▼
flask db-init  →  db.create_all()  →  CREATE TABLE users (...) in SQL Server
```

---

## Common Errors & Fixes

| Error | Cause | Fix |
|---|---|---|
| `pyodbc.InterfaceError: ('IM002', ...)` | ODBC Driver not installed | Install "ODBC Driver 17 for SQL Server" |
| `Login failed for user 'NT AUTHORITY\...'` | Windows Auth not configured | Open SSMS → Security → Logins → check your Windows user has access |
| `ModuleNotFoundError: No module named 'flask'` | venv not activated | Run `.venv\Scripts\activate` first |
| `flask: command not found` | PATH issue | Run `python -m flask run` instead |
| Templates not found | Wrong folder name | Folder must be exactly `templates` (lowercase) |

---

## VS Code Tips

1. **Select Python interpreter**: Ctrl+Shift+P → "Python: Select Interpreter" → choose `.venv`
2. **Run Flask with debugger**: Create `.vscode/launch.json`:
   ```json
   {
     "version": "0.2.0",
     "configurations": [{
       "name": "Flask",
       "type": "python",
       "request": "launch",
       "module": "flask",
       "args": ["run", "--debug"],
       "env": { "FLASK_APP": "app.py" }
     }]
   }
   ```
   Then press **F5** to run with breakpoints.

3. **Browse SQL Server in VS Code**: Install SQLTools extension + SQLTools MS SQL Server driver → connect to `localhost` → browse your tables visually.

---

## Quick Reference — All Routes

| URL | Method | What it does |
|---|---|---|
| `/` | GET | Redirects to feed (logged in) or login |
| `/login` | GET/POST | Email/password login form |
| `/register` | GET/POST | New account creation |
| `/login/google` | GET | Google OAuth (configure .env) |
| `/onboarding` | GET/POST | Name + city + family size |
| `/feed` | GET | Motivational pollution facts feed |
| `/calculate` | GET/POST | Activity input + CO2 computation |
| `/insights` | GET | Personalised reduction tips |
| `/dashboard` | GET | History chart + data table |
| `/api/city-stats` | GET | JSON: city average CO2 |
| `/logout` | GET | Logs out, redirects to login |
