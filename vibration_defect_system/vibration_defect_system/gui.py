"""Tkinter UI: login / forgot password -> Analyze (alerts) + Report (summary, expandable detail)."""
import os, tkinter as tk
from tkinter import ttk, messagebox, filedialog
from core.db import DB
from core.auth import Auth, validate_password
from core.detector import load_template, load_vibration, analyze
from core.report import summarize, export_csv

COLORS = {"Low": "#f1c40f", "Medium": "#e67e22", "High": "#e74c3c", "Critical": "#8e0000"}
TEMPLATE = os.path.join("config", "defect_template.json")

class App(tk.Tk):
    def __init__(self):
        super().__init__(); self.title("Vibration Defect Detection"); self.geometry("900x600")
        self.db = DB(); self.auth = Auth(self.db); self.user = None
        self.tpl = load_template(TEMPLATE)
        self.protocol("WM_DELETE_WINDOW", self.quit_app)
        self.login_screen()

    def clear(self):
        for w in self.winfo_children(): w.destroy()

    def quit_app(self):
        if self.user: self.auth.logout(self.user)
        self.destroy()

    # ---------- login ----------
    def login_screen(self):
        self.clear(); f = ttk.Frame(self, padding=40); f.pack(expand=True)
        ttk.Label(f, text="Machine Vibration Defect Detection", font=("", 16, "bold")).grid(columnspan=2, pady=10)
        u, p = tk.StringVar(), tk.StringVar()
        ttk.Label(f, text="Username").grid(row=1, column=0, sticky="e"); ttk.Entry(f, textvariable=u).grid(row=1, column=1, pady=3)
        ttk.Label(f, text="Password").grid(row=2, column=0, sticky="e"); e = ttk.Entry(f, textvariable=p, show="*"); e.grid(row=2, column=1, pady=3)
        msg = ttk.Label(f, foreground="red"); msg.grid(row=3, columnspan=2)
        def go(_=None):
            ok, r = self.auth.login(u.get(), p.get())
            if ok: self.user = r; self.main_screen()
            else: msg.config(text=r)
        e.bind("<Return>", go)
        ttk.Button(f, text="Login", command=go).grid(row=4, columnspan=2, pady=6)
        ttk.Button(f, text="Forgot Password?", command=lambda: self.forgot_dialog(u.get())).grid(row=5, columnspan=2)

    def forgot_dialog(self, uname):
        d = tk.Toplevel(self); d.title("Reset password"); d.grab_set()
        un, code, pw = tk.StringVar(value=uname), tk.StringVar(), tk.StringVar()
        for i, (t, v, s) in enumerate([("Username", un, ""), ("Temporary code", code, ""), ("New password", pw, "*")]):
            ttk.Label(d, text=t).grid(row=i, column=0, padx=8, pady=4); ttk.Entry(d, textvariable=v, show=s).grid(row=i, column=1, padx=8)
        def send(): messagebox.showinfo("Reset", self.auth.request_reset(un.get()), parent=d)
        def apply():
            ok, m = self.auth.reset_password(un.get(), code.get(), pw.get())
            (messagebox.showinfo if ok else messagebox.showerror)("Reset", m, parent=d)
            if ok: d.destroy()
        ttk.Button(d, text="1. Email me a code", command=send).grid(row=3, columnspan=2, pady=4)
        ttk.Button(d, text="2. Set new password", command=apply).grid(row=4, columnspan=2, pady=4)

    # ---------- main ----------
    def main_screen(self):
        self.clear()
        top = ttk.Frame(self); top.pack(fill="x", padx=8, pady=4)
        ttk.Label(top, text=f"User: {self.user}").pack(side="left")
        ttk.Button(top, text="Logout", command=lambda: (self.auth.logout(self.user), setattr(self, "user", None), self.login_screen())).pack(side="right")
        nb = ttk.Notebook(self); nb.pack(fill="both", expand=True, padx=8, pady=4)
        a, r = ttk.Frame(nb), ttk.Frame(nb); nb.add(a, text="Analyze"); nb.add(r, text="Report")
        self.build_analyze(a); self.build_report(r)

    def build_analyze(self, f):
        ttk.Button(f, text="Select vibration CSV and analyze...", command=self.run_analysis).pack(pady=10)
        self.banner = tk.Label(f, text="No analysis yet", font=("", 16, "bold"), height=3, bg="#dddddd"); self.banner.pack(fill="x", padx=10)
        self.alerts = ttk.Treeview(f, columns=("type", "intensity", "amp", "freq"), show="headings", height=8)
        for c, t in zip(self.alerts["columns"], ("Defect type", "Intensity", "Amplitude (g)", "Frequency (Hz)")):
            self.alerts.heading(c, text=t); self.alerts.column(c, width=150)
        for lvl, col in COLORS.items(): self.alerts.tag_configure(lvl, background=col, foreground="white")
        self.alerts.pack(fill="both", expand=True, padx=10, pady=10)
        self.status = ttk.Label(f); self.status.pack()

    def run_analysis(self):
        path = filedialog.askopenfilename(filetypes=[("CSV", "*.csv")])
        if not path: return
        try:
            x, fs = load_vibration(path, self.tpl["specs"]["sample_rate_hz"])
            found, info = analyze(x, fs, self.tpl)
        except Exception as ex:
            return messagebox.showerror("Error", str(ex))
        self.db.log_run(self.user, os.path.basename(path), found, self.tpl["machine_id"])
        self.alerts.delete(*self.alerts.get_children())
        for d in found: self.alerts.insert("", "end", values=(d["name"], d["intensity"], d["amplitude"], d["frequency_hz"]), tags=(d["intensity"],))
        self.status.config(text=f"RPM {info['rpm']} | RMS {info['rms_g']} g | iterations so far: {self.db.iteration_count()}")
        if found:
            worst = max(found, key=lambda d: ["Low", "Medium", "High", "Critical"].index(d["intensity"]))
            self.banner.config(text=f"ALERT: {worst['name']} - {worst['intensity'].upper()}", bg=COLORS[worst["intensity"]], fg="white")
            messagebox.showwarning("Defect detected", "\n".join(f"{d['name']}  -  {d['intensity']}" for d in found))
        else:
            self.banner.config(text="No defect detected - machine healthy", bg="#2ecc71", fg="white")

    def build_report(self, f):
        bar = ttk.Frame(f); bar.pack(fill="x", pady=6)
        self.fu = tk.StringVar(value="All"); self.d1, self.d2 = tk.StringVar(), tk.StringVar()
        ttk.Label(bar, text="User").pack(side="left"); ttk.Combobox(bar, textvariable=self.fu, values=["All"] + self.db.users(), width=12, state="readonly").pack(side="left", padx=4)
        ttk.Label(bar, text="From (YYYY-MM-DD)").pack(side="left"); ttk.Entry(bar, textvariable=self.d1, width=11).pack(side="left", padx=4)
        ttk.Label(bar, text="To").pack(side="left"); ttk.Entry(bar, textvariable=self.d2, width=11).pack(side="left", padx=4)
        ttk.Button(bar, text="Generate", command=self.gen_report).pack(side="left", padx=4)
        ttk.Button(bar, text="Export CSV (Power BI)", command=self.export).pack(side="left")
        self.totals = ttk.Label(f, text="", font=("", 10, "bold")); self.totals.pack(anchor="w", padx=6)
        self.tree = ttk.Treeview(f, columns=("count", "intensity", "when"), height=18)
        self.tree.heading("#0", text="Defect type / event"); self.tree.heading("count", text="Count"); self.tree.heading("intensity", text="Intensity"); self.tree.heading("when", text="Time / user")
        self.tree.pack(fill="both", expand=True, padx=6)
        self.gen_report()

    def _rows(self):
        return self.db.events(None if self.fu.get() == "All" else self.fu.get(), self.d1.get().strip() or None, self.d2.get().strip() or None)

    def gen_report(self):
        rows = self._rows(); s, tot = summarize(rows)
        self.tree.delete(*self.tree.get_children())
        for name, g in s.items():   # summary row; click the arrow to expand details
            p = self.tree.insert("", "end", text=name, values=(g["count"], f"max: {g['max']}", ""))
            for e in g["events"]: self.tree.insert(p, "end", text=f"{e['source_file']} ({e['machine_id']})", values=("1", e["intensity"], f"{e['ts']} / {e['username']}"))
        self.totals.config(text=f"Total defects: {len(rows)}   " + "  ".join(f"{k}: {tot.get(k, 0)}" for k in COLORS))

    def export(self):
        p = filedialog.asksaveasfilename(defaultextension=".csv", initialdir="reports", initialfile="defect_report.csv")
        if p: export_csv(self._rows(), p); messagebox.showinfo("Export", f"Saved {p}")

if __name__ == "__main__":
    App().mainloop()
