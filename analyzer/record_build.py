"""Called by Jenkins after every build. On failure: parse log, rank commits, open a problem, notify."""
import argparse, re, subprocess, datetime, os, smtplib
from email.message import EmailMessage
from common import q, ex, load_cfg, ROOT
import scorer

def git(*a):
    return subprocess.run(["git", *a], cwd=ROOT, capture_output=True, text=True).stdout.strip()

def detect(log):
    if "COMPILATION ERROR" in log:
        return "compile"
    if re.search(r"Could not resolve dependencies|Could not find artifact|Non-resolvable|could not be resolved", log):
        return "dependency"
    if "There are test failures" in log or ("Tests run:" in log and "FAILURE" in log):
        return "test"
    return "unknown"

def commits_since_last_success():
    row = q("SELECT commit_hash FROM builds WHERE result='SUCCESS' ORDER BY id DESC LIMIT 1")
    rng = [f"{row[0]['commit_hash']}..HEAD"] if row and git("cat-file", "-t", row[0]["commit_hash"]) == "commit" else ["-5"]
    lines = git("log", "--reverse", "--no-merges", "--pretty=%h|%an|%s", *rng).splitlines()
    commits = []
    for ln in lines:
        h, a, m = ln.split("|", 2)
        files = [f for f in git("show", "--name-only", "--pretty=format:", h).splitlines() if f]
        commits.append({"hash": h, "author": a, "message": m, "files": files})
    return commits

def notify(text, cfg):
    n = cfg["notification"]
    if not n.get("enabled"):
        return
    os.makedirs(os.path.join(ROOT, "reports"), exist_ok=True)
    with open(os.path.join(ROOT, "reports", "notifications.log"), "a") as f:
        f.write(f"{datetime.datetime.now():%Y-%m-%d %H:%M} {text}\n")
    print("NOTIFY:", text)
    if n.get("channel") == "email" and os.environ.get("SMTP_HOST"):
        msg = EmailMessage(); msg["Subject"] = "CommitSleuth: build failure"
        msg["From"] = os.environ["SMTP_USER"]; msg["To"] = os.environ["NOTIFY_TO"]; msg.set_content(text)
        with smtplib.SMTP_SSL(os.environ["SMTP_HOST"], 465) as s:
            s.login(os.environ["SMTP_USER"], os.environ["SMTP_PASS"]); s.send_message(msg)

def store_failure(build_no, log, commits, ftype=None):
    cfg = load_cfg()
    ftype = ftype or detect(log)
    ranked = scorer.rank(commits, log, ftype, cfg)
    top = ranked[0]
    action = scorer.decide(top, cfg)
    text = cfg["notification"]["template"].format(build_no=build_no, failure_type=ftype, commit=top["hash"],
                                                  author=top["author"], confidence=top["score"], action=action)
    pid = ex("INSERT INTO problems(build_no,failure_type,suspect_commit,confidence,assignee,status,action,notification,created) VALUES (?,?,?,?,?,?,?,?,?)",
             (build_no, ftype, top["hash"], top["score"], top["author"], "Open", action, text, f"{datetime.datetime.now():%Y-%m-%d %H:%M}"))
    for r in ranked:
        ex("INSERT INTO commit_scores(problem_id,commit_hash,author,message,files,score) VALUES (?,?,?,?,?,?)",
           (pid, r["hash"], r["author"], r["message"], ", ".join(r["files"]), r["score"]))
    notify(text, cfg)
    return pid

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--result", required=True, choices=["SUCCESS", "FAILURE"])
    ap.add_argument("--build", type=int, required=True)
    ap.add_argument("--log", default="build.log")
    a = ap.parse_args()
    head = git("rev-parse", "--short", "HEAD")
    if a.result == "FAILURE":
        log = open(a.log, errors="ignore").read() if os.path.exists(a.log) else ""
        commits = commits_since_last_success()
        if commits:
            store_failure(a.build, log, commits)
    ex("INSERT INTO builds(build_no,result,commit_hash,created) VALUES (?,?,?,?)",
       (a.build, a.result, head, f"{datetime.datetime.now():%Y-%m-%d %H:%M}"))
    print(f"Build #{a.build} recorded: {a.result} at {head}")
