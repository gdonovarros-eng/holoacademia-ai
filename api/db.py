"""
SQLite usage tracking for Holoacademia.
Tracks per-user monthly usage of the three metered AI tools.

Plans and monthly limits
------------------------
premium       $799 MXN  — sinodal:100  terapeuta:50  pares:50
elite_pro     $499 MXN  — sinodal:65   terapeuta:35  pares:35
iniciacion    $299 MXN  — sinodal:30   terapeuta:20  pares:20
medida        <$299 MXN — sinodal:10   terapeuta:10  pares:10
holoconexion  Gratis    — sinodal:3    terapeuta:2   pares:2

"mode" values match the ChatRequest.mode field:
  alumno    → counts against sinodal limit
  terapeuta → counts against terapeuta limit
  pares     → counts against pares limit

Tablas / Rastreo / Intake never consume quota.
"""
from __future__ import annotations

import hmac
import hashlib
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path

# ── Plan configuration ────────────────────────────────────────────────────────

PLAN_LIMITS: dict[str, dict[str, int]] = {
    "premium":      {"sinodal": 100, "terapeuta": 50, "pares": 50},
    "elite_pro":    {"sinodal": 65,  "terapeuta": 35, "pares": 35},
    "iniciacion":   {"sinodal": 30,  "terapeuta": 20, "pares": 20},
    "medida":       {"sinodal": 10,  "terapeuta": 10, "pares": 10},
    "holoconexion": {"sinodal": 3,   "terapeuta": 2,  "pares": 2},
}

PLAN_NAMES: dict[str, str] = {
    "premium":      "Secreta / Acceso Premium",
    "elite_pro":    "Elite Pro",
    "iniciacion":   "Iniciación Elite",
    "medida":       "Elite a tu medida",
    "holoconexion": "Holoconexión",
}

# Maps ChatRequest.mode → DB column + limit key
_MODE_COL: dict[str, str] = {
    "alumno":    "sinodal_used",
    "terapeuta": "terapeuta_used",
    "pares":     "pares_used",
}
_MODE_LIMIT_KEY: dict[str, str] = {
    "alumno":    "sinodal",
    "terapeuta": "terapeuta",
    "pares":     "pares",
}

_lock = threading.Lock()


# ── DB helpers ────────────────────────────────────────────────────────────────

def _conn(db_path: Path) -> sqlite3.Connection:
    c = sqlite3.connect(str(db_path), check_same_thread=False)
    c.row_factory = sqlite3.Row
    return c


def init_db(db_path: Path) -> None:
    """Create tables on first run (idempotent)."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with _lock:
        conn = _conn(db_path)
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                user_id        TEXT    PRIMARY KEY,
                plan           TEXT    NOT NULL DEFAULT 'holoconexion',
                sinodal_used   INTEGER NOT NULL DEFAULT 0,
                terapeuta_used INTEGER NOT NULL DEFAULT 0,
                pares_used     INTEGER NOT NULL DEFAULT 0,
                month          TEXT    NOT NULL DEFAULT '',
                updated_at     TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS session_log (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id    TEXT    NOT NULL,
                mode       TEXT    NOT NULL,
                started_at TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_log_user ON session_log (user_id);
        """)
        conn.commit()
        conn.close()


def _current_month() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m")


# ── Public API ────────────────────────────────────────────────────────────────

def upsert_user(db_path: Path, user_id: str, plan: str) -> None:
    """
    Create user if not exists, or update plan.
    Resets counters automatically when the calendar month changes.
    """
    if plan not in PLAN_LIMITS:
        plan = "holoconexion"
    month = _current_month()
    with _lock:
        conn = _conn(db_path)
        row = conn.execute(
            "SELECT plan, month FROM users WHERE user_id = ?", (user_id,)
        ).fetchone()
        if row is None:
            conn.execute(
                "INSERT INTO users (user_id, plan, month) VALUES (?, ?, ?)",
                (user_id, plan, month),
            )
        elif row["month"] != month:
            # New month — reset counters and update plan
            conn.execute(
                """UPDATE users
                   SET plan=?, sinodal_used=0, terapeuta_used=0,
                       pares_used=0, month=?, updated_at=CURRENT_TIMESTAMP
                   WHERE user_id=?""",
                (plan, month, user_id),
            )
        else:
            # Same month — just update plan in case subscription changed
            conn.execute(
                "UPDATE users SET plan=?, updated_at=CURRENT_TIMESTAMP WHERE user_id=?",
                (plan, user_id),
            )
        conn.commit()
        conn.close()


