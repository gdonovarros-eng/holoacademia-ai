"""
Pairs interpretation service.

Loads biomagnetic_pairs_db.json and provides:
  - lookup by name (fuzzy matching)
  - batch interpretation for a list of found pairs
  - pattern summary (what the body is communicating)
"""
from __future__ import annotations

import json
import os
import re
import unicodedata
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
PAIRS_DB_PATH = ROOT / "data" / "biomagnetic_pairs_db.json"

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

PAIRS_SYSTEM_PROMPT = """
Eres el Asistente Terapéutico de Holoacademia, especialista en biomagnetismo y holobiomagnetismo.
El terapeuta ya completó el rastreo y encontró los pares biomagnéticos activos. Tu trabajo es explicarle al terapeuta qué le está comunicando el cuerpo del paciente a través de esos pares.

Reglas:
- Sé claro y concreto. Habla de lo que el cuerpo está expresando, no de diagnósticos médicos.
- Si hay varios pares, identifica el patrón que forman juntos y qué dice ese patrón.
- Usa lenguaje clínico pero accesible para el terapeuta.
- Estructura: 1) lectura de cada par, 2) patrón general que forman, 3) qué le conviene explorar con el paciente.
- No diagnostiques enfermedades ni sustituyas atención médica.
""".strip()


def _normalize(text: str) -> str:
    n = unicodedata.normalize("NFKD", text or "")
    n = n.encode("ascii", "ignore").decode("ascii").lower()
    n = re.sub(r"[^a-z0-9]+", " ", n).strip()
    return n


def _make_search_id(text: str) -> str:
    return re.sub(r"\s+", "_", _normalize(text))


class PairsDB:
    def __init__(self) -> None:
        self._pairs: list[dict] = []
        self._index: dict[str, dict] = {}  # normalized_id → pair
        self._load()

    def _load(self) -> None:
        if not PAIRS_DB_PATH.exists():
            return
        try:
            data = json.loads(PAIRS_DB_PATH.read_text(encoding="utf-8"))
            self._pairs = data.get("pairs", [])
            for p in self._pairs:
                key = _make_search_id(p["nombre"])
                self._index[key] = p
                # Also index by parts (ORGAN1_ORGAN2 ignoring direction/invertido)
                parts = re.split(r"[-–]", p["nombre"])
                if len(parts) >= 2:
                    a = _make_search_id(parts[0])
                    b = _make_search_id(" ".join(parts[1:]))
                    alt = f"{a}_{b}"
                    if alt not in self._index:
                        self._index[alt] = p
        except Exception:
            pass

    def lookup(self, name: str) -> dict | None:
        """Find a pair by name (exact or fuzzy)."""
        key = _make_search_id(name)
        if key in self._index:
            return self._index[key]

        # Try partial match: find pairs where key is a substring of index key or vice versa
        best: dict | None = None
        best_score = 0
        name_tokens = set(key.split("_")) - {"", "derecho", "izquierdo", "invertido"}

        for idx_key, pair in self._index.items():
            idx_tokens = set(idx_key.split("_")) - {"", "derecho", "izquierdo", "invertido"}
            if not name_tokens or not idx_tokens:
                continue
            overlap = name_tokens & idx_tokens
            score = len(overlap) / max(len(name_tokens), len(idx_tokens))
            if score > best_score and score >= 0.6:
                best_score = score
                best = pair

        return best

    @property
    def all_pairs(self) -> list[dict]:
        return self._pairs


_db: PairsDB | None = None


def get_db() -> PairsDB:
    global _db
    if _db is None:
        _db = PairsDB()
    return _db


# ── LLM client ────────────────────────────────────────────────────────────────

class PairsLLMClient:
    def __init__(self) -> None:
        use_model = os.getenv("THERAPEUTIC_ASSISTANT_USE_MODEL", "false").strip().lower() in {"1", "true", "yes", "on"}
        provider = os.getenv("LLM_PROVIDER", "groq").strip().lower()
        if provider == "groq":
            api_key = os.getenv("GROQ_API_KEY", "").strip()
            base_url = os.getenv("LLM_BASE_URL", "https://api.groq.com/openai/v1").strip()
            model = os.getenv("OPENAI_MODEL", "openai/gpt-oss-20b").strip()
        else:
            api_key = os.getenv("OPENAI_API_KEY", "").strip()
            base_url = os.getenv("LLM_BASE_URL", "").strip() or None
            model = os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip()
        self.model = model
        self.enabled = bool(use_model and api_key and OpenAI is not None)
        self.client = None
        if self.enabled:
            kwargs: dict[str, Any] = {"api_key": api_key}
            if base_url:
                kwargs["base_url"] = base_url
            self.client = OpenAI(**kwargs)

    def interpret(self, pairs_summary: str, case_notes: str) -> str:
        if not self.enabled or self.client is None:
            return ""
        prompt = (
            f"Pares biomagnéticos encontrados en el rastreo:\n{pairs_summary}\n\n"
            + (f"Notas del caso: {case_notes}\n\n" if case_notes else "")
            + "Explica qué le está comunicando el cuerpo del paciente a través de estos pares. "
            "Estructura: 1) lectura breve de cada par, 2) patrón general que forman juntos, "
            "3) qué conviene explorar con el paciente."
        )
        try:
            resp = self.client.responses.create(
                model=self.model,
                instructions=PAIRS_SYSTEM_PROMPT,
                input=prompt,
                max_output_tokens=int(os.getenv("THERAPEUTIC_ASSISTANT_MAX_TOKENS", "900")),
                timeout=float(os.getenv("THERAPEUTIC_ASSISTANT_TIMEOUT_SECONDS", "25")),
            )
            text = getattr(resp, "output_text", "") or ""
            if not text.strip():
                for item in getattr(resp, "output", []) or []:
                    for content in getattr(item, "content", []) or []:
                        value = getattr(content, "text", None)
                        if value:
                            text += value
            return text.strip()
        except Exception:
            return ""


