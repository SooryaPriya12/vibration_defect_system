"""SQLite schema: users, access_log, defect_events (separate table), analysis_runs (iteration count), reset_codes."""
import sqlite3, hashlib, secrets
from datetime import datetime

SCHEMA = """
CREATE TABLE IF NOT EXISTS users(username TEXT PRIMARY KEY, email TEXT, salt TEXT, pw_hash TEXT);
CREATE TABLE IF NOT EXISTS access_log(id INTEGER PRIMARY KEY, username TEXT, event TEXT, ts TEXT);
CREATE TABLE IF NOT EXISTS analysis_runs(id INTEGER PRIMARY KEY, username TEXT, ts TEXT, source_file TEXT, defects_found INTEGER);
CREATE TABLE IF NOT EXISTS defect_events(id INTEGER PRIMARY KEY, run_id INTEGER, username TEXT, ts TEXT,
    machine_id TEXT, defect_type TEXT, intensity TEXT, amplitude REAL, frequency_hz REAL, source_file TEXT);
CREATE TABLE IF NOT EXISTS reset_codes(username TEXT PRIMARY KEY, code_hash TEXT, expires TEXT);
"""
now = lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S")
hash_pw = lambda pw, salt: hashlib.pbkdf2_hmac("sha256", pw.encode(), bytes.fromhex(salt), 120_000).hex()

class DB:
    def __init__(self, path="data/system.db"):
        self.con = sqlite3.connect(path)
        self.con.row_factory = sqlite3.Row
        self.con.executescript(SCHEMA)
        if not self.con.execute("SELECT 1 FROM users").fetchone():   # demo account
            self.add_user("admin", "admin@example.com", "Admin@123")

    def add_user(self, username, email, pw):
        salt = secrets.token_hex(16)
        self.con.execute("INSERT INTO users VALUES(?,?,?,?)", (username, email, salt, hash_pw(pw, salt)))
        self.con.commit()

    def log_access(self, user, event):
        self.con.execute("INSERT INTO access_log(username,event,ts) VALUES(?,?,?)", (user, event, now()))
        self.con.commit()

    def log_run(self, user, source, defects, machine_id):
        """One analysis run = one iteration; each detected defect is stored in defect_events."""
        ts = now()
        cur = self.con.execute("INSERT INTO analysis_runs(username,ts,source_file,defects_found) VALUES(?,?,?,?)",
                               (user, ts, source, len(defects)))
        for d in defects:
            self.con.execute("INSERT INTO defect_events(run_id,username,ts,machine_id,defect_type,intensity,amplitude,frequency_hz,source_file) VALUES(?,?,?,?,?,?,?,?,?)",
                             (cur.lastrowid, user, ts, machine_id, d["name"], d["intensity"], d["amplitude"], d["frequency_hz"], source))
        self.con.commit()
        return cur.lastrowid

    def iteration_count(self, user=None):
        q, a = "SELECT COUNT(*) FROM analysis_runs", ()
        if user: q, a = q + " WHERE username=?", (user,)
        return self.con.execute(q, a).fetchone()[0]

    def events(self, user=None, date_from=None, date_to=None):
        """Filter by user, date range (YYYY-MM-DD), or both."""
        q, a = "SELECT * FROM defect_events WHERE 1=1", []
        if user: q += " AND username=?"; a.append(user)
        if date_from: q += " AND date(ts)>=date(?)"; a.append(date_from)
        if date_to: q += " AND date(ts)<=date(?)"; a.append(date_to)
        return self.con.execute(q + " ORDER BY ts DESC", a).fetchall()

    def users(self):
        return [r[0] for r in self.con.execute("SELECT username FROM users ORDER BY 1")]
