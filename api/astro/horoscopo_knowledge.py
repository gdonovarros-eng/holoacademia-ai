"""
horoscopo_knowledge.py
======================
Base de conocimiento para el módulo de horóscopo personalizado.

Fuentes:
  - "Los Signos del Zodíaco" (492729132) — descripciones detalladas, elementos,
    regentes, correspondencias anatómicas y caracterología.
  - "Sincroniza: Cómo Entender Mejor a Los Signos del Zodíaco" (582802284) —
    perfiles relacionales, amor y compatibilidad.
  - "Los Signos Zodiacales" de Louise Huber (575724277) — perspectiva esotérica
    y psico-espiritual por signo.
  - "Los Símbolos del Horóscopo" de Robert Hand (457824349) — simbolismo
    planetario y significados esenciales.

Contenido exportado:
  SIGNOS               — dict completo de 12 signos
  PLANETAS_TRANSITO    — significados de tránsitos para 10 planetas
  ELEMENTOS            — características de los 4 elementos
  MODALIDADES          — características de las 3 modalidades
  get_signo_solar()    — calcula signo solar a partir de fecha de nacimiento
  get_elemento()       — devuelve elemento de un signo
  get_signos_compatibles() — devuelve lista de signos compatibles
  build_horoscopo_context() — bloque de texto estructurado para prompt LLM
"""

from __future__ import annotations
from datetime import date


# ---------------------------------------------------------------------------
# ELEMENTOS
# ---------------------------------------------------------------------------

ELEMENTOS: dict[str, dict] = {
    "Fuego": {
        "signos": ["Aries", "Leo", "Sagitario"],
        "cualidades": (
            "Vitalidad, entusiasmo, iniciativa, ardor y capacidad de inspirar a "
            "los demás. El fuego es la energía creadora y transformadora que "
            "impulsa la acción y da vida al espíritu."
        ),
        "sombra": "Impulsividad, irascibilidad, imprudencia y dificultad para "
                  "sostener proyectos a largo plazo.",
        "cuerpo": "Metabolismo acelerado, propensión al calor corporal y tensión "
                  "muscular; necesita movimiento físico regular como descarga.",
    },
    "Tierra": {
        "signos": ["Tauro", "Virgo", "Capricornio"],
        "cualidades": (
            "Firmeza, pragmatismo, paciencia, perseverancia y sentido de la "
            "realidad material. La tierra es la energía que construye, consolida "
            "y da forma concreta a los proyectos."
        ),
        "sombra": "Rigidez, egoísmo material, ansiedad ante el cambio y "
                  "tendencia al perfeccionismo paralizante.",
        "cuerpo": "Tendencia a somatizar tensiones en articulaciones, piel y "
                  "sistema digestivo; responde bien al contacto con la naturaleza.",
    },
    "Aire": {
        "signos": ["Géminis", "Libra", "Acuario"],
        "cualidades": (
            "Inteligencia, comunicación, sociabilidad, curiosidad intelectual e "
            "innovación. El aire es la energía mental que conecta ideas y personas, "
            "facilitando el intercambio y la síntesis creativa."
        ),
        "sombra": "Inconstancia, superficialidad, dificultad para comprometerse "
                  "emocionalmente e indecisión crónica.",
        "cuerpo": "Sensibilidad en sistema nervioso, vías respiratorias y "
                  "circulación; requiere descanso mental y técnicas de respiración.",
    },
    "Agua": {
        "signos": ["Cáncer", "Escorpio", "Piscis"],
        "cualidades": (
            "Profundidad emocional, intuición, empatía, imaginación y capacidad "
            "de conexión psíquica. El agua es la energía que nutre, sana y "
            "disuelve los límites del ego hacia lo colectivo."
        ),
        "sombra": "Susceptibilidad, autoengaño, dependencia emocional e "
                  "inseguridad que puede derivar en estados de ánimo fluctuantes.",
        "cuerpo": "Sensibilidad en sistema linfático, hormonal y digestivo; "
                  "vulnerable al estrés emocional no procesado.",
    },
}


# ---------------------------------------------------------------------------
# MODALIDADES
# ---------------------------------------------------------------------------

MODALIDADES: dict[str, dict] = {
    "Cardinal": {
        "signos": ["Aries", "Cáncer", "Libra", "Capricornio"],
        "descripcion": (
            "Los signos cardinales marcan el inicio de cada estación: son signos "
            "de acción, iniciativa y movimiento. Poseen audacia para comenzar "
            "proyectos y una energía que empuja constantemente hacia lo nuevo. "
            "Aries inicia la primavera, Cáncer el verano, Libra el otoño y "
            "Capricornio el invierno."
        ),
        "desafio": "Dificultad para mantener la constancia y terminar lo que "
                   "comienzan; la precipitación puede llevarlos a crisis de "
                   "desánimo pasajeras.",
    },
    "Fijo": {
        "signos": ["Tauro", "Leo", "Escorpio", "Acuario"],
        "descripcion": (
            "Los signos fijos consolidan y profundizan la energía de su estación. "
            "Poseen voluntad sólida, resistencia, lealtad y la capacidad de "
            "mantener el rumbo frente a la adversidad. Tauro fija la primavera, "
            "Leo el verano, Escorpio el otoño y Acuario el invierno."
        ),
        "desafio": "Tendencia a la rigidez, intolerancia al cambio y dificultad "
                   "para soltar lo que ya no les sirve.",
    },
    "Mutable": {
        "signos": ["Géminis", "Virgo", "Sagitario", "Piscis"],
        "descripcion": (
            "Los signos mutables cierran cada estación preparando el tránsito "
            "hacia la siguiente. Son flexibles, adaptativos e integradores, con "
            "una gran capacidad para evolucionar y abrirse a distintas "
            "perspectivas. Géminis cierra la primavera, Virgo el verano, "
            "Sagitario el otoño y Piscis el invierno."
        ),
        "desafio": "Indecisión, dispersión de energía y dificultad para tomar "
                   "posiciones firmes y sostenerlas en el tiempo.",
    },
}


# ---------------------------------------------------------------------------
# SIGNOS
# ---------------------------------------------------------------------------

