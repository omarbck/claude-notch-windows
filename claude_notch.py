"""
Claude Notch for Windows
Barre flottante affichant l'usage Claude en temps réel.
Inspiré de https://github.com/acenaut/claude-notch
"""

import tkinter as tk
import threading
import time
import json
import os
import sys

try:
    import customtkinter as ctk
except ImportError:
    print("customtkinter manquant. Lance setup.bat d'abord.")
    sys.exit(1)

try:
    import requests
except ImportError:
    print("requests manquant. Lance setup.bat d'abord.")
    sys.exit(1)

# ── Config ─────────────────────────────────────────────────────────────────────

CONFIG_FILE = os.path.join(os.path.expanduser("~"), ".claude_notch.json")
POLL_INTERVAL = 60          # secondes entre chaque refresh auto
BASE_URL = "https://claude.ai"

SIZES = {
    "S": {"w": 260, "h_col": 26, "h_exp": 175, "f_main": 10, "f_sub": 9},
    "M": {"w": 320, "h_col": 32, "h_exp": 200, "f_main": 11, "f_sub": 10},
    "L": {"w": 410, "h_col": 38, "h_exp": 230, "f_main": 13, "f_sub": 11},
}

def get_color(v: float) -> str:
    """Couleur selon le % d'utilisation (0.0 – 1.0)."""
    if v < 0.50: return "#4CAF50"
    if v < 0.70: return "#8BC34A"
    if v < 0.85: return "#FF9800"
    if v < 0.95: return "#FF5722"
    return "#F44336"


# ── Persistance ────────────────────────────────────────────────────────────────

class Config:
    def __init__(self):
        self.session_key: str = ""
        self.org_id: str = ""
        self.size: str = "M"
        self._load()

    def _load(self):
        if os.path.exists(CONFIG_FILE):
            try:
                d = json.loads(open(CONFIG_FILE).read())
                self.session_key = d.get("session_key", "")
                self.org_id     = d.get("org_id", "")
                self.size       = d.get("size", "M")
            except Exception:
                pass

    def save(self):
        with open(CONFIG_FILE, "w") as f:
            json.dump({
                "session_key": self.session_key,
                "org_id":      self.org_id,
                "size":        self.size,
            }, f)


# ── API Claude ─────────────────────────────────────────────────────────────────

class ClaudeAPI:
    def __init__(self, session_key: str):
        self.session_key = session_key
        self._s = requests.Session()
        self._s.cookies.set("sessionKey", session_key, domain="claude.ai")
        self._s.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer":    "https://claude.ai",
            "Accept":     "application/json",
        })

    def get_org_id(self) -> str | None:
        r = self._s.get(f"{BASE_URL}/api/organizations", timeout=10)
        r.raise_for_status()
        orgs = r.json()
        if isinstance(orgs, list) and orgs:
            return orgs[0].get("uuid") or orgs[0].get("id")
        return None

    def get_usage(self, org_id: str) -> dict:
        r = self._s.get(f"{BASE_URL}/api/organizations/{org_id}/usage", timeout=10)
        r.raise_for_status()
        return r.json()

    def get_subscription(self, org_id: str) -> dict:
        r = self._s.get(f"{BASE_URL}/api/organizations/{org_id}/subscription_details", timeout=10)
        r.raise_for_status()
        return r.json()


def _pct(d: dict, *keys) -> float:
    """Extrait un pourcentage normalisé 0.0–1.0 depuis plusieurs noms de clés possibles."""
    for k in keys:
        v = d.get(k)
        if v is not None:
            try:
                fv = float(v)
                return min(fv / 100.0 if fv > 1.0 else fv, 1.0)
            except (TypeError, ValueError):
                pass
    return 0.0

def parse_usage(data: dict) -> dict:
    """Normalise la réponse API en dict simple."""
    return {
        "session":        _pct(data, "session_usage_pct", "sessionUsagePct", "session_pct"),
        "weekly":         _pct(data, "weekly_usage_pct",  "weeklyUsagePct",  "weekly_pct"),
        "sonnet":         _pct(data, "sonnet_usage_pct",  "sonnetUsagePct",  "sonnet_pct"),
        "opus":           _pct(data, "opus_usage_pct",    "opusUsagePct",    "opus_pct"),
        "extra_spend":    float(data.get("extra_usage_spend", data.get("extraUsageSpend", 0)) or 0),
        "extra_currency": data.get("extra_usage_currency", data.get("extraUsageCurrency", "USD")),
    }


