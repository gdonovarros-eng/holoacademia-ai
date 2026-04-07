from __future__ import annotations

import re
import unicodedata
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
PAIR_VISUALS_ROOT = ROOT / "data" / "pair_visuals"


def _atlas_page_path(page: int) -> Path:
    if page <= 43:
        return PAIR_VISUALS_ROOT / "manual_2024" / f"page-{page:03d}.png"
    return PAIR_VISUALS_ROOT / "manual_2024_extra" / f"page-{page:03d}.png"


ATLAS_PAGES = {page: _atlas_page_path(page) for page in range(39, 58)}
GENERAL_BODY_MAP = [ATLAS_PAGES[39]]


ATLAS_POINT_PAGE_LABELS = {
    40: [
        "prepineal",
        "pineal",
        "postpineal",
        "nucleos basales",
        "cingular",
        "borde de calloso",
        "cisura media",
        "parietal",
    ],
    41: [
        "bulbo",
        "cisura de silvio",
        "occipital",
        "cerebelo",
    ],
    42: [
        "frontoparietal",
        "amigdala cerebral",
        "temporal",
        "oido",
        "pomulo",
        "cigomatico",
        "retromastoides",
        "quiasma",
        "sien",
        "poligono de willis",
        "parotida",
        "rama mandibular",
        "angulo mandibula",
    ],
    43: [
        "talamo",
        "hipofisis",
        "adenohipofisis",
        "supraciliar",
        "interciliar",
        "polo",
        "anterior",
        "frontal",
        "seno frontal",
        "ceja",
    ],
    44: [
        "parpado",
        "ojo",
        "piso orbital",
        "orbital",
        "craneal",
        "lacrimal",
        "canto",
        "pomulo",
        "nariz",
        "maxilar superior",
        "lengua",
        "comisura",
        "dental ras",
        "menton",
        "mandibula",
        "labio",
        "retronasal",
        "submaxilar",
        "inframenton",
        "punta de nariz",
    ],
    45: [
        "laringe",
        "hueco de la garganta",
        "garganta",
        "carotida",
        "tiroides",
        "paratiroides",
        "retromastoideo",
        "cuello",
        "nervio vago",
        "nudo cervical",
        "plexo cervical",
        "yugular",
    ],
    46: [
        "atlas",
        "cervical 3",
        "cervical 4",
        "cervical 3-4",
        "cervical 7",
        "dorsal 1",
        "supraespinoso",
        "nuca",
    ],
    47: [
        "epiclavia",
        "subclavia",
        "supratimo",
        "mango del esternon",
        "mediastino",
        "timo",
        "esternon",
        "carina",
        "traquea",
        "esofago",
        "hiato esofagico",
        "axila",
        "corazon",
        "seno auriculoventricular",
        "pericardio",
        "pectoral interno",
        "pectoral",
        "axilar",
        "pleura",
        "diafragma",
        "condral",
        "costilla 7",
        "peritoneo",
        "infratimo",
        "clavicula media",
        "tendon pectoral",
        "suprapulmon",
        "supraescapular",
        "retroaxilar",
        "latissimus",
        "dorso ancho",
    ],
    48: [
        "colon descendente",
        "higado",
        "pleura",
        "colon ascendente",
        "costo hepatico",
        "colon transverso",
        "cola de pancreas",
        "bazo",
        "piloro",
        "cabeza de pancreas",
    ],
    49: [
        "estomago",
        "piloro",
        "ligamento hepat",
        "cuerpo del estomago",
        "vesicula",
        "cuello de vesicula",
        "costal",
        "hiato diafragmatico",
        "antro de pancreas",
        "cuerpo de pancreas",
        "cola de pancreas",
        "punta de pancreas",
        "bazo",
        "iliaco",
        "mesenterio",
        "apendice",
        "uretero",
        "riñon",
        "rinon",
        "valvula ileocecal",
        "colon hepatico",
        "sigmoides",
        "vejiga media",
        "supraumbilical",
        "suprapiloro",
        "coledoco",
        "ganglios mesentericos",
        "vena porta",
    ],
    51: [
        "dorsal 2",
        "cava",
        "dorsal 5",
        "lumbar 2",
        "dorsal 6",
        "suprarrenal",
        "pulmon",
        "escapula",
        "lobulo posterior del higado",
        "flanco",
        "capsula renal",
        "riñon",
        "rinon",
        "lumbar 4",
        "cuadrado",
        "espalda",
        "perirrenal",
        "caliz renal interno",
    ],
    52: [
        "vejiga",
        "suprapubico",
        "cuerpo cavernoso",
        "pene",
        "testiculo",
        "cadera",
        "cresta iliaca",
        "nervio inguinal",
        "pudendo",
        "femur",
        "trocanter mayor",
        "trocanter menor",
        "femoral",
        "pelvis delantera",
        "conducto espermatico",
    ],
    53: [
        "interiliaco",
        "iliaco",
        "sacro",
        "saco de douglas",
        "gluteo",
        "coxis",
        "recto",
        "nervio isquiatica",
        "isquion",
        "pelvis trasera",
    ],
    54: [
        "utero",
        "clitoris",
        "uretra",
        "vagina",
        "trompa",
        "ovario",
        "prostata",
        "ano",
        "pelvis femenina",
        "perine",
    ],
    55: [
        "deltoides",
        "bursa",
        "triceps",
        "braquial",
        "radio",
        "cubito",
        "muneca anterior",
        "muneca posterior",
        "mano",
        "dorso mano",
        "indice",
        "brazos",
    ],
    56: [
        "aductor menor",
        "aductor mayor",
        "cuadriceps",
        "tensor fascia lata",
        "ciatico",
        "rotula",
        "cuello externo de la rodilla",
        "popliteo",
        "tibia",
        "perone",
        "gemelos",
        "aquiles",
        "aquiles bajo",
        "tobillo",
        "empeine",
        "dedo gordo",
        "planta",
        "piernas",
        "vasto lateral",
        "cabeza de perone",
        "maleolo interno",
        "base meñique del pie",
        "biceps femoral",
        "femur posterior",
        "suprapopliteo",
        "soleo",
        "talon",
    ],
    57: [
        "cervicales",
        "dorsales",
        "lumbares",
        "sacro",
        "coxis",
        "punto trauma",
        "punto trauma sedante",
        "punto trauma estimulante",
        "articulacion dolorosa",
        "inflamacion",
        "fiebre",
        "columna",
        "pares variables",
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


def _normalized_atlas_terms() -> dict[int, list[str]]:
    return {
        page: [_normalize_text(label) for label in labels]
        for page, labels in ATLAS_POINT_PAGE_LABELS.items()
    }


NORMALIZED_ATLAS_TERMS = _normalized_atlas_terms()


def _alias_matches(normalized_label: str, normalized_alias: str) -> bool:
    pattern = rf"(^|-){re.escape(normalized_alias)}($|-)"
    return re.search(pattern, normalized_label) is not None


def _matching_atlas_pages(point_label: str) -> list[Path]:
    normalized = _normalize_text(point_label)
    if not normalized:
        return []

    matches: list[Path] = []
    for page, labels in NORMALIZED_ATLAS_TERMS.items():
        if any(_alias_matches(normalized, alias) for alias in labels):
            path = ATLAS_PAGES.get(page)
            if path and path.exists():
                matches.append(path)

    deduped: list[Path] = []
    seen: set[str] = set()
    for path in matches:
        key = str(path)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(path)
    return deduped


def _point_visual(point_label: str) -> dict[str, Any]:
    exact_pages = _matching_atlas_pages(point_label)
    if exact_pages:
        return {
            "label": point_label,
            "image_candidates": [str(path) for path in exact_pages],
            "exact_atlas_match": True,
            "status": "exact_point_atlas",
        }

    fallback_pages = [str(path) for path in GENERAL_BODY_MAP if path.exists()]
    return {
        "label": point_label,
        "image_candidates": fallback_pages,
        "exact_atlas_match": False,
        "status": "general_body_map_only" if fallback_pages else "missing_reference_images",
    }


def build_pair_visual(pair_name: str) -> dict[str, Any]:
    point_a, point_b = split_pair_points(pair_name)
    point_a_visual = _point_visual(point_a)
    point_b_visual = _point_visual(point_b)

    all_images: list[str] = []
    for image in point_a_visual["image_candidates"] + point_b_visual["image_candidates"]:
        if image not in all_images:
            all_images.append(image)

    exact_pair_match = bool(point_a_visual["exact_atlas_match"] or point_b_visual["exact_atlas_match"])
    has_reference_images = bool(all_images)

    return {
        "pair_name": pair_name,
        "point_a": point_a_visual,
        "point_b": point_b_visual,
        "image_candidates": all_images,
        "has_reference_images": has_reference_images,
        "has_exact_point_match": exact_pair_match,
        "status": (
            "exact_point_atlas"
            if exact_pair_match
            else ("general_body_map_only" if has_reference_images else "missing_reference_images")
        ),
        "source_mode": (
            "manual_2024_exact_point_atlas"
            if exact_pair_match
            else ("manual_2024_general_body_map" if has_reference_images else "no_visual_reference")
        ),
    }


__all__ = ["build_pair_visual", "split_pair_points"]
