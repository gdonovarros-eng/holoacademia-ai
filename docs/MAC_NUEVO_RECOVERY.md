# Recuperación en Mac nuevo · Holoacademia

> Si llegaste a este documento es porque tu Mac falló, lo cambiaste, o
> querés trabajar desde otra computadora. En **15 minutos** todo va a
> funcionar idéntico a como lo dejaste.

---

## Pre-requisitos

- macOS Sequoia o superior
- Cuenta Google con acceso a `gdonovarros@gmail.com`
- Acceso a la cuenta de GitHub `gdonovarros-eng`
- Conexión de red (vas a bajar ~13 GB del Drive)

---

## Paso 1 · Homebrew + herramientas básicas (3 minutos)

```bash
# Instalar Homebrew
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Herramientas que necesitás
brew install gh git python@3.11 ffmpeg

# Autenticar GitHub
gh auth login
# → GitHub.com → HTTPS → Yes (autenticar git) → Login with web browser
```

---

## Paso 2 · Google Drive Desktop (5 minutos)

1. Descargar: https://www.google.com/drive/download/
2. Instalar `GoogleDrive.dmg`
3. Iniciar sesión con `gdonovarros@gmail.com`
4. **CRÍTICO:** elegir modo **"Mirror files"** (no "Stream files")
5. Esperar a que termine el sync inicial (~10-20 min para 13 GB)

Verificar que el sync terminó:

```bash
ls "$HOME/Library/CloudStorage/GoogleDrive-gdonovarros@gmail.com/My Drive/Holoacademia/"
# Deberías ver: code/  holo_pipeline/  _DR/  docs-recovery/
```

---

## Paso 3 · Restaurar symlinks (1 minuto)

Los proyectos viven físicamente en Drive, pero todos los scripts usan
las rutas viejas (`~/Documents/New Project`, `~/Documents/holo_pipeline`).
Recrear los symlinks:

```bash
DRIVE="$HOME/Library/CloudStorage/GoogleDrive-gdonovarros@gmail.com/My Drive/Holoacademia"

ln -s "$DRIVE/code"           "$HOME/Documents/New Project"
ln -s "$DRIVE/holo_pipeline"  "$HOME/Documents/holo_pipeline"

# Verificar
ls -la ~/Documents/ | grep -E "New Project|holo_pipeline"
```

---

## Paso 4 · Restaurar entorno Python (3 minutos)

```bash
cd "$HOME/Documents/New Project"

# Crear venv
python3.11 -m venv .venv
source .venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt   # si existe
# o las que estén documentadas en docs/architecture_overview.md
```

---

## Paso 5 · Verificar todo funciona (2 minutos)

```bash
cd "$HOME/Documents/New Project"

# Git status: debería estar limpio y up to date
git status
git log --oneline -3

# FastAPI arranca
uvicorn api.main:app --reload --host 127.0.0.1 --port 8000

# Probar UI
open http://localhost:8000/rastreo
```

---

## Paso 6 · Reactivar backup diario (1 minuto)

```bash
crontab -e
# Agregar línea (3 AM todos los días):
0 3 * * * $HOME/bin/holoacademia-backup.sh >> $HOME/bin/backup.log 2>&1
```

El script de backup ya está en Drive en `_DR/scripts/`, copiar a `~/bin/`:

```bash
mkdir -p ~/bin
cp "$DRIVE/_DR/scripts/holoacademia-backup.sh" ~/bin/
chmod +x ~/bin/holoacademia-backup.sh
```

---

## Troubleshooting

### "El proyecto pesa raro" o "faltan archivos"

Drive está en modo Stream, no Mirror. Cambiar:

1. Click ícono Drive en barra de menú
2. Engranaje → Preferencias → Pestaña "Google Drive"
3. **"Mirror files"** → reiniciar Drive

### "Git dice 'corrupt object'"

Drive sincronizó `.git/` parcialmente. Recuperar desde GitHub:

```bash
cd ~/Documents/
mv "New Project" "New Project.broken"
git clone https://github.com/gdonovarros-eng/holoacademia-ai.git
mv "holoacademia-ai" "New Project"
# Re-aplicar symlink si Drive todavía tiene la versión vieja
```

### "Faltan archivos grandes (>100 MB)"

Esos archivos NO están en GitHub por límite de tamaño. Están solo en Drive.
Asegurate que el sync completó (revisa el ícono en barra de menú).

### "Aparecen archivos con ` (1)` o ` 2`"

Drive detectó conflicto entre Macs. Comparar contenido y borrar el viejo:

```bash
find ~/Documents/New\ Project -name "* (1)*" -o -name "* 2.*" 2>/dev/null
```

---

## Estructura final esperada

```
$HOME/
├── bin/
│   ├── holoacademia-backup.sh        # backup diario
│   └── holoacademia-migrate-to-drive.sh
├── Documents/
│   ├── New Project → /…/Drive/Holoacademia/code           (symlink)
│   └── holo_pipeline → /…/Drive/Holoacademia/holo_pipeline  (symlink)
└── Library/CloudStorage/GoogleDrive-gdonovarros@gmail.com/My Drive/
    └── Holoacademia/
        ├── code/                ← proyecto principal
        ├── holo_pipeline/       ← RAG + Whisper
        ├── _DR/                 ← snapshots .tar.gz diarios
        │   └── scripts/         ← copia de los scripts de mantenimiento
        └── docs-recovery/       ← este documento
```

---

## Triple respaldo (capa por capa)

| Si falla… | Tenés esto como backup |
|---|---|
| Tu Mac muere | Drive (sync cloud) + GitHub (código) |
| Drive se corrompe | GitHub + snapshots `.tar.gz` en `_DR/` |
| GitHub borra el repo | Drive completo + snapshots locales |
| Borrás algo por error | Drive guarda historial 30 días + snapshots tienen 30 días |
| Acceso a Google bloqueado | GitHub + Render tiene los assets de producción |

---

**Última actualización:** $(date +%Y-%m-%d)
**Versión de este documento:** 1.0
