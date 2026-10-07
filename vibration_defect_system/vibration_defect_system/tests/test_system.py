import os, sys, unittest, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.detector import analyze, load_template
from core.db import DB
from core.auth import Auth
from core.report import summarize
from sample_data import make, FS

TPL = load_template("config/defect_template.json")
def run(**kw): return {d["name"]: d["intensity"] for d in analyze(make(**kw)[1], FS, TPL)[0]}

class Detector(unittest.TestCase):
    def test_healthy(self): self.assertEqual(run(), {})
    def test_unbalance(self): self.assertEqual(run(unb=0.25), {"Unbalance": "Medium"})
    def test_misalignment(self): self.assertEqual(run(mis=0.35), {"Misalignment": "High"})
    def test_looseness(self): self.assertEqual(run(loose=0.2), {"Mechanical Looseness": "Low"})
    def test_bearing_outer(self): self.assertIn("Bearing Outer Race Fault", run(bpfo=1.0, seed=1))
    def test_bearing_inner_multi(self):
        r = run(bpfi=4.0, unb=0.1, seed=2); self.assertEqual(r["Bearing Inner Race Fault"], "Critical"); self.assertIn("Unbalance", r)
    def test_rpm_variation(self): self.assertEqual(run(unb=0.25, rpm=1850), {"Unbalance": "Medium"})

class System(unittest.TestCase):
    def setUp(self):
        self.db = DB(":memory:"); self.a = Auth(self.db)
    def test_login(self):
        self.assertTrue(self.a.login("admin", "Admin@123")[0]); self.assertFalse(self.a.login("admin", "bad")[0])
        self.assertEqual(self.db.con.execute("SELECT COUNT(*) FROM access_log").fetchone()[0], 2)
    def test_reset(self):
        self.a._send = lambda to, code: setattr(self, "code", code)
        self.a.request_reset("admin"); self.assertFalse(self.a.reset_password("admin", "000000", "NewPass1")[0] and self.code != "000000")
        self.assertTrue(self.a.reset_password("admin", self.code, "NewPass1")[0]); self.assertTrue(self.a.login("admin", "NewPass1")[0])
        self.assertFalse(self.a.reset_password("admin", self.code, "Another1")[0])   # single use
    def test_report_filters(self):
        self.db.add_user("bob", "b@x.com", "Bob12345")
        self.db.log_run("admin", "a.csv", [{"name": "Unbalance", "intensity": "High", "amplitude": 1, "frequency_hz": 30}], "M1")
        self.db.log_run("bob", "b.csv", [{"name": "Misalignment", "intensity": "Low", "amplitude": 1, "frequency_hz": 60}], "M1")
        self.assertEqual(len(self.db.events("bob")), 1); self.assertEqual(len(self.db.events()), 2)
        self.assertEqual(len(self.db.events("bob", "2000-01-01", "2000-01-02")), 0)
        self.assertEqual(summarize(self.db.events())[1], {"High": 1, "Low": 1}); self.assertEqual(self.db.iteration_count(), 2)

if __name__ == "__main__": unittest.main()