SIGNOS: dict[str, dict] = {

    "Aries": {
        "fechas": "20 mar – 19 abr",
        "elemento": "Fuego",
        "modalidad": "Cardinal",
        "regente": "Marte",
        "casa_natural": 1,
        "polaridad": "Masculino",
        "cuerpo": ["Cabeza", "Cara", "Ojos", "Mandíbula"],
        "piedras": ["Amatista", "Diamante"],
        "metal": "Hierro",
        "color": "Rojo",
        "palabra_clave": "Yo soy",
        "perfil": (
            "Aries es el primer soplo de la primavera, el fuego primordial que "
            "irrumpe en el mundo con voluntad de existir y dejar huella. Regido "
            "por Marte, su energía es directa, pionera y esencialmente honesta: "
            "lo que siente, lo dice; lo que quiere, lo persigue. No le teme al "
            "riesgo ni a la fricción, pues vive la vida como una aventura que "
            "merece vivirse con toda intensidad. Su mayor don es la capacidad de "
            "iniciativa y el coraje para abrir caminos donde antes no existían; "
            "su sombra es la impaciencia y una cierta incapacidad para detenerse "
            "a evaluar las consecuencias antes de actuar. Louise Huber lo describe "
            "como el signo de los nuevos comienzos y de la formación del yo: cada "
            "Aries porta en su núcleo la pregunta '¿quién soy?' y su vida entera "
            "es una respuesta en movimiento."
        ),
        "fortalezas": [
            "Valentía e iniciativa sin igual",
            "Honestidad y transparencia directa",
            "Energía inagotable para comenzar proyectos",
            "Capacidad de inspirar y liderar",
            "Resiliencia para levantarse tras las caídas",
        ],
        "desafios": [
            "Impulsividad que precede a la reflexión",
            "Impaciencia ante los procesos lentos",
            "Tendencia a la irritabilidad cuando se siente bloqueado",
            "Dificultad para sostener compromisos a largo plazo",
        ],
        "amor": (
            "En el amor, Aries actúa por instinto y flechazo: se enamora rápido, "
            "apasionadamente, con una intensidad que puede resultar abrumadora "
            "para signos más cautelosos. Necesita una pareja que despierte su "
            "admiración y que sepa sostener su fuego sin apagas su llama; el "
            "aburrimiento es su mayor enemigo en la relación. Más sexual que "
            "sensual, busca la chispa continua y la renovación del deseo."
        ),
        "trabajo": (
            "Aries brilla en roles donde pueda liderar, tomar iniciativas y ver "
            "resultados rápidos de su esfuerzo. Emprendedor nato, se siente "
            "constreñido en estructuras muy rígidas o bajo supervisión constante. "
            "Su capacidad de abrir puertas y generar movimiento es un activo "
            "valioso en cualquier equipo que necesite impulso inicial."
        ),
        "salud": (
            "Aries rige la cabeza, los ojos y la cara; es propenso a cefaleas, "
            "sinusitis y tensión cervical cuando acumula estrés o frustración. "
            "La actividad física intensa es su mejor medicina: necesita liberar "
            "la energía marciana para evitar que se vuelva hacia adentro en forma "
            "de irritabilidad o inflamación."
        ),
        "espiritualidad": (
            "Espiritualmente, Aries transita el camino de la autoafirmación "
            "consciente: aprender que la verdadera valentía no consiste en "
            "imponerse a los demás sino en ser fiel a la propia esencia. Huber "
            "señala que su pensamiento semilla esotérico es 'Nací hacia la "
            "materia y hacia la luz': cada encarnación ariana es un acto de "
            "voluntad pura que empuja la conciencia hacia una nueva frontera."
        ),
        "compatible": ["Leo", "Sagitario", "Géminis", "Acuario"],
    },

    "Tauro": {
        "fechas": "20 abr – 20 may",
        "elemento": "Tierra",
        "modalidad": "Fijo",
        "regente": "Venus",
        "casa_natural": 2,
        "polaridad": "Femenino",
        "cuerpo": ["Cuello", "Garganta", "Nuca", "Órganos gustativos"],
        "piedras": ["Alabastro", "Coral", "Ágata"],
        "metal": "Bronce",
        "color": "Verde claro",
        "palabra_clave": "Yo tengo",
        "perfil": (
            "Tauro es la tierra fecunda de la primavera: paciente, sensual, "
            "constructora de mundos duraderos. Regido por Venus, posee una "
            "conexión profunda con la belleza, el placer y los ritmos de la "
            "naturaleza. Allí donde Aries comienza, Tauro consolida; su fuerza "
            "reside en la perseverancia tranquila y en la capacidad de nutrir lo "
            "que crece con paciencia infinita. Su naturaleza sensual no es solo "
            "física sino estética: aprecia la buena mesa, la música, los aromas, "
            "las telas suaves. Huber lo describe como el signo de la autoaceptación "
            "y la confianza en la vida, cuya tarea espiritual es aprender a "
            "transmitir la energía material hacia dimensiones más sutiles, "
            "transformando el apego en gratitud e inofensividad."
        ),
        "fortalezas": [
            "Estabilidad emocional y constancia",
            "Sentido práctico y realismo constructivo",
            "Lealtad y fidelidad profundas",
            "Sensualidad refinada y apreciación de la belleza",
            "Perseverancia para alcanzar metas a largo plazo",
        ],
        "desafios": [
            "Resistencia al cambio y rigidez ante lo desconocido",
            "Posesividad en relaciones afectivas",
            "Tendencia a la obstinación cuando se siente amenazado",
            "Apego excesivo a los bienes materiales y la comodidad",
        ],
        "amor": (
            "En el amor, Tauro es uno de los signos más sensuales y entregados "
            "del zodíaco. Busca relaciones profundas, estables y duraderas; puede "
            "mostrarse cauto al inicio pero, una vez comprometido, da todo de sí. "
            "No perdonará fácilmente la traición o la infidelidad. Necesita "
            "sentirse cortejado con cuidado y detalle, y valora enormemente el "
            "contacto físico y los gestos cotidianos de afecto."
        ),
        "trabajo": (
            "Tauro es un trabajador paciente y metódico que produce resultados "
            "sólidos y duraderos. Destacan en actividades relacionadas con las "
            "finanzas, la gastronomía, el arte, la arquitectura, la agricultura "
            "o cualquier oficio que requiera habilidad manual y atención al "
            "detalle. No le seduce la novedad por sí misma: prefiere la seguridad "
            "de lo probado y el valor de lo bien hecho."
        ),
        "salud": (
            "Tauro rige el cuello, la garganta y los órganos gustativos; es "
            "propenso a problemas de tiroides, laringitis y tensión en la zona "
            "cervical. Su tendencia al sedentarismo y el placer en la buena mesa "
            "puede afectar el metabolismo; el movimiento suave y regular —"
            "especialmente en contacto con la naturaleza— es su mejor equilibrador."
        ),
        "espiritualidad": (
            "La polaridad Tauro-Escorpio es el eje de las posesiones: Tauro "
            "aprende que lo verdaderamente valioso no puede poseerse sino solo "
            "experimentarse. Huber señala que su iluminación llega cuando "
            "transforma el deseo de tener en capacidad de compartir y la "
            "seguridad material en confianza espiritual. Su pensamiento semilla "
            "esotérico es: 'Soy luz y el fruto de la luz son el amor y el "
            "sacrificio cósmico'."
        ),
        "compatible": ["Virgo", "Capricornio", "Cáncer", "Piscis"],
    },

    "Géminis": {
        "fechas": "21 may – 20 jun",
        "elemento": "Aire",
        "modalidad": "Mutable",
        "regente": "Mercurio",
        "casa_natural": 3,
        "polaridad": "Masculino",
        "cuerpo": ["Manos", "Brazos", "Pulmones", "Sistema nervioso"],
        "piedras": ["Berilo", "Granate"],
        "metal": "Mercurio",
        "color": "Multicolor",
        "palabra_clave": "Yo pienso",
        "perfil": (
            "Géminis es el aire primaveral cargado de curiosidad: mente ágil, "
            "espíritu dual, mensajero entre mundos. Regido por Mercurio —el dios "
            "de alas en los tobillos—, su inteligencia es rápida, asociativa y "
            "siempre hambrienta de información nueva. Comunica, adapta, intercambia, "
            "y tiene un don natural para entender perspectivas diferentes sin "
            "necesidad de elegir entre ellas. Su dualidad no es debilidad sino "
            "versatilidad: puede ser serio y ligero, lógico y poético, solitario "
            "y absolutamente social, a veces dentro del mismo día. Huber señala "
            "que Géminis transita el camino del autoconocimiento a través del "
            "espejo del otro: necesita la mirada ajena para descubrir quién es."
        ),
        "fortalezas": [
            "Inteligencia viva y capacidad de aprendizaje rápido",
            "Habilidad comunicativa excepcional",
            "Adaptabilidad y flexibilidad ante los cambios",
            "Sentido del humor y ligereza que aligera el ambiente",
            "Curiosidad genuina por el ser humano y las ideas",
        ],
        "desafios": [
            "Dispersión y dificultad para profundizar y concluir",
            "Inconstancia emocional que puede generar inseguridad en el otro",
            "Tendencia a intelectualizar los sentimientos",
            "Dificultad para comprometerse cuando siente que pierde libertad",
        ],
        "amor": (
            "En el amor, Géminis necesita una pareja que sea también amigo "
            "intelectual: alguien que converse, sorprenda y renueve la chispa "
            "mental de forma continua. Se enamora de la mente antes que del cuerpo "
            "y puede distanciarse cuando la relación cae en la rutina. La "
            "comunicación es su lenguaje del amor: si hay diálogo y humor, Géminis "
            "puede ser increíblemente leal y presente."
        ),
        "trabajo": (
            "Géminis destaca en toda profesión que requiera comunicación, "
            "intercambio de información, gestión simultánea de múltiples proyectos "
            "o contacto con el público. Periodistas, docentes, terapeutas "
            "conversacionales, comerciales, escritores y mediadores son arquetipos "
            "geminianos. Necesita variedad y estimulación intelectual constante "
            "para no perder el foco."
        ),
        "salud": (
            "Géminis rige los pulmones, brazos, manos y sistema nervioso. Su "
            "mayor vulnerabilidad es la sobreestimulación mental que lleva al "
            "agotamiento nervioso, la ansiedad y los trastornos del sueño. "
            "Prácticas de respiración consciente, mindfulness y gestión de la "
            "hiperconectividad son especialmente beneficiosas para este signo."
        ),
        "espiritualidad": (
            "Huber señala que Géminis transita el eje de pensamiento "
            "Géminis-Sagitario: donde Géminis recopila datos e impresiones del "
            "entorno, Sagitario los sintetiza en visión filosófica. El camino "
            "espiritual geminiano pasa por aprender a integrar sus múltiples "
            "facetas en una síntesis coherente del yo. Su pensamiento semilla "
            "esotérico es: 'Soy la conciencia en acción'."
        ),
        "compatible": ["Libra", "Acuario", "Aries", "Leo"],
    },

    "Cáncer": {
        "fechas": "21 jun – 22 jul",
        "elemento": "Agua",
        "modalidad": "Cardinal",
        "regente": "Luna",
        "casa_natural": 4,
        "polaridad": "Femenino",
        "cuerpo": ["Senos", "Estómago", "Glándulas", "Sistema digestivo"],
        "piedras": ["Perla", "Piedra lunar", "Ópalo"],
        "metal": "Plata",
        "color": "Blanco nacarado y amarillo suave",
        "palabra_clave": "Yo siento",
        "perfil": (
            "Cáncer es el primer signo del verano: el útero cósmico donde la vida "
            "se gesta y se nutre. Regido por la Luna, su naturaleza es profundamente "
            "receptiva, emocional e intuitiva; sintoniza con el estado de ánimo de "
            "quienes le rodean con una precisión casi telepática. Tiene un lazo "
            "íntimo con el pasado, la familia y las raíces: el hogar es para "
            "Cáncer un santuario de restauración energética. Su imaginación fértil "
            "y su capacidad de cuidado son talentos extraordinarios que, cuando se "
            "vuelven hacia adentro por miedo, pueden convertirse en retraimiento "
            "y dependencia emocional. Huber lo describe como el signo del colectivo "
            "y de la gestación: Cáncer es el canal a través del cual las almas "
            "se encarnan en la materia."
        ),
        "fortalezas": [
            "Empatía y capacidad de cuidado profundas",
            "Intuición emocional casi instintiva",
            "Lealtad y protección incondicional hacia los seres queridos",
            "Creatividad e imaginación ricas",
            "Memoria emocional que honra la historia y las raíces",
        ],
        "desafios": [
            "Humores cambiantes ligados a los ciclos lunares",
            "Tendencia a la reactividad defensiva cuando se siente vulnerable",
            "Dificultad para separarse emocionalmente de las personas queridas",
            "Sobreprotección que puede volverse controladora",
        ],
        "amor": (
            "El amor canceriano es de cuento de hadas con sombras reales: romántico, "
            "profundo y absolutamente entregado. Busca seguridad afectiva y "
            "vínculos que duren; se enamora de personas que pueden contener su "
            "mundo interior. Muy sensible a las señales del entorno, necesita "
            "sentirse amado de forma constante y explícita. Cuando se siente "
            "seguro, puede ser el compañero más tierno, protector y sensual del zodíaco."
        ),
        "trabajo": (
            "Cáncer destaca en profesiones de cuidado, nutrición y sostén "
            "emocional: medicina, psicología, trabajo social, docencia, "
            "gastronomía, diseño de hogares o todo aquello relacionado con la "
            "memoria colectiva como la historia o la antropología. Su intuición "
            "para comprender las necesidades ajenas es un recurso terapéutico "
            "de primer orden."
        ),
        "salud": (
            "Cáncer rige el estómago, los senos y el sistema digestivo; es "
            "particularmente sensible a las somatizaciones emocionales: el "
            "estrés afectivo no procesado suele manifestarse como problemas "
            "digestivos, retención de líquidos o fatiga glandular. Prácticas de "
            "límites emocionales sanos, contacto con el agua y descanso adecuado "
            "son esenciales."
        ),
        "espiritualidad": (
            "La polaridad Cáncer-Capricornio es el eje de la individualización: "
            "Cáncer aprende a separarse del colectivo familiar y de las memorias "
            "del pasado para enraizarse en su propio ser. Huber señala que su "
            "mayor tarea espiritual es superar los miedos de nacimiento y confiar "
            "en el flujo de la vida. Su pensamiento semilla esotérico es: 'Soy "
            "el agua y el pez, y el agua es vida'."
        ),
        "compatible": ["Escorpio", "Piscis", "Tauro", "Virgo"],
    },

    "Leo": {
        "fechas": "23 jul – 22 ago",
        "elemento": "Fuego",
        "modalidad": "Fijo",
        "regente": "Sol",
        "casa_natural": 5,
        "polaridad": "Masculino",
        "cuerpo": ["Corazón", "Columna vertebral", "Plexo solar"],
        "piedras": ["Rubí", "Ámbar", "Crisólito"],
        "metal": "Oro",
        "color": "Amarillo dorado y anaranjado",
        "palabra_clave": "Yo quiero",
        "perfil": (
            "Leo es el fuego del Sol en su cenit: poderoso, generoso y creador "
            "de vida. Regido por el Sol —el único astro que no comparte su "
            "regencia—, porta en su esencia una llamada a brillar y a despertar "
            "en los demás su propia luz. No se conforma con la mediocridad: "
            "necesita un escenario donde su calor alcance a los demás. Su grandeza "
            "no es arrogancia sino magnanimidad genuina cuando está equilibrado; "
            "su sombra es la necesidad de reconocimiento que puede volverse "
            "demandante si el corazón no ha sido suficientemente nutrido. Huber "
            "describe a Leo como el signo de la prueba del yo y la verdadera "
            "autoconciencia: el camino leonino pasa por aprender que la "
            "autorealización no se opone sino que alimenta el amor."
        ),
        "fortalezas": [
            "Generosidad, calidez y capacidad de inspirar a otros",
            "Liderazgo natural con visión y carisma",
            "Creatividad expresiva y sentido estético vibrante",
            "Lealtad profunda y sinceridad sin rodeos",
            "Resiliencia y capacidad para recuperarse con dignidad",
        ],
        "desafios": [
            "Necesidad de reconocimiento que puede eclipsar a los demás",
            "Tendencia al orgullo herido cuando no se siente valorado",
            "Dificultad para adaptarse y ceder el protagonismo",
            "Posesividad en el amor cuando el ego no está integrado",
        ],
        "amor": (
            "En el amor, Leo es pasional, leal y extraordinariamente generoso. "
            "Busca una pareja de la que pueda sentirse orgulloso y que sepa "
            "admirarle de forma genuina —sin adulación vacía. La relación debe "
            "ser estimulante, apasionada y con espacio para el brillo mutuo; si "
            "se aburre o se siente ignorado, la llama se apaga. Cuando ama de "
            "verdad, su entrega es total y duradera."
        ),
        "trabajo": (
            "Leo brilla en posiciones de liderazgo, dirección creativa, artes "
            "escénicas, docencia transformadora y cualquier rol donde pueda "
            "impactar a un público o comunidad. Necesita proyectos que tengan "
            "sentido para él y donde pueda aportar su sello personal. La "
            "invisibilidad prolongada es su mayor desmotivación laboral."
        ),
        "salud": (
            "Leo rige el corazón, la columna vertebral y el plexo solar; es "
            "propenso a tensión cardiovascular, problemas de espalda y "
            "sobreexigencia energética cuando lleva demasiado tiempo sin recibir "
            "reconocimiento genuino. El juego, la creatividad expresiva y el descanso "
            "pleno son sus mejores remedios preventivos."
        ),
        "espiritualidad": (
            "La polaridad Leo-Acuario es el eje de las relaciones: Leo aprende "
            "que la luz del yo individual tiene sentido pleno cuando ilumina al "
            "grupo y a la humanidad. Huber describe el camino de Leo como el "
            "tránsito de la conciencia colectiva a la individual y de vuelta al "
            "servicio universal. Su pensamiento semilla esotérico es: 'Soy el "
            "Hijo de Dios y lo Uno que existe'."
        ),
        "compatible": ["Aries", "Sagitario", "Géminis", "Libra"],
    },

    "Virgo": {
        "fechas": "23 ago – 22 sep",
        "elemento": "Tierra",
        "modalidad": "Mutable",
        "regente": "Mercurio",
        "casa_natural": 6,
        "polaridad": "Femenino",
        "cuerpo": ["Intestinos", "Bazo", "Vesícula biliar", "Región abdominal"],
        "piedras": ["Jaspe", "Sílex", "Turmalina"],
        "metal": "Platino",
        "color": "Gris y azul pizarra",
        "palabra_clave": "Yo analizo",
        "perfil": (
            "Virgo es la tierra virgen después de la cosecha: serena, precisa y "
            "profundamente entregada al servicio. Regido por Mercurio en su "
            "dimensión analítica, posee una mente discriminadora capaz de "
            "distinguir lo esencial de lo accesorio con una claridad que ningún "
            "otro signo iguala. Su naturaleza no es perfeccionista por capricho "
            "sino porque comprende, instintivamente, que los detalles importan "
            "y que la excelencia es una forma de respeto. Huber describe a Virgo "
            "como el signo del servicio, la espera y la maduración: su trabajo "
            "espiritual consiste en aprender a confiar en el proceso, expandir "
            "su capacidad de ayudar y soltar la crítica que muchas veces se vuelve "
            "contra sí mismo."
        ),
        "fortalezas": [
            "Mente analítica y gran capacidad de discriminación",
            "Confiabilidad, responsabilidad y entrega al servicio",
            "Atención al detalle y precisión en la ejecución",
            "Humildad genuina y deseo de mejora continua",
            "Habilidad para organizar sistemas complejos",
        ],
        "desafios": [
            "Autocrítica excesiva que genera ansiedad y culpa",
            "Tendencia a la hiperanalisis que paraliza la acción",
            "Dificultad para mostrar vulnerabilidad emocional",
            "Preocupación crónica por la salud o los detalles cotidianos",
        ],
        "amor": (
            "Virgo es más apasionado de lo que aparenta: su pudor inicial puede "
            "confundirse con frialdad, pero esconde una profunda necesidad de "
            "conexión real y auténtica. Busca una pareja práctica, trabajadora y "
            "genuina, que no requiera grandes gestos teatrales sino presencia "
            "constante y cuidado en lo cotidiano. Una vez que confía, puede ser "
            "un compañero extraordinariamente atento, detallista y leal."
        ),
        "trabajo": (
            "Virgo sobresale en cualquier actividad que requiera análisis, "
            "metodología y precisión: medicina, nutrición, investigación, "
            "contabilidad, escritura técnica, terapias corporales y trabajo "
            "social. Es el arquetipo del sanador que sirve con humildad. Necesita "
            "sentir que su trabajo tiene utilidad real y contribuye al bienestar "
            "de otros."
        ),
        "salud": (
            "Virgo rige los intestinos, el bazo y la vesícula biliar. Su principal "
            "vulnerabilidad es la somatización del estrés mental en el tracto "
            "digestivo: la ansiedad se manifiesta frecuentemente como colon "
            "irritable, intolerancias alimentarias o fatiga crónica. La gestión "
            "del pensamiento rumiante y la integración de rituales de cuidado "
            "corporal son su medicina más poderosa."
        ),
        "espiritualidad": (
            "La polaridad Virgo-Piscis es el eje de la existencia: Virgo trabaja "
            "en la materia con precisión, Piscis disuelve en lo infinito. La "
            "tarea espiritual de Virgo es seleccionar, diferenciar y confiar en "
            "que el orden que percibe tiene sentido dentro de un plan mayor. "
            "Huber señala que Virgo y lo femenino están íntimamente ligados: "
            "es el signo que porta la semilla del Cristo en gestación."
        ),
        "compatible": ["Tauro", "Capricornio", "Cáncer", "Escorpio"],
    },

    "Libra": {
        "fechas": "23 sep – 22 oct",
        "elemento": "Aire",
        "modalidad": "Cardinal",
        "regente": "Venus",
        "casa_natural": 7,
        "polaridad": "Masculino",
        "cuerpo": ["Riñones", "Orejas", "Zona lumbar"],
        "piedras": ["Diamante", "Cuarzo", "Mármol"],
        "metal": "Cobre",
        "color": "Verde pálido y colores pastel",
        "palabra_clave": "Yo equilibro",
        "perfil": (
            "Libra es la balanza del equinoccio de otoño: el punto exacto donde "
            "la luz y la oscuridad se pesan mutuamente. Regido por Venus, posee "
            "un sentido innato de la armonía, la justicia y la belleza que le "
            "lleva a buscar el equilibrio en todas las dimensiones de la vida. "
            "Es el signo del 'tú': la presencia del otro no es solo deseable "
            "para Libra, es constitutiva de su identidad. Huber lo describe como "
            "el signo de la colaboración y la pareja, cuyo camino espiritual "
            "pasa por las crisis de decisión que le enseñan a actuar desde la "
            "sabiduría interior sin depender eternamente del consenso ajeno."
        ),
        "fortalezas": [
            "Sentido estético refinado y amor genuino por la belleza",
            "Diplomacia y capacidad para mediar conflictos",
            "Inteligencia social y encanto natural",
            "Sentido de la justicia y el equilibrio",
            "Capacidad para ver múltiples perspectivas simultáneamente",
        ],
        "desafios": [
            "Indecisión crónica al querer satisfacer a todas las partes",
            "Dependencia del juicio ajeno para afirmar la propia identidad",
            "Tendencia a evitar conflictos hasta el punto de la deshonestidad",
            "Dificultad para tomar partido cuando la situación lo requiere",
        ],
        "amor": (
            "Libra es el eterno romántico y seductor del zodíaco: coqueto, "
            "encantador y profundamente necesitado de una pareja con quien "
            "construir armonía. Excluye las relaciones pasionales sin alma y "
            "busca una unión basada en el respeto mutuo, la conversación y la "
            "estética compartida. La armonía en la convivencia es para Libra tan "
            "importante como el amor mismo."
        ),
        "trabajo": (
            "Libra sobresale en derecho, mediación, diplomacia, diseño, moda, "
            "relaciones públicas, terapia de pareja y cualquier profesión que "
            "requiera tacto y sentido estético. Necesita un entorno laboral "
            "armonioso para rendir al máximo; los ambientes conflictivos le "
            "drenan la energía de forma desproporcionada."
        ),
        "salud": (
            "Libra rige los riñones y la zona lumbar; es propenso a problemas "
            "renales, retención de líquidos y dolores de espalda baja cuando "
            "lleva demasiado tiempo en desequilibrio emocional o evitando "
            "decisiones importantes. El movimiento fluido como el yoga o la "
            "danza, y el descanso en espacios estéticos y serenos, son sus "
            "mejores remedios."
        ),
        "espiritualidad": (
            "La polaridad Aries-Libra es el eje del encuentro: donde Aries "
            "afirma el yo, Libra aprende el arte del nosotros. Huber señala que "
            "el cruce de caminos librano —elegir y comprometerse— es su prueba "
            "iniciática mayor. Su pensamiento semilla esotérico es: 'Regreso "
            "al centro donde habita Dios. Sé paz y amor y servicio'."
        ),
        "compatible": ["Géminis", "Acuario", "Leo", "Sagitario"],
    },

    "Escorpio": {
        "fechas": "23 oct – 21 nov",
        "elemento": "Agua",
        "modalidad": "Fijo",
        "regente": "Plutón",
        "regente_tradicional": "Marte",
        "casa_natural": 8,
        "polaridad": "Femenino",
        "cuerpo": ["Órganos genitales", "Vejiga", "Ano", "Pubis"],
        "piedras": ["Cornalina", "Hematites", "Topacio"],
        "metal": "Hierro",
        "color": "Verde esmeralda, rojo y negro",
        "palabra_clave": "Yo transformo",
        "perfil": (
            "Escorpio es las aguas profundas del otoño: inmóviles en la superficie, "
            "hirviendo de vida en las profundidades. Regido por Plutón —y "
            "co-regido por Marte en la tradición— es el signo de la regeneración, "
            "el misterio y la transformación radical. Nadie siente tan hondo como "
            "Escorpio ni se compromete con tanta intensidad; pero esa misma "
            "profundidad puede volverse destructiva cuando opera desde el miedo "
            "o la herida no sanada. Huber describe a Escorpio como el signo de "
            "los procesos de muerte y renacimiento: cada crisis escorpiana es una "
            "invitación a soltar una capa vieja del yo para emerger más auténtico "
            "y más libre."
        ),
        "fortalezas": [
            "Profundidad emocional y psicológica excepcional",
            "Voluntad inquebrantable y resistencia ante la adversidad",
            "Intuición penetrante y capacidad investigadora",
            "Lealtad absoluta con quienes merecen su confianza",
            "Poder de regeneración y transformación personal",
        ],
        "desafios": [
            "Tendencia al control y la desconfianza cuando se siente vulnerable",
            "Rencor profundo ante la traición percibida",
            "Intensidad que puede abrumar a perfiles más livianos",
            "Dificultad para soltar vínculos o situaciones que ya han muerto",
        ],
        "amor": (
            "El amor escorpiano es visceral, absoluto y transformador: aspira a "
            "la fusión total —cuerpo, mente y alma— y no acepta las medias tintas. "
            "Es posesivo y celoso, pero también extraordinariamente fiel cuando "
            "ha otorgado su confianza. Una relación con Escorpio cambia para "
            "siempre a quien la vive; su intensidad no es para todos, pero para "
            "quienes la pueden sostener es una experiencia de profundidad "
            "incomparable."
        ),
        "trabajo": (
            "Escorpio sobresale en psicología, psicoterapia, investigación "
            "profunda, medicina, cirugía, criminología, trabajo con la muerte o "
            "el duelo, finanzas y cualquier campo que requiera penetrar en lo que "
            "otros no se atreven a mirar. Su capacidad de mantener confidencias "
            "y trabajar en la sombra con integridad es un don terapéutico de "
            "primer orden."
        ),
        "salud": (
            "Escorpio rige los órganos genitales, la vejiga y los sistemas de "
            "eliminación; es propenso a infecciones del tracto urinario y "
            "reproductivo, y a enfermedades de origen psicosomático ligadas a "
            "emociones reprimidas —especialmente la rabia, el resentimiento y "
            "el deseo de control. La expresión emocional honesta, el trabajo "
            "corporal profundo y la liberación de lo no procesado son su "
            "medicina esencial."
        ),
        "espiritualidad": (
            "Huber describe la triple prueba escorpiana: conversión, "
            "transmutación y victoria. El Morador del Umbral —la sombra "
            "personal acumulada— debe ser enfrentado y transformado, no huido. "
            "Escorpio tiene acceso a los poderes de regeneración más profundos "
            "del zodíaco; su pensamiento semilla esotérico es: 'Muero para "
            "renacer como Cristo, quien conoce la muerte y resucita'."
        ),
        "compatible": ["Cáncer", "Piscis", "Virgo", "Capricornio"],
    },

    "Sagitario": {
        "fechas": "22 nov – 21 dic",
        "elemento": "Fuego",
        "modalidad": "Mutable",
        "regente": "Júpiter",
        "casa_natural": 9,
        "polaridad": "Masculino",
        "cuerpo": ["Caderas", "Muslos", "Glúteos", "Nervio ciático"],
        "piedras": ["Turquesa", "Lapislázuli", "Carbunclo"],
        "metal": "Estaño",
        "color": "Azul cobalto y turquesa",
        "palabra_clave": "Yo veo",
        "perfil": (
            "Sagitario es el fuego interior que arde en el corazón del invierno "
            "que se acerca: el arquero que apunta su flecha hacia el horizonte "
            "más lejano y más luminoso. Regido por Júpiter, posee una sed de "
            "verdad, expansión y significado que ningún límite ordinario puede "
            "contener. Es el filósofo, el viajero, el buscador de sentido; su "
            "alegría es contagiosa y su optimismo puede ser un regalo auténtico "
            "o una negación sofisticada de la realidad. Huber señala que la "
            "flecha sagitariana simboliza la aspiración a una meta superior, y "
            "que su camino espiritual pasa por desarrollar la concentración y "
            "la orientación que transforman el entusiasmo disperso en sabiduría "
            "real."
        ),
        "fortalezas": [
            "Optimismo genuino y capacidad de ver oportunidades donde otros ven obstáculos",
            "Espíritu aventurero y amor por el aprendizaje continuo",
            "Generosidad y sentido del humor que abre corazones",
            "Visión filosófica y búsqueda honesta de la verdad",
            "Adaptabilidad y facilidad para conectar con personas muy diversas",
        ],
        "desafios": [
            "Exceso de confianza que puede derivar en imprudencia",
            "Dificultad para sostener el compromiso cuando la novedad se agota",
            "Tendencia a predicar verdades sin consultar si el otro quiere escucharlas",
            "Dispersión de proyectos por querer abarcar demasiado",
        ],
        "amor": (
            "En el amor, Sagitario se enamora con fuego y velocidad, pero puede "
            "aburrise si la relación se vuelve demasiado predecible o demandante "
            "de su libertad. Necesita una pareja que sea también compañera de "
            "aventuras —literales o intelectuales—, que tenga humor y que entienda "
            "que amar a Sagitario no es poseerlo. Cuando encuentra ese espacio "
            "de libertad dentro del compromiso, puede ser un amante generoso, "
            "apasionado y profundamente leal."
        ),
        "trabajo": (
            "Sagitario sobresale en docencia, filosofía, derecho, viajes, "
            "publicación, espiritualidad, política, deportes al aire libre y "
            "cualquier actividad que implique comunicar verdades o explorar "
            "territorios desconocidos. Necesita proyectos con visión de largo "
            "alcance y libertad de movimiento; la rutina burocrática es su "
            "peor hábitat."
        ),
        "salud": (
            "Sagitario rige las caderas, los muslos y el nervio ciático; es "
            "propenso a lesiones por exceso de actividad física, ciática y "
            "problemas de hígado por tendencia al exceso en la alimentación y "
            "el disfrute. El movimiento activo al aire libre y la moderación "
            "consciente son sus mejores preventivos."
        ),
        "espiritualidad": (
            "Huber describe el progreso espiritual de Sagitario como el tránsito "
            "de la intuición dispersa hacia la sabiduría integrada. Su polaridad "
            "con Géminis es el eje del pensamiento: donde Géminis recoge datos, "
            "Sagitario los eleva a síntesis filosófica. Su pensamiento semilla "
            "esotérico es: 'Veo la meta, persigo el camino que me conduce hacia "
            "la luz'."
        ),
        "compatible": ["Aries", "Leo", "Libra", "Acuario"],
    },

    "Capricornio": {
        "fechas": "22 dic – 19 ene",
        "elemento": "Tierra",
        "modalidad": "Cardinal",
        "regente": "Saturno",
        "casa_natural": 10,
        "polaridad": "Femenino",
        "cuerpo": ["Rodillas", "Piel", "Articulaciones", "Huesos", "Esqueleto"],
        "piedras": ["Ámbar", "Ónice"],
        "metal": "Plomo",
        "color": "Violeta oscuro y marrón sepia",
        "palabra_clave": "Yo uso",
        "perfil": (
            "Capricornio es la tierra austera del solsticio de invierno: fría y "
            "aparentemente estéril en la superficie, pero guardando en sus "
            "profundidades las semillas del futuro. Regido por Saturno, posee "
            "una disciplina y una visión de largo plazo que ningún otro signo "
            "iguala; escala la montaña con paso firme y sin prisa, consciente de "
            "que la cima requiere tiempo y sacrificio. Huber describe a Capricornio "
            "como el signo de la autoridad madura y la responsabilidad: su camino "
            "pasa por desarrollar una individualidad plenamente consciente que "
            "trascienda el ego para servir a un plan evolutivo mayor."
        ),
        "fortalezas": [
            "Disciplina, constancia y capacidad de trabajo sostenido",
            "Sentido de la responsabilidad y la integridad",
            "Pragmatismo y pensamiento estratégico a largo plazo",
            "Resiliencia ante la adversidad y madurez prematura",
            "Autoridad natural que inspira confianza y respeto",
        ],
        "desafios": [
            "Tendencia al pesimismo o la frialdad emocional cuando se cierra",
            "Dificultad para mostrar vulnerabilidad y pedir ayuda",
            "Rigidez de carácter que puede volverse autoritarismo",
            "Workaholismo y descuido de las necesidades afectivas propias",
        ],
        "amor": (
            "Capricornio vive el amor de forma más intelectual que emocional en "
            "la superficie, pero su interior es más cálido de lo que muestra. "
            "Se toma su tiempo para evaluar al posible compañero, y solo cuando "
            "está seguro abre su mundo interior con una intensidad que sorprende. "
            "Busca relaciones a largo plazo con personas que compartan sus "
            "ambiciones y valores; la estabilidad y el compromiso serio son para "
            "él el lenguaje del amor."
        ),
        "trabajo": (
            "Capricornio sobresale en administración, dirección de empresas, "
            "política, arquitectura, ingeniería, derecho y cualquier campo que "
            "requiera planificación estratégica y visión a largo plazo. No teme "
            "las responsabilidades pesadas; al contrario, se siente más seguro "
            "cuantas más tiene. Necesita sentir que su trabajo tiene valor real "
            "y que construye algo que perdura."
        ),
        "salud": (
            "Capricornio rige rodillas, huesos, articulaciones y piel; es propenso "
            "a artritis, problemas óseos y afecciones cutáneas relacionadas con "
            "el estrés crónico y la autoexigencia. Las técnicas de soltar el "
            "control, el movimiento suave de las articulaciones y el descanso "
            "emocional son su mejor medicina preventiva."
        ),
        "espiritualidad": (
            "Huber describe a Capricornio como el signo donde la voluntad se "
            "despierta para servir al Plan de Evolución. La polaridad "
            "Capricornio-Cáncer es el eje de la individualización: donde Cáncer "
            "se arraiga en la familia, Capricornio debe individualizar esa energía "
            "para encarnar una autoridad al servicio de lo colectivo. Su "
            "pensamiento semilla esotérico es: 'Perdida en la luz del alma, "
            "avanzo hacia la oscuridad y descanso en el corazón del amor'."
        ),
        "compatible": ["Tauro", "Virgo", "Escorpio", "Piscis"],
    },

    "Acuario": {
        "fechas": "20 ene – 18 feb",
        "elemento": "Aire",
        "modalidad": "Fijo",
        "regente": "Urano",
        "regente_tradicional": "Saturno",
        "casa_natural": 11,
        "polaridad": "Masculino",
        "cuerpo": ["Piernas", "Tobillos", "Talones", "Sistema nervioso"],
        "piedras": ["Zafiro", "Perla negra"],
        "metal": "Plomo",
        "color": "Gris plateado y azul eléctrico",
        "palabra_clave": "Yo sé",
        "perfil": (
            "Acuario es el aire helado y visionario del corazón del invierno: "
            "independiente, fraternal y esencialmente libre. Regido por Urano y "
            "co-regido por Saturno en la tradición, combina la ruptura con lo "
            "establecido con una profunda responsabilidad colectiva. No sigue "
            "tendencias: las anticipa o las crea. Su inteligencia es sistémica "
            "y humanista, siempre orientada al bien de la comunidad más que al "
            "beneficio individual. Huber describe a Acuario como el signo de la "
            "conciencia de grupo y la fraternidad universal, cuya tarea es "
            "superar la dualidad interna para encarnar la síntesis y la "
            "impersonalidad amorosa que caracterizará a la nueva Era."
        ),
        "fortalezas": [
            "Visión innovadora y pensamiento sistémico",
            "Idealismo humanista y compromiso con el bien común",
            "Independencia y autenticidad sin necesidad de aprobación",
            "Apertura mental y tolerancia ante la diversidad",
            "Capacidad para la amistad profunda y la lealtad grupal",
        ],
        "desafios": [
            "Desapego emocional que puede percibirse como frialdad",
            "Rebeldía reactiva que puede dificultar la cooperación",
            "Dificultad para vincularse íntimamente a nivel emocional",
            "Rigidez ideológica disfrazada de apertura mental",
        ],
        "amor": (
            "Acuario valora la amistad y la libertad por encima de todo en el "
            "amor: necesita una pareja que sea también compañera intelectual y "
            "que no le acose con celos ni posesividad. Su romanticismo existe, "
            "pero se expresa más a través del diálogo profundo y los proyectos "
            "compartidos que a través de gestos convencionales. Cuando se siente "
            "libre para ser auténtico, puede ser un compañero sorprendentemente "
            "leal y generoso."
        ),
        "trabajo": (
            "Acuario destaca en ciencia, tecnología, activismo social, humanidades, "
            "astrología, psicología transpersonal, innovación organizacional y "
            "cualquier campo que trabaje con visión de futuro y trabajo en red. "
            "Necesita autonomía, proyectos con impacto colectivo y la posibilidad "
            "de cuestionar lo establecido con libertad."
        ),
        "salud": (
            "Acuario rige piernas, tobillos y el sistema nervioso periférico; es "
            "propenso a problemas circulatorios en extremidades inferiores, "
            "espasmos musculares y sobrecarga nerviosa por hiperactividad mental. "
            "El movimiento regular, la conexión a tierra y la desconexión digital "
            "periódica son sus mejores preventivos."
        ),
        "espiritualidad": (
            "Huber describe la conciencia de grupo como la tónica de Acuario y "
            "el Séptimo Rayo de Orden Ceremonial como su influencia esotérica. "
            "Su mayor tarea es la superación de la dualidad interna: integrar "
            "el mundo exterior y el interior para encarnar la síntesis universal. "
            "Su pensamiento semilla esotérico es: 'Con agua de vida inundo la "
            "tierra sedienta'."
        ),
        "compatible": ["Géminis", "Libra", "Sagitario", "Aries"],
    },

    "Piscis": {
        "fechas": "19 feb – 19 mar",
        "elemento": "Agua",
        "modalidad": "Mutable",
        "regente": "Neptuno",
        "regente_tradicional": "Júpiter",
        "casa_natural": 12,
        "polaridad": "Femenino",
        "cuerpo": ["Pies", "Venas", "Sistema linfático", "Glándula pineal"],
        "piedras": ["Aguamarina", "Coral", "Jade"],
        "metal": "Estaño",
        "color": "Azul marino, verde agua y violeta",
        "palabra_clave": "Yo creo",
        "perfil": (
            "Piscis es el deshielo del final del invierno: las aguas que disuelven "
            "todo límite para reunirse con el océano de lo posible. Último signo "
            "del zodíaco y síntesis de todos los anteriores, Piscis lleva en su "
            "interior la experiencia acumulada de las once etapas previas. Regido "
            "por Neptuno, posee una permeabilidad emocional y espiritual que le "
            "convierte en receptor privilegiado de lo invisible: la intuición, "
            "la inspiración artística y la empatía mística son sus dones naturales. "
            "Huber describe a Piscis como el signo de la invocación, el "
            "sacrificio y el regreso del alma a su fuente; su camino pasa por "
            "aprender a distinguir la compasión real de la disolución del yo."
        ),
        "fortalezas": [
            "Empatía e intuición de profundidad oceánica",
            "Creatividad artística e inspiración genuina",
            "Compasión y capacidad de servicio desinteresado",
            "Espiritualidad natural y apertura a lo trascendente",
            "Adaptabilidad y capacidad de resonar con el otro",
        ],
        "desafios": [
            "Tendencia a la evasión y el autoengaño ante el dolor",
            "Dificultad para establecer límites emocionales sanos",
            "Idealización que lleva a la decepción cuando la realidad no coincide",
            "Vulnerabilidad a la influencia negativa del entorno por exceso de permeabilidad",
        ],
        "amor": (
            "En el amor, Piscis busca la fusión total: carnal, espiritual y "
            "emocional. Es soñador e idealista, y puede comenzar una relación "
            "proyectando sobre el otro una imagen casi mítica que tarde o temprano "
            "choca con la realidad humana. Cuando se siente contenido por una "
            "pareja presente y amorosa, puede ser mágico, sensible y entregado "
            "de una forma que pocas personas experimentan. Necesita romanticismo, "
            "profundidad y una conexión que trascienda lo mundano."
        ),
        "trabajo": (
            "Piscis destaca en artes —música, poesía, fotografía, cine—, "
            "psicología profunda, terapias alternativas, trabajo espiritual, "
            "enfermería, oceanografía y cualquier campo que requiera empatía, "
            "intuición o acceso a dimensiones no ordinarias de la realidad. "
            "Necesita un entorno laboral que respete su sensibilidad y le permita "
            "trabajar con propósito y significado."
        ),
        "salud": (
            "Piscis rige los pies, las venas y el sistema linfático; es propenso "
            "a infecciones fúngicas en los pies, problemas linfáticos y "
            "sensibilidad extrema a sustancias —fármacos, alcohol, toxinas— "
            "que en otros signos no generan reacción. El establecimiento de límites "
            "energéticos, la hidroterapia y las prácticas de conexión a tierra "
            "son sus mejores recursos preventivos."
        ),
        "espiritualidad": (
            "Huber describe el anhelo de Piscis como el deseo profundo de "
            "regresar a la fuente: la función redentora de este signo consiste "
            "en transformar el sufrimiento colectivo en comprensión universal. "
            "La polaridad Piscis-Virgo es el eje de la existencia: donde Virgo "
            "trabaja en la materia con precisión, Piscis la trasciende hacia la "
            "unidad. Su pensamiento semilla esotérico es: 'Abandono la casa del "
            "Padre y, regresando, salvo y sirvo'."
        ),
        "compatible": ["Cáncer", "Escorpio", "Tauro", "Capricornio"],
    },
}


