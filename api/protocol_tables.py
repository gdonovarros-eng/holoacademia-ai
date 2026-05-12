"""
Tablas de conflictología del Método Lavín por sistema.
Se inyectan en el prompt del terapeuta cuando se identifica el sistema a trabajar.
"""
from __future__ import annotations
import re
from typing import Optional

# Patrones que indican que "mama" se usa como "madre" (posesivo personal),
# no como síntoma mamario. Solo excluimos posesivos: "su mama", "mi mama", "tu mama".
# "la mama" y "una mama" SÍ pueden ser síntoma → no se neutralizan.
_MADRE_PATTERN = re.compile(
    r'\b(su|mi|tu)\s+mam[aá]\b',
    re.IGNORECASE,
)

# Marcadores de alta confianza: siempre son narrativa independientemente de la longitud.
_STRONG_NARRATIVE = [
    "el paciente", "la paciente", "mi paciente",
    "su papa", "su papá", "su padre", "su madre",
    "el dice", "ella dice", "me dice", "me dijo",
    "refiere que", "cuenta que",
    "le marcó", "le marco", "le dijo", "le dijeron",
    "habia fallecido", "había fallecido",
]

# Marcadores de narrativa que requieren mensaje largo (≥ 45 chars) para evitar falsos positivos.
NARRATIVE_MARKERS = [
    "dice que", "me cuenta", "su esposo", "su esposa",
    "siente que", "el estaba", "ella estaba", "él estaba",
    "cuando el", "cuando ella", "su hijo", "su hija", "su pareja",
    "tenia miedo", "tenía miedo", "se fue", "no pudo",
    "queria", "quería",
]

# ── Tablas de conflictos por sistema ─────────────────────────────────────────

