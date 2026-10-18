"""Promotion gate: allow promotion only if tests passed and the commit's CR is approved."""
import argparse, re, subprocess, sys, datetime
from common import q, ex, ROOT

ap = argparse.ArgumentParser()
ap.add_argument("--item", default="CommitSleuth demo app")
ap.add_argument("--from", dest="frm", required=True)
ap.add_argument("--to", required=True)
ap.add_argument("--approver", default="CCB")
ap.add_argument("--tests-passed", action="store_true")
a = ap.parse_args()

msg = subprocess.run(["git", "log", "--no-merges", "-1", "--pretty=%s"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
m = re.match(r"(CR-\d+)", msg)
reasons = []
if not a.tests_passed:
    reasons.append("tests did not pass")
if not m:
    reasons.append("HEAD commit has no CR id")
else:
    row = q("SELECT status FROM change_requests WHERE cr_id=?", (m.group(1),))
    status = row[0]["status"] if row else "Unknown"
    if status not in ("Approved", "Implemented"):
        reasons.append(f"{m.group(1)} is '{status}', not approved")
result = "BLOCKED" if reasons else "PASSED"
ex("INSERT INTO promotions(item,from_level,to_level,promo_date,approver,result,reason) VALUES (?,?,?,?,?,?,?)",
   (a.item, a.frm, a.to, f"{datetime.datetime.now():%Y-%m-%d %H:%M}", a.approver, result, "; ".join(reasons) or "all gates satisfied"))
print(f"PROMOTION {result}: {a.frm} -> {a.to}  {'; '.join(reasons)}")
sys.exit(1 if reasons else 0)
