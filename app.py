"""PulseTeen: Igniting Youth Energy. Flask + SQLite.  Run: python app.py"""
import json, os, re, secrets, sqlite3
from datetime import date, datetime, timedelta
from functools import wraps
from flask import Flask, abort, flash, g, redirect, render_template, request, session, url_for
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.security import check_password_hash, generate_password_hash
from i18n import t
from plan_generator import generate_plan, sleep_for, water_for

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)   # correct https links behind Render's proxy
app.config.update(SECRET_KEY=os.environ.get("SECRET_KEY") or secrets.token_hex(32),
                  SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax",
                  SESSION_COOKIE_SECURE=bool(os.environ.get("RENDER")))
# On Render, set DB_PATH to a file on the persistent disk (see render.yaml).
DB = os.environ.get("DB_PATH") or os.path.join(os.path.dirname(os.path.abspath(__file__)), "pulseteen.db")
SCHEMA = """
CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, name TEXT NOT NULL, email TEXT UNIQUE NOT NULL,
  pw_hash TEXT NOT NULL, age INTEGER NOT NULL, guardian INTEGER DEFAULT 0, created TEXT);
CREATE TABLE IF NOT EXISTS answers(user_id INTEGER PRIMARY KEY, data TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS plans(user_id INTEGER PRIMARY KEY, data TEXT NOT NULL, created TEXT);
CREATE TABLE IF NOT EXISTS progress(user_id INTEGER, day_key TEXT, PRIMARY KEY(user_id, day_key));
CREATE TABLE IF NOT EXISTS daily(user_id INTEGER, day TEXT, steps INTEGER DEFAULT 0, cups INTEGER DEFAULT 0,
  checkin INTEGER DEFAULT 0, PRIMARY KEY(user_id, day));
CREATE TABLE IF NOT EXISTS resets(token TEXT PRIMARY KEY, user_id INTEGER, expires TEXT);
"""


def db():
    if "db" not in g:
        g.db = sqlite3.connect(DB); g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(_):
    d = g.pop("db", None)
    if d: d.close()


def init_db():
    os.makedirs(os.path.dirname(DB), exist_ok=True)
    with sqlite3.connect(DB) as c: c.executescript(SCHEMA)


def csrf_token():
    if "_csrf" not in session: session["_csrf"] = secrets.token_hex(16)
    return session["_csrf"]


ICONS = {'home': '<path d="M3 11l9-8 9 8M5 10v10h14V10"/>', 'plan': '<rect x="3" y="5" width="18" height="16" rx="3"/><path d="M3 10h18M8 3v4M16 3v4"/>', 'life': '<path d="M12 21s-8-5-8-11a4.5 4.5 0 0 1 8-2.5A4.5 4.5 0 0 1 20 10c0 6-8 11-8 11z"/>', 'moti': '<path d="M12 2c1 4 5 6 5 11a5 5 0 0 1-10 0c0-2 1-3 2-4 0 2 1 3 2 3 0-4-1-6 1-10z"/>', 'prof': '<circle cx="12" cy="8" r="4"/><path d="M4 21c0-4 4-6 8-6s8 2 8 6"/>'}
app.jinja_env.globals.update(csrf_token=csrf_token, t=t, ICONS=ICONS)


@app.before_request
def before():
    if request.method == "POST" and not secrets.compare_digest(
            request.form.get("_csrf", ""), session.get("_csrf", "")):
        abort(400)
    g.user = None
    if session.get("uid"):
        g.user = db().execute("SELECT * FROM users WHERE id=?", (session["uid"],)).fetchone()


def login_required(f):
    @wraps(f)
    def w(*a, **k):
        if not g.user:
            flash("Please log in to continue.", "info"); return redirect(url_for("login"))
        return f(*a, **k)
    return w


def password_ok(p): return bool(re.fullmatch(r"(?=.*[A-Za-z])(?=.*\d).{8,}", p or ""))
def my_answers():
    r = db().execute("SELECT data FROM answers WHERE user_id=?", (g.user["id"],)).fetchone()
    return json.loads(r["data"]) if r else None
def my_plan():
    r = db().execute("SELECT data FROM plans WHERE user_id=?", (g.user["id"],)).fetchone()
    return json.loads(r["data"]) if r else None
def my_age():
    if not g.user: return None
    a = my_answers(); return a["age"] if a else g.user["age"]


# ---------- public pages ----------
@app.route("/")
def index(): return render_template("index.html")


@app.route("/lifestyle")
def lifestyle():
    age = my_age()
    return render_template("lifestyle.html", age=age, water=water_for(age)[0], sleep=sleep_for(age))


