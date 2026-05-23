#!/usr/bin/env python3
import json, re, unicodedata, sys
from collections import Counter, defaultdict

print("Iniciando diagnóstico...", flush=True)

with open("data/biomagnetic_pairs_db.json") as f:
    db = json.load(f)

def _norm(s):
    s = unicodedata.normalize("NFC", s.strip())
    s = re.sub(r'\s+', ' ', s)
    return s.lower()

all_pares = []
for reg in db["regiones"]:
    rn = reg["nombre"]
    for zona in reg.get("zonas", []):
        zn = zona["nombre"]
        for bloque in zona.get("bloques", []):
            bn = bloque["nombre"]
            for p in bloque.get("pares", []):
                all_pares.append((rn, zn, bn, p))

print(f"Total pares: {len(all_pares)}", flush=True)

# 1. Concatenated names (lowercase immediately followed by uppercase: "Cisurade")
concat = [(r,z,b,p) for (r,z,b,p) in all_pares if re.search(r'[a-záéíóúüñ][A-ZÁÉÍÓÚÜÑ]', p)]
print(f"\n=== CONCATENADOS (falta espacio): {len(concat)} ===", flush=True)
for r,z,b,p in concat:
    print(f"  [{r}>{z}>{b}] {p!r}", flush=True)

# 2. All-caps with odd internal space (like "PÁNCRE AS")
split_w = [(r,z,b,p) for (r,z,b,p) in all_pares
           if re.search(r'[A-ZÁÉÍÓÚÜÑ]{2,} [A-ZÁÉÍÓÚÜÑ]', p)]
print(f"\n=== PALABRAS PARTIDAS (espacio interno en mayúsculas): {len(split_w)} ===", flush=True)
for r,z,b,p in split_w:
    print(f"  [{r}>{z}>{b}] {p!r}", flush=True)

# 3. Intra-bloque duplicates
print(f"\n=== DUPLICADOS DENTRO DEL MISMO BLOQUE ===", flush=True)
intra_dup = 0
for reg in db["regiones"]:
    for zona in reg.get("zonas", []):
        for bloque in zona.get("bloques", []):
            pares = bloque.get("pares", [])
            norms = [_norm(p) for p in pares]
            c = Counter(norms)
            for k,v in c.items():
                if v > 1:
                    intra_dup += 1
                    originals = [p for p in pares if _norm(p) == k]
                    print(f"  [{reg['nombre']}>{zona['nombre']}>{bloque['nombre']}] x{v}: {originals}", flush=True)
print(f"  Total grupos duplicados intra-bloque: {intra_dup}", flush=True)

# 4. Cross-location duplicates
norm_locs = defaultdict(list)
for r,z,b,p in all_pares:
    norm_locs[_norm(p)].append((r,z,b,p))
cross = {k:v for k,v in norm_locs.items() if len(v) > 1}
print(f"\n=== DUPLICADOS ENTRE DISTINTAS UBICACIONES: {len(cross)} grupos ===", flush=True)
for k,locs in list(cross.items()):
    print(f"  norm={k!r}", flush=True)
    for r,z,b,p in locs:
        print(f"    [{r}>{z}>{b}] {p!r}", flush=True)

print("\nDiagnóstico completo.", flush=True)