CONFLICTOS = {

    # ══════════════════════════════════════════════════════════════════
    "respiratorio": {
        "titulo": "CONFLICTOLOGÍA RESPIRATORIA (95 conflictos)",
        "subsistemas": {
            "NASAL": [
                ('1', 'Pestilencia', '"Algo huele mal"'),
                ('2', 'Impotencia para eliminar un olor', '"No puedo evitar oler a esa persona/lugar"'),
                ('3', 'Sospecha', '"Alguien conspira en mi contra"'),
                ('4', 'Presentimiento', '"Siento que algo malo va a suceder"'),
                ('5', 'Amenaza invisible', '"Alguien desea agredirme aunque no sé de dónde viene"'),
                ('1', 'Separación + peligro', '"En el momento crítico no estás"'),
                ('2', 'Relación tensa', '"Alguien cercano me desagrada constantemente"'),
                ('3', 'Deseo de separación del exterior', '"Necesito recuperarme en soledad"'),
                ('4', 'Presión', '"No sé cómo adaptarme a esta nueva situación estresante"'),
                ('5', 'Dirección', '"No sé cómo o hacia dónde orientarme"'),
                ('1', 'Dirección equivocada', '"Transito en el camino incorrecto"'),
                ('2', 'Deseo de aumentar el contacto con alguien ausente', '"Extraño el intercambio con el que ya no está"'),
                ('3', 'Miedo a la curación imposible', '"Siento que no me voy a curar"'),
                ('4', 'Angustia', '"Hay algo que no sé cómo resolver"'),
                ('5', 'Miedo a la sangre', '"Ver sangre me provoca malestar"'),
                ('1', 'Rechazo ante una presencia invasora', '"No soporto que alguien invada mi territorio"'),
                ('2', 'Territorial familiar', '"Un familiar me invade, lo necesito fuera"'),
                ('3', 'Miedo frontal', '"Algo/alguien frente a mí me aterroriza"'),
                ('4', 'Miedo a sentir dolor', '"Me aterra el sufrimiento"'),
                ('5', 'Miedo al futuro', '"Siento que vienen problemas"'),
                ('1', 'Miedo a la amenaza incomprensible', '"Algo metafísico/sobrenatural me lastimará"'),
            ],
            "LARÍNGEA": [
                ('1', 'Expresión', '"No puedo hablar/ser/comunicar lo que soy"'),
                ('2', 'Prohibición de la expresión', '"Tengo que callar para sobrevivir"'),
                ('3', 'Secreto', '"Hay una verdad que no puedo revelar"'),
                ('4', 'Timidez', '"Me cuesta trabajo conectar/vincularme"'),
                ('5', 'Mensaje no entregado', '"Necesito contar esto pero no puedo"'),
                ('1', 'Comunicación excesiva', '"Hablé de más y provoqué consecuencias indeseables"'),
                ('2', 'Miedo cerval', '"Algo/alguien me provoca un pánico repentino"'),
                ('3', 'Grito suprimido', '"No pude gritar en el momento"'),
                ('4', 'Impotencia + pánico', '"No pude hacer nada ante el terror"'),
                ('5', 'Miedo a responder un ataque', '"Si me defiendo algo malo pasará"'),
                ('1', 'Agresión', '"Algo me ha hecho sentir lastimado"'),
            ],
            "TRAQUEAL": [
                ('1', 'Miedo frontal + impotencia', '"No me puedo mover/actuar ante el terror frente a mí"'),
                ('2', 'Impotencia de no poder tomar el espacio para vivir', '"Me es prohibido ocupar mi lugar esencial"'),
                ('3', 'Separación + asfixia', '"Perderte me deja sin aliento"'),
            ],
            "BRONQUIAL": [
                ('1', 'Miedo en el territorio', '"Algo me hace sentir aterrado/vulnerable en mi espacio vital"'),
                ('2', 'Amenaza en el territorio', '"Algo que no sé dónde está, viene hacia mi espacio vital"'),
                ('3', 'Miedo frontal en el territorio', '"Mi adversario está frente a mí, en mi lugar vital"'),
                ('4', 'Miedo a perder contacto con mi espacio', '"Algo/alguien me aleja de mi espacio vital"'),
                ('5', 'Miedo a no poder reaccionar', '"Me siento impotente ante el ataque o la huida"'),
                ('1', 'Amenaza por pérdida de territorio', '"Algo/alguien me quiere despojar de mi espacio vital"'),
                ('2', 'Injusticia + resentimiento en el territorio', '"Estoy enojado por algo injusto en mi espacio vital"'),
                ('3', 'Amenaza dentro de la relación social', '"Algo/alguien amenaza mi intercambio afectivo"'),
                ('4', 'Invasión en el territorio', '"Alguien rompe mi armonía, dentro de mi espacio vital"'),
                ('5', 'Asfixia', '"Algo/alguien no me deja respirar, ser"'),
                ('1', 'Intolerancia', '"Quiero expulsar algo/alguien que no soporto"'),
                ('2', 'Obstrucción', '"Hay una situación imposible de resolver"'),
                ('3', 'Obstrucción impedida', '"No puedo permitir que esta amenaza entre en mí"'),
                ('4', 'Oposición estática', '"Estoy en contra de algo/alguien que no cederá"'),
                ('5', 'Toxicidad', '"El ambiente que respiro es venenoso, hostil"'),
                ('1', 'Insulto', '"Me agredieron verbalmente y es injusto"'),
                ('2', 'Aliento insuficiente', '"No es posible descansar, recuperarme"'),
                ('3', 'Del último aliento', '"Necesito aferrarme a mi último residuo de fuerza"'),
                ('4', 'Libertad impedida', '"No puedo ser/hacer lo que soy/quiero"'),
                ('5', 'Obligación', '"Estoy sumergido en responsabilidades"'),
                ('1', 'Financiero', '"Estoy muy presionado en tema de dinero"'),
                ('2', 'Ingestión', '"No quiero tragarme esta sustancia"'),
                ('3', 'Sometimiento', '"Me siento subyugado ante una autoridad"'),
                ('4', 'Autoafirmación', '"No quiero molestar con mi presencia"'),
            ],
            "ALVEOLAR": [
                ('1', 'Miedo a la muerte por hipoxia', '"Siento que no puedo respirar"'),
                ('2', 'Miedo a la muerte', '"Siento que me voy a morir"'),
                ('3', 'Conflicto de muerte', '"Estuve a punto de morir"'),
                ('4', 'Hipoxia', '"Siento que me sofoco"'),
                ('5', 'Intercambio', '"Ya no hay muestras de afecto con alguien"'),
                ('1', 'Existencial profundo', '"No sé cuál es mi razón de vivir"'),
                ('2', 'Tristeza', '"No sé cómo salir de esta emoción"'),
                ('3', 'Duelo bloqueado', '"No sé cómo superar la pérdida de alguien"'),
                ('4', 'Soledad', '"No hay nadie para mí"'),
            ],
            "DIAFRAGMÁTICA": [
                ('1', 'Vivo/Muerto', '"Me quiero morir"'),
                ('2', 'Vulnerabilidad', '"Necesito defenderme"'),
                ('3', 'Sobrevivencia + impotencia', '"Siento que no podré sobrevivir"'),
            ],
            "GRIPAL": [
                ('1', 'Pelea dentro del territorio', '"Riña con alguien que comparte mi espacio"'),
                ('2', 'Pelea dentro del territorio + necesidad de calor', '"Tengo una riña, y necesito cariño"'),
                ('3', 'Amor/odio', '"No te soporto pero no puedo vivir sin ti"'),
            ],
            "TOS": [
                ('1', 'Rechazo', '"No soporto la presencia, opinión o forma de ser de alguien"'),
            ],
            "ASMÁTICA": [
                ('1', 'Enojo interiorizado', '"Algo me molesta mucho pero no lo voy a hacer notar"'),
                ('2', 'Separación del territorio', '"Estoy lejos de mi espacio vital"'),
                ('3', 'Autoafirmación + impotencia', '"Quiero hacer notar mi presencia, pero no tengo derecho"'),
            ],
            "APNEA": [
                ('1', 'Camuflaje de defunción', '"Tengo que aparentar estar muerto para sobrevivir"'),
            ],
            "TABAQUISTA": [
                ('1', 'Opresión', '"Mi ambiente me limita"'),
                ('2', 'Fase oral', '"No pude conocer el mundo a través de la boca"'),
                ('3', 'Destete', '"No me amamantaron lo suficiente"'),
            ],
            "TRANSGENERACIONAL": [
                ('1', 'Memoria fetal de cordón en cuello', ''),
                ('2', 'Yaciente', ''),
                ('3', 'Memoria de secreto', ''),
                ('4', 'Memoria de ambiente tóxico', ''),
                ('5', 'Memoria de asfixia virtual (ambiente opresivo)', ''),
                ('1', 'Memoria de ahogo (Agua)', ''),
                ('2', 'Memoria de asfixia (Gas)', ''),
                ('3', 'Memoria de incendio (Humo)', ''),
                ('4', 'Memoria de silicosis (Partículas)', ''),
                ('5', 'Memoria de estrangulamiento (Mecánico)', ''),
                ('1', 'Memoria de decapitación/degüello (Herida)', ''),
                ('2', 'Memoria de suicidio (Impidiendo la respiración)', ''),
                ('3', 'Memoria de sepultura en vida', ''),
            ],
        }
    },

    # ══════════════════════════════════════════════════════════════════
    "digestivo": {
        "titulo": "CONFLICTOLOGÍA DIGESTIVA (200 conflictos)",
        "subsistemas": {
            "BUCAL": [
                ('1', 'Respuesta ante la injuria', '"No puedo responder ante el insulto"'),
                ('2', 'Pequeño conflicto de cochinada', '"Me han herido levemente, y no respondí"'),
                ('3', 'Bocado no atrapado', '"No puedo alimentarme / captar lo que deseo"'),
                ('4', 'Pérdida de contacto con el protector', '"Ya no he hablado con mi padre"'),
                ('5', 'Alimento tóxico', '"Vivo alimentándome de sufrimiento"'),
                ('1', 'Palabra contenida', '"Tengo algo que decir pero no puedo"'),
                ('2', 'Nudo en la garganta', '"Algo se me quedó atravesado en la garganta"'),
                ('3', 'Discurso distorsionado', '"Tengo que aclarar lo que dije"'),
                ('4', 'Bocado venenoso anticipado', '"Tengo que tragarme algo que podría envenenarme"'),
                ('5', 'Traición oral', '"Me prometió algo y lo rompió"'),
                ('1', 'Bocado envenenado', '"Me quieren envenenar a través de la alimentación"'),
                ('2', 'Bocado arrebatado', '"Se van a quedar con lo que necesito"'),
                ('3', 'Rencor ante la pérdida de bocado', '"No me dieron lo que me correspondía"'),
                ('4', 'Bocado demasiado grande para tragar', '"No me puedo tragar este problema"'),
                ('5', 'Bocado que puede envenenar', '"Tengo miedo de tragarme lo que me dan"'),
                ('1', 'Conflicto dental', '"Me quieren destituir del rol de cazador, defensor"'),
                ('2', 'Bocado encallado', '"No puedo atrapar lo que me falta"'),
                ('3', 'Conflicto de las glándulas salivares', '"Tengo miedo de que llegue o se vaya el bocado"'),
                ('4', 'Memoria de veneno materno', '"La leche de mi madre me envenenó"'),
                ('5', 'Memoria de mordedura', '"Fui atacado en mis primeras defensas"'),
                ('1', 'Lingual', '"No puedo expresar nada de lo que siento"'),
                ('2', 'Conflicto de aprendizaje', '"No quiero o no puedo aceptar los conocimientos"'),
            ],
            "ESTOMACAL": [
                ('1', 'Bocado indigerible', '"No puedo asimilar lo que me pasó"'),
                ('2', 'Rabia ante lo indigesto', '"Me da mucha rabia no poder superar esto"'),
                ('3', 'Bocado envenenado', '"La persona / situación me intoxicó el estómago"'),
                ('4', 'No poder soltar lo indigesto', '"Me aferro a lo que no pude digerir"'),
                ('5', 'Acumulación indigesta', '"Todo lo que vivo me resulta difícil de procesar"'),
                ('1', 'Bocado indigesto transgeneracional', '"Hay una historia familiar que no puedo digerir"'),
                ('2', 'Bocado indigerible + impotencia', '"No puedo digerir lo que me pasó y no puedo hacer nada"'),
                ('3', 'Contrariedad inesperada', '"No esperaba que esto sucediera"'),
                ('4', 'Angustia de la identidad', '"No sé quién soy en este entorno"'),
                ('5', 'Miedo a no nutrirse', '"Tengo miedo de que no me alimenten lo suficiente"'),
                ('1', 'Conflicto del cazador defraudado', '"Atrape el bocado pero lo perdí"'),
                ('2', 'Contrariedad feroz', '"Me han atacado o defraudado de la peor manera"'),
                ('3', 'Conflicto de contrariedad + traición', '"Alguien de confianza me traicionó"'),
                ('4', 'Bocado que se va', '"No puedo retener lo que necesito"'),
                ('5', 'Contrariedad + injusticia', '"Me hicieron algo injusto y no puedo reponerme"'),
                ('1', 'Contrariedad familiar intensa', '"Alguien de la familia me ha hecho un daño grave"'),
                ('2', 'Contrariedad ante el miedo', '"Me paraliza esta situación injusta"'),
                ('3', 'Bocado arrebatado + injusticia', '"Me quitaron lo que era mío injustamente"'),
                ('4', 'Defraudación financiera', '"Me quitaron mi dinero, mi sustento"'),
                ('5', 'Contrariedad + culpa', '"Cometí algo imperdonable"'),
                ('1', 'Miedo a perder el bocado', '"Siento que perderé lo que tengo"'),
                ('2', 'Conflicto de robo', '"Me están robando lo que me pertenece"'),
                ('3', 'Conflicto del bocado arrebatado por el padre', '"Mi padre no me dio lo que necesitaba"'),
                ('4', 'Contrariedad + miedo al futuro', '"Lo que viene me aterra"'),
                ('5', 'Contrariedad existencial', '"No entiendo por qué existo si todo me falla"'),
                ('1', 'Contrariedad + enojo profundo', '"Estoy harto de todo"'),
            ],
            "INTESTINAL DELGADA": [
                ('1', 'Bocado indigerible sucio', '"Me pasó algo asqueroso que no puedo asimilar"'),
                ('2', 'Conflicto de asimilación de la pérdida', '"No puedo asimilar que lo perdí"'),
                ('3', 'Separación asquerosa', '"La separación fue repugnante"'),
                ('4', 'Indigestión de la pérdida + enojo', '"No acepto haber perdido esto"'),
                ('5', 'Separación indigesta', '"Esta separación no la puedo procesar"'),
                ('1', 'Asimilación de lo asqueroso', '"Tengo que asimilar algo repugnante"'),
                ('2', 'Ingestión de lo feo', '"Me obligan a tragarme algo repulsivo"'),
                ('3', 'Suciedad ingerible', '"Tengo que tragarme algo sucio"'),
                ('4', 'Conflicto de separación sucio + indigerible', '"La separación dejó algo muy sucio"'),
                ('5', 'Bocado de separación no asimilado', '"No puedo superar esta separación"'),
                ('1', 'Pérdida del bocado de separación', '"Perdí la relación que me nutría"'),
                ('2', 'Indigestión de la separación', '"Separación que no puedo procesar"'),
            ],
            "HEPÁTICA": [
                ('1', 'Miedo a carecer de reservas', '"Tengo miedo de quedarme sin sustento"'),
                ('2', 'Rabia acumulada', '"Tengo mucha ira acumulada que no he podido soltar"'),
                ('3', 'Carencia de bocado futuro', '"No habrá suficiente para mí en el futuro"'),
                ('4', 'Miedo a morirse de hambre', '"Tengo miedo de no tener con qué sustentarme"'),
                ('5', 'Bocado perdido + miedo', '"Perdí algo que me daba sustento y me da miedo el futuro"'),
                ('1', 'Miedo acumulado al futuro', '"El futuro me aterra"'),
                ('2', 'Bocado perdido + rabia', '"Perdí algo importante y estoy furioso"'),
                ('3', 'Conflicto de escasez generalizada', '"Nunca será suficiente para mí"'),
                ('4', 'Miedo a la escasez + desesperanza', '"Esto no tiene solución"'),
                ('5', 'Carencia + rabia', '"No tengo lo suficiente y estoy enojado por eso"'),
                ('1', 'Miedo financiero + carencia', '"Tengo miedo de quedarme sin dinero"'),
                ('2', 'Rabia ante la toxicidad', '"Me envenenan con su presencia"'),
            ],
            "BILIAR": [
                ('1', 'Rabia territorial + rencor acumulado', '"Alguien invadió mi territorio y no lo olvido"'),
                ('2', 'Rabia en el territorio', '"Hay algo en mi espacio vital que me produce ira"'),
                ('3', 'Rabia por el bocado perdido', '"Me quitaron lo que era mío y sigo con rabia"'),
                ('4', 'Rabia ante la injusticia en el territorio', '"Algo injusto sucedió en mi entorno"'),
                ('1', 'Rencor violento', '"Guardo un rencor muy intenso"'),
                ('2', 'Rabia + separación territorial', '"Me separaron de mi espacio y estoy furioso"'),
                ('3', 'Rabia ante la contrariedad', '"Lo que me hicieron me genera una ira que no para"'),
                ('4', 'Rabia + separación del territorio', '"Alejarse de mi territorio me genera ira"'),
            ],
            "INTESTINAL GRUESA": [
                ('1', 'Bocado indigesto asqueroso sin valor', '"No vale la pena guardar lo que me dieron"'),
                ('2', 'Conflicto de identidad sucia', '"Me avergüenzo de lo que soy"'),
                ('3', 'Bocado feo que hay que soltar', '"Tengo que deshacerme de lo que me intoxica"'),
                ('4', 'Conflicto de lo sucio que hay que guardar', '"Hay algo sucio que no puedo soltar"'),
                ('5', 'Separación de lo asqueroso que no termina', '"Sigo ligado a algo que me resulta repugnante"'),
                ('1', 'Suciedad que hay que expulsar', '"Necesito sacar algo de mí que me ensucia"'),
                ('2', 'Bocado indigesto sin salida', '"Lo que viví se me quedó atorado"'),
                ('3', 'Lo sucio que no hay que soltar', '"Necesito retener lo que me dieron aunque sea feo"'),
                ('4', 'Identidad + suciedad', '"Me siento sucio en mi identidad"'),
                ('5', 'Separación sucia + rencor', '"La separación dejó algo muy sucio y lo odio"'),
                ('1', 'Bocado retenido por rencor', '"No puedo soltar lo que me dieron porque sigo enojado"'),
                ('2', 'Separación con suciedad acumulada', '"Esta separación dejó mucha suciedad acumulada"'),
                ('3', 'Conflicto de lo vergonzoso que hay que guardar', '"Guardo algo que me avergüenza"'),
                ('4', 'Conflicto de identidad sucia transgeneracional', '"Hay algo sucio en mi historia familiar"'),
                ('5', 'Vergüenza interna', '"Me avergüenzo de lo que hice/viví"'),
                ('1', 'Conflicto de defensa territorial de lo sucio', '"Defiendo algo que sé que está mal"'),
                ('2', 'Miedo a contaminarse', '"Tengo miedo de que algo sucio me afecte"'),
                ('3', 'Separación sucia que hay que retener', '"Aunque fue sucio, no quiero soltar eso"'),
            ],
            "ANAL": [
                ('1', 'Pérdida del territorio + sucio', '"Perdí lo que era mío de una manera terrible"'),
                ('2', 'Bocado no digerido que hay que expulsar', '"Necesito soltar lo que no pude digerir"'),
                ('3', 'Conflicto de fronteras', '"No sé dónde termino yo y empieza el otro"'),
                ('4', 'Suciedad territorial que hay que retener', '"Tengo miedo de soltar lo que tengo"'),
                ('5', 'Conflicto de límites + suciedad', '"Mis límites han sido violados de manera sucia"'),
                ('1', 'Conflicto de identidad del territorio', '"No sé qué es mío y qué no"'),
                ('2', 'Expulsión del bocado podrido', '"Tengo que deshacerme de lo que ya se pudrió"'),
            ],
            "PERITONEAL": [
                ('1', 'Ataque frontal al territorio + miedo', '"Alguien ataca directamente lo que es mío"'),
                ('2', 'Invasión del territorio vital + rabia', '"Alguien ha invadido mi espacio más íntimo"'),
                ('3', 'Miedo grave a la muerte en el territorio', '"Siento que el peligro me puede matar en mi propio espacio"'),
                ('4', 'Conflicto de contaminación del espacio vital', '"Mi entorno se ha contaminado"'),
                ('5', 'Territorio vital en riesgo de desaparecer', '"Siento que perderé todo lo que es mío"'),
                ('1', 'Conflicto de límites violados + muerte', '"Alguien rompió mis límites y me puede matar"'),
            ],
            "DEL QUIMO": [
                ('1', 'Bocado indigesto + urgencia', '"Tengo que procesar rápido lo que no puedo asimilar"'),
                ('2', 'Urgencia ante el bocado no digerido', '"Tengo que resolver urgente lo que no he procesado"'),
                ('3', 'Bocado indigesto + miedo', '"Lo que no puedo digerir me da miedo"'),
                ('4', 'Bocado arrebatado + urgencia', '"Me quitaron algo urgente que necesitaba"'),
                ('5', 'Urgencia del bocado', '"Necesito resolver urgente mi sustento"'),
                ('1', 'Conflicto del quimo frenado', '"El flujo de mi vida se ha detenido"'),
                ('2', 'Urgencia ante la separación del bocado', '"La separación me urge resolver"'),
                ('3', 'Bocado urgente + rabia', '"Necesito urgente lo que me quitaron y estoy furioso"'),
                ('4', 'Urgencia del bocado + miedo al futuro', '"Lo que necesito urge y me aterra no tenerlo"'),
                ('5', 'Urgencia + toxicidad del bocado', '"Necesito expulsar urgente lo que me intoxica"'),
                ('1', 'Conflicto del quimo acelerado', '"Todo va demasiado rápido en mi vida"'),
                ('2', 'Urgencia + rencor', '"Quiero urgente lo que me quitaron y guardo resentimiento"'),
                ('3', 'Urgencia + vergüenza', '"Necesito urgente solucionar algo vergonzoso"'),
            ],
        }
    },

    # ══════════════════════════════════════════════════════════════════
    "endocrino": {
        "titulo": "CONFLICTOLOGÍA ENDÓCRINA (58 conflictos)",
        "subsistemas": {
            "HIPOFISIARIA": [
                ('1', 'Inferioridad', '"No me siento a la altura / Soy demasiado pequeño para lograr el objetivo"'),
                ('2', 'Perfeccionismo', '"No tengo derecho a equivocarme (ante la mirada de algo/alguien)"'),
                ('3', 'Ascensión', '"Tengo que escalar / llegar / alcanzar una alta meta / portería / rango"'),
                ('4', 'Inmersión', '"Tengo que sacar la cabeza fuera del agua, estoy ahogándome en problemas"'),
                ('5', 'Defensa insuficiente', '"Necesito aparentar más fuerza y tamaño para defenderme / lograr"'),
                ('1', 'Crecimiento', '"Está prohibido / es peligroso crecer / ser adulto / más grande que alguien"'),
                ('2', 'Ahorcamiento', '"Suicidio del colgado"'),
                ('3', 'Lactancia', '"Tengo que producir más leche / No puedo alimentar a los míos"'),
                ('4', 'Introyecto de infancia', '"Quiero darle de comer a mi niño interno para que crezca"'),
                ('5', 'Extravío del buen camino', '"No puedo / debo encontrar el buen camino / Es peligroso cambiar de dirección"'),
                ('1', 'Producción', '"Mi plan es no equivocarme nunca en mis decisiones / Tengo que esforzarme al máximo"'),
                ('2', 'Satisfacción imposible', '"No puedo / debo / logro satisfacer a X, es insaciable"'),
            ],
            "TIROIDEA": [
                ('1', 'Rapidez', '"No voy suficientemente rápido / He llegado demasiado tarde / Tengo que recuperar el tiempo perdido"'),
                ('2', 'Urgencia', '"Necesito llegar porque hay mucho por hacer / Necesito hacerlo más rápido"'),
                ('3', 'Evolución demasiado lenta', '"Necesito saltarme estas etapas / Quiero evolucionar más rápido"'),
                ('4', 'Rapidez + impotencia', '"Hay que actuar rápidamente y nadie hace nada / Pedí auxilio y nadie llegó a tiempo"'),
                ('5', 'Miedo frontal con matiz de tiempo', '"No pude dar la alarma a tiempo / Me quedo en mi lugar cuando el peligro ya viene"'),
                ('1', 'Rapidez fútil', '"Tengo que ir deprisa y de todos modos no funciona"'),
                ('2', 'Objetivo en rapidez', '"Tengo que terminar / concretar rápidamente"'),
                ('3', 'Bocado ocular', '"Tengo que atrapar el bocado con la mirada / ver que esto pase rápidamente"'),
                ('4', 'Peligro con matiz de velocidad', '"Tengo que ver venir el peligro y escapar rápidamente"'),
                ('5', 'Lentitud', '"Todo va demasiado rápido, necesito alentar el tiempo / Es peligroso ir demasiado rápido"'),
                ('1', 'Detención del tiempo', '"Me arrepiento de lo que pasó / Nunca lo voy a lograr si el tiempo sigue avanzando / No quiero enfrentar lo que viene"'),
                ('2', 'Intolerancia a la velocidad', '"Me niego a ir más deprisa / Todo debería ir más lentamente"'),
                ('3', 'Dependencia ante la velocidad', '"Solo puedo vivir si el tiempo se detiene / Solo si el tiempo pasa más lento seré querido"'),
                ('4', 'Encrucijada', '"Estoy en un problema, no sé cómo actuar / Tengo miedo a comprometerme con esto"'),
                ('5', 'Memoria de estrangulamiento', 'Gestación con el cordón en el cuello'),
            ],
            "PARATIROIDEA": [
                ('1', 'Esfuerzo insuficiente / impotencia', '"No logro lo necesario para atrapar el bocado / No puedo tragar el bocado porque me lo impiden"'),
                ('2', 'Sumisión parental', '"Mis padres me quieren dominar, no encuentro el equilibrio entre ellos y yo"'),
                ('3', 'Impotencia con matiz de muerte', '"Quiero escapar del peligro mortal pero no puedo / Me quedé congelado en lugar de haber actuado"'),
            ],
            "PANCREÁTICA": [
                ('1', 'Resistencia', ''),
                ('2', 'Asco', ''),
                ('3', 'Impotencia', ''),
                ('4', 'Amor tóxico', ''),
                ('5', 'Casa dividida', ''),
                ('1', 'Soledad', ''),
                ('2', 'Peligro constante', ''),
                ('3', 'Carencia afectiva', ''),
                ('4', 'Carencia financiera', ''),
                ('5', 'Solución no encontrada', ''),
                ('1', 'Ignominia', ''),
                ('2', 'Ira', ''),
                ('3', 'Proyecto sentido', ''),
                ('4', 'Carga transgeneracional', ''),
            ],
            "SUPRARRENAL": [
                ('1', 'Liquidez', '"No tengo dinero disponible"'),
                ('2', 'Maternidad en peligro', '"No quiero perder a mi madre / Mi madre se aleja de mí"'),
                ('3', 'Soledad', '"Me encuentro aislado en este momento / lugar / circunstancia"'),
                ('4', 'Desvalorización de la dirección', '"Elegí el camino incorrecto / No tomé la decisión correcta"'),
                ('5', 'Desorientación', '"No sé qué camino elegir / Me siento perdido"'),
                ('1', 'Alienación', '"Soy la oveja negra de la familia / Soy un extraterrestre en este mundo"'),
                ('2', 'Desinterés', '"No me interesa nada del mundo exterior / No quiero que nadie dependa de mí"'),
                ('3', 'Liquidez', '"No tengo dinero disponible"'),
                ('4', 'Maternidad en peligro', '"No quiero perder a mi madre"'),
                ('5', 'Soledad', '"Me encuentro aislado / No sé qué opción elegir"'),
                ('1', 'Globalidad', '"Quiero estar satisfecho en todos los aspectos de mi vida / Ya no soy el mismo de antes"'),
                ('2', 'Dirección global', '"Una parte de mí se ha equivocado de camino"'),
                ('3', 'Dirección sexual', '"Me he equivocado de pareja / No tomé el camino sexual correcto"'),
                ('4', 'Identidad sexual', '"Mi identidad de género no es reconocida"'),
            ],
        }
    },

    # ══════════════════════════════════════════════════════════════════
    "cardiovascular": {
        "titulo": "CONFLICTOLOGÍA CARDIOVASCULAR (69 conflictos)",
        "subsistemas": {
            "MIOCARDIAL": [
                ('1', 'Desvalorización territorial', '"No valgo nada porque no tengo territorio"'),
                ('2', 'Desvalorización por eficiencia cardíaca', '"Mi corazón no podrá, no soy lo suficientemente fuerte/poderoso"'),
                ('3', 'Inferioridad', '"No me siento a la altura"'),
                ('4', 'Toxicidad', '"Me siento envenenado / Si la sangre fluye, el veneno me matará"'),
                ('5', 'Miedo a salir del territorio', '"Si salgo de aquí, algo malo me pasará"'),
                ('1', 'Vida impedida', '"Alguien me impide vivir / No puedo vivir como quiero"'),
                ('2', 'Relativo al suicidio', '"No puedo vivir, moriré / Me siento muerto en vida"'),
                ('3', 'Memoria de envenenamiento', '"Me siento envenenado / La presencia de alguien me envenena"'),
                ('4', 'Tono masculino', '"Mi padre no me ama / Carezco de suficiente masculinidad / No soy suficientemente hombre"'),
                ('5', 'Desvalorización vital', '"Soy incapaz de dar vida / Soy impotente para valerme por mí mismo"'),
            ],
            "VALVULAR": [
                ('1', 'Puerta maternal abierta', '"Quiero volver a casa / Quiero regresar a mi madre / Tengo esperanza de regresar algún día"'),
                ('2', 'Contrariedad parental', '"Mi padre y mi madre tienen problemas para hablar / La puerta está cerrada para mi padre"'),
                ('3', 'Retorno a lo femenino impedido', '"Mi madre no me dejará regresar / No puedo volver con mi madre"'),
                ('4', 'Retorno a lo femenino impedido (variante)', '"No quiero volver nunca a la casa de mamá / Es peligroso que regresen"'),
                ('5', 'Puerta paternal abierta', '"Mi padre me corrió pero quiero regresar / Deseo reconciliarme con mi padre"'),
            ],
            "DEL RITMO": [
                ('1', 'Miedo al futuro del amor', '"No quiero que se frustre esta relación / Tengo miedo de perder a esta persona"'),
                ('2', 'Urgencia de la solución', '"Necesito acabar ya con este problema / Me siento en una lucha que me urge terminar"'),
                ('3', 'Autoridad injustificada', '"No aguanto que no me den la razón / Quiero tener la razón a como de lugar"'),
                ('4', 'Conservación tóxica', '"Quiero conservar a este muerto conmigo / Deseo quedarme con lo sucio de la familia"'),
                ('5', 'Miedo a la toxicidad', '"No quiero que entre veneno a mi corazón / Tengo miedo a que me envenenen"'),
                ('1', 'Alargamiento de vida', '"Quiero vivir lo más posible, lo haré lentamente / No quiero apurar a mi corazón"'),
                ('2', 'Frustración sexual', '"No soy poseída por el macho / No me importo sexualmente"'),
                ('3', 'Miedo de perder el territorio en el futuro', '"Siento que perderé mi territorio / Me estoy arriesgando"'),
                ('4', 'Miedo grave de pérdida del territorio', '"Tengo que luchar mucho para mantener el territorio / Debo dar más de todo"'),
            ],
            "DE MEMBRANAS": [
                ('1', 'Corazón partido', '"Me rompe separarme de algo/alguien del hogar"'),
                ('2', 'Ataque al corazón', '"Tengo miedo de que me dañen físicamente el corazón / Miedo a cirugía"'),
                ('3', 'Riesgo de enfermedad cardíaca', '"Tengo miedo a infartarme / Miedo a una enfermedad cardiovascular"'),
                ('4', 'Separación dolorosa del territorio', '"Me duele mucho alejarme de lo que es mío"'),
            ],
            "ARTERIAL": [
                ('1', 'Conflicto del padre ausente', '"Mi padre no está / nunca estuvo / me abandonó"'),
                ('2', 'Conflicto de transmisión paterna', '"No recibí lo que necesitaba de mi padre"'),
                ('3', 'Conflicto del padre tóxico', '"Mi padre me envenenó con su presencia / sus palabras"'),
                ('4', 'Desvalorización por el padre', '"Mi padre me hizo sentir que no valía nada"'),
                ('5', 'Conflicto de muerte del padre', '"Perdí a mi padre / mi figura paterna"'),
                ('1', 'Conflicto de dirección paterna', '"Mi padre me dirigió por el camino equivocado"'),
                ('2', 'Conflicto de protección paterna ausente', '"Mi padre no me protegió cuando lo necesitaba"'),
                ('3', 'Conflicto del padre sustituto', '"Busco en otro lo que mi padre no me dio"'),
                ('4', 'Traición paterna', '"Mi padre me traicionó de la peor manera"'),
                ('5', 'Conflicto de identidad paterna', '"No sé quién es mi padre / No sé quién soy sin mi padre"'),
            ],
            "VENOSA": [
                ('1', 'Conflicto de la madre ausente', '"Mi madre no está / nunca estuvo"'),
                ('2', 'Conflicto de la madre tóxica', '"Mi madre me envenenó con su presencia / sus palabras"'),
                ('3', 'Conflicto de transmisión materna', '"No recibí lo que necesitaba de mi madre"'),
                ('4', 'Desvalorización por la madre', '"Mi madre me hizo sentir que no valía nada"'),
                ('5', 'Conflicto de muerte de la madre', '"Perdí a mi madre / mi figura materna"'),
                ('1', 'Conflicto de regreso al nido materno', '"Quiero volver a la seguridad que me daba mi madre"'),
                ('2', 'Conflicto de la madre sobreprotectora', '"Mi madre no me deja ser independiente"'),
            ],
            "DE PRESIÓN": [
                ('1', 'Conflicto de presión territorial', '"Siento una presión enorme en mi entorno / mi espacio vital"'),
                ('2', 'Presión familiar', '"Mi familia me presiona constantemente"'),
                ('3', 'Presión ante el peligro', '"Siento que hay un peligro inminente que me presiona"'),
                ('4', 'Presión ante la responsabilidad', '"El peso de mis responsabilidades me aplasta"'),
                ('5', 'Presión ante la autoridad', '"Una figura de autoridad me tiene bajo presión constante"'),
            ],
            "ADJUNTA": [
                ('1', 'Conflicto de los ganglios linfáticos cardíacos', '"Algo ataca el centro de mi ser"'),
                ('2', 'Conflicto del timo cardíaco', '"Me atacan en lo más íntimo de mi identidad"'),
                ('3', 'Conflicto de pericardio', '"Necesito proteger mi corazón de lo que me rodea"'),
                ('4', 'Conflicto de pleura cardíaca', '"Algo me ahoga desde afuera"'),
                ('5', 'Conflicto de médula ósea cardíaca', '"Siento que me destruyen por dentro"'),
                ('1', 'Conflicto de la sangre', '"Hay algo malo en mi sangre / en mi linaje"'),
            ],
            "LIPÍDICA": [
                ('1', 'Conflicto de reserva de emergencia', '"Necesito guardar reservas para cuando todo se acabe"'),
                ('2', 'Conflicto de protección grasa', '"Necesito una capa protectora para sobrevivir"'),
                ('3', 'Conflicto de la sangre espesa', '"Siento que todo en mí está pesado, denso, cargado"'),
            ],
        }
    },

    # ══════════════════════════════════════════════════════════════════
    "osteomuscular": {
        "titulo": "CONFLICTOLOGÍA OSTEOMUSCULAR (159 conflictos)",
        "subsistemas": {
            "GENERAL": [
                ('1', 'Desvalorización grave hacia uno mismo', '"No valgo nada"'),
                ('2', 'Rechazo de valores', '"Tengo que negar / desechar lo que soy"'),
                ('3', 'Desvalorización por haber estado ausente', '"No valgo por haberme ido de aquí"'),
                ('4', 'Rechazo a uno mismo', '"Tengo que rechazar mis valores"'),
                ('5', 'Valores en derrumbe', '"Los valores que me construyen se están desmoronando"'),
                ('1', 'Desvalorización crónica', '"Siempre he valido poco / No valgo nada porque siempre he estado solo"'),
                ('2', 'Desvalorización progresiva', '"Poco a poco mi valor se reduce / No tengo derecho a nada más en la vida"'),
                ('3', 'Desvalorización sexual', '"Ya nadie se fija en mí"'),
                ('4', 'Desvalorización por haber estado demasiado presente', '"Estuve muy encima de alguien, hubiera preferido estar menos"'),
                ('5', 'Desvalorización existencial', '"No tengo derecho a existir / No tengo derecho a elegir mis propios valores"'),
                ('1', 'Amor propio', '"No me amo"'),
                ('2', 'Apoyo parental', '"Necesito a mi padre / madre para sostenerme"'),
                ('3', 'Gran desvalorización', '"No valgo nada, quisiera ser otra persona"'),
                ('4', 'Necesidad de fortaleza futura', '"Tengo que ser más sólido / fuerte la próxima vez"'),
                ('5', 'Desvalorización por haber estado ausente', '"No valgo por haberme ido de aquí"'),
            ],
            "VERTEBRAL": [
                ('1', 'El pilar', '"Siempre soy el pilar de mi familia / tribu / compañía / Siempre soy el que sostiene a todos"'),
                ('2', 'Enfoque hacia el padre', '"Mi atención irá hacia mi padre porque mi madre no me valora"'),
                ('3', 'Enfoque hacia la madre', '"Mi atención irá hacia mi madre porque mi padre no me valora"'),
                ('4', 'Desvalorización comparativa', '"Valgo menos comparado con alguien cercano a mí"'),
                ('5', 'Apoyo imposible', '"No me puedo apoyar en ningún lugar, ni en un lado ni en otro"'),
                ('1', 'Sobrecarga', '"El peso que cargo es demasiado para mí"'),
                ('2', 'Desunión parental', 'Los valores de padre y madre no coinciden / Rivalidad en la pareja'),
            ],
            "ÓSEA DIVERSA": [
                ('1', 'Peligro de muerte vinculado a ruido', 'Situación de peligro letal relativa a una explosión/disparo/vehículo'),
                ('2', 'Auditivo de muerte', '"Ya estoy muerto / Tengo la muerte asegurada / He vivido como muerto en vida"'),
                ('3', 'Desvalorización de la palabra', '"Por haber dicho X, ya no valgo"'),
                ('4', 'Desvalorización crónica', '"Siempre he valido poco"'),
                ('5', 'Desvalorización transgeneracional', '"Hay un mal familiar del que me debo deshacer"'),
                ('1', 'Valores endebles', '"Necesito edificarme con valores más sólidos / fuertes"'),
            ],
            "PERIOSTIO": [
                ('1', 'Contacto no deseado brutal', '"Tuve que golpear a alguien, pero no quería / Alguien me golpeó"'),
                ('2', 'Separación con matiz estructural', '"Esta separación es definitiva, irrevocable"'),
                ('3', 'Separación violenta', '"Alguien se fue repentina y violentamente"'),
                ('4', 'Separación con dilema', '"Al que se fue lo quiero tocar, pero no quiero tocarlo"'),
                ('5', 'Desvalorización autoprogramante', '"Valgo menos por la fractura que tuve / No soporto estar inmovilizado"'),
            ],
            "ARTICULAR": [
                ('1', 'Gran desvalorización con requerimiento de apoyo', '"Necesito estar a la altura de X, porque si no, no valgo / Por más que lo intento no funciona"'),
                ('2', 'Desvalorización + impotencia articular', '"No puedo moverme / actuar sin sentir que valgo menos"'),
            ],
            "LIGAMENTOS": [
                ('1', 'Conflicto de dirección + desvalorización', '"Me equivoqué de camino y eso me hace sentir que valgo menos"'),
                ('2', 'Desvalorización por haber seguido instrucciones equivocadas', '"Seguí lo que me dijeron y resultó mal"'),
                ('3', 'Conflicto de unión imposible', '"Lo que quiero unir no se puede unir"'),
                ('4', 'Desvalorización por ruptura relacional', '"Desde que se rompió esa relación no valgo nada"'),
                ('5', 'Conflicto de límites relacionales', '"No sé cómo manejar mis vínculos sin desvalorizarme"'),
                ('1', 'Conflicto de movimiento impedido', '"No puedo avanzar hacia lo que quiero"'),
                ('2', 'Desvalorización por inmovilidad', '"No puedo moverme y eso me hace sentir que no valgo"'),
                ('3', 'Conflicto de tensión relacional', '"La tensión entre X y yo me tiene paralizado"'),
            ],
            "TENDONES": [
                ('1', 'Desvalorización por haber cedido', '"Cedí cuando no debí y eso me hace sentir que no valgo"'),
                ('2', 'Desvalorización por rigidez', '"Soy demasiado rígido / inflexible y eso me hace valer menos"'),
                ('3', 'Conflicto de esfuerzo sin reconocimiento', '"Me esfuerzo al máximo y nadie lo reconoce"'),
                ('4', 'Desvalorización por el esfuerzo excesivo', '"Me exijo demasiado y eso me destruye"'),
                ('5', 'Conflicto de dirección del esfuerzo', '"Me esfuerzo pero en la dirección equivocada"'),
            ],
            "MUSCULAR": [
                ('1', 'Desvalorización por impotencia de acción', '"Quise actuar y no pude / No soy suficientemente hábil para hacer esto"'),
                ('2', 'Desvalorización por rendimiento insuficiente', '"No doy la talla / No soy suficientemente bueno"'),
                ('3', 'Desvalorización por pérdida de destreza', '"Ya no puedo hacer lo que antes hacía bien"'),
                ('4', 'Desvalorización relativa al rendimiento', '"Comparado con otros, mi rendimiento es muy bajo"'),
                ('5', 'Desvalorización por falta de fuerza', '"No soy suficientemente fuerte para esto"'),
                ('1', 'Desvalorización ante el reto', '"Sé que no voy a poder con este desafío"'),
                ('2', 'Desvalorización por la debilidad mostrada', '"Todos vieron que soy débil"'),
                ('3', 'Conflicto de potencia perdida', '"Perdí la fuerza que antes tenía"'),
                ('4', 'Desvalorización por dependencia', '"Necesito a otros para moverme y eso me hace sentir menos"'),
                ('5', 'Conflicto de movimiento bloqueado', '"Quiero avanzar pero algo me lo impide desde adentro"'),
                ('1', 'Desvalorización por parálisis temporal', '"Me quedé paralizado y no pude actuar"'),
                ('2', 'Conflicto de la contracción involuntaria', '"No controlo mis propios movimientos"'),
                ('3', 'Conflicto de agotamiento', '"Estoy exhausto pero no me puedo detener"'),
                ('4', 'Desvalorización por el cansancio', '"Mi cansancio me hace sentir que no valgo"'),
                ('5', 'Conflicto de sobreesfuerzo', '"Me exijo más allá de mis límites y eso me destruye"'),
                ('1', 'Conflicto de crispación', '"Algo me tiene tenso, crispado, sin poder relajarme"'),
            ],
        }
    },

    # ══════════════════════════════════════════════════════════════════
    "dermato_lipofascial": {
        "titulo": "CONFLICTOLOGÍA DERMATOLÓGICA-LIPOFASCIAL (44 conflictos)",
        "subsistemas": {
            "DESVALORIZACIÓN": [
                ('1', 'Desvalorización estética', '"Me siento feo / Critican mi aspecto / Dicen que estoy gordo"'),
                ('2', 'Desvalorización grupal', '"No valgo nada para esta gente / Nadie me valora en este lugar"'),
                ('3', 'Desvalorización grave + impotencia', '"A partir de ahora, no valgo para nada / No puedo hacer nada"'),
                ('4', 'Desvalorización intelectual', '"Me critican por lo que pienso / A nadie le importa mi opinión"'),
                ('5', 'Separación + desvalorización + desprotección', '"Se fue por mi culpa, ahora nadie me cuidará"'),
                ('1', 'No ser amado', '"Nadie me quiere"'),
                ('2', 'Inexistencia', '"Siento que no existo para alguien / Soy invisible"'),
                ('3', 'Comunicación', '"Nadie me entiende / No puedo confiar en nadie"'),
                ('4', 'Rigidez', '"Tengo que ser así, para que me acepten"'),
            ],
            "CONTACTO IMPUESTO": [
                ('1', 'Humillación', '"Me han hecho pasar el ridículo / Me denigraron frente a los demás"'),
                ('2', 'Cuerpo extraño (bacterias)', '"Hay algo que quiero sacar de mí"'),
                ('3', 'Suciedad', '"Hay algo que necesito lavar en mí"'),
                ('4', 'Peso excesivo', '"Necesito soltar esta carga pesada"'),
                ('5', 'Escape', '"Necesito deslizarme a través de esta situación complicada"'),
                ('1', 'Integridad física/mental', '"No respetan mi espacio / Me han atacado fuertemente"'),
                ('2', 'Indignidad', '"Me han herido en mi dignidad / Me han sobajado"'),
                ('3', 'Agresión local', '"Siento un ataque en X parte del cuerpo"'),
                ('4', 'Contacto insoportable', '"Tengo que aguantar estar con X"'),
                ('5', 'Intocabilidad', '"No soy digno de ser amado / tocado"'),
                ('1', 'Vergüenza', ''),
                ('2', 'Invisibilidad', '"Tengo que desaparecer / esconderme"'),
                ('3', 'Mancha', '"Hay un lugar que ha sido ensuciado / Tengo una marca que no me puedo borrar"'),
                ('4', 'Pureza', '"Tengo que llevar luz a un lugar oscurecido, sucio"'),
                ('5', 'Rechazo paternal', '"No quiero la protección de mi padre / No puedo protegerme de mi padre"'),
                ('1', 'Juicio ajeno', '"No soporto cómo me critican"'),
                ('2', 'Ataque', '"Me dieron de golpes en X lugar"'),
            ],
            "SEPARACIÓN": [
                ('1', 'Separación (ruptura de contacto)', '"Murió un ser querido / Me acabo de divorciar / Rompimos lazos"'),
                ('2', 'Miedo a la separación', '"No me quiero quedar solo"'),
                ('3', 'Separación con el protector/progenitor', '"Mis padres se han ido"'),
                ('4', 'Contacto perdido', '"Extraño ser tocado como antes"'),
                ('5', 'Separación desvalorizante', '"Desde que se fue, soy un inútil / Si se va, es mi culpa"'),
                ('1', 'Separación semi-íntima', '"Se fue una persona muy importante para mí"'),
                ('2', 'Separación brutal', '"Murió instantáneamente el ser querido, sin aviso"'),
                ('3', 'Separación paterna', '"Mi padre no me protegerá / Mi padre se fue / nunca me cuidó"'),
                ('4', 'Duelo bloqueado', '"No he podido superar una muerte / Quiero retener al muerto"'),
                ('5', 'Contacto propio', '"Rechazo contactar conmigo mismo / Tengo que ser otro para no ser rechazado"'),
                ('1', 'Desprotección', '"Nadie me cuida / Estoy en peligro y nadie me salva"'),
                ('2', 'Programa de incesto simbólico', '"Estoy virtualmente unido a mi progenitor"'),
                ('3', 'Dolor moral', '"Sufro por la separación"'),
                ('1', 'Mirada paternal', '"Quiero ser mirada por mi padre"'),
                ('2', 'Falta de mirada', '"Sufro porque nadie me vio cuando quería ser visto"'),
                ('3', 'Reconocimiento', '"Nadie me felicitó / Nadie valora mis acciones"'),
            ],
        }
    },

    # ══════════════════════════════════════════════════════════════════
    "reproductivo": {
        "titulo": "CONFLICTOLOGÍA REPRODUCTIVA (125 conflictos)",
        "subsistemas": {
            "OVÁRICA": [
                ('1', 'Pérdida filial', '"Perdí a mi hijo / Era como mi hijo y murió"'),
                ('2', 'Miedo a pérdida filial', '"No quiero perder a mi hijo"'),
                ('3', 'Grave conflicto de pérdida', '"Perdí a mi mascota / Murió mi mejor amigo"'),
                ('4', 'Fusión maternal', '"No sé dónde termina mi madre y empiezo yo"'),
                ('5', 'Seducción perdida', '"Ya no logro atraer a el/los que me atraen / Ya no me miran los hombres"'),
                ('1', 'Semigenital', '"Sufrí un golpe bajo a mi femeneidad / Ese hombre me rebajó"'),
                ('2', 'Falta filial', '"Como no tengo pareja para engendrar, hago un hijo yo misma"'),
                ('3', 'Masculinidad deseada', '"Quisiera haber nacido hombre"'),
                ('4', 'Identidad femenina', '"No sé qué tipo de mujer quiero ser"'),
                ('5', 'Genital desvalorizante', '"Me han criticado en mi sexualidad / Me dejó porque no sé hacer el amor"'),
                ('1', 'Infancia prolongada', '"Quiero seguir siendo una niña"'),
                ('2', 'Culpabilidad femenina', '"Me siento mal por no ser una mujer completa"'),
                ('3', 'Maternidad imposible', '"No soy capaz de tener hijos"'),
            ],
            "OVIDUCTAL": [
                ('1', 'Sexual sucio', '"Mi amiga se acostó con mi novio / Me acosté con él y era casado"'),
                ('2', 'Violación sexual', '"Fui abusada sexualmente"'),
                ('3', 'Agresión sexual', '"Me tocó íntimamente sin mi consentimiento"'),
                ('4', 'Secreto sexual', '"Tuve una relación sexual que no puedo contar a nadie"'),
                ('5', 'Dilema filial', '"Quiero pero no quiero tener un hijo"'),
                ('1', 'Espacio filial', '"Mi hijo no tendrá hogar cuando llegue"'),
            ],
            "UTERINA": [
                ('1', 'Familiar fuera de la norma', '"Nuestra forma de ser familia es socialmente reprochable"'),
                ('2', 'Descontrol familiar', '"No puedo hacer nada para redirigir el destino de la familia"'),
                ('3', 'Pérdida', '"Murió un ser familiar querido"'),
                ('4', 'Producto perdido', '"Aborté y no supero el duelo / Perdí a mi bebé"'),
                ('5', 'Maternidad imposible', '"No soy capaz de tener hijos / Mi pareja no quiere tener un hijo conmigo"'),
                ('1', 'Sexualidad fuera de la norma', '"Tuvimos sexo de manera pecaminosa / Hicimos algo sexualmente indebido"'),
                ('2', 'Sexual con matiz filial', '"Mi hijo nos descubrió teniendo sexo / Tengo una pulsión incestuosa"'),
                ('3', 'Disconformidad sexual', '"No estoy de acuerdo con cómo mis hijos llevan su sexualidad"'),
                ('4', 'Sexualidad obligada', '"Tengo que cumplirle a mi marido aunque no tengo ganas"'),
                ('5', 'Embarazo fuera de lugar', '"Quiero embarazarme pero no es el momento o lugar adecuado"'),
                ('1', 'Penetración no deseada', '"No quiero tener relaciones sexuales"'),
                ('2', 'Femineidad complicada', '"Ser mujer es muy difícil / Tengo que ser como hombre para resolver esto"'),
                ('3', 'Frustración sexual', '"Mi hombre no es como yo quiero / Mi pareja no se fija en mí"'),
                ('4', 'Dependencia negativa romántica', '"Mi pareja ni siquiera me mira / Mi vida depende de mi pareja"'),
                ('5', 'Violación sexual', '"Fui abusada sexualmente"'),
                ('1', 'Miedo al parto', '"Me da terror que algo salga mal durante el parto"'),
                ('2', 'Hogar lejano', '"No siento que esta casa/pareja/familia sea mi hogar"'),
                ('3', 'Poder divino', '"Quiero ser como Dios / Quiero poder controlarlo todo"'),
                ('4', 'Maternidad equivocada', '"Mi hijo no es del hombre que yo quería"'),
                ('5', 'Pareja equivocada', '"Tengo sexo con mi pareja mientras pienso en otro"'),
            ],
            "MENSTRUAL": [
                ('1', 'Miedo a la adultez', '"Me aterra mostrar que ya no soy una niña / La sexualidad adulta me asusta"'),
                ('2', 'Oposición maternal', '"Soy lo contrario a mi madre / No estoy de acuerdo con la postura de mi mamá"'),
                ('3', 'Madre abrumadora', '"Mi madre no me permite ser mujer / Mi madre me hace sentir inhibida"'),
                ('4', 'Expulsión familiar', '"Quiero que alguien de la familia se vaya"'),
                ('5', 'Miedo al abandono romántico', '"No quiero que mi pareja se vaya"'),
                ('1', 'Vampirismo', '"Tengo miedo a que me chupen la sangre"'),
                ('2', 'Daño familiar', '"Mi familia me lastima"'),
                ('3', 'Menstruación vergonzosa', '"En mi menarquía tuve una experiencia desagradable"'),
                ('4', 'Normativa impuesta', '"Este sistema de reglas me está ahogando"'),
                ('5', 'Femineidad no deseada', '"No quiero tener que ver con todos los temas de la mujer / Es muy doloroso ser mujer"'),
            ],
            "VAGINAL": [
                ('1', 'Contacto sexual no deseado', '"Hay algo que quiero separar de mi cuerpo sexual"'),
                ('2', 'Separación + suciedad sexual', '"La separación dejó algo sucio en mí"'),
                ('3', 'Miedo al contacto sexual', '"Tengo miedo de que me toquen íntimamente"'),
                ('4', 'Separación del protector sexual', '"Me separé de quien me hacía sentir segura"'),
                ('5', 'Separación con dolor sexual', '"La separación duele en lo más íntimo"'),
                ('1', 'Penetración traumática', '"El acto sexual fue traumatizante"'),
                ('2', 'Suciedad íntima', '"Siento que lo que viví sexualmente me ensució"'),
                ('3', 'Aislamiento sexual', '"Me quedé sola en lo sexual"'),
                ('4', 'Miedo a la penetración', '"Tengo miedo de que algo entre en mí"'),
                ('5', 'Rechazo del compañero sexual', '"No quiero estar con mi pareja sexualmente"'),
            ],
            "DEL ESCROTO": [
                ('1', 'Conflicto de pérdida del territorio reproductivo', '"Perdí lo que era mío en el área reproductiva"'),
                ('2', 'Conflicto de marca del territorio sexual', '"Alguien marca mi territorio sexual"'),
                ('3', 'Separación del territorio genital', '"Me separé de mi espacio reproductivo"'),
                ('4', 'Conflicto de invasión del territorio sexual', '"Alguien invade mi espacio sexual"'),
                ('5', 'Conflicto de pérdida + suciedad genital', '"Perdí algo en lo sexual de manera sucia"'),
            ],
            "FÁLICA": [
                ('1', 'Conflicto sexual masculino + desvalorización', '"Me han golpeado en mi masculinidad"'),
                ('2', 'Conflicto de potencia sexual', '"No puedo / no logro ser el hombre que quiero ser en lo sexual"'),
                ('3', 'Conflicto de identidad fálica', '"No sé cómo expresar mi masculinidad"'),
                ('4', 'Conflicto de rendimiento sexual', '"No doy la talla en lo sexual"'),
                ('5', 'Conflicto de vergüenza sexual', '"Me avergüenza lo que pasó en lo sexual"'),
                ('1', 'Conflicto de rechazo sexual', '"Mi pareja me rechaza sexualmente"'),
            ],
            "TESTICULAR": [
                ('1', 'Pérdida filial masculina', '"Perdí a mi hijo / alguien como un hijo"'),
                ('2', 'Miedo a pérdida filial masculina', '"Tengo miedo de perder a mi hijo"'),
                ('3', 'Gran conflicto de pérdida masculina', '"Perdí algo o alguien muy importante"'),
                ('4', 'Identidad masculina en duda', '"No sé qué tipo de hombre quiero ser"'),
                ('5', 'Desvalorización genital masculina', '"Me han criticado en mi sexualidad / No doy la talla"'),
                ('1', 'Macho desvalorizado', '"No soy suficientemente hombre"'),
                ('2', 'Culpabilidad masculina', '"Me siento mal por no ser un hombre completo"'),
                ('3', 'Imposibilidad de procrear', '"No puedo tener hijos / No quiero tener hijos"'),
                ('4', 'Masculinidad femenina deseada', '"Quisiera haber nacido mujer"'),
                ('5', 'Conflicto de los atributos masculinos', '"Me avergüenzan mis atributos masculinos"'),
                ('1', 'Conflicto testicular de pérdida', '"Perdí algo que me hacía hombre"'),
            ],
            "PROSTÁTICA": [
                ('1', 'Conflicto sexual sucio de contacto', '"Hay algo en lo sexual que me produce asco"'),
                ('2', 'Conflicto de contrariedad masculina', '"Algo me ha contrariado en lo que soy como hombre"'),
                ('3', 'Conflicto de identidad viril', '"No sé quién soy como hombre"'),
                ('4', 'Conflicto de la virilidad en peligro', '"Mi masculinidad está amenazada"'),
                ('5', 'Conflicto de la vejez viril', '"Ya no soy el hombre que era / Mi masculinidad se va"'),
                ('1', 'Conflicto del macho perdedor', '"Perdí ante otro hombre / Me ganaron el territorio"'),
                ('2', 'Conflicto de la marca territorial masculina', '"Tengo que marcar mi territorio como hombre"'),
                ('3', 'Conflicto de la conquista fallida', '"No logré conquistar lo que quería"'),
            ],
            "SEXUAL": [
                ('1', 'Conflicto de identidad sexual', '"No sé qué tipo de ser sexual soy"'),
                ('2', 'Conflicto de orientación sexual', '"Mi orientación sexual me genera conflicto"'),
                ('3', 'Conflicto de frustración sexual generalizada', '"Mi vida sexual no es lo que quiero"'),
                ('4', 'Conflicto de la sexualidad prohibida', '"La sexualidad es peligrosa / pecaminosa / prohibida"'),
                ('5', 'Conflicto de trauma sexual', '"Lo que viví en lo sexual me marcó profundamente"'),
                ('1', 'Conflicto de la sexualidad vergonzosa', '"Me avergüenzo de mi vida sexual"'),
                ('2', 'Conflicto de la sexualidad obligada', '"Tengo que cumplir sexualmente aunque no quiero"'),
            ],
            "MAMARIA": [
                ('1', 'Conflicto de protección del nido', '"Quiero proteger a los que amo de algo que los amenaza"'),
                ('2', 'Conflicto de separación del nido', '"Me separé de alguien a quien quería proteger"'),
                ('3', 'Conflicto de cría en peligro', '"Algo amenaza a alguien que está bajo mi cuidado"'),
                ('4', 'Conflicto de la madre que no puede nutrir', '"No puedo dar lo que mis seres queridos necesitan"'),
                ('5', 'Conflicto de la cría abandonada', '"Abandoné a alguien que dependía de mí"'),
                ('1', 'Conflicto del nido roto', '"La familia se destruyó / El hogar se perdió"'),
                ('2', 'Conflicto del nido contaminado', '"Algo sucio entró al espacio de protección"'),
                ('3', 'Conflicto de la separación del hijo', '"Mi hijo se fue / lo alejé de mí"'),
                ('4', 'Conflicto de la desprotección del cría', '"No pude proteger a quien debía proteger"'),
            ],
        }
    },

    # ══════════════════════════════════════════════════════════════════
    "urinario": {
        "titulo": "CONFLICTOLOGÍA URINARIA (59 conflictos)",
        "subsistemas": {
            "RENAL": [
                ('1', 'Impotencia al enfrentar la situación', '"Esta vida es demasiado para mí"'),
                ('2', 'Derrumbamiento', '"He perdido todas mis referencias, mis ejes"'),
                ('3', 'Pez fuera del agua', '"Estoy fuera de mi elemento" — desplazado, inmigrante, damnificado'),
                ('4', 'Grave extravío', '"Me siento totalmente perdido"'),
                ('5', 'Grave abandono', '"No tengo a nadie en mi vida"'),
                ('1', 'Grave pérdida', '"Lo perdí todo"'),
                ('2', 'Sueño existencial perdido', '"Todo lo que deseaba ahora es imposible"'),
                ('3', 'Incapacidad de hacer frente', '"No sé cómo dar la cara a esta situación"'),
                ('4', 'Miedo a lo desconocido', '"Me aterra eso aunque no lo he visto / no ha sucedido"'),
                ('5', 'Sangre', '"Hay algo malo en la sangre que corre por mis venas, familiar"'),
                ('1', 'Líquidos', '"No quiero perder el dinero / No quiero que mi madre se vaya"'),
                ('2', 'Miedo al derrumbamiento', '"No quiero perderlo todo"'),
                ('3', 'Sostén de referencia', '"No quiero perder mis ejes, dinero, vínculos"'),
                ('4', 'Desvalorización por falta de territorio', '"No valgo nada desde que perdí la casa"'),
                ('5', 'Economía forzada', '"Necesito los desechos que todavía pueden ser aprovechados"'),
                ('1', 'Referencia forzada', '"Debo sobrevivir en estas circunstancias aunque son peligrosas"'),
                ('2', 'Líquido pulmonar', '"Quiero sacar el agua de mi pulmón"'),
                ('3', 'Alargamiento de vida', '"Quiero seguir vivo, bajo mis propias referencias"'),
                ('4', 'Apoyo en tema de líquidos', '"Necesito que me ayuden porque me ahogo"'),
                ('5', 'Aniquilamiento', '"Esta forma de vida es insostenible, no puedo más"'),
            ],
            "DE GLOMÉRULO": [
                ('1', 'Proteína', '"Hay una carne que quiero eliminar / Alguien se ahogó con una albóndiga"'),
                ('2', 'Miedo al derrumbamiento', '"Temo que mis ejes se pierdan, y yo me muera en el proceso"'),
                ('3', 'Huida', '"Tengo que escapar de este lugar"'),
                ('4', 'Canibalismo', '"Hay una persona a la que hay que eliminar"'),
                ('5', 'Atracción insuficiente', '"No logro atraer a la pareja, tengo que atraerla con olor"'),
                ('1', 'Desarraigo', '"Ya perdí todo, aquí no hay nada para mí"'),
                ('2', 'Territorial con marca ajena', '"No quiero que otros marquen mi territorio"'),
                ('3', 'Ocupación territorial', '"Alguien ya invadió mi territorio"'),
            ],
            "DE VEJIGA": [
                ('1', 'Marcaje del territorio', '"Quiero marcar lo que es mío / Necesito delimitar mi territorio"'),
                ('2', 'Conflicto de territorio amenazado', '"Alguien quiere quitarme lo que es mío"'),
                ('3', 'Conflicto de los límites del territorio', '"No sé dónde terminan mis límites y empiezan los del otro"'),
                ('4', 'Conflicto de invasión por marca ajena', '"Alguien ha marcado lo que es mío"'),
                ('5', 'Conflicto de la pérdida del marcaje', '"Perdí lo que había marcado como mío"'),
                ('1', 'Conflicto de la retención territorial', '"Tengo que retener lo que es mío a como dé lugar"'),
                ('2', 'Conflicto de la expulsión del intruso', '"Necesito expulsar al que invadió mi territorio"'),
                ('3', 'Conflicto del territorio sin dueño', '"Lo que debería ser mío no tiene dueño"'),
            ],
        }
    },

    # ══════════════════════════════════════════════════════════════════
    "inmunologico": {
        "titulo": "CONFLICTOLOGÍA INMUNOLÓGICA (73 conflictos)",
        "subsistemas": {
            "INMUNOLÓGICA": [
                ('1', 'Miedo al combate', '"No tengo permitido pelear, defenderme, accionar"'),
                ('2', 'Impotencia ante el combate', '"Para qué pelear si no voy a poder ganar / Me niego a defenderme"'),
                ('3', 'Miedo a lo desconocido + identidad', '"Tengo miedo de todo lo extraño porque no sé quién soy yo"'),
                ('4', 'Identidad endeble', '"No sé poner límites estables / Palabras y emociones ajenas me afectan demasiado"'),
                ('5', 'Autoabandono', '"Tengo que renunciar a mis deseos para sobrevivir / Los deseos de los demás son más importantes"'),
                ('1', 'Miedo al abandono', '"Si soy como soy, se terminarán yendo"'),
                ('2', 'Miedo al rechazo', '"No me permito ser, porque no seré amado / Me señalarán si me acepto"'),
                ('3', 'Carencia afectiva', '"No me siento amado / Nadie me quiere"'),
                ('4', 'Identidad invadida', '"Carezco de aspiración y territorio propio, pertenezco a otra persona"'),
                ('5', 'Enemigo interno', '"El agresor está en mi familia"'),
                ('1', 'Familia patógena', '"Estoy dentro de una familia tóxica"'),
                ('2', 'Autoreconocimiento', '"No soy reconocido por nadie / Quiero ser reconocido por una familia que no reconozco"'),
                ('3', 'Autodestrucción', '"Mi identidad debe ser destruída / Debo destruir mi identidad"'),
                ('4', 'Límitrofe', '"No sé dónde empiezo yo y termina el otro / No sé quién soy"'),
            ],
            "ESPLÉNICA": [
                ('1', 'Hemorragia virtual', '"Tengo miedo intenso a perder la sangre, de morir en un baño de sangre"'),
                ('2', 'Grave conflicto familiar', '"Tengo un problema que no sé cómo resolver con mis lazos de sangre"'),
                ('3', 'Hemorragia simbólica', '"Siento que esta herida aún la tengo abierta"'),
            ],
            "AMIGDALINA": [
                ('1', 'Bocado arrebatado', '"No puedo tragar el bocado que ya he comenzado a tragar, porque me lo arrancan"'),
                ('2', 'Bocado impuesto', '"No me quiero tragar esto que me imponen / No puedo responder como yo quisiera"'),
                ('3', 'Bocado demasiado grande', '"No me puedo tragar esto, es demasiado para mí"'),
                ('4', 'Bocado improbable', '"No creo poder alcanzar este bocado que es vital para mí"'),
                ('5', 'Cólera encerrada', ''),
                ('1', 'Defensa infantil impedida', '"No me puedo defender de mis padres / hermanos / No me dan permiso de defenderme"'),
                ('2', 'Amor parental insuficiente', '"Mi madre / padre no me ama en la forma o magnitud que yo quisiera"'),
            ],
            "GANGLIONAR": [
                ('1', 'Conflicto de linfa', '"Algo no fluye bien en mi vida / Hay un estancamiento"'),
                ('2', 'Conflicto de contaminación grupal', '"Mi grupo/familia me contamina"'),
                ('3', 'Conflicto de linfa familiar', '"Hay algo tóxico que circula en mi familia"'),
                ('4', 'Conflicto de la identidad del grupo', '"No sé a qué grupo pertenezco"'),
                ('5', 'Conflicto de la batalla interna', '"Hay una lucha dentro de mí que no para"'),
                ('1', 'Conflicto de pertenencia', '"No me siento parte de ningún grupo"'),
                ('2', 'Conflicto de la familia tóxica', '"Mi familia me envenena"'),
                ('3', 'Conflicto de la red de apoyo perdida', '"Perdí mi red de apoyo"'),
                ('4', 'Conflicto de la invasión de la identidad grupal', '"Me quieren cambiar quién soy dentro del grupo"'),
            ],
            "DEL TIMO": [
                ('1', 'Conflicto de identidad amenazada desde la infancia', '"Desde pequeño me amenazaron en lo que soy"'),
                ('2', 'Conflicto de la inocencia perdida', '"Perdí la inocencia antes de tiempo"'),
                ('3', 'Conflicto de la infancia robada', '"Me robaron la infancia"'),
            ],
            "LEUCOCITARIA": [
                ('1', 'Conflicto del combatiente solo', '"Tengo que luchar solo contra todo"'),
                ('2', 'Conflicto de la defensa excesiva', '"Me defiendo de todo aunque no haya amenaza real"'),
                ('3', 'Conflicto del enemigo omnipresente', '"Hay enemigos por todas partes"'),
                ('4', 'Conflicto de la destrucción del yo', '"Algo en mí quiere destruir lo que soy"'),
                ('5', 'Conflicto de la identidad del guerrero', '"Nací para pelear / Siempre estoy en guerra"'),
            ],
            "LINFÁTICA": [
                ('1', 'Conflicto de circulación de la identidad', '"No sé quién soy en este flujo de vida"'),
                ('2', 'Conflicto del flujo familiar contaminado', '"Hay algo que circula en mi familia y me daña"'),
                ('3', 'Conflicto del estancamiento', '"Me siento estancado / nada fluye en mi vida"'),
                ('4', 'Conflicto de la linfa transgeneracional', '"Hay algo que viene de atrás en mi linaje"'),
            ],
            "DE SIDA": [
                ('1', 'Conflicto de identidad sexual + muerte', '"Mi identidad sexual me puede matar / es peligrosa"'),
                ('2', 'Conflicto de la sexualidad prohibida + muerte', '"La sexualidad me puede llevar a la muerte"'),
                ('3', 'Conflicto de la muerte por identidad', '"Ser como soy me puede costar la vida"'),
                ('4', 'Conflicto del linaje contaminado + muerte', '"Hay algo en mi linaje que me puede matar"'),
                ('5', 'Conflicto del abandono + muerte', '"Me abandonaron a mi suerte y eso me puede matar"'),
                ('1', 'Conflicto del rechazo + muerte', '"Me rechazaron de tal manera que es como si me hubieran dado la muerte"'),
                ('2', 'Conflicto de la autodestrucción + identidad', '"Tengo que destruirme para ser aceptado"'),
                ('3', 'Conflicto de la impureza mortal', '"Lo que hice o lo que me hicieron me puede matar"'),
            ],
        }
    },

    # ══════════════════════════════════════════════════════════════════
    "neurosensorial": {
        "titulo": "CONFLICTOLOGÍA NEUROSENSORIAL (130 conflictos)",
        "subsistemas": {
            "TUMORAL": [
                ('1', 'Solución intelectual', '"Tengo que pensar una solución que está más allá de mi capacidad mental"'),
                ('2', 'Apoyo intelectual', '"Necesito que me apoyen para encontrar la solución mental que no encuentro"'),
                ('3', 'Solución imposible', '"Sé cómo arreglar la situación, pero no puedo hacerlo porque moriré / morirán"'),
                ('4', 'Solución equivocada', '"Arreglé una situación que no era la que tenía que arreglar"'),
                ('5', 'Larga duración', '"Llevo años atorado en este problema que no se soluciona"'),
                ('1', 'En balance', '"Cuando parece arreglarse el problema surge un nuevo matiz"'),
                ('2', 'Negación permanente', '"Todo está bien siempre, no me pasa nada"'),
                ('3', 'Campeón', '"Tengo que ser el primer lugar en lo poderoso / inteligente / fuerte"'),
                ('4', 'El salvador único', '"Tengo que encargarme de todos, atenderlos, proteger a todo mundo"'),
            ],
            "CEFÁLICA": [
                ('1', 'Miedo a vacío', '"Me aterroriza la ausencia de estímulos"'),
                ('2', 'Correcaminos', '"Tengo que correr a todas partes, siempre"'),
                ('3', 'Miedo a morir', ''),
                ('4', 'Prolongación de la vida', '"Quiero que lo vivo continúe"'),
                ('5', 'Eternidad', '"Quiero que lo que yo vivo continúe"'),
                ('1', 'Desvalorización intelectual', '"No soy tan listo como quisiera"'),
                ('2', 'Descanso imposible', '"No descansaré hasta que…"'),
                ('3', 'Necedad', '"Esto tiene que ser como yo pienso"'),
                ('4', 'Saturación mental', '"Estoy abrumado entre todos mis pensamientos"'),
                ('5', 'Perfeccionismo', '"Tengo que alcanzar un estándar altísimo"'),
                ('1', 'No aceptación de la realidad', '"Esto que sucedió no puede estar pasando"'),
                ('2', 'Acción imposible', '"No sirvo de nada porque no puedo actuar"'),
                ('3', 'Sufrimiento inaceptable', '"No puedo / quiero reconocer el sufrimiento que vivo"'),
                ('4', 'Impotencia intelectual', '"No puedo encontrar la solución a mi problema"'),
                ('5', 'Frustración sexual llevada a lo intelectual', '"No logro encontrar la relación íntima que quiero"'),
                ('1', 'Duda sobre el padre', '"No sé si este hombre es mi padre"'),
                ('2', 'Rencor hacia el padre', '"Odio a mi papá por cierta situación"'),
            ],
            "ALZHEIMER": [
                ('1', 'Conflicto de identidad perdida', '"No sé quién soy / Quiero olvidar quién fui"'),
                ('2', 'Conflicto de la memoria insoportable', '"Hay algo en mi pasado que no puedo recordar"'),
                ('3', 'Conflicto del regreso al pasado', '"Prefiero vivir en el pasado que en el presente"'),
                ('4', 'Conflicto del olvido protector', '"Si olvido, no sufro"'),
                ('5', 'Conflicto de la identidad transgeneracional', '"Hay algo en mi linaje que quiero olvidar"'),
                ('1', 'Conflicto de la solución imposible que hay que olvidar', '"El problema no tiene solución, prefiero olvidarlo"'),
                ('2', 'Conflicto de la vergüenza que hay que olvidar', '"Lo que hice / me hicieron es tan vergonzoso que prefiero olvidarlo"'),
            ],
            "HEMIPLÉJICA": [
                ('1', 'Conflicto de la parálisis ante la autoridad', '"Me paralizo ante quien tiene poder sobre mí"'),
                ('2', 'Conflicto del movimiento bloqueado por la autoridad', '"No puedo avanzar porque alguien me lo impide"'),
                ('3', 'Conflicto del movimiento hacia el padre bloqueado', '"Quiero acercarme a mi padre pero algo me lo impide"'),
                ('4', 'Conflicto del movimiento hacia la madre bloqueado', '"Quiero acercarme a mi madre pero algo me lo impide"'),
                ('5', 'Conflicto de la parálisis existencial', '"No puedo avanzar en ninguna dirección"'),
            ],
            "HEMORRÁGICA": [
                ('1', 'Conflicto de la pérdida de la dirección vital', '"Perdí el rumbo de mi vida"'),
                ('2', 'Conflicto de la explosión interna', '"Algo explotó dentro de mí"'),
                ('3', 'Conflicto de la presión insoportable', '"La presión que siento es demasiada"'),
                ('4', 'Conflicto del desbordamiento', '"Ya no puedo contener más"'),
            ],
            "INSOMNIO": [
                ('1', 'Conflicto de la vigilancia permanente', '"No me puedo relajar porque algo o alguien me amenaza"'),
                ('2', 'Conflicto de la solución nocturna', '"Tengo que resolver este problema mientras duermo"'),
                ('3', 'Conflicto del miedo nocturno', '"La noche es peligrosa"'),
                ('4', 'Conflicto de la culpa que no deja dormir', '"Lo que hice no me deja descansar"'),
                ('5', 'Conflicto de la preocupación crónica', '"Siempre hay algo de qué preocuparse"'),
                ('1', 'Conflicto del territorio nocturno amenazado', '"En la noche mi territorio está en peligro"'),
            ],
            "NERVIOSA": [
                ('1', 'Conflicto de la dirección correcta', '"No sé qué camino tomar"'),
                ('2', 'Conflicto de la coordinación perdida', '"Ya no puedo coordinar lo que hago"'),
                ('3', 'Conflicto del control perdido', '"Perdí el control de mi vida / de mi cuerpo"'),
                ('4', 'Conflicto de la tensión permanente', '"Siempre estoy tenso, a la defensiva"'),
                ('5', 'Conflicto de la comunicación neurológica', '"Algo en mí no se comunica bien"'),
                ('1', 'Conflicto del sistema nervioso en guerra', '"Mi sistema nervioso está en guerra"'),
                ('2', 'Conflicto de la desconexión', '"Me siento desconectado de mí mismo y del mundo"'),
                ('3', 'Conflicto del corto circuito', '"Hay algo que cortocircuita mi funcionamiento"'),
                ('4', 'Conflicto de la sobrecarga nerviosa', '"Estoy saturado, mi sistema no da más"'),
            ],
            "OCULAR": [
                ('1', 'Conflicto de lo que no quiero ver', '"Hay algo que no quiero ver"'),
                ('2', 'Conflicto de lo que no puedo ver', '"No me permiten ver algo"'),
                ('3', 'Conflicto de lo que quiero ver y no puedo', '"Quiero ver algo y no me lo permiten"'),
                ('4', 'Conflicto del peligro visual', '"Hay algo que temo ver"'),
                ('5', 'Conflicto de la separación visual', '"Me separé de lo que quería ver / de lo que me gustaba ver"'),
                ('1', 'Conflicto de la visión del futuro', '"No quiero / puedo ver lo que viene"'),
                ('2', 'Conflicto de la visión del pasado', '"No quiero ver lo que fue"'),
                ('3', 'Conflicto del bocado visual', '"Quiero atrapar algo con la mirada"'),
                ('4', 'Conflicto de la visión del territorio', '"No me dejan ver lo que es mío"'),
                ('5', 'Conflicto de la belleza', '"No quiero ver fealdad / sólo quiero ver belleza"'),
                ('1', 'Conflicto del peligro que quiero ver venir', '"Necesito ver el peligro antes de que llegue"'),
                ('2', 'Conflicto de la mirada del padre', '"Quiero ser visto por mi padre"'),
                ('3', 'Conflicto de la mirada de la madre', '"Quiero ser visto por mi madre"'),
                ('4', 'Conflicto de la mirada del grupo', '"Quiero ser reconocido por mi grupo"'),
                ('5', 'Conflicto de la identidad visual', '"No me reconozco cuando me veo"'),
                ('1', 'Conflicto de la visión de la muerte', '"Vi algo tan terrible que no lo puedo superar"'),
                ('2', 'Conflicto de la separación visual brutal', '"Algo o alguien que amaba desapareció de mi vista"'),
                ('3', 'Conflicto de la mirada rechazada', '"Mi mirada fue rechazada"'),
            ],
            "AUDITIVA": [
                ('1', 'Conflicto de lo que no quiero oír', '"Hay algo que no quiero escuchar"'),
                ('2', 'Conflicto de lo que no puedo oír', '"No me permiten escuchar algo"'),
                ('3', 'Conflicto de lo que quiero oír y no puedo', '"Quiero escuchar algo y no me lo permiten"'),
                ('4', 'Conflicto del peligro auditivo', '"Hay algo que temo oír"'),
                ('5', 'Conflicto de la separación auditiva', '"Me separé de lo que quería escuchar"'),
                ('1', 'Conflicto del ruido insoportable', '"Hay un ruido que no soporto"'),
                ('2', 'Conflicto de las palabras que lastiman', '"Me dijeron algo que no puedo superar"'),
                ('3', 'Conflicto de la orden auditiva', '"Me dieron una orden que me marcó"'),
                ('4', 'Conflicto del silencio impuesto', '"Me impusieron el silencio"'),
                ('5', 'Conflicto de la separación auditiva brutal', '"El sonido de algo o alguien amado desapareció"'),
                ('1', 'Conflicto de la alarma que no sonó', '"Nadie me avisó del peligro que venía"'),
                ('2', 'Conflicto de la orden paterna', '"Mi padre me dio una orden que me marcó"'),
                ('3', 'Conflicto de la orden materna', '"Mi madre me dio una orden que me marcó"'),
                ('4', 'Conflicto de la voz interna', '"Hay una voz dentro de mí que no calla"'),
                ('5', 'Conflicto del mandato auditivo', '"Algo que escuché me programó negativamente"'),
                ('1', 'Conflicto de la memoria auditiva traumática', '"Un sonido me recuerda algo traumático"'),
            ],
        }
    },

    # ══════════════════════════════════════════════════════════════════
    "alimenticio": {
        "titulo": "CONFLICTOLOGÍA ALIMENTICIA",
        "subsistemas": {
            "SOBREPESO / OBESIDAD": [
                ('A1', 'Reserva de emergencia', 'Necesidad de acumular para el futuro'),
                ('A2', 'Protección territorial', 'Necesidad de crear una barrera física'),
                ('A3', 'Carencia afectiva', 'Llenar con comida el vacío emocional'),
                ('A4', 'Miedo al abandono', 'La gordura como protección contra el rechazo'),
                ('A5', 'Conflicto de supervivencia', 'Guardar reservas ante escasez real o imaginaria'),
            ],
            "ANOREXIA / BULIMIA": [
                ('A1', 'Función materna', ''),
                ('A2', 'Amor tóxico', ''),
                ('A3', 'Leche materna tóxica', ''),
                ('A4', 'Nutrición orgánica (Comida = muerte)', ''),
                ('B1', 'Protección insatisfecha', ''),
                ('B2', 'Duelos bloqueados en periodo semilla', ''),
                ('B3', 'Duelos simbólicos en periodo semilla', ''),
                ('B4', 'Proyecto sentido', ''),
                ('C1', 'Duda instintiva', ''),
                ('C2', 'Discordancia', ''),
                ('C3', 'Imagen corporal', ''),
            ],
        }
    },

}


