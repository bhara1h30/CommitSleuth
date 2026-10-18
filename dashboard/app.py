"""CommitSleuth web dashboard: login + roles, builds, problems, CRs, CI register, promotions, CSAR, config."""
import os, sys, datetime
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "analyzer"))
from functools import wraps
from flask import Flask, request, redirect, session, flash, get_flashed_messages
from markupsafe import Markup, escape
from werkzeug.security import check_password_hash
from common import q, ex, ROOT
import status_reporter

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-only-change-me")
JENKINS = os.environ.get("JENKINS_URL", "http://localhost:8080")
GITHUB = os.environ.get("GITHUB_URL", "https://github.com")
NAV = [("/", "Dashboard"), ("/builds", "Builds"), ("/problems", "Problems"), ("/crs", "Change Requests"),
       ("/cis", "CI Register"), ("/promotions", "Promotions"), ("/report", "CSAR Report"), ("/config", "Config")]
LIFECYCLE = ["Open", "Assigned", "Fixed", "Verified", "Closed"]

def layout(title, body):
    nav = "".join(f'<a href="{u}">{n}</a>' for u, n in NAV)
    who = f'{escape(session["user"])} ({session["role"]}) &nbsp;<a href="/logout">Logout</a>' if "user" in session else ""
    msgs = "".join(f'<div class="msg">{escape(m)}</div>' for m in get_flashed_messages())
    return f"""<!doctype html><html><head><meta charset="utf-8"><title>CommitSleuth - {escape(title)}</title><style>
body{{font-family:Segoe UI,Arial,sans-serif;margin:0;background:#f4f6f8;color:#222}}
header{{background:#1f3a5f;color:#fff;padding:10px 20px;display:flex;justify-content:space-between}}
nav a,header a{{color:#cfe3ff;margin-right:14px;text-decoration:none}} nav{{background:#2b4c7e;padding:8px 20px}}
main{{padding:20px}} table{{border-collapse:collapse;background:#fff;width:100%}}
th,td{{border:1px solid #ccd;padding:6px 10px;text-align:left;font-size:14px}} th{{background:#e3eaf3}}
.msg{{background:#fff3cd;padding:8px;margin-bottom:10px;border:1px solid #e0c86a}}
.card{{display:inline-block;background:#fff;border:1px solid #ccd;padding:14px 22px;margin:6px;min-width:140px}}
.card b{{font-size:26px;display:block}} input,select,button{{padding:5px;margin:2px}} pre{{background:#fff;padding:14px;border:1px solid #ccd}}
.bad{{color:#b00020;font-weight:600}} .good{{color:#1b7f3b;font-weight:600}}
</style></head><body><header><b>CommitSleuth - Build Failure Attribution</b><span>{who}</span></header>
<nav>{nav}<a href="{JENKINS}" target="_blank">Jenkins</a><a href="{GITHUB}" target="_blank">GitHub</a></nav>
<main><h2>{escape(title)}</h2>{msgs}{body}</main></body></html>"""

def table(headers, rows):
    h = "".join(f"<th>{escape(x)}</th>" for x in headers)
    r = "".join("<tr>" + "".join(f"<td>{escape(c)}</td>" for c in row) + "</tr>" for row in rows)
    return Markup(f"<table><tr>{h}</tr>{r}</table>")

def login_required(f):
    @wraps(f)
    def w(*a, **k):
        return f(*a, **k) if "user" in session else redirect("/login")
    return w

def admin_required(f):
    @wraps(f)
    def w(*a, **k):
        if "user" not in session:
            return redirect("/login")
        if session["role"] != "admin":
            return layout("Access denied", f"<p class='bad'>403 - role '{escape(session['role'])}' is not allowed to perform this action.</p>"), 403
        return f(*a, **k)
    return w

def is_admin():
    return session.get("role") == "admin"

def btn(action, label, extra=""):
    return Markup(f'<form method="post" action="{action}" style="display:inline">{extra}<button>{escape(label)}</button></form>')

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        row = q("SELECT * FROM users WHERE username=?", (request.form["username"],))
        if row and check_password_hash(row[0]["password_hash"], request.form["password"]):
            session["user"], session["role"] = row[0]["username"], row[0]["role"]
            return redirect("/")
        flash("Invalid username or password")
    return layout("Login", '<form method="post">User <input name="username"> Password <input name="password" type="password"> <button>Login</button></form>')

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

@app.route("/")
@login_required
def home():
    def n(sql): return q(sql)[0][0]
    cards = [("Configuration items", n("SELECT COUNT(*) FROM ci_register")),
             ("Builds", n("SELECT COUNT(*) FROM builds")),
             ("Failed builds", n("SELECT COUNT(*) FROM builds WHERE result='FAILURE'")),
             ("Open problems", n("SELECT COUNT(*) FROM problems WHERE status!='Closed'")),
             ("Pending CRs", n("SELECT COUNT(*) FROM change_requests WHERE status IN ('Raised','Under Review')")),
             ("Blocked promotions", n("SELECT COUNT(*) FROM promotions WHERE result='BLOCKED'"))]
    return layout("Dashboard", "".join(f'<div class="card"><b>{v}</b>{escape(k)}</div>' for k, v in cards))

@app.route("/builds")
@login_required
def builds():
    rows = [[r["build_no"], r["result"], r["commit_hash"], r["created"]] for r in q("SELECT * FROM builds ORDER BY id DESC")]
    return layout("Build History", table(["Build #", "Result", "Commit", "Time"], rows))

