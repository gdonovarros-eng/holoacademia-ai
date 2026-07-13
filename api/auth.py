"""
auth.py — Authentication and subscription module for HoloAcademia.

Pure stdlib, no FastAPI dependency.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import sqlite3
import time
import uuid
import base64
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────────────────

USERDATA_DIR = Path(os.getenv("USERDATA_DIR", "./userdata"))
DB_PATH = USERDATA_DIR / "holoacademia.db"

_JWT_SECRET = os.getenv("JWT_SECRET", "")
if not _JWT_SECRET:
    import secrets as _secrets
    _JWT_SECRET = _secrets.token_hex(32)
    logger.warning(
        "JWT_SECRET env var not set — using random secret. "
        "Tokens will be invalidated on each restart. Set JWT_SECRET in production."
    )

TOKEN_TTL_SECONDS = 7 * 24 * 3600  # 7 days

PLANS: dict[str, dict] = {
    "basic":        {"sessions": 30,     "label": "Básico ($29/mes)"},
    "professional": {"sessions": 80,     "label": "Profesional ($59/mes)"},
    "unlimited":    {"sessions": 200,    "label": "Ilimitado ($99/mes)"},
    "admin":        {"sessions": 999999, "label": "Admin"},
}

# Credenciales de admin: SIN valor por defecto. Antes traían "holo2024admin"
# hardcodeado en un repo PÚBLICO: quien leyera el código entraba como admin.
# Si no están en el entorno, la cuenta de admin simplemente no existe.
ADMIN_EMAIL    = os.getenv("ADMIN_EMAIL", "").strip()
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "").strip()
ADMIN_ENABLED  = bool(ADMIN_EMAIL and ADMIN_PASSWORD)

# ── DB helpers ────────────────────────────────────────────────────────────────

def _get_conn() -> sqlite3.Connection:
    USERDATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Create tables and seed admin user if none exists."""
    with _get_conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id           TEXT PRIMARY KEY,
                email        TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                name         TEXT NOT NULL DEFAULT '',
                plan         TEXT NOT NULL DEFAULT 'basic',
                sessions_used INT NOT NULL DEFAULT 0,
                month        TEXT NOT NULL DEFAULT '',
                active       INT NOT NULL DEFAULT 1,
                created_at   TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS session_log (
                id         TEXT PRIMARY KEY,
                user_id    TEXT NOT NULL,
                started_at TEXT NOT NULL,
                mode       TEXT NOT NULL DEFAULT 'terapeuta'
            );
        """)

        # Check if any admin user exists
        row = conn.execute(
            "SELECT id FROM users WHERE plan = 'admin' LIMIT 1"
        ).fetchone()
        if row is None and ADMIN_ENABLED:
            try:
                create_user(ADMIN_EMAIL, ADMIN_PASSWORD, "Administrador", "admin")
                logger.info("Admin user created: %s", ADMIN_EMAIL)
            except ValueError:
                pass  # Ya existe (condición de carrera)
        elif row is None:
            logger.warning(
                "No se creó cuenta de admin: falta ADMIN_EMAIL / ADMIN_PASSWORD en el entorno."
            )


# ── Password helpers ──────────────────────────────────────────────────────────

def _hash_password(password: str) -> str:
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 260000)
    return salt.hex() + ":" + dk.hex()


def _verify_password(password: str, stored_hash: str) -> bool:
    try:
        salt_hex, dk_hex = stored_hash.split(":", 1)
        salt = bytes.fromhex(salt_hex)
        dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 260000)
        return hmac.compare_digest(dk.hex(), dk_hex)
    except Exception:
        return False


# ── Token helpers ─────────────────────────────────────────────────────────────

def _make_token(user_id: str, plan: str) -> str:
    payload = json.dumps({
        "sub": user_id,
        "exp": int(time.time()) + TOKEN_TTL_SECONDS,
        "plan": plan,
    }, separators=(",", ":")).encode()
    b64 = base64.urlsafe_b64encode(payload).rstrip(b"=").decode()
    sig = hmac.new(_JWT_SECRET.encode(), b64.encode(), hashlib.sha256).hexdigest()
    return f"{b64}.{sig}"


def verify_token(token: str) -> dict | None:
    """Return the user dict if the token is valid and not expired, else None."""
    try:
        b64, sig = token.rsplit(".", 1)
        expected = hmac.new(_JWT_SECRET.encode(), b64.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected):
            return None
        # pad base64
        pad = 4 - len(b64) % 4
        payload = json.loads(base64.urlsafe_b64decode(b64 + "=" * (pad % 4)))
        if payload["exp"] < time.time():
            return None
        user = get_user(payload["sub"])
        if user is None or not user["active"]:
            return None
        return user
    except Exception:
        return None


# ── User CRUD ─────────────────────────────────────────────────────────────────

def _row_to_dict(row: sqlite3.Row) -> dict:
    d = dict(row)
    d["active"] = bool(d.get("active", 1))
    plan_key = d.get("plan", "basic")
    d["sessions_limit"] = PLANS.get(plan_key, PLANS["basic"])["sessions"]
    d["plan_label"]     = PLANS.get(plan_key, PLANS["basic"])["label"]
    d.pop("password_hash", None)
    return d


def get_user(user_id: str) -> dict | None:
    with _get_conn() as conn:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    return _row_to_dict(row) if row else None


def get_user_by_email(email: str) -> dict | None:
    with _get_conn() as conn:
        row = conn.execute("SELECT * FROM users WHERE email = ?", (email.lower().strip(),)).fetchone()
    return _row_to_dict(row) if row else None


def _get_user_with_hash(user_id: str) -> sqlite3.Row | None:
    with _get_conn() as conn:
        return conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()


def _get_user_with_hash_by_email(email: str) -> sqlite3.Row | None:
    with _get_conn() as conn:
        return conn.execute(
            "SELECT * FROM users WHERE email = ?", (email.lower().strip(),)
        ).fetchone()


def create_user(email: str, password: str, name: str, plan: str = "basic") -> dict:
    """Create a new user. Raises ValueError if email already exists."""
    email = email.lower().strip()
    if plan not in PLANS:
        plan = "basic"
    user_id = str(uuid.uuid4())
    ph = _hash_password(password)
    now = datetime.now(timezone.utc).isoformat()
    try:
        with _get_conn() as conn:
            conn.execute(
                "INSERT INTO users (id, email, password_hash, name, plan, sessions_used, month, active, created_at) "
                "VALUES (?, ?, ?, ?, ?, 0, '', 1, ?)",
                (user_id, email, ph, name, plan, now),
            )
    except sqlite3.IntegrityError:
        raise ValueError(f"Email already exists: {email}")
    return get_user(user_id)  # type: ignore[return-value]


def list_users() -> list[dict]:
    with _get_conn() as conn:
        rows = conn.execute("SELECT * FROM users ORDER BY created_at DESC").fetchall()
    result = []
    for row in rows:
        d = dict(row)
        d.pop("password_hash", None)
        d["active"] = bool(d.get("active", 1))
        plan_key = d.get("plan", "basic")
        d["sessions_limit"] = PLANS.get(plan_key, PLANS["basic"])["sessions"]
        d["plan_label"]     = PLANS.get(plan_key, PLANS["basic"])["label"]
        result.append(d)
    return result


def update_user(user_id: str, **fields) -> dict | None:
    """Update allowed fields: name, plan, active."""
    allowed = {"name", "plan", "active"}
    updates = {k: v for k, v in fields.items() if k in allowed}
    if not updates:
        return get_user(user_id)
    if "plan" in updates and updates["plan"] not in PLANS:
        raise ValueError(f"Invalid plan: {updates['plan']}")
    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [user_id]
    with _get_conn() as conn:
        conn.execute(f"UPDATE users SET {set_clause} WHERE id = ?", values)
    return get_user(user_id)


def delete_user(user_id: str) -> None:
    with _get_conn() as conn:
        conn.execute("DELETE FROM session_log WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM users WHERE id = ?", (user_id,))


# ── Auth ──────────────────────────────────────────────────────────────────────

def login(email: str, password: str) -> dict | None:
    """Verify credentials. Returns {token, user} or None."""
    row = _get_user_with_hash_by_email(email)
    if row is None:
        return None
    if not bool(row["active"]):
        return None
    if not _verify_password(password, row["password_hash"]):
        return None
    token = _make_token(row["id"], row["plan"])
    user = _row_to_dict(row)
    return {"token": token, "user": user}


# ── Session tracking ──────────────────────────────────────────────────────────

def _current_month() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m")


def start_session(user_id: str, mode: str = "terapeuta") -> dict:
    """
    Increment sessions_used (resetting if it's a new month).
    Returns {"ok": True, "sessions_used": n, "sessions_limit": n}
    or      {"ok": False, "reason": "limit_reached"}.
    """
    with _get_conn() as conn:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        if row is None:
            return {"ok": False, "reason": "user_not_found"}

        plan_key = row["plan"]
        limit = PLANS.get(plan_key, PLANS["basic"])["sessions"]
        current_month = _current_month()

        sessions_used = row["sessions_used"]
        if row["month"] != current_month:
            # New month — reset counter
            sessions_used = 0
            conn.execute(
                "UPDATE users SET sessions_used = 0, month = ? WHERE id = ?",
                (current_month, user_id),
            )

        if sessions_used >= limit:
            return {"ok": False, "reason": "limit_reached", "sessions_used": sessions_used, "sessions_limit": limit}

        sessions_used += 1
        conn.execute(
            "UPDATE users SET sessions_used = ?, month = ? WHERE id = ?",
            (sessions_used, current_month, user_id),
        )
        log_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        conn.execute(
            "INSERT INTO session_log (id, user_id, started_at, mode) VALUES (?, ?, ?, ?)",
            (log_id, user_id, now, mode),
        )

    return {"ok": True, "sessions_used": sessions_used, "sessions_limit": limit}


def get_usage(user_id: str) -> dict:
    """Return usage info for the current user."""
    with _get_conn() as conn:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        if row is None:
            return {}
        plan_key = row["plan"]
        limit = PLANS.get(plan_key, PLANS["basic"])["sessions"]
        current_month = _current_month()
        sessions_used = row["sessions_used"] if row["month"] == current_month else 0
        # Count sessions this month from log
        log_count = conn.execute(
            "SELECT COUNT(*) FROM session_log WHERE user_id = ? AND started_at LIKE ?",
            (user_id, f"{current_month}%"),
        ).fetchone()[0]
    return {
        "plan": plan_key,
        "plan_label": PLANS.get(plan_key, PLANS["basic"])["label"],
        "sessions_used": sessions_used,
        "sessions_limit": limit,
        "sessions_remaining": max(0, limit - sessions_used),
        "month": current_month,
        "sessions_this_month_log": log_count,
    }


# ── Admin stats ───────────────────────────────────────────────────────────────

def get_stats() -> dict:
    """Return aggregate stats for admin panel."""
    current_month = _current_month()
    with _get_conn() as conn:
        total_users  = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        active_users = conn.execute("SELECT COUNT(*) FROM users WHERE active = 1").fetchone()[0]
        sessions_this_month = conn.execute(
            "SELECT COUNT(*) FROM session_log WHERE started_at LIKE ?",
            (f"{current_month}%",),
        ).fetchone()[0]
        plan_counts_rows = conn.execute(
            "SELECT plan, COUNT(*) as cnt FROM users GROUP BY plan"
        ).fetchall()
    plan_counts = {row["plan"]: row["cnt"] for row in plan_counts_rows}
    return {
        "total_users": total_users,
        "active_users": active_users,
        "sessions_this_month": sessions_this_month,
        "plan_counts": plan_counts,
    }
