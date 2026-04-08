from __future__ import annotations

from typing import Any


def _safe_text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _dedupe_keep_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        text = _safe_text(value)
        key = text.lower()
        if not text or key in seen:
            continue
        seen.add(key)
        result.append(text)
    return result


def _patient_name(case_payload: dict[str, Any]) -> str:
    consultant = case_payload.get("consultant") if isinstance(case_payload.get("consultant"), dict) else {}
    return _safe_text(consultant.get("full_name")) or _safe_text(case_payload.get("patient_name"))


def _patient_birth_date(case_payload: dict[str, Any]) -> str:
    consultant = case_payload.get("consultant") if isinstance(case_payload.get("consultant"), dict) else {}
    return _safe_text(consultant.get("birth_date")) or _safe_text(case_payload.get("patient_birth_date"))


def build_radionic_pair_table(
    case_payload: dict[str, Any],
    pair_names: list[str],
    *,
    title: str = "Tabla radiónica sugerida",
) -> dict[str, Any]:
    patient_name = _patient_name(case_payload)
    patient_birth_date = _patient_birth_date(case_payload)
    pairs = _dedupe_keep_order(pair_names)
    circuit = ["∞"] * 5
    patient_line = " · ".join(part for part in [patient_name, patient_birth_date] if part)
    intention_line = "Activo pares biomagnéticos a una potencia de 3000 gauss durante 30 minutos."

    lines = [
        " ".join(circuit),
        patient_line,
        intention_line,
        *pairs,
        " ".join(circuit),
    ]
    lines = [line for line in lines if line]

    return {
        "title": title,
        "active": bool(patient_name or patient_birth_date or pairs),
        "top_circuit": circuit,
        "bottom_circuit": circuit,
        "patient_name": patient_name,
        "patient_birth_date": patient_birth_date,
        "patient_line": patient_line,
        "intention_line": intention_line,
        "pairs": pairs,
        "copy_text": "\n".join(lines),
    }


__all__ = ["build_radionic_pair_table"]