# ── Mapeo de keywords a sistemas ─────────────────────────────────────────────

SISTEMA_KEYWORDS = {
    "respiratorio": [
        "nariz", "olfato", "alergia nasal", "rinitis", "sinusitis", "estornudos",
        "laringe", "voz", "ronquera", "afonía", "garganta", "tráquea", "traqueitis",
        "bronquios", "bronquitis", "broncoespasmo", "pulmones", "alveolos", "enfisema",
        "diafragma", "hipo", "gripe", "influenza", "resfriado", "tos", "tos crónica",
        "asma", "asmático", "apnea", "tabaco", "tabaquismo", "fumar",
        "respiración", "respiratorio", "pulmonar", "pulmón", "falta de aire",
        "ahogo", "asfixia", "disnea", "respirar",
    ],
    "digestivo": [
        "boca", "bucal", "dientes", "encías", "lengua", "saliva", "masticar",
        "estómago", "gástrico", "gastritis", "úlcera", "acidez", "reflujo",
        "náusea", "vómito", "intestino delgado", "intestino grueso", "colon",
        "colitis", "diarrea", "estreñimiento", "hígado", "hepático", "hepatitis",
        "cirrosis", "vesícula", "biliar", "bilis", "cálculos biliares",
        "ano", "anal", "hemorroides", "fisura anal", "peritoneo", "peritonitis",
        "digestión", "digestivo", "abdomen", "abdominal", "inflamación intestinal",
        "hinchazón", "flatulencias", "gases", "intestino irritable", "crohn",
        "hígado", "pancreatitis", "quimo",
    ],
    "endocrino": [
        "tiroides", "hipotiroidismo", "hipertiroidismo", "bocio", "diabetes",
        "insulina", "páncreas", "glucosa", "azúcar", "hipófisis", "pituitaria",
        "hormona", "suprarrenal", "cortisol", "adrenalina", "paratiroides",
        "calcio", "metabolismo", "metabólico", "endócrino", "glándula",
        "cansancio crónico", "fatiga crónica", "hipoglucemia", "hiperglucemia",
        "papiloma", "endocrino", "hipofisiario", "tiroideo", "pancreático",
    ],
    "cardiovascular": [
        "corazón", "cardíaco", "infarto", "arritmia", "taquicardia", "bradicardia",
        "presión arterial", "hipertensión", "hipotensión", "presión alta", "presión baja",
        "arteria", "arterial", "vena", "venoso", "circulación", "colesterol",
        "triglicéridos", "lípidos", "válvula", "valvular", "pericardio",
        "angina", "dolor de pecho", "palpitaciones", "trombosis", "flebitis",
        "varices", "varicosas", "cardiovascular", "vascular",
    ],
    "osteomuscular": [
        "hueso", "óseo", "fractura", "osteoporosis", "articulación", "columna",
        "vertebral", "espalda", "lumbar", "cervical", "torácica", "hernia de disco",
        "rodilla", "cadera", "hombro", "codo", "muñeca", "tobillo", "pie",
        "músculo", "muscular", "contractura", "espasmo", "fibromialgia",
        "tendón", "tendinitis", "ligamento", "esguince", "artritis", "artrosis",
        "reumatismo", "reuma", "dolor de espalda", "dolor de huesos",
        "dolor articular", "periostio", "locomotor", "cuello", "cervicalgia",
        "lumbago", "escoliosis",
    ],
    "dermato_lipofascial": [
        "piel", "dermatitis", "eczema", "psoriasis", "urticaria", "acné",
        "sarpullido", "picazón", "comezón", "prurito", "escozor", "herpes",
        "varicela", "zona", "herpes zóster", "manchas en la piel", "vitíligo",
        "alergia cutánea", "grasa", "lipoma", "celulitis", "fascia",
        "tejido conectivo", "tejido adiposo", "dermatológico", "cutáneo", "epidermis",
        "papiloma cutáneo",
    ],
    "reproductivo": [
        "ovario", "quiste ovárico", "ovario poliquístico", "útero", "uterino",
        "mioma", "endometriosis", "matriz", "menstruación", "ciclo menstrual",
        "regla", "período", "vagina", "vaginal", "flujo", "candidiasis",
        "próstata", "testículo", "testicular", "pene", "disfunción eréctil",
        "impotencia sexual", "mama", "seno", "pecho", "mastitis",
        "fertilidad", "infertilidad", "embarazo", "aborto", "reproductivo",
        "sexual", "libido", "sexualidad", "menopausia", "climaterio",
        "amenorrea", "dismenorrea",
    ],
    "urinario": [
        "riñón", "renal", "insuficiencia renal", "cálculos renales",
        "piedras en el riñón", "vejiga", "cistitis", "infección urinaria",
        "infección de vías urinarias", "uretra", "orina", "orinar",
        "incontinencia urinaria", "retención urinaria", "urinario",
        "glomérulo", "nefritis", "ardor al orinar", "frecuencia urinaria",
    ],
    "inmunologico": [
        "inmune", "inmunológico", "sistema inmune", "defensas bajas",
        "alergias", "alergia", "alérgico", "bazo", "esplénico", "amígdalas",
        "amigdalitis", "anginas", "ganglios", "ganglionar", "linfoma",
        "timo", "leucocitos", "linfocitos", "linfático", "linfa",
        "VIH", "SIDA", "inmunodeficiencia", "autoinmune", "lupus",
        "esclerosis múltiple", "artritis reumatoide",
    ],
    "neurosensorial": [
        "cerebro", "neurológico", "sistema nervioso", "nervio",
        "dolor de cabeza", "migraña", "cefalea", "jaqueca",
        "vértigo", "mareo", "tinnitus", "zumbido de oídos",
        "insomnio", "no puedo dormir", "alteración del sueño",
        "ansiedad", "ataques de pánico", "angustia", "depresión",
        "alzheimer", "demencia", "parkinson", "epilepsia", "convulsiones",
        "parálisis", "hemiplejia", "accidente cerebrovascular", "derrame",
        "embolia", "ojo", "ocular", "visión", "miopía", "conjuntivitis",
        "glaucoma", "oído", "auditivo", "sordera", "hipoacusia",
        "estrés", "tensión nerviosa", "tumor cerebral",
    ],
    "alimenticio": [
        "sobrepeso", "obesidad", "anorexia", "bulimia",
        "trastorno alimenticio", "compulsión al comer", "comer en exceso",
        "apetito", "hambre compulsiva", "no quiero comer",
        "miedo a engordar", "imagen corporal", "peso",
        "adelgazar", "dieta", "atracón", "vomitar",
    ],
}