_llm: PairsLLMClient | None = None


def get_llm() -> PairsLLMClient:
    global _llm
    if _llm is None:
        _llm = PairsLLMClient()
    return _llm


# ── fallback pattern builder (no LLM) ────────────────────────────────────────

_TIPO_LABELS = {
    "hongo": "presencia de hongo",
    "bacteria": "presencia de bacteria",
    "virus": "presencia de virus",
    "parasito": "presencia de parásito",
    "emocional": "bloqueo emocional",
    "disfuncional": "disfunción orgánica",
    "especial": "par especial de corrección",
    "reservorio": "reservorio activo",
    "desconocido": "afectación no clasificada",
}

def _build_fallback_pattern(interpretations: list[dict]) -> str:
    if not interpretations:
        return "No se encontraron pares reconocidos en la base de datos."

    sistemas: dict[str, int] = {}
    tipos: dict[str, int] = {}
    for item in interpretations:
        for s in item.get("sistemas_afectados", []):
            sistemas[s] = sistemas.get(s, 0) + 1
        t = item.get("tipo", "")
        if t:
            tipos[t] = tipos.get(t, 0) + 1

    dominant_sistema = max(sistemas, key=sistemas.get) if sistemas else None
    dominant_tipo = max(tipos, key=tipos.get) if tipos else None

    parts = []
    if dominant_sistema:
        parts.append(f"El sistema más comprometido es el {dominant_sistema}.")
    if dominant_tipo:
        label = _TIPO_LABELS.get(dominant_tipo, dominant_tipo)
        parts.append(f"El patrón predominante indica {label}.")
    if len(interpretations) >= 3:
        parts.append("Con varios pares activos, conviene explorar el contexto emocional del paciente para identificar el conflicto que sostiene el cuadro.")
    elif len(interpretations) == 1:
        cond = interpretations[0].get("condiciones", "")
        if cond:
            parts.append(f"El cuerpo señala: {cond[:200]}")

    return " ".join(parts) if parts else "Los pares encontrados muestran actividad que conviene explorar con el paciente."


# ── main service function ─────────────────────────────────────────────────────

def interpret_found_pairs(
    pares_encontrados: list[str],
    notas: str = "",
) -> dict[str, Any]:
    db = get_db()
    llm = get_llm()

    interpretations: list[dict] = []
    not_found: list[str] = []

    for name in pares_encontrados:
        name = (name or "").strip()
        if not name:
            continue
        pair = db.lookup(name)
        if pair:
            interpretations.append({
                "par_ingresado": name,
                "par_encontrado": pair["nombre"],
                "tipo": pair["tipo"],
                "tipo_raw": pair.get("tipo_raw", ""),
                "condiciones": pair.get("condiciones", ""),
                "significado_emocional": pair.get("significado_emocional", ""),
                "sistemas_afectados": pair.get("sistemas_afectados", []),
            })
        else:
            not_found.append(name)

    # Build LLM input summary
    pairs_summary_lines = []
    for item in interpretations:
        line = f"- {item['par_encontrado']} [{item['tipo']}]: {item['condiciones'][:180]}"
        if item["significado_emocional"]:
            line += f" | Emocional: {item['significado_emocional'][:120]}"
        pairs_summary_lines.append(line)
    pairs_summary = "\n".join(pairs_summary_lines)

    # Generate pattern narrative
    patron_general = ""
    if interpretations:
        patron_general = llm.interpret(pairs_summary, notas)
    if not patron_general:
        patron_general = _build_fallback_pattern(interpretations)

    # Aggregate systems and types
    all_sistemas: list[str] = []
    all_tipos: list[str] = []
    for item in interpretations:
        all_sistemas.extend(item["sistemas_afectados"])
        if item["tipo"]:
            all_tipos.append(item["tipo"])

    sistemas_counter: dict[str, int] = {}
    for s in all_sistemas:
        sistemas_counter[s] = sistemas_counter.get(s, 0) + 1
    sistemas_dominantes = sorted(sistemas_counter, key=sistemas_counter.get, reverse=True)[:4]  # type: ignore[arg-type]

    tipos_presentes = list(dict.fromkeys(all_tipos))

    return {
        "interpretaciones": interpretations,
        "patron_general": patron_general,
        "sistemas_dominantes": sistemas_dominantes,
        "tipos_presentes": tipos_presentes,
        "encontrados": len(interpretations),
        "no_encontrados": not_found,
    }
