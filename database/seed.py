"""Create the database and load users, the 20 CIs and CR-001..CR-008.
Usage: python database/seed.py [--reset] [--demo]"""
import os, sys, datetime
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "analyzer"))
from werkzeug.security import generate_password_hash
import common
from common import connect, ROOT

if "--reset" in sys.argv and os.path.exists(common.DB):
    os.remove(common.DB)
con = connect()
con.executescript(open(os.path.join(ROOT, "database", "schema.sql")).read())

con.executemany("INSERT OR IGNORE INTO users VALUES (?,?,?)", [
    ("admin", generate_password_hash("admin123"), "admin"),
    ("viewer", generate_password_hash("viewer123"), "viewer")])

B, P = "Bharathwaraj K S", "Prakash Raj U"
cis = [
 ("CSDOC01","Project Proposal","v1.0","Baselined (BL-01)",B,"Approved"),
 ("CSDOC02","Software Requirement Specification (SRS)","v1.0","Baselined (BL-01)",P,"Approved"),
 ("CSDOC03","Software Configuration Management Plan","v1.0","Baselined (BL-01)",B,"Approved"),
 ("CSDOC04","System Design Document","v1.0","Baselined (BL-02)",P,"Approved"),
 ("CSSRC01","Source Code (Python modules)","v0.1.0","In Development",P,"Pending"),
 ("CSSRC02","Git Repository","v0.1.0","Baselined (BL-02)",B,"Approved"),
 ("CSBLD01","Jenkinsfile","v1.0","Tested, Baselined (BL-03)",B,"Approved"),
 ("CSBLD02","Maven Configuration (pom.xml)","v1.0","Tested, Baselined (BL-03)",B,"Approved"),
 ("CSMOD01","Build Log Parser","v0.4","In Development",B,"Pending"),
 ("CSMOD02","pom.xml Diff Analyzer","v0.2","In Development",P,"Pending"),
 ("CSMOD03","Commit Ranking Engine","-","Planned (Sprint 4)",P,"Pending"),
 ("CSMOD04","Notification Module","-","Planned (Sprint 4)",B,"Pending"),
 ("CSMOD05","Rollback Recommendation Module","-","Planned (Sprint 4)",P,"Pending"),
 ("CSMOD06","Dashboard Module","-","Planned (Sprint 5)",P,"Pending"),
 ("CSDB01","Database (build history and reports)","v0.5","In Development",P,"Partial (schema only)"),
 ("CSDOC05","Test Plan","v0.1","Draft",B,"Pending"),
 ("CSDOC06","Test Cases","v0.2","In Development",P,"Pending"),
 ("CSDOC07","User Manual","-","Planned (Sprint 6)",P,"Pending"),
 ("CSDOC08","Deployment Guide","-","Planned (Sprint 6)",B,"Pending"),
 ("CSREL01","Release Package (CommitSleuth_v1.0)","-","Planned (Sprint 6)",B,"Pending")]
con.executemany("INSERT OR IGNORE INTO ci_register VALUES (?,?,?,?,?,?)", cis)

crs = [  # EDIT these descriptions to match your real CR register from Review 2
 ("CR-001","Add batching-problem definition to SRS",B,"SRS","Implemented","Approved by CCB","2026-08-12","feature/srs-batching",""),
 ("CR-002","Add pom.xml diff and isolation requirements to SRS",P,"SRS","Implemented","Approved by CCB","2026-08-12","feature/srs-isolation",""),
 ("CR-003","Add post-failure hook and artifact archiving to Jenkinsfile",B,"Jenkinsfile","Implemented","Approved by CCB","2026-09-02","feature/jenkins-hook",""),
 ("CR-004","Add change_requests table to database schema",P,"Database","Implemented","Approved by CCB","2026-09-03","feature/db-schema",""),
 ("CR-005","Add XML report support to Build Log Parser",B,"Build Log Parser","Approved","Approved by CCB","2026-09-18","feature/parser-xml",""),
 ("CR-006","Make scoring weights configurable (YAML)",P,"Ranking Engine","Approved","Approved by CCB","2026-09-19","feature/scoring-config",""),
 ("CR-007","Redesign dashboard layout",P,"Dashboard","Under Review","Awaiting CCB decision","","",""),
 ("CR-008","Replace Jenkins with another CI server",B,"Jenkinsfile, pipeline","Rejected","Rejected: uncontrolled design drift","2026-09-20","","")]
con.executemany("INSERT OR IGNORE INTO change_requests VALUES (?,?,?,?,?,?,?,?,?)", crs)
con.commit(); con.close()
print("Database ready:", common.DB)

if "--demo" in sys.argv:   # fallback sample problems (use if Jenkins is not ready)
    import record_build
    L = lambda s: [{"hash": h, "author": a, "message": m, "files": f} for h, a, m, f in s]
    sets = [
     ("compile", "[ERROR] Calculator.java:[9,31] ';' expected  COMPILATION ERROR", 101, L([
        ("a1b2c3d","BKS","CR-005: update parser",["analyzer/record_build.py"]),
        ("e4f5a6b","PRU","CR-006: change calculator",["maven/src/main/java/com/commitsleuth/demo/Calculator.java"]),
        ("c7d8e9f","BKS","CR-004: docs",["docs/notes.md","README.md"])])),
     ("test", "Tests run: 4, Failures: 1  CalculatorTest.addsTwoNumbers  There are test failures. FAILURE", 102, L([
        ("1a2b3c4","PRU","CR-006: refactor validator",["maven/src/main/java/com/commitsleuth/demo/Validator.java"]),
        ("5d6e7f8","BKS","CR-003: change add()",["maven/src/main/java/com/commitsleuth/demo/Calculator.java"])])),
     ("dependency", "Could not resolve dependencies for project: junit-jupiter:5.99.9 pom.xml", 103, L([
        ("9a8b7c6","PRU","CR-006: bump junit",["maven/pom.xml"]),
        ("5e4d3c2","BKS","CR-004: readme",["README.md"]),
        ("1f0e9d8","PRU","CR-005: parser tweak",["analyzer/record_build.py"])]))]
    for ftype, log, bno, commits in sets:
        record_build.store_failure(bno, log, commits, ftype)
        common.ex("INSERT INTO builds(build_no,result,commit_hash,created) VALUES (?,?,?,?)",
                  (bno, "FAILURE", commits[-1]["hash"], f"{datetime.datetime.now():%Y-%m-%d %H:%M}"))
    print("Demo problems added.")
