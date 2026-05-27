# Tarot Thoth — uso personal local

⚠️ **El deck Thoth (Crowley/Harris, 1969) está bajo copyright vigente** hasta aproximadamente 2042
(Lady Frieda Harris murió en 1962; los términos legales varían por jurisdicción).

Por esta razón **las imágenes NO se versionan en este repositorio público**
(`.gitignore` las excluye explícitamente).

## Para usar el deck Thoth en tu instancia local

1. Conseguí las imágenes de tu deck Thoth (compra digital, scan personal, etc.)
2. Copialas a esta carpeta con la siguiente convención de nombres:

### Arcanos Mayores (22)

```
00_loco.jpg           ← El Loco / The Fool
01_mago.jpg           ← El Mago / Magus
02_sacerdotisa.jpg    ← La Sacerdotisa / The Priestess
03_emperatriz.jpg     ← La Emperatriz / The Empress
04_emperador.jpg      ← El Emperador / The Emperor
05_sumo_sacerdote.jpg ← El Sumo Sacerdote / The Hierophant
06_amantes.jpg        ← Los Amantes / The Lovers
07_carro.jpg          ← El Carro / The Chariot
08_justicia.jpg       ← La Justicia / Adjustment (en Thoth)
09_ermitano.jpg       ← El Ermitaño / The Hermit
10_rueda.jpg          ← La Rueda / Fortune
11_fuerza.jpg         ← La Fuerza / Lust (en Thoth)
12_colgado.jpg        ← El Colgado / The Hanged Man
13_muerte.jpg         ← La Muerte / Death
14_templanza.jpg      ← La Templanza / Art (en Thoth)
15_diablo.jpg         ← El Diablo / The Devil
16_torre.jpg          ← La Torre / The Tower
17_estrella.jpg       ← La Estrella / The Star
18_luna.jpg           ← La Luna / The Moon
19_sol.jpg            ← El Sol / The Sun
20_juicio.jpg         ← El Juicio / Aeon (en Thoth)
21_mundo.jpg          ← El Mundo / Universe (en Thoth)
```

> **Nota**: Crowley invirtió 8/11 respecto a Marsella tradicional. En Thoth:
> "Adjustment" = nuestro `08_justicia`, "Lust" = nuestro `11_fuerza`.

### Arcanos Menores (56)

Patrón: `{palo}_{NN}_{rango}.jpg`

- **Palos**: `bastos`, `copas`, `espadas`, `pentaculos`
- **Rangos** (Crowley usa Princess/Prince/Queen/Knight):
  - `01_as` (Ace)
  - `02_dos`, `03_tres`, ..., `10_diez`
  - `11_paje` ← Princess (Crowley)
  - `12_caballero` ← Prince (Crowley)
  - `13_reina` ← Queen
  - `14_rey` ← Knight (Crowley) — en Thoth el Knight es el más maduro

Ejemplos:
```
bastos_01_as.jpg
bastos_05_cinco.jpg
bastos_11_paje.jpg     ← Princess of Wands
bastos_12_caballero.jpg ← Prince of Wands
bastos_13_reina.jpg
bastos_14_rey.jpg      ← Knight of Wands
copas_01_as.jpg
...
pentaculos_14_rey.jpg
```

## Auto-detección

Una vez que copies los archivos, el backend los autodetecta vía
`GET /tarot/decks/scan`. No requiere reiniciar el servidor — solo
recargar la pestaña Referencia o Lectura en el navegador.

## Deploy a Render / producción

Si despliegas a un servidor público (Render, Vercel, etc.) y querés que el
deck Thoth funcione allí, tenés que subir las imágenes manualmente al
volumen persistente del servidor. **Nunca incluirlas en el commit/repo**
porque eso constituiría infracción de copyright.

## Estatus actual

- ✅ Frontend: detecta y muestra Thoth si hay archivos
- ✅ Backend: endpoint `/tarot/decks/scan` autoescanea
- ✅ `.gitignore`: excluye `*.jpg/png/jpeg/webp` de este folder
- 🔒 Las imágenes solo viven en tu Mac local
