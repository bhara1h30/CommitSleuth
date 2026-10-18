import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "analyzer"))
import scorer

CFG = {"weights": {"file_match": 0.55, "pom_change": 0.25, "recency": 0.10, "change_size": 0.10},
       "rollback": {"confidence_threshold": 0.6, "max_files_for_isolation": 3}}

def test_file_in_log_ranks_first():
    commits = [{"hash": "a", "author": "x", "message": "m", "files": ["Calculator.java"]},
               {"hash": "b", "author": "y", "message": "m", "files": ["README.md"]}]
    r = scorer.rank(commits, "Calculator.java:[9,31] error", "compile", CFG)
    assert r[0]["hash"] == "a"

def test_confidence_sums_to_one():
    commits = [{"hash": str(i), "author": "x", "message": "m", "files": ["f%d.java" % i]} for i in range(4)]
    r = scorer.rank(commits, "f1 f2", "test", CFG)
    assert abs(sum(c["score"] for c in r) - 1) < 0.01
