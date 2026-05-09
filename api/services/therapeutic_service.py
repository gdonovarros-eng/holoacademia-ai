from __future__ import annotations

import sys
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parents[2]
THERAPEUTIC_ENGINE_DIR = BASE_DIR / "Motor terapeutico"

if str(THERAPEUTIC_ENGINE_DIR) not in sys.path:
    sys.path.insert(0, str(THERAPEUTIC_ENGINE_DIR))

from therapeutic_assistant.service import answer_therapeutic_query


def run_therapeutic_analysis(data: dict[str, Any]) -> dict[str, Any]:
    try:
        result = answer_therapeutic_query(data)
        return {
            "answer": str(result.get("answer", "")),
            "confidence": str(result.get("confidence", "low")),
            "entrevista_base": dict(result.get("entrevista_base", {})),
            "ruta_principal": str(result.get("ruta_principal", "")),
            "lectura_inicial": str(result.get("lectura_inicial", "")),
            "puerta_principal": dict(result.get("puerta_principal", {})),
            "ruta_sugerida": str(result.get("ruta_sugerida", "")),
            "accion_inmediata": str(result.get("accion_inmediata", "")),
            "evidencias_principales": list(result.get("evidencias_principales", [])),
            "validaciones_clave": list(result.get("validaciones_clave", [])),
            "protocolo_principal": dict(result.get("protocolo_principal", {})),
            "protocolo_sugerido": dict(result.get("protocolo_sugerido", {})),
            "herramientas_clave": list(result.get("herramientas_clave", [])),
            "herramientas_relevantes": list(result.get("herramientas_relevantes", [])),
            "pasos_inmediatos": list(result.get("pasos_inmediatos", [])),
            "punto_de_decision": str(result.get("punto_de_decision", "")),
            "si_no_confirma": str(result.get("si_no_confirma", "")),
            "preguntas_clave": list(result.get("preguntas_clave", [])),
            "limites": list(result.get("limites", [])),
            "missing_data": list(result.get("missing_data", [])),
            "priority_questions": list(result.get("priority_questions", [])),
            "possible_lines": list(result.get("possible_lines", [])),
            "warnings": list(result.get("warnings", [])),
            "used_patterns": list(result.get("used_patterns", [])),
            "used_guides": list(result.get("used_guides", [])),
            "trace": dict(result.get("trace", {})),
            "genogram_resolution": result.get("genogram_resolution") or None,
        }
    except Exception as exc:
        return {
            "answer": "Hubo un problema al procesar el caso. Intenta nuevamente.",
            "confidence": "low",
            "entrevista_base": {},
            "ruta_principal": "",
            "lectura_inicial": "",
            "puerta_principal": {},
            "ruta_sugerida": "",
            "accion_inmediata": "",
            "evidencias_principales": [],
            "validaciones_clave": [],
            "protocolo_principal": {},
            "protocolo_sugerido": {},
            "herramientas_clave": [],
            "herramientas_relevantes": [],
            "pasos_inmediatos": [],
            "punto_de_decision": "",
            "si_no_confirma": "",
            "preguntas_clave": [],
            "limites": [],
            "missing_data": [],
            "priority_questions": [],
            "possible_lines": [],
            "warnings": [],
            "used_patterns": [],
            "used_guides": [],
            "trace": {"error": str(exc)},
            "genogram_resolution": None,
        }
