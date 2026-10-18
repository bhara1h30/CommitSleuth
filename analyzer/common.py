import os, sqlite3, yaml
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.environ.get("CS_DB", os.path.join(ROOT, "database", "commitsleuth.db"))

def connect():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    return con

def q(sql, args=()):
    con = connect()
    rows = con.execute(sql, args).fetchall()
    con.close()
    return rows

def ex(sql, args=()):
    con = connect()
    cur = con.execute(sql, args)
    con.commit()
    last = cur.lastrowid
    con.close()
    return last

def load_cfg():
    with open(os.path.join(ROOT, "scoring_config.yaml")) as f:
        return yaml.safe_load(f)
