from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

from api.domain_knowledge import TeacherKnowledge
from api.pair_visual_engine import build_pair_visual


ROOT = Path(__file__).resolve().parent.parent
TEACHER_KNOWLEDGE_CACHE_PATH = ROOT / "data" / "teacher_knowledge_cache.json"


teacher = TeacherKnowledge.from_cache(TEACHER_KNOWLEDGE_CACHE_PATH)


ROUTE_PROTOCOL_PREFERENCES = {
    "estres_postraumatico_si_aplica": [
        "Protocolo para la liberación del estrés postraumático",
        "PROTOCOLO PARA EMOCIONES BLOQUEADAS O NEGADAS",
        "PROTOCOLO PARA EMOCIÓN-REACCIÓN",
    ],
    "sistemico": [
        "Protocolo para eliminar conflictos sistémicos",
        "Protocolo para rastreo sentimental",
        "Protocolo para resolución de hologramas emocionales",
    ],
    "transgeneracional": [
        "Protocolo para liberar conflictos de tipo transgeneracional",
        "Protocolo de vidas pasadas",
    ],
    "transgeneracional_si_aplica": [
        "Protocolo para liberar conflictos de tipo transgeneracional",
        "Protocolo para eliminar conexiones sentimentales",
    ],
    "sentimental_si_aplica": [
        "Protocolo para rastreo sentimental",
        "Protocolo para eliminar conexiones sentimentales",
        "Protocolo para eliminar cuerdas invisibles",
        "Protocolo para eliminar cordones energéticos",
    ],
}


def _safe_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _safe_text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _dedupe_protocols(protocols: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    result: list[dict[str, Any]] = []
    for item in protocols:
        title = item["title"]
        if title in seen:
            continue
        seen.add(title)
        result.append(item)
    return result


def _normalize_pair_input(item: Any) -> str:
    if isinstance(item, str):
        return item.strip()
    if isinstance(item, dict):
        return _safe_text(item.get("pair_name"))
    return ""


def _suggest_protocols(release_routes: list[str]) -> list[dict[str, Any]]:
    matches: list[dict[str, Any]] = []
    for route in release_routes:
        for title in ROUTE_PROTOCOL_PREFERENCES.get(route, []):
            protocol = teacher.find_protocol(title)
            if protocol:
                matches.append(
                    {
                        "title": protocol.title,
                        "body": protocol.body,
                        "source_file": protocol.source_file,
                        "route": route,
                    }
                )
    return _dedupe_protocols(matches)


def interpret_pairs(
    case_analysis: dict[str, Any],
    pairs_input: list[Any],
) -> dict[str, Any]:
    interpreted_pairs: list[dict[str, Any]] = []
    dominant_types: list[str] = []
    related_conditions: list[str] = []

    for raw_item in pairs_input:
        pair_query = _normalize_pair_input(raw_item)
        if not pair_query:
            continue

        entry = teacher.find_pair(pair_query)
        if not entry:
            interpreted_pairs.append(
                {
                    "pair_name": pair_query,
                    "found": False,
                    "pair_type": "",
                    "related_condition": "",
                    "source_file": "",
                    "visual": build_pair_visual(pair_query),
                }
            )
            continue

        interpreted_pairs.append(
            {
                "pair_name": entry.pair_name,
                "found": True,
                "pair_type": entry.pair_type,
                "related_condition": entry.related_condition,
                "source_file": entry.source_file,
                "visual": build_pair_visual(entry.pair_name),
            }
        )
        if entry.pair_type:
            dominant_types.append(entry.pair_type)
        if entry.related_condition:
            related_conditions.append(entry.related_condition)

    dominant_types = list(dict.fromkeys(dominant_types))
    related_conditions = list(dict.fromkeys(related_conditions))

    probable_systems = _safe_list(case_analysis.get("probable_systems"))
    probable_conflicts = _safe_list(case_analysis.get("probable_conflicts"))
    family_axes = _safe_list(case_analysis.get("family_axes"))
    release_routes = _safe_list(case_analysis.get("release_protocol_routes"))

    if interpreted_pairs:
        integrated_reading = (
            "La lectura integrada de pares sugiere revisar "
            + ", ".join(probable_systems[:3] or ["los ejes principales del caso"])
            + ", con predominio de "
            + ", ".join(dominant_types[:3] or ["pares sin tipo dominante claro"])
            + "."
        )
    else:
        integrated_reading = (
            "Aún no hay pares capturados para construir una lectura integrada. Primero registra los pares encontrados."
        )

    if related_conditions:
        integrated_reading += " Los pares encontrados apuntan especialmente a: " + "; ".join(related_conditions[:4]) + "."

    if family_axes:
        integrated_reading += " También conviene mantener presentes estos ejes del caso: " + ", ".join(family_axes[:3]) + "."

    suggested_protocols = _suggest_protocols(release_routes)

    return {
        "pairs_count": len(interpreted_pairs),
        "interpreted_pairs": interpreted_pairs,
        "dominant_pair_types": dominant_types,
        "related_conditions": related_conditions,
        "probable_systems": probable_systems,
        "probable_conflicts": probable_conflicts,
        "family_axes": family_axes,
        "integrated_reading": integrated_reading,
        "suggested_protocols": suggested_protocols,
    }


__all__ = ["interpret_pairs", "teacher"]
