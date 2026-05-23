# SES Metrics Setup

Objetivo: medir por campana que funciona y que no con eventos de SES separados por tags.

## Lo que ya quedo listo en codigo

- `scripts/ses_warmup.py` ya puede enviar `EmailTags` a SES.
- Cada wrapper manda tags consistentes:
  - warm-up: `campaign=ses-warmup`, `stream=warmup`
  - anuncio 3 dias: `campaign=ia-announcement`, `stream=announcement`
  - anuncio full: `campaign=ia-launch-full`, `stream=announcement`
- Si `SES_CONFIGURATION_SET` esta definido, los envios ya salen etiquetados y listos para tracking por campana.

## Lo que falta activar en AWS

Necesitas crear y usar un `Configuration Set` de SES con un destino de eventos.

Minimo recomendado:

- Eventos: `SEND`, `DELIVERY`, `BOUNCE`, `COMPLAINT`, `OPEN`, `CLICK`
- Tags a usar como dimensiones:
  - `campaign`
  - `stream`

## Variables del proyecto

Agrega esto a `.env` cuando el configuration set exista:

```env
SES_CONFIGURATION_SET=holo-campaign-metrics
```

## Que metricas conviene revisar

Por campana y por dia:

- enviados
- entregados
- rebotes
- quejas
- aperturas
- clics

Y derivadas:

- delivery rate = entregados / enviados
- bounce rate = rebotes / enviados
- complaint rate = quejas / entregados
- open rate = aperturas / entregados
- click rate = clics / entregados
- CTR abierto = clics / aperturas

## Lectura recomendada

- Si una campana tiene buen open pero mal click, suele fallar oferta, CTA o mensaje.
- Si tiene mal delivery o mucho bounce, el problema es lista, reputacion o autenticacion.
- Si tiene complaint alta, el problema suele ser segmentacion, expectativa o frecuencia.

## Estado actual

Hoy el proyecto solo guarda bien:

- enviados por corrida
- fallos locales de envio

Todavia no hay reporte local de aperturas/clics/rebotes porque falta activar `SES_CONFIGURATION_SET` y el destino de eventos en AWS.
