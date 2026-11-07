"""Cupos del Copiloto: Especialista (y su alias premium) no tiene tope; los demás sí."""
import os
import tempfile
from pathlib import Path

os.environ.pop("DATABASE_URL", None)  # siempre SQLite temporal en pruebas

from api.db import ILIMITADO, get_usage, init_db, try_consume, upsert_user


def _db():
    d = Path(tempfile.mkdtemp()) / "cupos.db"
    init_db(d)
    return d


def test_especialista_sin_tope():
    db = _db()
    for plan in ("especialista", "premium"):
        upsert_user(db, "u-" + plan, plan)
        for _ in range(120):  # más que el tope viejo de 100
            ok, _, limit = try_consume(db, "u-" + plan, "alumno")
            assert ok and limit == ILIMITADO
        u = get_usage(db, "u-" + plan)["usage"]
        assert all(v["unlimited"] and v["allowed"] for v in u.values())


def test_aprendiz_conserva_tope():
    db = _db()
    upsert_user(db, "u-ap", "aprendiz")
    resultados = [try_consume(db, "u-ap", "pares")[0] for _ in range(21)]
    assert resultados[:20] == [True] * 20 and resultados[20] is False
    u = get_usage(db, "u-ap")["usage"]["pares"]
    assert u["unlimited"] is False and u["allowed"] is False
