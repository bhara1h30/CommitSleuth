"""Generates the Configuration Status Accounting Report (CSAR) from the status database."""
import subprocess, datetime, os
from common import q, ROOT

def counts(sql):
    return {r[0]: r[1] for r in q(sql)}

def build_csar():
    cis = q("SELECT status FROM ci_register")
    approved = sum(1 for c in cis if "Baselined" in c["status"])
    planned = sum(1 for c in cis if c["status"].startswith("Planned"))
    dev = len(cis) - approved - planned
    crs = counts("SELECT status, COUNT(*) FROM change_requests GROUP BY status")
    builds = counts("SELECT result, COUNT(*) FROM builds GROUP BY result")
    probs = counts("SELECT status, COUNT(*) FROM problems GROUP BY status")
    promos = counts("SELECT result, COUNT(*) FROM promotions GROUP BY result")
    tags = subprocess.run(["git", "tag"], cwd=ROOT, capture_output=True, text=True).stdout.split()
    n = len(cis) or 1
    lines = [
        "CONFIGURATION STATUS ACCOUNTING REPORT (CSAR)",
        "Project : CommitSleuth - Intelligent Build Failure Attribution System",
        f"Generated: {datetime.datetime.now():%d %b %Y %H:%M}  (by status_reporter.py)",
        "-" * 60,
        f"Configuration items under control : {len(cis)}",
        f"  Approved / baselined            : {approved} ({approved*100//n}%)",
        f"  In development / progress       : {dev} ({dev*100//n}%)",
        f"  Planned                         : {planned} ({planned*100//n}%)",
        f"Change requests                   : {sum(crs.values())}  {crs}",
        f"Builds                            : {sum(builds.values())}  {builds}",
        f"Problem reports                   : {sum(probs.values())}  {probs}",
        f"Promotions                        : {sum(promos.values())}  {promos}",
        f"Git tags (releases/baselines)     : {', '.join(tags) or 'none'}",
    ]
    return "\n".join(lines)

if __name__ == "__main__":
    text = build_csar()
    os.makedirs(os.path.join(ROOT, "reports"), exist_ok=True)
    path = os.path.join(ROOT, "reports", f"CSAR-{datetime.date.today():%Y%m%d}.txt")
    open(path, "w").write(text + "\n")
    print(text); print("\nSaved:", path)