# ── Mapa síntoma → subsistema específico ─────────────────────────────────────

SINTOMA_SUBSISTEMA = {
    # Digestivo
    "hemorroides": ("digestivo", "ANAL"),
    "fisura anal": ("digestivo", "ANAL"),
    "estreñimiento": ("digestivo", "INTESTINAL GRUESA"),
    "colitis": ("digestivo", "INTESTINAL GRUESA"),
    "colon": ("digestivo", "INTESTINAL GRUESA"),
    "diarrea": ("digestivo", "INTESTINAL GRUESA"),
    "intestino irritable": ("digestivo", "INTESTINAL GRUESA"),
    "crohn": ("digestivo", "INTESTINAL GRUESA"),
    "gastritis": ("digestivo", "ESTOMACAL"),
    "úlcera": ("digestivo", "ESTOMACAL"),
    "reflujo": ("digestivo", "ESTOMACAL"),
    "acidez": ("digestivo", "ESTOMACAL"),
    "náusea": ("digestivo", "ESTOMACAL"),
    "vómito": ("digestivo", "ESTOMACAL"),
    "hígado": ("digestivo", "HEPÁTICA"),
    "hepatitis": ("digestivo", "HEPÁTICA"),
    "cirrosis": ("digestivo", "HEPÁTICA"),
    "vesícula": ("digestivo", "BILIAR"),
    "cálculos biliares": ("digestivo", "BILIAR"),
    "bilis": ("digestivo", "BILIAR"),
    "peritonitis": ("digestivo", "PERITONEAL"),
    # Respiratorio
    "rinitis": ("respiratorio", "NASAL"),
    "sinusitis": ("respiratorio", "NASAL"),
    "alergia nasal": ("respiratorio", "NASAL"),
    "estornudos": ("respiratorio", "NASAL"),
    "ronquera": ("respiratorio", "LARÍNGEA"),
    "afonía": ("respiratorio", "LARÍNGEA"),
    "laringitis": ("respiratorio", "LARÍNGEA"),
    "tos": ("respiratorio", "TOS"),
    "bronquitis": ("respiratorio", "BRONQUIAL"),
    "broncoespasmo": ("respiratorio", "BRONQUIAL"),
    "asma": ("respiratorio", "ASMÁTICA"),
    "asmático": ("respiratorio", "ASMÁTICA"),
    "enfisema": ("respiratorio", "ALVEOLAR"),
    "apnea": ("respiratorio", "APNEA"),
    "tabaquismo": ("respiratorio", "TABAQUISTA"),
    "fumar": ("respiratorio", "TABAQUISTA"),
    "hipo": ("respiratorio", "DIAFRAGMÁTICA"),
    "gripe": ("respiratorio", "GRIPAL"),
    "influenza": ("respiratorio", "GRIPAL"),
    # Endócrino
    "tiroides": ("endocrino", "TIROIDEA"),
    "hipotiroidismo": ("endocrino", "TIROIDEA"),
    "hipertiroidismo": ("endocrino", "TIROIDEA"),
    "bocio": ("endocrino", "TIROIDEA"),
    "diabetes": ("endocrino", "PANCREÁTICA"),
    "insulina": ("endocrino", "PANCREÁTICA"),
    "glucosa": ("endocrino", "PANCREÁTICA"),
    "páncreas": ("endocrino", "PANCREÁTICA"),
    "hipófisis": ("endocrino", "HIPOFISIARIA"),
    "pituitaria": ("endocrino", "HIPOFISIARIA"),
    "papiloma": ("endocrino", "HIPOFISIARIA"),
    "cortisol": ("endocrino", "SUPRARRENAL"),
    "adrenalina": ("endocrino", "SUPRARRENAL"),
    "paratiroides": ("endocrino", "PARATIROIDEA"),
    "calcio": ("endocrino", "PARATIROIDEA"),
    # Cardiovascular
    "infarto": ("cardiovascular", "MIOCARDIAL"),
    "arritmia": ("cardiovascular", "DEL RITMO"),
    "taquicardia": ("cardiovascular", "DEL RITMO"),
    "bradicardia": ("cardiovascular", "DEL RITMO"),
    "palpitaciones": ("cardiovascular", "DEL RITMO"),
    "válvula": ("cardiovascular", "VALVULAR"),
    "presión alta": ("cardiovascular", "DE PRESIÓN"),
    "hipertensión": ("cardiovascular", "DE PRESIÓN"),
    "presión baja": ("cardiovascular", "DE PRESIÓN"),
    "hipotensión": ("cardiovascular", "DE PRESIÓN"),
    "colesterol": ("cardiovascular", "LIPÍDICA"),
    "triglicéridos": ("cardiovascular", "LIPÍDICA"),
    "varices": ("cardiovascular", "VENOSA"),
    "trombosis": ("cardiovascular", "VENOSA"),
    "flebitis": ("cardiovascular", "VENOSA"),
    "angina": ("cardiovascular", "MIOCARDIAL"),
    # Osteomuscular
    "lumbar": ("osteomuscular", "VERTEBRAL"),
    "lumbago": ("osteomuscular", "VERTEBRAL"),
    "hernia de disco": ("osteomuscular", "VERTEBRAL"),
    "escoliosis": ("osteomuscular", "VERTEBRAL"),
    "cervical": ("osteomuscular", "VERTEBRAL"),
    "cervicalgia": ("osteomuscular", "VERTEBRAL"),
    "artritis": ("osteomuscular", "ARTICULAR"),
    "artrosis": ("osteomuscular", "ARTICULAR"),
    "rodilla": ("osteomuscular", "ARTICULAR"),
    "cadera": ("osteomuscular", "ARTICULAR"),
    "hombro": ("osteomuscular", "ARTICULAR"),
    "tendinitis": ("osteomuscular", "TENDONES"),
    "esguince": ("osteomuscular", "LIGAMENTOS"),
    "fibromialgia": ("osteomuscular", "MUSCULAR"),
    "contractura": ("osteomuscular", "MUSCULAR"),
    "osteoporosis": ("osteomuscular", "ÓSEA DIVERSA"),
    "fractura": ("osteomuscular", "ÓSEA DIVERSA"),
    # Dermatológico
    "psoriasis": ("dermato_lipofascial", "CONTACTO IMPUESTO"),
    "eczema": ("dermato_lipofascial", "CONTACTO IMPUESTO"),
    "dermatitis": ("dermato_lipofascial", "CONTACTO IMPUESTO"),
    "urticaria": ("dermato_lipofascial", "CONTACTO IMPUESTO"),
    "acné": ("dermato_lipofascial", "CONTACTO IMPUESTO"),
    "herpes": ("dermato_lipofascial", "SEPARACIÓN"),
    "vitíligo": ("dermato_lipofascial", "SEPARACIÓN"),
    "manchas": ("dermato_lipofascial", "DESVALORIZACIÓN"),
    "lipoma": ("dermato_lipofascial", "CONTACTO IMPUESTO"),
    # Reproductivo
    "ovario": ("reproductivo", "OVÁRICA"),
    "quiste ovárico": ("reproductivo", "OVÁRICA"),
    "ovario poliquístico": ("reproductivo", "OVÁRICA"),
    "útero": ("reproductivo", "UTERINA"),
    "mioma": ("reproductivo", "UTERINA"),
    "endometriosis": ("reproductivo", "UTERINA"),
    "menstruación": ("reproductivo", "MENSTRUAL"),
    "regla": ("reproductivo", "MENSTRUAL"),
    "amenorrea": ("reproductivo", "MENSTRUAL"),
    "dismenorrea": ("reproductivo", "MENSTRUAL"),
    "vagina": ("reproductivo", "VAGINAL"),
    "candidiasis": ("reproductivo", "VAGINAL"),
    "flujo": ("reproductivo", "VAGINAL"),
    "próstata": ("reproductivo", "PROSTÁTICA"),
    "testículo": ("reproductivo", "TESTICULAR"),
    "pene": ("reproductivo", "FÁLICA"),
    "disfunción eréctil": ("reproductivo", "FÁLICA"),
    "mama": ("reproductivo", "MAMARIA"),
    "seno": ("reproductivo", "MAMARIA"),
    "mastitis": ("reproductivo", "MAMARIA"),
    "menopausia": ("reproductivo", "MENSTRUAL"),
    # Urinario
    "cistitis": ("urinario", "DE VEJIGA"),
    "infección urinaria": ("urinario", "DE VEJIGA"),
    "vejiga": ("urinario", "DE VEJIGA"),
    "riñón": ("urinario", "RENAL"),
    "cálculos renales": ("urinario", "RENAL"),
    "piedras en el riñón": ("urinario", "RENAL"),
    "incontinencia": ("urinario", "DE VEJIGA"),
    # Inmunológico
    "amígdalas": ("inmunologico", "AMIGDALINA"),
    "amigdalitis": ("inmunologico", "AMIGDALINA"),
    "anginas": ("inmunologico", "AMIGDALINA"),
    "bazo": ("inmunologico", "ESPLÉNICA"),
    "ganglios": ("inmunologico", "GANGLIONAR"),
    "linfoma": ("inmunologico", "GANGLIONAR"),
    "lupus": ("inmunologico", "INMUNOLÓGICA"),
    "esclerosis múltiple": ("inmunologico", "INMUNOLÓGICA"),
    # Neurosensorial
    "migraña": ("neurosensorial", "CEFÁLICA"),
    "cefalea": ("neurosensorial", "CEFÁLICA"),
    "jaqueca": ("neurosensorial", "CEFÁLICA"),
    "dolor de cabeza": ("neurosensorial", "CEFÁLICA"),
    "insomnio": ("neurosensorial", "INSOMNIO"),
    "no puedo dormir": ("neurosensorial", "INSOMNIO"),
    "vértigo": ("neurosensorial", "CEFÁLICA"),
    "tinnitus": ("neurosensorial", "AUDITIVA"),
    "zumbido": ("neurosensorial", "AUDITIVA"),
    "sordera": ("neurosensorial", "AUDITIVA"),
    "conjuntivitis": ("neurosensorial", "OCULAR"),
    "glaucoma": ("neurosensorial", "OCULAR"),
    "visión": ("neurosensorial", "OCULAR"),
    "ansiedad": ("neurosensorial", "NERVIOSA"),
    "depresión": ("neurosensorial", "NERVIOSA"),
    "pánico": ("neurosensorial", "NERVIOSA"),
    "alzheimer": ("neurosensorial", "ALZHEIMER"),
    "demencia": ("neurosensorial", "ALZHEIMER"),
    "parálisis": ("neurosensorial", "HEMIPLÉJICA"),
    "hemiplejia": ("neurosensorial", "HEMIPLÉJICA"),
    # Alimenticio
    "sobrepeso": ("alimenticio", "SOBREPESO / OBESIDAD"),
    "obesidad": ("alimenticio", "SOBREPESO / OBESIDAD"),
    "anorexia": ("alimenticio", "ANOREXIA / BULIMIA"),
    "bulimia": ("alimenticio", "ANOREXIA / BULIMIA"),
    # Dermatológico-lipofascial (caída de cabello / alopecia)
    "pérdida de cabello": ("dermato_lipofascial", "DESVALORIZACIÓN"),
    "perdida de cabello": ("dermato_lipofascial", "DESVALORIZACIÓN"),
    "caída de cabello": ("dermato_lipofascial", "DESVALORIZACIÓN"),
    "caida de cabello": ("dermato_lipofascial", "DESVALORIZACIÓN"),
    "alopecia": ("dermato_lipofascial", "DESVALORIZACIÓN"),
    "calvicie": ("dermato_lipofascial", "DESVALORIZACIÓN"),
    "se le cae el cabello": ("dermato_lipofascial", "DESVALORIZACIÓN"),
    "se le cae el pelo": ("dermato_lipofascial", "DESVALORIZACIÓN"),
    "caída de pelo": ("dermato_lipofascial", "DESVALORIZACIÓN"),
}