# ---------- accounts ----------
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        f = request.form; name = f.get("name", "").strip(); email = f.get("email", "").strip().lower()
        try: age = int(f.get("age", ""))
        except ValueError: age = 0
        err = None
        if len(name) < 2: err = "Please enter your name."
        elif not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email): err = "Please enter a valid email address."
        elif not 3 <= age <= 99: err = "Please enter an age between 3 and 99."
        elif age < 18 and not f.get("guardian"): err = "Please confirm parent/guardian permission."
        elif not password_ok(f.get("pw")): err = "Password needs 8+ characters with at least one letter and one number."
        elif f.get("pw") != f.get("pw2"): err = "Passwords do not match."
        elif db().execute("SELECT 1 FROM users WHERE email=?", (email,)).fetchone():
            err = "An account with this email already exists. Try logging in."
        if err: flash(err, "error")
        else:
            cur = db().execute("INSERT INTO users(name,email,pw_hash,age,guardian,created) VALUES(?,?,?,?,?,?)",
                               (name, email, generate_password_hash(f["pw"]), age, int(age < 18),
                                datetime.utcnow().isoformat()))
            db().commit(); session.clear(); session["uid"] = cur.lastrowid
            return redirect(url_for("quiz"))
    return render_template("signup.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        u = db().execute("SELECT * FROM users WHERE email=?", (request.form.get("email", "").strip().lower(),)).fetchone()
        if u and check_password_hash(u["pw_hash"], request.form.get("pw", "")):
            session.clear(); session["uid"] = u["id"]
            return redirect(url_for("plan"))
        flash("Email or password is incorrect.", "error")
    return render_template("login.html")


@app.route("/logout", methods=["POST"])
def logout():
    session.clear(); return redirect(url_for("index"))


@app.route("/forgot", methods=["GET", "POST"])
def forgot():
    if request.method == "POST":
        u = db().execute("SELECT id FROM users WHERE email=?", (request.form.get("email", "").strip().lower(),)).fetchone()
        if u:
            tok = secrets.token_urlsafe(24)
            db().execute("INSERT INTO resets VALUES(?,?,?)", (tok, u["id"], (datetime.utcnow() + timedelta(hours=1)).isoformat()))
            db().commit()
            # Replace with real email sending in production:
            print("PASSWORD RESET LINK:", url_for("reset", token=tok, _external=True))
        flash("If that email has an account, a reset link has been sent.", "info")
        return redirect(url_for("login"))
    return render_template("forgot.html")


@app.route("/reset/<token>", methods=["GET", "POST"])
def reset(token):
    r = db().execute("SELECT * FROM resets WHERE token=?", (token,)).fetchone()
    if not r or datetime.fromisoformat(r["expires"]) < datetime.utcnow():
        flash("This reset link is invalid or has expired.", "error"); return redirect(url_for("forgot"))
    if request.method == "POST":
        pw = request.form.get("pw", "")
        if not password_ok(pw): flash("Password needs 8+ characters with at least one letter and one number.", "error")
        elif pw != request.form.get("pw2"): flash("Passwords do not match.", "error")
        else:
            db().execute("UPDATE users SET pw_hash=? WHERE id=?", (generate_password_hash(pw), r["user_id"]))
            db().execute("DELETE FROM resets WHERE token=?", (token,)); db().commit()
            flash("Password updated. Please log in.", "info"); return redirect(url_for("login"))
    return render_template("reset.html")


@app.route("/profile")
@login_required
def profile(): return render_template("profile.html", a=my_answers(), has_plan=my_plan() is not None)


# ---------- questionnaire and plan ----------
def parse_answers(f):
    try:
        a = dict(age=int(f["age"]), gender=f.get("gender", ""), height=float(f["height"]),
                 weight=float(f["weight"]), body=f.get("body"), level=f.get("level"),
                 goal=f.get("goal"), time=int(f["time"]), eq=f.getlist("eq") or ["none"],
                 lim=f.get("lim", "").strip()[:300])
    except (KeyError, ValueError):
        return None, "Please fill in every required answer."
    if not 3 <= a["age"] <= 99: return None, "Please enter an age between 3 and 99."
    if not 80 <= a["height"] <= 230: return None, "Please enter your height in cm (80–230)."
    if not 10 <= a["weight"] <= 250: return None, "Please enter your weight in kg (10–250)."
    if a["body"] not in ("slim", "athletic", "average", "broader", "heavier"): return None, "Please pick a build."
    if a["level"] not in ("beginner", "intermediate", "active"): return None, "Please choose a fitness level."
    if a["goal"] not in ("fat", "strength", "stamina", "flex", "focus", "health"): return None, "Please choose a goal."
    if a["time"] not in (15, 20, 30, 45, 60): return None, "Please choose your daily time."
    return a, None


def save_plan(a):
    db().execute("INSERT OR REPLACE INTO plans VALUES(?,?,?)",
                 (g.user["id"], json.dumps(generate_plan(a)), datetime.utcnow().isoformat()))
    db().execute("DELETE FROM progress WHERE user_id=?", (g.user["id"],))


@app.route("/quiz", methods=["GET", "POST"])
@login_required
def quiz():
    a = my_answers() or {"age": g.user["age"]}
    if request.method == "POST":
        new, err = parse_answers(request.form)
        if err: flash(err, "error"); a = {**a, **request.form.to_dict()}
        else:
            db().execute("INSERT OR REPLACE INTO answers VALUES(?,?)", (g.user["id"], json.dumps(new)))
            save_plan(new); db().commit()
            return redirect(url_for("plan"))
    return render_template("quiz.html", a=a)


@app.route("/plan")
@login_required
def plan():
    p = my_plan()
    if not p: return redirect(url_for("quiz"))
    week = min(max(request.args.get("week", 0, type=int), 0), 3)
    done = {r["day_key"] for r in db().execute("SELECT day_key FROM progress WHERE user_id=?", (g.user["id"],))}
    key = lambda i: f"{i // 7}-{i % 7}"
    last = max((i for i in range(28) if key(i) in done), default=-1)
    streak = 0
    while last - streak >= 0 and key(last - streak) in done: streak += 1
    wk_done = [sum(1 for d in range(7) if f"{w}-{d}" in done) for w in range(4)]
    xp = sum(wk_done) * 50
    trophies = [("First step", xp >= 50)] + [(f"Week {i + 1}", wk_done[i] >= 7) for i in range(4)] + [("7-day streak", streak >= 7)]
    return render_template("plan.html", xp=xp, level=xp // 200 + 1, into=xp % 200, trophies=trophies, flame=ICONS["moti"], p=p, week=week, done=done, streak=streak,
                           wk_done=wk_done, total=sum(wk_done))


@app.post("/plan/done")
@login_required
def plan_done():
    k = request.form.get("key", "")
    if re.fullmatch(r"[0-3]-[0-6]", k):
        c = db().execute("DELETE FROM progress WHERE user_id=? AND day_key=?", (g.user["id"], k))
        if c.rowcount == 0: db().execute("INSERT INTO progress VALUES(?,?)", (g.user["id"], k))
        db().commit()
    return redirect(url_for("plan", week=k[0]) + "#d" + k[2:])


@app.post("/plan/regenerate")
@login_required
def plan_regen():
    a = my_answers()
    if a: save_plan(a); db().commit(); flash("Your plan was regenerated.", "info")
    return redirect(url_for("plan"))


# ---------- motivation ----------
def today_row():
    d = date.today().isoformat()
    db().execute("INSERT OR IGNORE INTO daily(user_id,day) VALUES(?,?)", (g.user["id"], d))
    return db().execute("SELECT * FROM daily WHERE user_id=? AND day=?", (g.user["id"], d)).fetchone()


@app.route("/motivation")
def motivation():
    row = checkins = None; goal = water_for(my_age())[1]
    if g.user:
        row = today_row()
        checkins = db().execute("SELECT COUNT(*) c FROM daily WHERE user_id=? AND checkin=1", (g.user["id"],)).fetchone()["c"]
    return render_template("motivation.html", row=row, goal=goal, checkins=checkins)


@app.post("/motivation/<action>")
@login_required
def motivation_action(action):
    d, uid = date.today().isoformat(), g.user["id"]; today_row()
    if action == "steps":
        try: s = max(0, min(100000, int(request.form.get("steps", 0))))
        except ValueError: s = 0
        db().execute("UPDATE daily SET steps=? WHERE user_id=? AND day=?", (s, uid, d))
    elif action == "cup":
        delta = 1 if request.form.get("d") == "1" else -1
        db().execute("UPDATE daily SET cups=MAX(0,MIN(30,cups+?)) WHERE user_id=? AND day=?", (delta, uid, d))
    elif action == "checkin":
        db().execute("UPDATE daily SET checkin=1-checkin WHERE user_id=? AND day=?", (uid, d))
    db().commit(); return redirect(url_for("motivation"))


init_db()
if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG") == "1")