@app.route("/cis")
@login_required
def cis():
    rows = [[r[k] for k in r.keys()] for r in q("SELECT * FROM ci_register")]
    return layout("Configuration Item Status Register", table(["CI ID", "Item", "Version", "Status", "Owner", "Approval"], rows))

@app.route("/crs")
@login_required
def crs():
    rows = []
    for r in q("SELECT * FROM change_requests ORDER BY cr_id"):
        acts = Markup("")
        if is_admin():
            for a, lab in (("review", "Review"), ("approve", "Approve"), ("reject", "Reject"), ("implement", "Implemented")):
                acts += btn(f"/cr/{r['cr_id']}/{a}", lab)
        rows.append([r["cr_id"], r["description"], r["requester"], r["impact"], r["status"], r["decision"], r["decision_date"], r["branch"], acts])
    form = Markup("")
    if is_admin():
        form = Markup('<h3>Raise a change request</h3><form method="post" action="/cr/new">ID <input name="cr_id" size=7 placeholder="CR-009"> '
                      'Description <input name="description" size=40> Impact <input name="impact"> Branch <input name="branch"> <button>Raise</button></form>')
    return layout("Change Requests", table(["CR", "Description", "Requester", "Impact", "Status", "CCB decision", "Date", "Branch", "Actions"], rows) + form)

@app.route("/cr/new", methods=["POST"])
@admin_required
def cr_new():
    f = request.form
    ex("INSERT INTO change_requests VALUES (?,?,?,?,?,?,?,?,?)",
       (f["cr_id"], f["description"], session["user"], f["impact"], "Raised", "Awaiting CCB", "", f["branch"], ""))
    flash(f"{f['cr_id']} raised")
    return redirect("/crs")

@app.route("/cr/<cr_id>/<action>", methods=["POST"])
@admin_required
def cr_action(cr_id, action):
    m = {"review": ("Under Review", "Under CCB review"), "approve": ("Approved", "Approved by CCB"),
         "reject": ("Rejected", "Rejected by CCB"), "implement": ("Implemented", "Implemented and verified")}
    if action in m:
        ex("UPDATE change_requests SET status=?, decision=?, decision_date=? WHERE cr_id=?",
           (m[action][0], m[action][1], f"{datetime.date.today():%Y-%m-%d}", cr_id))
        flash(f"{cr_id} -> {m[action][0]}")
    return redirect("/crs")

@app.route("/problems")
@login_required
def problems():
    rows = []
    for r in q("SELECT * FROM problems ORDER BY id DESC"):
        nxt = LIFECYCLE[LIFECYCLE.index(r["status"]) + 1] if r["status"] in LIFECYCLE[:-1] else None
        act = btn(f"/problem/{r['id']}/advance", f"Mark {nxt}") if (is_admin() and nxt) else ""
        rows.append([f"P-{r['id']:03d}", r["build_no"], r["failure_type"], r["suspect_commit"], r["confidence"],
                     r["assignee"], r["status"], Markup(f'<a href="/problem/{r["id"]}">details</a> ') + act])
    return layout("Problem Tracking", table(["Problem", "Build", "Type", "Suspect commit", "Confidence", "Assignee", "Status", ""], rows))

@app.route("/problem/<int:pid>")
@login_required
def problem(pid):
    p = q("SELECT * FROM problems WHERE id=?", (pid,))[0]
    rows = [[r["commit_hash"], r["author"], r["message"], r["files"], r["score"]]
            for r in q("SELECT * FROM commit_scores WHERE problem_id=? ORDER BY score DESC", (pid,))]
    info = f"<p><b>Notification:</b> {escape(p['notification'])}</p><p><b>Recommended action:</b> {escape(p['action'])}</p><p><b>Status:</b> {escape(p['status'])}</p>"
    return layout(f"Problem P-{pid:03d}", Markup(info) + table(["Commit", "Author", "Message", "Files", "Confidence"], rows))

@app.route("/problem/<int:pid>/advance", methods=["POST"])
@admin_required
def problem_advance(pid):
    p = q("SELECT status FROM problems WHERE id=?", (pid,))[0]
    if p["status"] in LIFECYCLE[:-1]:
        ex("UPDATE problems SET status=? WHERE id=?", (LIFECYCLE[LIFECYCLE.index(p["status"]) + 1], pid))
    return redirect("/problems")

@app.route("/promotions")
@login_required
def promotions():
    rows = [[r["item"], r["from_level"], r["to_level"], r["promo_date"], r["approver"], r["result"], r["reason"]]
            for r in q("SELECT * FROM promotions ORDER BY id DESC")]
    return layout("Promotion Management", table(["Item", "From", "To", "Date", "Approver", "Result", "Reason"], rows))

@app.route("/report")
@login_required
def report():
    return layout("Configuration Status Accounting Report (CSAR)", Markup("<pre>") + escape(status_reporter.build_csar()) + Markup("</pre>"))

@app.route("/config")
@login_required
def config():
    text = open(os.path.join(ROOT, "scoring_config.yaml")).read()
    return layout("Customization: scoring_config.yaml", Markup("<pre>") + escape(text) + Markup("</pre>"))

if __name__ == "__main__":
    app.run(port=5000, debug=False)
