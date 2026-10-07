import re, secrets, os, smtplib, hmac
from datetime import datetime, timedelta
from email.message import EmailMessage
from .db import hash_pw, now

def validate_password(pw):
    if len(pw) < 8 or not re.search(r"[A-Z]", pw) or not re.search(r"\d", pw):
        return "Password needs 8+ characters, an uppercase letter and a digit."

class Auth:
    def __init__(self, db): self.db = db

    def login(self, username, pw):
        if not username.strip() or not pw:
            return False, "Enter username and password."
        r = self.db.con.execute("SELECT * FROM users WHERE username=?", (username.strip(),)).fetchone()
        if r and hmac.compare_digest(hash_pw(pw, r["salt"]), r["pw_hash"]):
            self.db.log_access(r["username"], "LOGIN")
            return True, r["username"]
        self.db.log_access(username.strip() or "?", "LOGIN_FAILED")
        return False, "Invalid username or password."

    def logout(self, user): self.db.log_access(user, "LOGOUT")

    def request_reset(self, username):
        """Create a 6-digit temporary code (valid 10 min) and send it to the user's email."""
        r = self.db.con.execute("SELECT * FROM users WHERE username=?", (username.strip(),)).fetchone()
        if r:
            code = f"{secrets.randbelow(10**6):06d}"
            exp = (datetime.now() + timedelta(minutes=10)).strftime("%Y-%m-%d %H:%M:%S")
            self.db.con.execute("REPLACE INTO reset_codes VALUES(?,?,?)", (r["username"], hash_pw(code, r["salt"]), exp))
            self.db.con.commit()
            self._send(r["email"], code)
            self.db.log_access(r["username"], "RESET_REQUESTED")
        return "If the account exists, a code has been sent to its email."   # no user enumeration

    def reset_password(self, username, code, new_pw):
        err = validate_password(new_pw)
        if err: return False, err
        u = username.strip()
        r = self.db.con.execute("SELECT u.salt, c.code_hash, c.expires FROM users u JOIN reset_codes c USING(username) WHERE u.username=?", (u,)).fetchone()
        if not r or now() > r["expires"] or not hmac.compare_digest(hash_pw(code.strip(), r["salt"]), r["code_hash"]):
            return False, "Invalid or expired code."
        self.db.con.execute("UPDATE users SET pw_hash=? WHERE username=?", (hash_pw(new_pw, r["salt"]), u))
        self.db.con.execute("DELETE FROM reset_codes WHERE username=?", (u,))
        self.db.con.commit()
        self.db.log_access(u, "PASSWORD_RESET")
        return True, "Password updated. You can log in now."

    @staticmethod
    def _send(to, code):
        """Real SMTP if SMTP_HOST/SMTP_USER/SMTP_PASS env vars are set; otherwise saved to data/outbox.txt (demo)."""
        body = f"Your temporary reset code is {code}. It expires in 10 minutes."
        host = os.environ.get("SMTP_HOST")
        if host:
            m = EmailMessage(); m["Subject"], m["From"], m["To"] = "Password reset code", os.environ["SMTP_USER"], to
            m.set_content(body)
            with smtplib.SMTP_SSL(host, 465) as s:
                s.login(os.environ["SMTP_USER"], os.environ["SMTP_PASS"]); s.send_message(m)
        else:
            with open("data/outbox.txt", "a") as f: f.write(f"[{now()}] To: {to} | {body}\n")
