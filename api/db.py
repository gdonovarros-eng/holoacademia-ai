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
import os
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path

# ── Dónde viven los datos ─────────────────────────────────────────────────────
# ANTES: SQLite en el disco de Render. Ese disco es EFÍMERO: cada redeploy borraba
# el consumo acumulado de todos los usuarios y las cuotas se reiniciaban solas.
# AHORA: si hay DATABASE_URL (la misma Neon del Hub), se usa Postgres y el consumo
# sobrevive a los despliegues. Sin DATABASE_URL cae a SQLite (útil en local).
#
# Las tablas van con prefijo copiloto_ para no chocar con las del Hub en la misma base.
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
IS_PG = bool(DATABASE_URL)

if IS_PG:
    import psycopg2
    import psycopg2.extras


class _Cur:
    """Cursor mínimo que traduce los '?' de SQLite a los '%s' de psycopg2, para que
    el resto del módulo se escriba una sola vez."""

    def __init__(self, conn, pg: bool):
        self._pg = pg
        self._cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) if pg else conn.cursor()

    def execute(self, sql: str, params=()):
        if self._pg:
            sql = sql.replace("?", "%s")
        self._cur.execute(sql, params)
        return self

    def fetchone(self):
        return self._cur.fetchone()

    def close(self):
        self._cur.close()


class _Conn:
    def __init__(self, db_path: Path):
        if IS_PG:
            self._c = psycopg2.connect(DATABASE_URL)
        else:
            self._c = sqlite3.connect(str(db_path), check_same_thread=False)
            self._c.row_factory = sqlite3.Row

    def execute(self, sql: str, params=()):
        return _Cur(self._c, IS_PG).execute(sql, params)

    def commit(self):
        self._c.commit()

    def close(self):
        self._c.close()

# ── Plan configuration ────────────────────────────────────────────────────────

PLAN_LIMITS: dict[str, dict[str, int]] = {
    # ── Planes vigentes (holoacademia.tv) ──
    # Espejo de los cupos que ya tenían sus equivalentes viejos. Si quieres otros
    # números, este es el único lugar donde se cambian.
    "especialista": {"sinodal": 100, "terapeuta": 50, "pares": 50},   # antes: premium
    "terapeuta":    {"sinodal": 65,  "terapeuta": 35, "pares": 35},   # antes: elite_pro
    "aprendiz":     {"sinodal": 30,  "terapeuta": 20, "pares": 20},   # antes: iniciacion
    # ── Planes anteriores (se respetan mientras existan suscriptores) ──
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

def _conn(db_path: Path) -> _Conn:
    return _Conn(db_path)


def init_db(db_path: Path) -> None:
    """Crea las tablas la primera vez (idempotente)."""
    if not IS_PG:
        db_path.parent.mkdir(parents=True, exist_ok=True)

    serial = "SERIAL" if IS_PG else "INTEGER"
    pk = "PRIMARY KEY" if IS_PG else "PRIMARY KEY AUTOINCREMENT"

    with _lock:
        conn = _conn(db_path)
        conn.execute(f"""
            CREATE TABLE IF NOT EXISTS copiloto_users (
                user_id        TEXT    PRIMARY KEY,
                plan           TEXT    NOT NULL DEFAULT 'holoconexion',
                sinodal_used   INTEGER NOT NULL DEFAULT 0,
                terapeuta_used INTEGER NOT NULL DEFAULT 0,
                pares_used     INTEGER NOT NULL DEFAULT 0,
                month          TEXT    NOT NULL DEFAULT '',
                updated_at     TEXT    NOT NULL DEFAULT ''
            )""").close()
        conn.execute(f"""
            CREATE TABLE IF NOT EXISTS copiloto_session_log (
                id         {serial} {pk},
                user_id    TEXT NOT NULL,
                mode       TEXT NOT NULL,
                started_at TEXT NOT NULL DEFAULT ''
            )""").close()
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_copiloto_log_user ON copiloto_session_log (user_id)"
        ).close()
        conn.commit()
        conn.close()


def _ahora() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


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
    ahora = _ahora()
    with _lock:
        conn = _conn(db_path)
        row = conn.execute(
            "SELECT plan, month FROM copiloto_users WHERE user_id = ?", (user_id,)
        ).fetchone()
        if row is None:
            conn.execute(
                "INSERT INTO copiloto_users (user_id, plan, month, updated_at) VALUES (?, ?, ?, ?)",
                (user_id, plan, month, ahora),
            ).close()
        elif row["month"] != month:
            # Mes nuevo — reinicia contadores y actualiza el plan
            conn.execute(
                """UPDATE copiloto_users
                   SET plan=?, sinodal_used=0, terapeuta_used=0,
                       pares_used=0, month=?, updated_at=?
                   WHERE user_id=?""",
                (plan, month, ahora, user_id),
            ).close()
        else:
            # Mismo mes — solo refresca el plan por si cambió la suscripción
            conn.execute(
                "UPDATE copiloto_users SET plan=?, updated_at=? WHERE user_id=?",
                (plan, ahora, user_id),
            ).close()
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
            "SELECT * FROM copiloto_users WHERE user_id = ?", (user_id,)
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
    ahora = _ahora()
    with _lock:
        conn = _conn(db_path)
        row = conn.execute(
            "SELECT plan, month, sinodal_used, terapeuta_used, pares_used "
            "FROM copiloto_users WHERE user_id = ?",
            (user_id,),
        ).fetchone()

        if row is None:
            conn.close()
            return False, 0, 0

        plan = row["plan"] if row["plan"] in PLAN_LIMITS else "holoconexion"
        limit = PLAN_LIMITS[plan][limit_key]

        # Mes nuevo → los contadores se reinician solos
        if row["month"] != month:
            conn.execute(
                """UPDATE copiloto_users
                   SET sinodal_used=0, terapeuta_used=0, pares_used=0,
                       month=?, updated_at=?
                   WHERE user_id=?""",
                (month, ahora, user_id),
            ).close()
            current = 0
        else:
            current = row[col]

        if current >= limit:
            conn.close()
            return False, current, limit

        # Consumo ATÓMICO: la condición del límite va DENTRO del UPDATE, así que dos
        # peticiones simultáneas no pueden pasarse del cupo (antes solo lo protegía
        # un lock de proceso, que no sirve con varios workers).
        cur = conn.execute(
            f"""UPDATE copiloto_users
                SET {col} = {col} + 1, updated_at=?
                WHERE user_id=? AND {col} < ?
                RETURNING {col}""",
            (ahora, user_id, limit),
        )
        got = cur.fetchone()
        cur.close()

        if not got:
            conn.close()
            return False, current, limit

        new_val = got[col] if not isinstance(got, tuple) else got[0]

        conn.execute(
            "INSERT INTO copiloto_session_log (user_id, mode, started_at) VALUES (?, ?, ?)",
            (user_id, mode, ahora),
        ).close()
        conn.commit()
        conn.close()
        return True, int(new_val), limit


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