# ---------------------------------------------------------------------------
# PLANETAS_TRANSITO
# ---------------------------------------------------------------------------

PLANETAS_TRANSITO: dict[str, dict] = {
    "Sol": {
        "rapidez": "rápido",
        "dominio": (
            "Vitalidad, voluntad de ser, identidad esencial, creatividad y "
            "expresión del yo. El Sol representa la energía yang fundamental "
            "de la que son reflejos todos los demás planetas; en la carta, "
            "señala el área donde la persona está llamada a brillar y a "
            "desarrollar su heroísmo personal."
        ),
        "transito": (
            "Cuando el Sol transita una casa o forma aspecto con un planeta natal, "
            "activa y ilumina esa área de vida durante aproximadamente un mes. "
            "Es un período de mayor visibilidad y energía en ese sector: "
            "oportunidad para iniciar, expresar y reclamar protagonismo. "
            "Los tránsitos del Sol son activadores y catalizadores; no producen "
            "cambios radicales por sí solos, sino que encienden el foco en lo "
            "que ya está en proceso."
        ),
    },
    "Luna": {
        "rapidez": "muy rápido",
        "dominio": (
            "Emociones, instintos, necesidades de seguridad, memoria, cuerpo, "
            "ritmos vitales y relación con la figura materna. La Luna es el "
            "arquetipo del recipiente y la matriz: define cómo el individuo "
            "recibe, procesa y expresa sus necesidades más íntimas."
        ),
        "transito": (
            "La Luna transita el zodíaco completo en aproximadamente 28 días, "
            "permaneciendo dos o tres días en cada signo y casa. Sus tránsitos "
            "modulan el estado emocional cotidiano y la receptividad a los "
            "estímulos del entorno. La Luna nueva marca inicios y siembras; "
            "la Luna llena, culminaciones y revelaciones. La luna en relación "
            "con planetas natales amplifica la sensibilidad en esa área durante "
            "horas o pocos días."
        ),
    },
    "Mercurio": {
        "rapidez": "rápido",
        "dominio": (
            "Mente, comunicación, aprendizaje, intercambio de información, "
            "lenguaje, viajes cortos y conexiones cotidianas. Mercurio modula "
            "la energía del Sol convirtiéndola en información comprensible; "
            "es el mensajero que conecta los mundos interior y exterior."
        ),
        "transito": (
            "Los tránsitos de Mercurio activan el pensamiento, la comunicación "
            "y los intercambios en el área que transita. Son ideales para "
            "firmar contratos, tener conversaciones importantes, estudiar o "
            "comenzar proyectos creativos de comunicación. En retrogradación "
            "(3-4 semanas, 3 veces al año) es prudente revisar antes que iniciar: "
            "los planes y acuerdos pueden necesitar revisión."
        ),
    },
    "Venus": {
        "rapidez": "rápido",
        "dominio": (
            "Amor, belleza, armonía, valores, placeres, relaciones afectivas, "
            "creatividad estética y autoestima. Venus es el arquetipo del 'tú': "
            "la energía que crea vínculos, atrae la armonía y desarrolla el "
            "sentido de lo bello y lo valioso."
        ),
        "transito": (
            "Los tránsitos de Venus facilitan la atracción, la armonía y la "
            "abundancia en el área activada. Son momentos propicios para el "
            "amor, la negociación, la creatividad artística y el autocuidado. "
            "Cuando Venus hace aspecto con planetas natales, suaviza sus "
            "energías y propicia encuentros significativos o mejoras en la "
            "autoestima y las finanzas."
        ),
    },
    "Marte": {
        "rapidez": "medio",
        "dominio": (
            "Voluntad de acción, energía física, asertividad, deseo, impulso "
            "y capacidad para defender límites. Marte es el arquetipo del 'yo': "
            "la energía que separa, define y protege la individualidad frente "
            "al entorno."
        ),
        "transito": (
            "Los tránsitos de Marte activan la energía, la motivación y la "
            "capacidad de acción en el área que transita durante 4-6 semanas. "
            "Son períodos de mayor impulso y productividad, pero también de "
            "mayor irritabilidad y tendencia al conflicto si la energía no "
            "encuentra cauce constructivo. Ideales para iniciar proyectos que "
            "requieran valentía y esfuerzo físico."
        ),
    },
    "Júpiter": {
        "rapidez": "lento",
        "dominio": (
            "Expansión, crecimiento, abundancia, sabiduría, fe, viajes largos, "
            "filosofía y sentido de lo posible. Júpiter es el arquetipo del "
            "apoyo y la integración social: la energía que nos impulsa a crecer "
            "más allá de la matriz original y a ocupar nuestro lugar en el mundo."
        ),
        "transito": (
            "Júpiter transita cada signo durante aproximadamente un año, "
            "expandiendo y amplificando el área de vida que toca. Sus tránsitos "
            "son generalmente benéficos: abren oportunidades, generan confianza "
            "y facilitan el crecimiento en el sector activado. Sin embargo, "
            "también pueden exagerar los excesos o crear falsas expectativas "
            "si no hay discernimiento. Es el gran ciclo de oportunidad."
        ),
    },
    "Saturno": {
        "rapidez": "lento",
        "dominio": (
            "Estructura, límites, disciplina, responsabilidad, karma, tiempo "
            "y realidad. Saturno es el principio de resistencia que pone a "
            "prueba la solidez de lo construido; define los límites de la "
            "realidad perceptible por la conciencia ordinaria y demanda "
            "madurez, integridad y trabajo para superar sus pruebas."
        ),
        "transito": (
            "Saturno transita cada signo durante 2-3 años y cada vuelta completa "
            "dura 29 años. Sus tránsitos marcan períodos de prueba, consolidación "
            "y madurez forzada en el área que toca. No destruye lo que está bien "
            "construido; sí elimina lo que solo sostenía la ilusión. Los tránsitos "
            "saturnianos requieren paciencia, responsabilidad y voluntad de "
            "trabajo; sus frutos son duraderos. El retorno de Saturno a su posición "
            "natal (~29 años) es un rito de iniciación mayor."
        ),
    },
    "Urano": {
        "rapidez": "muy lento",
        "dominio": (
            "Liberación, originalidad, ruptura con lo establecido, genialidad, "
            "cambio súbito e innovación. Urano trasciende los límites de Saturno "
            "y trae libertad donde hay exceso de estructura. Su acción puede "
            "percibirse como disruptiva desde la conciencia ordinaria, pero "
            "desde una perspectiva expandida es el canal de la evolución "
            "acelerada."
        ),
        "transito": (
            "Urano transita cada signo durante 7 años y su ciclo completo dura "
            "84 años. Sus tránsitos producen cambios repentinos e inesperados "
            "en el área que activa, muchas veces disrupciones que en retrospectiva "
            "resultan liberadoras. El tránsito de Urano a posiciones natales "
            "importantes puede traer revelaciones, quiebres de identidad "
            "necesarios o giros vitales que no pueden planificarse, solo navegarse "
            "con apertura."
        ),
    },
    "Neptuno": {
        "rapidez": "muy lento",
        "dominio": (
            "Espiritualidad, intuición profunda, compasión, disolución de "
            "fronteras, imaginación creativa, misterio y conexión con lo "
            "trascendente. Neptuno es el canal de acceso a realidades que "
            "superan los límites de la conciencia racional ordinaria; cuando "
            "se maneja bien, genera inspiración y amor universal; cuando se "
            "maneja mal, produce confusión, evasión y autoengaño."
        ),
        "transito": (
            "Neptuno transita cada signo durante 14 años y su ciclo completo "
            "dura 165 años. Sus tránsitos disuelven gradualmente la solidez "
            "de lo que toca, abriendo espacio para una comprensión más sutil "
            "y espiritual. Las áreas transitadas por Neptuno pueden volverse "
            "difusas, idealizadas o confusas; el antídoto es la honestidad "
            "radical y el discernimiento espiritual. También puede traer "
            "inspiración artística e intensificación de la vida interior."
        ),
    },
    "Plutón": {
        "rapidez": "muy lento",
        "dominio": (
            "Transformación profunda, muerte y renacimiento, poder, sombra "
            "psicológica, regeneración y acceso al inconsciente colectivo. "
            "Plutón provoca la crisis que precede al renacimiento; exige que "
            "el individuo esté dispuesto a soltar lo que ya ha muerto para "
            "que pueda nacer lo nuevo."
        ),
        "transito": (
            "Plutón transita cada signo entre 12 y 31 años (por la excentricidad "
            "de su órbita) y su ciclo completo dura 248 años. Sus tránsitos a "
            "posiciones natales importantes marcan períodos de transformación "
            "radical e irreversible en el área activada: procesos de poder, "
            "crisis de identidad profunda, encuentros con la sombra o con la "
            "muerte simbólica. Son tránsitos que no pueden ignorarse: exigen "
            "trabajo profundo y la disposición a renacer transformado."
        ),
    },
}


