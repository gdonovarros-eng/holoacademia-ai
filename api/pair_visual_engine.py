from __future__ import annotations

import re
import unicodedata
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
PAIR_VISUALS_ROOT = ROOT / "data" / "pair_visuals"
MANUAL_2020_ATLAS = {
    "craneo": [PAIR_VISUALS_ROOT / "manual_2020" / "page-039.png"],
    "cara": [PAIR_VISUALS_ROOT / "manual_2020" / "page-039.png"],
    "cuello": [PAIR_VISUALS_ROOT / "manual_2020" / "page-039.png"],
    "torax": [
        PAIR_VISUALS_ROOT / "manual_2020" / "page-039.png",
        PAIR_VISUALS_ROOT / "manual_2020" / "page-042.png",
    ],
    "abdomen": [
        PAIR_VISUALS_ROOT / "manual_2020" / "page-039.png",
        PAIR_VISUALS_ROOT / "manual_2020" / "page-042.png",
    ],
    "abdomen_posterior": [
        PAIR_VISUALS_ROOT / "manual_2020" / "page-041.png",
        PAIR_VISUALS_ROOT / "manual_2020" / "page-042.png",
    ],
    "pelvis": [
        PAIR_VISUALS_ROOT / "manual_2020" / "page-041.png",
        PAIR_VISUALS_ROOT / "manual_2020" / "page-042.png",
    ],
    "columna": [PAIR_VISUALS_ROOT / "manual_2020" / "page-041.png"],
    "extremidades": [PAIR_VISUALS_ROOT / "manual_2020" / "page-042.png"],
    "general": [
        PAIR_VISUALS_ROOT / "manual_2020" / "page-042.png",
        PAIR_VISUALS_ROOT / "manual_2020" / "page-043.png",
    ],
}


def _normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value or "")
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii").lower()
    ascii_value = re.sub(r"[^a-z0-9]+", "-", ascii_value).strip("-")
    return ascii_value


def _clean_point_label(value: str) -> str:
    text = (value or "").strip()
    text = re.sub(r"\s+", " ", text)
    return text


def split_pair_points(pair_name: str) -> tuple[str, str]:
    if " - " in pair_name:
        left, right = pair_name.split(" - ", 1)
        return _clean_point_label(left), _clean_point_label(right)

    parts = re.split(r"\s*[-–]\s*", pair_name, maxsplit=1)
    if len(parts) == 2:
        return _clean_point_label(parts[0]), _clean_point_label(parts[1])

    text = _clean_point_label(pair_name)
    return text, ""


def _region_hint(point_label: str) -> str:
    normalized = _normalize_text(point_label)
    region_map = [
        ("hipofisis", "craneo"),
        ("adenohipofisis", "craneo"),
        ("pineal", "craneo"),
        ("temporal", "craneo"),
        ("parietal", "craneo"),
        ("occipital", "craneo"),
        ("ojo", "cara"),
        ("orbital", "cara"),
        ("menton", "cara"),
        ("pomulo", "cara"),
        ("oido", "cara"),
        ("parotida", "cuello"),
        ("tiroides", "cuello"),
        ("garganta", "cuello"),
        ("cervical", "cuello"),
        ("torax", "torax"),
        ("pleura", "torax"),
        ("corazon", "torax"),
        ("mama", "torax"),
        ("mediastino", "torax"),
        ("diafragma", "torax"),
        ("higado", "abdomen"),
        ("estomago", "abdomen"),
        ("pancreas", "abdomen"),
        ("colon", "abdomen"),
        ("intestino", "abdomen"),
        ("duodeno", "abdomen"),
        ("piloro", "abdomen"),
        ("apendice", "abdomen"),
        ("retrohepatico", "abdomen"),
        ("bazo", "abdomen"),
        ("vejiga", "pelvis"),
        ("utero", "pelvis"),
        ("ovario", "pelvis"),
        ("vagina", "pelvis"),
        ("ano", "pelvis"),
        ("recto", "pelvis"),
        ("prostata", "pelvis"),
        ("testiculo", "pelvis"),
        ("sacro", "columna"),
        ("coxis", "columna"),
        ("lumbar", "columna"),
        ("dorsal", "columna"),
        ("escapula", "extremidades"),
        ("deltoides", "extremidades"),
        ("aductor", "extremidades"),
        ("muneca", "extremidades"),
        ("trocanter", "extremidades"),
        ("rodilla", "extremidades"),
        ("tobillo", "extremidades"),
        ("isquion", "pelvis"),
        ("rinon", "abdomen_posterior"),
        ("renal", "abdomen_posterior"),
        ("uretero", "abdomen_posterior"),
    ]
    for needle, region in region_map:
        if needle in normalized:
            return region
    return "general"


def _possible_image_paths(point_label: str, region_hint: str) -> list[str]:
    slug = _normalize_text(point_label)
    candidates = [
        PAIR_VISUALS_ROOT / "points" / f"{slug}.png",
        PAIR_VISUALS_ROOT / "points" / f"{slug}.jpg",
        PAIR_VISUALS_ROOT / "points" / f"{slug}.webp",
        PAIR_VISUALS_ROOT / "regions" / f"{region_hint}.png",
        PAIR_VISUALS_ROOT / "regions" / f"{region_hint}.jpg",
        PAIR_VISUALS_ROOT / "regions" / f"{region_hint}.webp",
        PAIR_VISUALS_ROOT / "full_body" / "front.png",
        PAIR_VISUALS_ROOT / "full_body" / "back.png",
    ]
    candidates.extend(MANUAL_2020_ATLAS.get(region_hint, []))
    found = [str(path) for path in candidates if path.exists()]
    deduped: list[str] = []
    seen: set[str] = set()
    for item in found:
        if item in seen:
            continue
        seen.add(item)
        deduped.append(item)
    return deduped


def build_pair_visual(pair_name: str) -> dict[str, Any]:
    point_a, point_b = split_pair_points(pair_name)
    point_a_region = _region_hint(point_a)
    point_b_region = _region_hint(point_b)

    point_a_images = _possible_image_paths(point_a, point_a_region)
    point_b_images = _possible_image_paths(point_b, point_b_region)

    all_images = []
    for image in point_a_images + point_b_images:
        if image not in all_images:
            all_images.append(image)

    return {
        "pair_name": pair_name,
        "point_a": {
            "label": point_a,
            "region_hint": point_a_region,
            "image_candidates": point_a_images,
        },
        "point_b": {
            "label": point_b,
            "region_hint": point_b_region,
            "image_candidates": point_b_images,
        },
        "image_candidates": all_images,
        "has_reference_images": bool(all_images),
        "status": "ready" if all_images else "missing_reference_images",
        "source_mode": "atlas_pages_or_point_images" if all_images else "no_visual_reference",
    }


__all__ = ["build_pair_visual", "split_pair_points"]