# ── UI principale ──────────────────────────────────────────────────────────────

class ClaudeNotchApp:

    def __init__(self):
        self.config   = Config()
        self.api      = None
        self.usage    = parse_usage({})
        self.expanded = False

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")

        self.root = ctk.CTk()
        self.root.title("Claude Notch")
        self.root.overrideredirect(True)        # pas de bordure Windows
        self.root.attributes("-topmost", True)  # toujours au premier plan
        self.root.wm_attributes("-alpha", 0.93)

        self.sz = SIZES[self.config.size]
        self._place_window(collapsed=True)

        self._build_ui()
        self._bind_events()

        if self.config.session_key:
            threading.Thread(target=self._init_api, daemon=True).start()
        else:
            self.root.after(300, self._open_setup)

    # ── Placement ─────────────────────────────────────────────────────────────

    def _screen_cx(self) -> int:
        return (self.root.winfo_screenwidth() - self.sz["w"]) // 2

    def _place_window(self, collapsed: bool):
        h = self.sz["h_col"] if collapsed else self.sz["h_exp"]
        x = self._screen_cx()
        self.root.geometry(f"{self.sz['w']}x{h}+{x}+0")

    # ── Construction UI ────────────────────────────────────────────────────────

    def _build_ui(self):
        sz = self.sz
        bg = "#111111"
        self.root.configure(fg_color=bg)

        # ─ Barre collapsed ─
        self.bar = ctk.CTkFrame(self.root, fg_color=bg, corner_radius=0)
        self.bar.place(x=0, y=0, relwidth=1.0, height=sz["h_col"])

        # Dot indicateur
        self._dot_canvas = tk.Canvas(self.bar, width=9, height=9, bg=bg, highlightthickness=0)
        self._dot_id = self._dot_canvas.create_oval(1, 1, 8, 8, fill="#E87443", outline="")
        self._dot_canvas.pack(side="left", padx=(10, 2), pady=0)

        self.lbl_session = ctk.CTkLabel(
            self.bar, text="Session --",
            font=("Segoe UI", sz["f_main"]), text_color="#CCCCCC"
        )
        self.lbl_session.pack(side="left", padx=5)

        ctk.CTkLabel(self.bar, text="·", font=("Segoe UI", sz["f_main"]),
                     text_color="#444").pack(side="left")

        self.lbl_weekly = ctk.CTkLabel(
            self.bar, text="Weekly --",
            font=("Segoe UI", sz["f_main"]), text_color="#CCCCCC"
        )
        self.lbl_weekly.pack(side="left", padx=5)

        self.lbl_sonnet = ctk.CTkLabel(
            self.bar, text="⚩ --",
            font=("Segoe UI", sz["f_main"] - 1), text_color="#555"
        )
        self.lbl_sonnet.pack(side="right", padx=10)

        # ─ Panel expanded (caché par défaut) ─
        self.panel = ctk.CTkFrame(self.root, fg_color="#1a1a1a", corner_radius=0)

        ctk.CTkFrame(self.panel, fg_color="#2a2a2a", height=1,
                     corner_radius=0).pack(fill="x", pady=(0, 6))

        self._bars: dict[str, tuple] = {}
        for key, label in [("session", "Session (5h)"),
                            ("weekly",  "Weekly (7d)"),
                            ("sonnet",  "Sonnet"),
                            ("opus",    "Opus")]:
            row = ctk.CTkFrame(self.panel, fg_color="transparent")
            row.pack(fill="x", padx=14, pady=3)

            ctk.CTkLabel(row, text=label,
                         font=("Segoe UI", sz["f_sub"]),
                         width=82, anchor="w", text_color="#999").pack(side="left")

            bar = ctk.CTkProgressBar(row, height=7, corner_radius=3,
                                     progress_color="#4CAF50")
            bar.pack(side="left", fill="x", expand=True, padx=6)
            bar.set(0)

            pct = ctk.CTkLabel(row, text="0%",
                               font=("Segoe UI", sz["f_sub"]),
                               width=36, anchor="e", text_color="#666")
            pct.pack(side="right")

            self._bars[key] = (bar, pct)

        self.lbl_extra = ctk.CTkLabel(
            self.panel, text="",
            font=("Segoe UI", sz["f_sub"] - 1), text_color="#555"
        )
        self.lbl_extra.pack(pady=(5, 2))

        # Boutons footer
        foot = ctk.CTkFrame(self.panel, fg_color="transparent")
        foot.pack(fill="x", padx=14, pady=(2, 10))

        ctk.CTkButton(
            foot, text="↻", width=36, height=22,
            font=("Segoe UI", sz["f_sub"]), fg_color="#222", hover_color="#333",
            command=lambda: threading.Thread(target=self._fetch, daemon=True).start()
        ).pack(side="left")

        ctk.CTkButton(
            foot, text="⚙ Settings", width=90, height=22,
            font=("Segoe UI", sz["f_sub"]), fg_color="#222", hover_color="#333",
            command=self._open_setup
        ).pack(side="right")

        ctk.CTkButton(
            foot, text="✕", width=36, height=22,
            font=("Segoe UI", sz["f_sub"]), fg_color="#222", hover_color="#550000",
            command=self.root.destroy
        ).pack(side="right", padx=6)

    # ── Events ────────────────────────────────────────────────────────────────

    def _bind_events(self):
        for w in (self.root, self.bar, self.panel):
            w.bind("<Enter>", self._on_enter)
            w.bind("<Leave>", self._on_leave)

        # Drag de la barre
        self.bar.bind("<Button-1>",   self._drag_start)
        self.bar.bind("<B1-Motion>",  self._drag_move)

        # Clic droit → menu
        self.bar.bind("<Button-3>", self._context_menu)

    def _on_enter(self, _=None):
        if not self.expanded:
            self.expanded = True
            self._place_window(collapsed=False)
            self.panel.place(x=0, y=self.sz["h_col"],
                             relwidth=1.0,
                             height=self.sz["h_exp"] - self.sz["h_col"])

    def _on_leave(self, _=None):
        rx, ry = self.root.winfo_x(), self.root.winfo_y()
        rw, rh = self.root.winfo_width(), self.root.winfo_height()
        px, py = self.root.winfo_pointerx(), self.root.winfo_pointery()
        if not (rx <= px <= rx + rw and ry <= py <= ry + rh):
            if self.expanded:
                self.expanded = False
                self.panel.place_forget()
                self._place_window(collapsed=True)

    def _drag_start(self, e):
        self._dx = e.x_root - self.root.winfo_x()

    def _drag_move(self, e):
        nx = e.x_root - self._dx
        self.root.geometry(f"+{nx}+{self.root.winfo_y()}")

    def _context_menu(self, e):
        m = tk.Menu(self.root, tearoff=0, bg="#1a1a1a", fg="white",
                    activebackground="#333", activeforeground="white")
        m.add_command(label="↻  Rafraîchir",
                      command=lambda: threading.Thread(target=self._fetch, daemon=True).start())
        m.add_command(label="⚙  Settings", command=self._open_setup)
        m.add_separator()
        m.add_command(label="✕  Quitter", command=self.root.destroy)
        m.tk_popup(e.x_root, e.y_root)

    # ── API & polling ─────────────────────────────────────────────────────────

    def _init_api(self):
        self.api = ClaudeAPI(self.config.session_key)
        if not self.config.org_id:
            try:
                self.config.org_id = self.api.get_org_id() or ""
                self.config.save()
            except Exception as ex:
                print(f"[ClaudeNotch] Impossible de récupérer l'org ID : {ex}")
                self.root.after(0, lambda: self.lbl_session.configure(
                    text="Auth error", text_color="#F44336"))
                return
        self._fetch()
        # Polling
        threading.Thread(target=self._poll_loop, daemon=True).start()

    def _poll_loop(self):
        while True:
            time.sleep(POLL_INTERVAL)
            self._fetch()

    def _fetch(self):
        if not self.api or not self.config.org_id:
            return
        try:
            data = self.api.get_usage(self.config.org_id)
            self.usage = parse_usage(data)
            self.root.after(0, self._refresh_ui)
        except Exception as ex:
            print(f"[ClaudeNotch] Erreur fetch : {ex}")

    # ── Mise à jour UI ────────────────────────────────────────────────────────

    def _refresh_ui(self):
        u = self.usage
        max_v = max(u["session"], u["weekly"])

        # Dot
        self._dot_canvas.itemconfig(self._dot_id, fill=get_color(max_v))

        # Labels collapsed
        self.lbl_session.configure(
            text=f"Session {int(u['session']*100)}%",
            text_color=get_color(u["session"]))
        self.lbl_weekly.configure(
            text=f"Weekly {int(u['weekly']*100)}%",
            text_color=get_color(u["weekly"]))
        self.lbl_sonnet.configure(text=f"⚩ {int(u['sonnet']*100)}%")

        # Barres
        for key in ("session", "weekly", "sonnet", "opus"):
            v = u[key]
            bar, pct_lbl = self._bars[key]
            bar.set(v)
            bar.configure(progress_color=get_color(v))
            pct_lbl.configure(text=f"{int(v*100)}%", text_color=get_color(v))

        # Extra spend
        if u["extra_spend"] > 0:
            self.lbl_extra.configure(
                text=f"Extra usage : {u['extra_currency']} {u['extra_spend']:.2f}")
        else:
            self.lbl_extra.configure(text="")

    # ── Setup wizard ──────────────────────────────────────────────────────────

    def _open_setup(self):
        if hasattr(self, "_setup_win"):
            try:
                if self._setup_win.winfo_exists():
                    self._setup_win.lift()
                    return
            except Exception:
                pass

        win = ctk.CTkToplevel(self.root)
        win.title("Claude Notch — Configuration")
        win.geometry("440x320")
        win.resizable(False, False)
        win.grab_set()
        self._setup_win = win

        ctk.CTkLabel(win, text="🔑  Session Key claude.ai",
                     font=("Segoe UI", 15, "bold")).pack(pady=(22, 4))

        ctk.CTkLabel(
            win,
            text=(
                "1. Ouvre claude.ai dans Chrome et connecte-toi\n"
                "2. Appuie sur F12 → onglet Application\n"
                "3. Cookies → https://claude.ai → copie sessionKey"
            ),
            font=("Segoe UI", 10), text_color="#888", justify="left"
        ).pack(padx=30, pady=4, anchor="w")

        entry = ctk.CTkEntry(win, placeholder_text="Colle ta sessionKey ici…",
                             width=390, height=36)
        entry.pack(pady=10, padx=24)
        if self.config.session_key:
            entry.insert(0, self.config.session_key)

        # Taille
        sz_row = ctk.CTkFrame(win, fg_color="transparent")
        sz_row.pack(pady=4)
        ctk.CTkLabel(sz_row, text="Taille :", font=("Segoe UI", 11)).pack(side="left", padx=8)
        sz_var = tk.StringVar(value=self.config.size)
        for s in ("S", "M", "L"):
            ctk.CTkRadioButton(sz_row, text=s, variable=sz_var, value=s,
                               font=("Segoe UI", 11)).pack(side="left", padx=10)

        err_lbl = ctk.CTkLabel(win, text="", text_color="#F44336",
                               font=("Segoe UI", 10))
        err_lbl.pack()

        def save():
            key = entry.get().strip()
            if not key:
                err_lbl.configure(text="Session key vide !")
                return
            self.config.session_key = key
            self.config.size        = sz_var.get()
            self.config.org_id      = ""    # reset pour re-fetch
            self.config.save()
            self.sz = SIZES[self.config.size]
            win.destroy()
            threading.Thread(target=self._init_api, daemon=True).start()

        ctk.CTkButton(win, text="Valider", width=130, height=38,
                      font=("Segoe UI", 12, "bold"), command=save).pack(pady=14)

    # ── Lancement ─────────────────────────────────────────────────────────────

    def run(self):
        self.root.mainloop()


# ── Entrée ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    ClaudeNotchApp().run()