# ---------------------------------------------------------------------------
# HELPER FUNCTIONS
# ---------------------------------------------------------------------------

# Rangos de fechas por signo: (mes_inicio, día_inicio, mes_fin, día_fin)
_RANGOS_SIGNOS: list[tuple[str, int, int, int, int]] = [
    ("Aries",       3, 20,  4, 19),
    ("Tauro",       4, 20,  5, 20),
    ("Géminis",     5, 21,  6, 20),
    ("Cáncer",      6, 21,  7, 22),
    ("Leo",         7, 23,  8, 22),
    ("Virgo",       8, 23,  9, 22),
    ("Libra",       9, 23, 10, 22),
    ("Escorpio",   10, 23, 11, 21),
    ("Sagitario",  11, 22, 12, 21),
    ("Capricornio",12, 22,  1, 19),
    ("Acuario",     1, 20,  2, 18),
    ("Piscis",      2, 19,  3, 19),
]


def get_signo_solar(fecha_nacimiento: str) -> str:
    """
    Devuelve el nombre del signo solar en español a partir de la fecha de
    nacimiento.

    Args:
        fecha_nacimiento: cadena en formato "YYYY-MM-DD"

    Returns:
        Nombre del signo solar (ej. "Tauro") o "Desconocido" si no se puede
        determinar.

    Raises:
        ValueError: si el formato de fecha es incorrecto.
    """
    try:
        d = date.fromisoformat(fecha_nacimiento)
    except (ValueError, TypeError) as exc:
        raise ValueError(
            f"Formato de fecha inválido: '{fecha_nacimiento}'. "
            "Use 'YYYY-MM-DD'."
        ) from exc

    mes = d.month
    dia = d.day

    for signo, m_ini, d_ini, m_fin, d_fin in _RANGOS_SIGNOS:
        if m_ini == m_fin:
            if mes == m_ini and d_ini <= dia <= d_fin:
                return signo
        elif m_ini < m_fin:
            if (mes == m_ini and dia >= d_ini) or (mes == m_fin and dia <= d_fin):
                return signo
        else:
            # Capricornio: cruza el año (dic → ene)
            if (mes == m_ini and dia >= d_ini) or (mes == m_fin and dia <= d_fin):
                return signo

    return "Desconocido"


