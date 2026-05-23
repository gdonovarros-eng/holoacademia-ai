# SES Warm-Up

Utilidad para hacer warm-up diario con Amazon SES usando listas CSV con columna `email`.

## Archivos

- `scripts/ses_warmup.py`: envia la siguiente tanda del dia y guarda avance.
- `data/ses_warmup_plan.json`: plan diario de volumen.
- `data/ses_warmup_state.json`: estado acumulado del warm-up.
- `data/ses_warmup_runs.jsonl`: bitacora de corridas.
- `data/ses_warmup_failures.csv`: fallos por direccion.
- `data/ses_suppression.csv`: exclusiones manuales con columna `email`.

## Variables de entorno

Puedes ponerlas en `.env`:

```env
AWS_REGION=us-east-1
SES_TRANSPORT=smtp
SES_FROM_NAME=Holoacademia
SES_FROM_EMAIL=tu-remitente@tudominio.com
SES_REPLY_TO=respuesta@tudominio.com
SES_CONFIGURATION_SET=tu-configuration-set
SES_LIST_MANAGEMENT_TOPIC=
SES_SMTP_HOST=email-smtp.us-east-1.amazonaws.com
SES_SMTP_PORT=587
SES_SMTP_USERNAME=tu_usuario_smtp
SES_SMTP_PASSWORD=tu_password_smtp
EMAIL_BRAND_NAME=Holoacademia
EMAIL_SUPPORT_EMAIL=soporte@tudominio.com
EMAIL_UNSUBSCRIBE_URL=https://www.tudominio.com/baja
```

Si prefieres usar la API de SES en lugar de SMTP, cambia `SES_TRANSPORT=api`.
La plantilla reemplaza automaticamente `{{BRAND_NAME}}`, `{{SUPPORT_EMAIL}}`, `{{FROM_EMAIL}}` y `{{UNSUBSCRIBE_URL}}` usando estas variables.
`SES_FROM_NAME` controla el nombre visible del remitente, por ejemplo `Holoacademia`.

## Dependencias

```bash
./.venv/bin/pip install -r requirements.txt
```

## Dry-run

Muestra la siguiente tanda sin enviar ni avanzar el cursor:

```bash
./.venv/bin/python scripts/ses_warmup.py \
  --list-dir "/Users/m2/Desktop/base de datos/amazon lista unificada" \
  --subject "Asunto de prueba" \
  --text "Hola, este es un mensaje de prueba."
```

El dry-run valida asunto, remitente y configuracion SMTP, pero no intenta conectarse al servidor hasta que uses `--execute`.

## Envio real

Atajo con las plantillas base del proyecto:

```bash
./scripts/run_ses_warmup.sh
```

Con archivos de contenido:

```bash
./.venv/bin/python scripts/ses_warmup.py \
  --list-dir "/Users/m2/Desktop/base de datos/amazon lista unificada" \
  --subject-file "/ruta/subject.txt" \
  --html-file "/ruta/body.html" \
  --text-file "/ruta/body.txt" \
  --execute
```

Con contenido directo:

```bash
./.venv/bin/python scripts/ses_warmup.py \
  --list-dir "/Users/m2/Desktop/base de datos/amazon lista unificada" \
  --subject "Tu asunto" \
  --html "<p>Tu mensaje</p>" \
  --text "Tu mensaje" \
  --execute
```

## Como avanza

- Toma la lista completa de `1.csv`, `2.csv`, `3.csv`, etc.
- Excluye direcciones de `data/ses_suppression.csv` si existe.
- Usa el siguiente limite del plan diario.
- Guarda el cursor para continuar en la siguiente corrida.
- Si ya corrio hoy, no repite salvo que uses `--force`.
- La idea es revisar metricas cada dia antes de soltar el siguiente tramo.

## Plan por defecto

```json
[10, 50, 100, 200, 350, 600, 900, 1300, 1800, 2500, 3500, 5000, 7000, 9000, 11500, 14500, 18000, 22000, 23000, 24739]
```

Despues del dia 20, el script se pausa automaticamente. Este plan cubre `146,049` contactos con crecimiento ascendente, subida mas suave al inicio y cierre manual al terminar.

## Revision diaria sugerida

Antes de pasar al siguiente dia, conviene revisar al menos:

- entregas y rebotes del dia
- quejas por spam
- aperturas y clics
- respuestas reales
- si hubo caida a spam, promociones o alertas nuevas en Gmail/Postmaster

Si un dia sale mal, lo ideal es pausar y no avanzar automaticamente al siguiente volumen.

## Gate de escala

Antes de dejar correr cada siguiente tramo grande, revisa al menos esto:

- Open rate interno arriba de `35%` como referencia, pero no como unica senal.
- CTR arriba de `3%` a `5%`.
- Respuestas reales.
- Rebotes bajos.
- Quejas por spam muy bajas.
- Spam rate en Gmail Postmaster idealmente por debajo de `0.10%` y nunca `0.30%` o mas.

Google recomienda mantener el spam rate por debajo de `0.10%` y evitar llegar a `0.30%` o mas. Google tambien aclara que no puede verificar la precision de open rates de terceros:
- [Email sender guidelines](https://support.google.com/a/answer/81126?hl=en-na)

Por eso, la apertura sirve como senal interna, pero conviene tomar mas peso de clics, respuestas, quejas y spam rate.
