#!/usr/bin/env python3
"""Genera en lote TODAS las fichas faltantes (1,296 pares).

Características:
- ✅ Resume-safe: salta las que ya existen
- ✅ Rate-limiting: respeta límite OpenAI (~40 RPM)
- ✅ Retry con backoff exponencial
- ✅ Checkpoint en _progress.json
- ✅ Pausable con Ctrl+C, continuable después
- ✅ Log de fallos en _failures.log
- ✅ Estimación de costo previa

Uso:
    python3 scripts/ficha_generator/03_generate_batch.py                    # todo
    python3 scripts/ficha_generator/03_generate_batch.py --limit 20         # primeras 20
    python3 scripts/ficha_generator/03_generate_batch.py --quality high     # alta calidad
    python3 scripts/ficha_generator/03_generate_batch.py --region Cabeza    # solo Cabeza
    python3 scripts/ficha_generator/03_generate_batch.py --dry-run          # solo mostrar plan
"""
import argparse, os, sys, json, base64, re, time, signal
from datetime import datetime
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)

from dotenv import load_dotenv
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

from openai import OpenAI
from prompt_template import build_prompt

OUTPUT_DIR = os.path.join(PROJECT_ROOT, "data", "fichas_generadas")
PROGRESS_FILE = os.path.join(OUTPUT_DIR, "_progress.json")
FAILURES_LOG = os.path.join(OUTPUT_DIR, "_failures.log")

# Costos en USD (gpt-image-1 según OpenAI 2026)
COSTS = {
    ("low",    "1024x1024"): 0.011,
    ("medium", "1024x1024"): 0.042,
    ("high",   "1024x1024"): 0.167,
    ("low",    "1536x1024"): 0.017,
    ("medium", "1536x1024"): 0.063,
    ("high",   "1536x1024"): 0.250,
    ("low",    "1024x1536"): 0.017,
    ("medium", "1024x1536"): 0.063,
    ("high",   "1024x1536"): 0.250,
}

def safe_filename(idx: int, par_name: str) -> str:
    s = re.sub(r'[^A-Za-z0-9]+', '_', par_name).strip('_')
    return f"{idx:04d}_{s[:60]}.png"

def load_progress() -> dict:
    if not os.path.exists(PROGRESS_FILE):
        return {"completed": [], "failed": [], "started": None}
    with open(PROGRESS_FILE) as f:
        return json.load(f)

def save_progress(progress: dict):
    with open(PROGRESS_FILE, "w") as f:
        json.dump(progress, f, ensure_ascii=False, indent=2)

def log_failure(par_key: str, error: str):
    with open(FAILURES_LOG, "a") as f:
        f.write(f"{datetime.now().isoformat()} | {par_key} | {error}\n")

def get_pending_pairs(region_filter: str | None = None) -> list:
    """Devuelve lista de pares sin ficha (ni en Symbelia ni en generadas)."""
    db_path = os.path.join(PROJECT_ROOT, "data", "biomagnetic_pairs_db.json")
    map_path = os.path.join(PROJECT_ROOT, "data", "fichas_mapping.json")
    clas_path = os.path.join(PROJECT_ROOT, "data", "pares_clasificacion.json")

    with open(db_path) as f:
        db = json.load(f)
    with open(map_path) as f:
        symbelia = json.load(f)
    classifications = {}
    if os.path.exists(clas_path):
        with open(clas_path) as f:
            for c in json.load(f)["clasificaciones"]:
                key = (c["region"], c["zona"], c["bloque"], c["par"])
                classifications[key] = c

    have_ficha = {(m["db_region"], m["db_zona"], m["db_bloque"], m["db_par"])
                  for m in symbelia["mappings"]}

    pending = []
    for reg in db["regiones"]:
        if region_filter and reg["nombre"] != region_filter:
            continue
        for zona in reg.get("zonas", []):
            for bloque in zona.get("bloques", []):
                for par in bloque.get("pares", []):
                    key = (reg["nombre"], zona["nombre"], bloque["nombre"], par)
                    if key not in have_ficha:
                        clf = classifications.get(key, {})
                        pending.append({
                            "region": reg["nombre"],
                            "zona": zona["nombre"],
                            "bloque": bloque["nombre"],
                            "par": par,
                            "tipo": clf.get("tipo"),
                            "patogeno": clf.get("patogeno_canonico") or clf.get("patogeno"),
                            "enfermedades": clf.get("enfermedades_reales"),
                        })
    return pending

def generate_one(client: OpenAI, pair: dict, idx: int,
                 quality: str, size: str, with_reference: bool,
                 retries: int = 3) -> tuple[bool, str]:
    """Genera una ficha. Devuelve (success, message/path)."""
    fname = safe_filename(idx, pair["par"])
    out_path = os.path.join(OUTPUT_DIR, fname)

    if os.path.exists(out_path):
        return True, f"skipped (exists)"

    prompt = build_prompt(
        par_name=pair["par"],
        region=pair["region"],
        zona=pair["zona"],
        bloque=pair["bloque"],
        tipo=pair.get("tipo"),
        patogeno=pair.get("patogeno"),
        enfermedades=pair.get("enfermedades"),
    )

    for attempt in range(retries):
        try:
            if with_reference:
                ref_path = os.path.join(PROJECT_ROOT, "data", "fichas_pares",
                                        "000_Timo_Esternon_plantilla_aprobada.png")
                with open(ref_path, "rb") as ref_file:
                    response = client.images.edit(
                        model="gpt-image-1",
                        image=ref_file,
                        prompt=prompt,
                        size=size,
                        quality=quality,
                        n=1,
                    )
            else:
                response = client.images.generate(
                    model="gpt-image-1",
                    prompt=prompt,
                    size=size,
                    quality=quality,
                    n=1,
                )
            b64 = response.data[0].b64_json
            with open(out_path, "wb") as f:
                f.write(base64.b64decode(b64))
            return True, out_path
        except Exception as e:
            err = str(e)
            # Rate limit: wait longer
            if "rate" in err.lower() or "429" in err:
                wait = 30 + (attempt * 30)
            else:
                wait = (2 ** attempt) * 5
            if attempt < retries - 1:
                print(f"   ⚠ Attempt {attempt+1}: {err[:80]}... waiting {wait}s")
                time.sleep(wait)
            else:
                return False, err

    return False, "max retries"

