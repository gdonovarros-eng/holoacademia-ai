from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - optional dependency
    load_dotenv = None

from openai import OpenAI


BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_CHUNKS_PATH = BASE_DIR / "data" / "chunks" / "library_chunks.jsonl"
DEFAULT_OUTPUT_PATH = BASE_DIR / "data" / "embeddings" / "library_vectors.npy"
DEFAULT_MANIFEST_PATH = BASE_DIR / "data" / "embeddings" / "library_vectors_manifest.json"


def build_embedding_text(record: dict) -> str:
    parts = [
        f"Curso: {record.get('course_name', '')}",
        f"Línea: {record.get('linea', '')}",
        f"Tipo: {record.get('tipo', '')}",
        f"Fuente: {record.get('source_file', '')}",
        f"Sección: {record.get('heading', '')}",
        "",
        str(record.get("text", "")),
    ]
    return "\n".join(part for part in parts if part is not None).strip()


def load_records(chunks_path: Path) -> list[dict]:
    records = []
    with chunks_path.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            records.append(json.loads(line))
    return records


def main() -> None:
    if load_dotenv is not None:
        load_dotenv(BASE_DIR / ".env")

    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY no está configurada.")

    model = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small").strip()
    batch_size = int(os.getenv("OPENAI_EMBEDDING_BATCH_SIZE", "64"))
    chunks_path = Path(os.getenv("CHUNKS_PATH", DEFAULT_CHUNKS_PATH)).expanduser().resolve()
    output_path = Path(os.getenv("EMBEDDINGS_VECTORS_PATH", DEFAULT_OUTPUT_PATH)).expanduser().resolve()
    manifest_path = Path(os.getenv("EMBEDDINGS_MANIFEST_PATH", DEFAULT_MANIFEST_PATH)).expanduser().resolve()

    records = load_records(chunks_path)
    texts = [build_embedding_text(record) for record in records]
    client = OpenAI(api_key=api_key)

    embeddings: list[list[float]] = []
    total = len(texts)
    print(f"Generando embeddings para {total} chunks con {model}...", flush=True)

    for start in range(0, total, batch_size):
        end = min(start + batch_size, total)
        batch = texts[start:end]
        response = client.embeddings.create(model=model, input=batch)
        batch_vectors = [item.embedding for item in sorted(response.data, key=lambda item: item.index)]
        embeddings.extend(batch_vectors)
        print(f"Embeddings {start + 1}-{end} de {total}", flush=True)

    vectors = np.asarray(embeddings, dtype=np.float32)
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    norms[norms == 0.0] = 1.0
    vectors = vectors / norms

    output_path.parent.mkdir(parents=True, exist_ok=True)
    np.save(output_path, vectors)

    manifest = {
        "model": model,
        "chunks_path": str(chunks_path),
        "vectors_path": str(output_path),
        "count": int(vectors.shape[0]),
        "dimensions": int(vectors.shape[1]),
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Índice guardado en {output_path}", flush=True)
    print(f"Manifiesto guardado en {manifest_path}", flush=True)


if __name__ == "__main__":
    main()
