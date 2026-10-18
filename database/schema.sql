CREATE TABLE IF NOT EXISTS users(username TEXT PRIMARY KEY, password_hash TEXT, role TEXT);
CREATE TABLE IF NOT EXISTS ci_register(ci_id TEXT PRIMARY KEY, name TEXT, version TEXT, status TEXT, owner TEXT, approval TEXT);
CREATE TABLE IF NOT EXISTS change_requests(cr_id TEXT PRIMARY KEY, description TEXT, requester TEXT, impact TEXT, status TEXT, decision TEXT, decision_date TEXT, branch TEXT, pull_request TEXT);
CREATE TABLE IF NOT EXISTS builds(id INTEGER PRIMARY KEY AUTOINCREMENT, build_no INTEGER, result TEXT, commit_hash TEXT, created TEXT);
CREATE TABLE IF NOT EXISTS problems(id INTEGER PRIMARY KEY AUTOINCREMENT, build_no INTEGER, failure_type TEXT, suspect_commit TEXT, confidence REAL, assignee TEXT, status TEXT, action TEXT, notification TEXT, created TEXT);
CREATE TABLE IF NOT EXISTS commit_scores(id INTEGER PRIMARY KEY AUTOINCREMENT, problem_id INTEGER, commit_hash TEXT, author TEXT, message TEXT, files TEXT, score REAL);
CREATE TABLE IF NOT EXISTS promotions(id INTEGER PRIMARY KEY AUTOINCREMENT, item TEXT, from_level TEXT, to_level TEXT, promo_date TEXT, approver TEXT, result TEXT, reason TEXT);