# ── Funciones principales ─────────────────────────────────────────────────────

def get_subsystem_table(sistema: str, subsistema: str) -> str:
    """
    Devuelve la tabla de UN solo subsistema formateado para mostrar al terapeuta.
    """
    data = CONFLICTOS.get(sistema)
    if not data:
        return ""

    conflictos = data["subsistemas"].get(subsistema)
    if not conflictos:
        return ""

    sistema_titulo = data["titulo"].split("(")[0].strip()
    lines = [f"\n📋 {sistema_titulo} — {subsistema}\n"]
    for num, nombre, frase in conflictos:
        if frase:
            lines.append(f"  {num}. {nombre} — {frase}")
        else:
            lines.append(f"  {num}. {nombre}")
    lines.append(f"\n{'─'*40}")
    lines.append("Pregunta por bloque (rojo/naranja/amarillo/etc.) y luego por número.")
    return "\n".join(lines)


def get_subsystems_list(sistema: str) -> str:
    """
    Devuelve solo la lista de subsistemas (para cuando aún no se sabe cuál es).
    El terapeuta los pregunta a la MS uno por uno.
    """
    data = CONFLICTOS.get(sistema)
    if not data:
        return ""

    sistema_titulo = data["titulo"].split("(")[0].strip()
    subsistemas = list(data["subsistemas"].keys())
    lines = [f"\n📋 {sistema_titulo}\n"]
    lines.append("Pregunta a la MS por cada subsistema:\n")
    for i, sub in enumerate(subsistemas, 1):
        lines.append(f"  {i}. {sub}")
    lines.append(f"\n{'─'*40}")
    lines.append("MS: ¿Es [subsistema]? → Bloque → Número")
    return "\n".join(lines)