# Graceful interrupt
_interrupted = False
def _on_sigint(sig, frame):
    global _interrupted
    print("\n\n⏸  Interrupted. Saving progress... (Ctrl+C again to force quit)")
    _interrupted = True
signal.signal(signal.SIGINT, _on_sigint)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, help="Solo generar N fichas")
    ap.add_argument("--quality", default="medium", choices=["low","medium","high"])
    ap.add_argument("--size", default="1024x1024",
                    choices=["1024x1024","1024x1536","1536x1024"])
    ap.add_argument("--region", help="Filtrar por región (Cabeza/Tronco/etc.)")
    ap.add_argument("--with-reference", action="store_true",
                    help="Usar ficha Timo-Esternón como referencia visual")
    ap.add_argument("--rpm", type=int, default=40, help="Requests per minute target")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Cargar pendientes
    pending = get_pending_pairs(region_filter=args.region)
    total = len(pending)
    print(f"📋 Total pendientes (sin ficha): {total}")

    if args.limit:
        pending = pending[:args.limit]
        print(f"   Limitando a primeras {args.limit}")

    # Estimación de costo
    cost_per = COSTS.get((args.quality, args.size), 0.05)
    est_cost = cost_per * len(pending)
    est_time_min = (len(pending) / args.rpm)
    print(f"\n💰 Estimación:")
    print(f"   {len(pending)} fichas × ${cost_per:.3f} = ${est_cost:.2f}")
    print(f"   Tiempo a {args.rpm} RPM: ~{est_time_min:.1f} min")

    if args.dry_run:
        print(f"\n📌 Dry-run. Primeros 5 pares a generar:")
        for p in pending[:5]:
            print(f"   - [{p['region']}>{p['zona']}>{p['bloque']}] {p['par']}")
        return 0

    # Confirmar
    print(f"\n⚠ Continuar? [y/N] ", end='', flush=True)
    resp = input().strip().lower()
    if resp != 'y':
        print("Cancelado.")
        return 0

    # Cargar progress
    progress = load_progress()
    if not progress.get("started"):
        progress["started"] = datetime.now().isoformat()

    client = OpenAI()
    delay = 60.0 / args.rpm  # segundos entre llamadas

    ok_count, fail_count, skip_count = 0, 0, 0
    start = time.time()

    for i, pair in enumerate(pending):
        if _interrupted:
            break

        par_key = f"{pair['region']}|{pair['zona']}|{pair['bloque']}|{pair['par']}"
        idx = len(progress["completed"]) + ok_count + skip_count

        print(f"\n[{i+1}/{len(pending)}] {pair['par']!r}")
        print(f"   {pair['region']} > {pair['zona']} > {pair['bloque']}")
        if pair.get("tipo"):
            print(f"   {pair['tipo']} · {pair.get('patogeno','-')}")

        success, msg = generate_one(
            client, pair, idx,
            quality=args.quality, size=args.size,
            with_reference=args.with_reference
        )

        if success:
            if "skipped" in msg:
                skip_count += 1
                print(f"   ⏭ skipped")
            else:
                ok_count += 1
                progress["completed"].append(par_key)
                size_kb = os.path.getsize(msg) // 1024 if os.path.exists(msg) else 0
                print(f"   ✅ {os.path.basename(msg)} ({size_kb} KB)")
        else:
            fail_count += 1
            progress["failed"].append({"key": par_key, "error": msg, "time": datetime.now().isoformat()})
            log_failure(par_key, msg)
            print(f"   ❌ FAIL: {msg[:120]}")

        # Save progress every 10 ok
        if (ok_count + fail_count) % 10 == 0:
            save_progress(progress)

        # Rate limit delay
        time.sleep(delay)

    # Final save
    save_progress(progress)

    elapsed = time.time() - start
    print(f"\n{'='*60}")
    print(f"📊 RESUMEN")
    print(f"{'='*60}")
    print(f"   ✅ Generadas:   {ok_count}")
    print(f"   ⏭  Saltadas:    {skip_count}")
    print(f"   ❌ Fallidas:    {fail_count}")
    print(f"   ⏱  Tiempo:      {elapsed/60:.1f} min")
    if ok_count:
        print(f"   💰 Costo aprox: ${ok_count * cost_per:.2f}")
    if fail_count:
        print(f"\n   Ver fallos en: {FAILURES_LOG}")
    if _interrupted:
        print(f"\n⏸  Interrumpido. Vuelve a correr para continuar desde donde quedaste.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
