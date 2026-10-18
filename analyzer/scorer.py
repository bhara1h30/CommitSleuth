"""Commit Ranking Engine: weighted evidence score, normalised to a confidence value."""
import os
from common import load_cfg

def rank(commits, log_text, failure_type, cfg=None):
    """commits: list of dicts (oldest first) with hash, author, message, files (list)."""
    cfg = cfg or load_cfg()
    w = cfg["weights"]
    n = max(len(commits), 1)
    raw = []
    for i, c in enumerate(commits):
        stems = [os.path.splitext(os.path.basename(f))[0] for f in c["files"]]
        f_match = 1.0 if any(s and s in log_text for s in stems) else 0.0
        pom = 1.0 if ("pom.xml" in c["files"] and failure_type == "dependency") else 0.0
        recency = (i + 1) / n
        size = min(len(c["files"]) / 5.0, 1.0)
        raw.append(w["file_match"] * f_match + w["pom_change"] * pom
                   + w["recency"] * recency + w["change_size"] * size)
    total = sum(raw) or 1.0
    out = []
    for c, s in zip(commits, raw):
        d = dict(c); d["score"] = round(s / total, 3)
        out.append(d)
    return sorted(out, key=lambda d: d["score"], reverse=True)

def decide(top, cfg=None):
    cfg = cfg or load_cfg()
    r = cfg["rollback"]
    isolated = len(top["files"]) <= r["max_files_for_isolation"]
    if top["score"] >= r["confidence_threshold"] and isolated:
        return f"Rollback recommended: git revert {top['hash']}"
    return "Manual investigation (confidence below threshold or commit not isolated)"

if __name__ == "__main__":   # customization demo: python analyzer/scorer.py
    sample = [
        {"hash": "a111111", "author": "PRU", "message": "CR-005: parser xml", "files": ["analyzer/parser.py"]},
        {"hash": "b222222", "author": "BKS", "message": "CR-002: update validator", "files": ["maven/src/main/java/com/commitsleuth/demo/Validator.java"]},
        {"hash": "c333333", "author": "PRU", "message": "CR-004: pom tweak", "files": ["maven/pom.xml", "README.md"]},
    ]
    log = "[ERROR] Validator.java:[12,30] ';' expected  COMPILATION ERROR"
    cfg = load_cfg()
    print("Weights:", cfg["weights"], "threshold:", cfg["rollback"]["confidence_threshold"])
    for r in rank(sample, log, "compile", cfg):
        print(f'{r["hash"]}  {r["author"]}  confidence={r["score"]}  {r["message"]}')
    print(decide(rank(sample, log, "compile", cfg)[0], cfg))