def get_conflict_table(sistema: str) -> str:
    """
    Devuelve la tabla completa de conflictos del sistema.
    Solo usar cuando no se puede detectar subsistema específico.
    """
    data = CONFLICTOS.get(sistema)
    if not data:
        return ""

    lines = [f"\n📋 {data['titulo']}\n"]
    lines.append("Muéstrale esta lista al terapeuta para que la lea con la MS:\n")

    for subsistema, conflictos in data["subsistemas"].items():
        lines.append(f"\n{'─'*40}")
        lines.append(f"  {subsistema}:")
        for num, nombre, frase in conflictos:
            if frase:
                lines.append(f"  {num}. {nombre} — {frase}")
            else:
                lines.append(f"  {num}. {nombre}")

    lines.append(f"\n{'─'*40}")
    lines.append("Pregunta por bloque (rojo/naranja/amarillo/etc.) y luego por número.")
    return "\n".join(lines)


def is_patient_narrative(text: str) -> bool:
    """
    Devuelve True si el mensaje parece ser el relato del terapeuta sobre el paciente
    (no un reporte directo de síntoma). En ese caso se suprime la inyección de tablas.

    Dos niveles:
    - Marcadores de alta confianza → True sin importar la longitud del mensaje.
    - Marcadores de confianza media → True solo si el mensaje tiene ≥ 45 caracteres.
    """
    text_lower = text.lower()
    # Alta confianza: siempre narrativa
    if any(marker in text_lower for marker in _STRONG_NARRATIVE):
        return True
    # Confianza media: solo si el texto es largo (evita falsos positivos)
    if len(text) >= 45 and any(marker in text_lower for marker in NARRATIVE_MARKERS):
        return True
    return False