def get_usage(db_path: Path, user_id: str) -> dict:
    """
    Return usage stats for a user without modifying anything.

    Returns:
        {
            "plan": "elite_pro",
            "plan_name": "Elite Pro",
            "month": "2026-05",
            "usage": {
                "sinodal":   {"used": 5,  "limit": 65, "allowed": True},
                "terapeuta": {"used": 2,  "limit": 35, "allowed": True},
                "pares":     {"used": 35, "limit": 35, "allowed": False},
            }
        }
    """
    month = _current_month()
    with _lock:
        conn = _conn(db_path)
        row = conn.execute(
            "SELECT * FROM users WHERE user_id = ?", (user_id,)
        ).fetchone()
        conn.close()

    if row is None:
        plan = "holoconexion"
        used = {"sinodal": 0, "terapeuta": 0, "pares": 0}
    else:
        plan = row["plan"] if row["plan"] in PLAN_LIMITS else "holoconexion"
        if row["month"] != month:
            used = {"sinodal": 0, "terapeuta": 0, "pares": 0}
        else:
            used = {
                "sinodal":   row["sinodal_used"],
                "terapeuta": row["terapeuta_used"],
                "pares":     row["pares_used"],
            }

    limits = PLAN_LIMITS[plan]
    return {
        "plan": plan,
        "plan_name": PLAN_NAMES.get(plan, plan),
        "month": month,
        "usage": {
            k: {"used": used[k], "limit": limits[k], "allowed": used[k] < limits[k]}
            for k in ("sinodal", "terapeuta", "pares")
        },
    }


def try_consume(db_path: Path, user_id: str, mode: str) -> tuple[bool, int, int]:
    """
    Atomically check + consume one session for the given mode.

    Returns (allowed, used_after, limit).
    If not allowed, returns (False, current_used, limit) without modifying DB.
    """
    col = _MODE_COL.get(mode)
    limit_key = _MODE_LIMIT_KEY.get(mode)
    if not col or not limit_key:
        return True, 0, 0  # Unknown mode → allow (non-metered tool)

    month = _current_month()
    with _lock:
        conn = _conn(db_path)
        row = conn.execute(
            "SELECT plan, month, sinodal_used, terapeuta_used, pares_used "
            "FROM users WHERE user_id = ?",
            (user_id,),
        ).fetchone()

        if row is None:
            conn.close()
            return False, 0, 0

        plan = row["plan"] if row["plan"] in PLAN_LIMITS else "holoconexion"
        limits = PLAN_LIMITS[plan]
        limit = limits[limit_key]

        # Auto-reset on new month
        if row["month"] != month:
            conn.execute(
                """UPDATE users
                   SET sinodal_used=0, terapeuta_used=0, pares_used=0,
                       month=?, updated_at=CURRENT_TIMESTAMP
                   WHERE user_id=?""",
                (month, user_id),
            )
            current = 0
        else:
            current = row[col]

        if current >= limit:
            conn.close()
            return False, current, limit

        new_val = current + 1
        conn.execute(
            f"UPDATE users SET {col}=?, updated_at=CURRENT_TIMESTAMP WHERE user_id=?",
            (new_val, user_id),
        )
        conn.execute(
            "INSERT INTO session_log (user_id, mode) VALUES (?, ?)",
            (user_id, mode),
        )
        conn.commit()
        conn.close()
        return True, new_val, limit


# ── Cookie signing ────────────────────────────────────────────────────────────

def sign_session(user_id: str, plan: str, secret: str) -> str:
    """Create a tamper-proof session cookie value: 'uid|plan.hmac'."""
    payload = f"{user_id}|{plan}"
    sig = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return f"{payload}.{sig}"


def verify_session(cookie: str, secret: str) -> tuple[str, str] | None:
    """
    Verify and decode a session cookie.
    Returns (user_id, plan) or None if invalid/tampered.
    """
    try:
        payload, sig = cookie.rsplit(".", 1)
        expected = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected):
            return None
        uid, plan = payload.split("|", 1)
        if uid and plan in PLAN_LIMITS:
            return uid, plan
    except Exception:
        pass
    return None