def get_elemento(signo: str) -> str:
    """
    Devuelve el elemento (Fuego, Tierra, Aire, Agua) de un signo dado.

    Args:
        signo: nombre del signo en español con mayúscula inicial.

    Returns:
        Nombre del elemento o cadena vacía si el signo no se reconoce.
    """
    datos = SIGNOS.get(signo)
    if datos is None:
        return ""
    return datos.get("elemento", "")


def get_signos_compatibles(signo: str) -> list[str]:
    """
    Devuelve la lista de signos más compatibles con el signo dado.

    Args:
        signo: nombre del signo en español con mayúscula inicial.

    Returns:
        Lista de nombres de signos compatibles, o lista vacía si el signo
        no se reconoce.
    """
    datos = SIGNOS.get(signo)
    if datos is None:
        return []
    return datos.get("compatible", [])


# ---------------------------------------------------------------------------
# CONTEXT BUILDER PARA LLM
# ---------------------------------------------------------------------------

def build_horoscopo_context(signo: str) -> str:
    """
    Construye un bloque de texto estructurado con toda la información del
    signo, listo para inyectar en un prompt de LLM.

    Args:
        signo: nombre del signo en español con mayúscula inicial.

    Returns:
        Cadena de texto formateada con secciones etiquetadas, o mensaje de
        error si el signo no se reconoce.

    Example:
        >>> ctx = build_horoscopo_context("Escorpio")
        >>> print(ctx[:200])
    """
    datos = SIGNOS.get(signo)
    if datos is None:
        signos_validos = ", ".join(SIGNOS.keys())
        return (
            f"[ERROR] Signo '{signo}' no reconocido. "
            f"Signos válidos: {signos_validos}"
        )

    elemento = datos["elemento"]
    elem_datos = ELEMENTOS.get(elemento, {})
    modalidad = datos["modalidad"]
    mod_datos = MODALIDADES.get(modalidad, {})

    fortalezas_str = "\n".join(f"  • {f}" for f in datos.get("fortalezas", []))
    desafios_str = "\n".join(f"  • {d}" for d in datos.get("desafios", []))
    cuerpo_str = ", ".join(datos.get("cuerpo", []))
    piedras_str = ", ".join(datos.get("piedras", []))
    compatible_str = ", ".join(datos.get("compatible", []))

    regente_info = datos.get("regente", "")
    regente_trad = datos.get("regente_tradicional")
    if regente_trad:
        regente_info = f"{regente_info} (moderno) / {regente_trad} (tradicional)"

    lines = [
        f"=== PERFIL ASTROLÓGICO: {signo.upper()} ===",
        "",
        f"Fechas:        {datos.get('fechas', '')}",
        f"Elemento:      {elemento}",
        f"Modalidad:     {modalidad}",
        f"Regente:       {regente_info}",
        f"Casa natural:  {datos.get('casa_natural', '')}",
        f"Polaridad:     {datos.get('polaridad', '')}",
        f"Palabra clave: {datos.get('palabra_clave', '')}",
        f"Color:         {datos.get('color', '')}",
        f"Piedras:       {piedras_str}",
        f"Metal:         {datos.get('metal', '')}",
        f"Cuerpo:        {cuerpo_str}",
        "",
        "--- PERFIL GENERAL ---",
        datos.get("perfil", ""),
        "",
        "--- FORTALEZAS ---",
        fortalezas_str,
        "",
        "--- DESAFÍOS Y SOMBRA ---",
        desafios_str,
        "",
        "--- AMOR Y RELACIONES ---",
        datos.get("amor", ""),
        "",
        "--- VOCACIÓN Y TRABAJO ---",
        datos.get("trabajo", ""),
        "",
        "--- SALUD Y CUERPO ---",
        datos.get("salud", ""),
        "",
        "--- DIMENSIÓN ESPIRITUAL Y ESOTÉRICA ---",
        datos.get("espiritualidad", ""),
        "",
        f"--- ELEMENTO: {elemento} ---",
        elem_datos.get("cualidades", ""),
        f"Sombra del elemento: {elem_datos.get('sombra', '')}",
        "",
        f"--- MODALIDAD: {modalidad} ---",
        mod_datos.get("descripcion", ""),
        f"Desafío de modalidad: {mod_datos.get('desafio', '')}",
        "",
        "--- COMPATIBILIDAD ---",
        f"Signos más afines: {compatible_str}",
        "",
        "=== FIN DEL PERFIL ===",
    ]

    return "\n".join(lines)