def detect_sintoma(text: str) -> Optional[tuple]:
    """
    Detecta si el texto menciona un síntoma con subsistema conocido.
    Devuelve (sistema, subsistema) o None.

    Reglas:
    - Usa límites de palabra (\b) para evitar coincidencias parciales.
    - Neutraliza referencias a la madre ("su mama", "mi mamá") antes de buscar "mama".
    - Ignora textos de narrativa larga del paciente (is_patient_narrative).
    """
    if is_patient_narrative(text):
        return None

    # Neutralizar "su/mi/tu mamá" para que no dispare el subsistema MAMARIA
    text_clean = _MADRE_PATTERN.sub('__madre__', text)
    text_lower = text_clean.lower()

    for sintoma, (sistema, subsistema) in SINTOMA_SUBSISTEMA.items():
        # Límite de palabra; sintomas multi-palabra también se evalúan bien
        pattern = r'\b' + re.escape(sintoma) + r'\b'
        if re.search(pattern, text_lower):
            return (sistema, subsistema)
    return None


def detect_sistema(text: str) -> Optional[str]:
    """
    Detecta el sistema corporal mencionado en el texto del terapeuta.
    Devuelve el id del sistema o None.
    No dispara en narrativas largas del paciente.
    """
    if is_patient_narrative(text):
        return None

    text_lower = text.lower()

    # Prioridad explícita: palabras de sistema directamente mencionadas
    explicit = {
        "respiratorio": ["respiratorio", "respiratoria", "pulmonar", "bronquial", "laringeo", "laríngeo"],
        "digestivo": ["digestivo", "digestiva", "estomacal", "intestinal", "hepático", "biliar"],
        "endocrino": ["endócrino", "endocrino", "tiroides", "tiroides", "hipofis", "suprarrenal", "pancreático"],
        "cardiovascular": ["cardiovascular", "cardíaco", "cardiaco", "corazón", "arterial", "venoso"],
        "osteomuscular": ["osteomuscular", "locomotor", "muscular", "vertebral", "articular", "óseo", "oseo"],
        "dermato_lipofascial": ["dermatológico", "dermatologico", "piel", "cutáneo", "lipofascial"],
        "reproductivo": ["reproductivo", "reproductiva", "ovárico", "uterino", "prostático", "testicular", "mamario"],
        "urinario": ["urinario", "urinaria", "renal", "vejiga", "riñón", "rinon"],
        "inmunologico": ["inmunológico", "inmunologico", "inmune", "linfático", "ganglionar", "esplénico"],
        "neurosensorial": ["neurosensorial", "neurológico", "neurologico", "cerebral", "ocular", "auditivo"],
        "alimenticio": ["alimenticio", "alimenticia", "sobrepeso", "obesidad", "anorexia", "bulimia"],
    }
    for sistema, words in explicit.items():
        if any(w in text_lower for w in words):
            return sistema

    # Fallback: keywords de síntomas
    scores = {}
    for sistema, keywords in SISTEMA_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in text_lower)
        if score > 0:
            scores[sistema] = score

    if scores:
        return max(scores, key=scores.get)
    return None
