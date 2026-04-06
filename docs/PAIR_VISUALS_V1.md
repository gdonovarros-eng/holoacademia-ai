# Visuales De Pares V1

## Objetivo

Cuando el terapeuta capture un par biomagnético, el sistema debe poder devolver:

- los dos puntos anatómicos del par
- una pista de región corporal
- una o varias imágenes de referencia si existen en la biblioteca visual

---

## Archivo de motor

- [api/pair_visual_engine.py](/Users/m2/Documents/New%20project/api/pair_visual_engine.py)

---

## Regla importante

El sistema **no inventa imágenes anatómicas**.

Solo enlaza imágenes reales si se colocan en:

- [data/pair_visuals](/Users/m2/Documents/New%20project/data/pair_visuals)

Además, esta versión ya usa páginas reales exportadas del manual 2020 en:

- [data/pair_visuals/manual_2020](/Users/m2/Documents/New%20project/data/pair_visuals/manual_2020)

---

## Estructura esperada

### Imágenes por punto exacto

- `data/pair_visuals/points/<slug-del-punto>.png`

Ejemplos:

- `data/pair_visuals/points/ano.png`
- `data/pair_visuals/points/piloro.png`
- `data/pair_visuals/points/adenohipofisis.png`

### Imágenes por región

- `data/pair_visuals/regions/<region>.png`

Regiones sugeridas:

- `craneo`
- `cara`
- `cuello`
- `torax`
- `abdomen`
- `abdomen_posterior`
- `pelvis`
- `columna`
- `extremidades`
- `general`

### Vista anatómica completa

- `data/pair_visuals/full_body/front.png`
- `data/pair_visuals/full_body/back.png`

---

## Qué devuelve el motor

Por cada par:

- `point_a.label`
- `point_a.region_hint`
- `point_a.image_candidates`
- `point_b.label`
- `point_b.region_hint`
- `point_b.image_candidates`
- `image_candidates`
- `has_reference_images`
- `status`
- `source_mode`

---

## Uso práctico

Si el terapeuta captura:

- `ANO - PILORO`

el sistema puede devolver:

- punto A: `ANO`
- punto B: `PILORO`
- región sugerida: `pelvis` y `abdomen`
- imágenes exactas si existen
- o páginas reales del atlas/manual según la región corporal si aún no existe una lámina exacta del punto

---

## Alcance actual

La versión actual ya puede mostrar:

- interpretación del par
- dos puntos anatómicos
- región corporal sugerida
- láminas anatómicas regionales del manual 2020

Todavía no hace:

- coordenada exacta del punto dentro de la lámina
- recorte exacto del órgano o tejido
- mapa punto-a-punto completo por cada par

---

## Siguiente paso

Cuando exista un atlas visual más específico de pares biomagnéticos, bastará con colocarlo en:

- [data/pair_visuals](/Users/m2/Documents/New%20project/data/pair_visuals)

y el motor lo empezará a enlazar automáticamente.
