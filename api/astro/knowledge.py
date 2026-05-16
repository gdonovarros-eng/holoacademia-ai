"""
Base de conocimiento astrológico extraída de los textos estudiados:
  - Volguine: Técnica de las Revoluciones Solares
  - Maurice Privat: Los Mensales
  - Maurice Froger: RSP sidéreas
  - Tito Maciá: RS y sus Atacires (figuras aspectuales)
  - Astrología Horaria (sistema H1-H12, triplicidades)
  - Astrología Electiva (principios de timing)

Todo codificado en español, para ser inyectado en los prompts de Claude.
"""
from __future__ import annotations

# ─── ASC anual por signo (Volguine) ──────────────────────────────────────────────
ASC_ANUAL_POR_SIGNO: dict[str, str] = {
    "Aries": (
        "Año de energía desbordante, iniciativas múltiples, impulso vital renovado. "
        "El nativo actúa antes de pensar; gran potencial de logro si canaliza el fuego. "
        "Riesgo de dispersión, conflictos por impaciencia o agresividad. "
        "El cuerpo físico pide movimiento y acción directa."
    ),
    "Tauro": (
        "Año de estabilidad y construcción material. El nativo busca seguridad, "
        "posesiones, placeres sensoriales y resultados tangibles. "
        "Gran perseverancia pero resistencia al cambio. "
        "Año favorable para finanzas, arte, amor estable y bienes materiales."
    ),
    "Géminis": (
        "Año de movilidad intelectual y comunicación intensa. Múltiples proyectos, "
        "viajes cortos, escritura, redes y contactos. Dispersión posible por exceso de intereses. "
        "El nativo vive en su mente; conversaciones y relaciones superficiales abundan. "
        "Favorable para estudios, contratos y medios de comunicación."
    ),
    "Cáncer": (
        "Año de alta sensibilidad emocional y protagonismo de la vida doméstica/familiar. "
        "Intuición aumentada, necesidad de protección y pertenencia. "
        "Los cambios en el hogar, la familia o la madre marcan el año. "
        "Favorable para terapia, nutrición, cuidado de otros y asuntos inmobiliarios."
    ),
    "Leo": (
        "Año de voluntad creativa y necesidad de reconocimiento. El nativo brilla, "
        "lidera y busca el centro de la escena. "
        "Generosidad natural, capacidad de inspirar a otros. "
        "Riesgo de soberbia o agotamiento por querer controlar todo. "
        "Favorable para liderazgo, arte, amor apasionado e hijos."
    ),
    "Virgo": (
        "Año de análisis, detalle y servicio. La salud y el trabajo diario toman protagonismo. "
        "El nativo entra en modo crítico y perfeccionista; puede agotarse en detalles. "
        "Excelente para reorganizar, aprender técnicas, cuidar el cuerpo y mejorar procesos. "
        "Autocrítica elevada: cuidado con la ansiedad."
    ),
    "Libra": (
        "Año centrado en relaciones interpersonales, contratos y búsqueda de armonía. "
        "El nativo necesita el otro para definirse; asociaciones clave, posible matrimonio. "
        "Estética, diplomacia y justicia como temas dominantes. "
        "Riesgo de indecisión y dependencia emocional."
    ),
    "Escorpio": (
        "Año de transformación profunda e intensidad emocional. Crisis que regeneran. "
        "Temas de poder, sexualidad, secretos, deudas y herencias afloran. "
        "El nativo va al fondo de las cosas; puede haber pérdidas necesarias para renacer. "
        "Favorable para psicología, inversiones, terapia y asuntos ocultos."
    ),
    "Sagitario": (
        "Año de expansión, optimismo y apertura filosófica. Viajes largos, estudios superiores, "
        "publicaciones y contactos con el extranjero. Fe renovada en el futuro. "
        "Riesgo de exceso de confianza o promesas incumplibles. "
        "Favorable para enseñanza, viajes, religión y crecimiento espiritual."
    ),
    "Capricornio": (
        "Año de ambición estructurada y responsabilidad máxima. El nativo construye "
        "con paciencia; resultados a largo plazo. Restricciones temporales que forjan carácter. "
        "Temas de autoridad, carrera y reputación en juego. "
        "Riesgo de rigidez, aislamiento o exceso de trabajo."
    ),
    "Acuario": (
        "Año de independencia, innovación y colectividad. Rupturas liberadoras con lo establecido. "
        "El nativo busca su unicidad; amistades y grupos cobran protagonismo. "
        "Ideas originales, tecnología, causas humanitarias. "
        "Riesgo de frialdad emocional o radicalismo."
    ),
    "Piscis": (
        "Año de sensibilidad extrema, espiritualidad y posible confusión. "
        "Arte, sueños, intuición y compasión en primer plano. "
        "Riesgo de evasión, victimismo o falta de límites. "
        "Favorable para creatividad artística, retiro espiritual y ayuda a otros. "
        "Los límites entre lo real y lo imaginado se difuminan."
    ),
}

# ─── MC anual por casa natal (Volguine) ──────────────────────────────────────────
MC_ANUAL_POR_CASA: dict[int, str] = {
    1: "El ego y la identidad personal como principal instrumento de logro. Año de máximo protagonismo; la persona es el proyecto. Riesgo de egocentrismo.",
    2: "Las finanzas y los valores personales como eje dominante del año. Ganancias o pérdidas importantes marcan la trayectoria. Capacidad de monetizar talentos.",
    3: "La comunicación, escritura, hermanos y desplazamientos cortos definen el rumbo profesional. Contratos, cursos y redes de contacto como palanca de éxito.",
    4: "El hogar, la familia y las raíces como centro de la actividad. Posibles mudanzas, herencias o transformaciones familiares que afectan la carrera. Final de un ciclo vital.",
    5: "La creatividad, los hijos, los placeres y la especulación como motor del año. Proyectos artísticos o recreativos que pueden devenir en carrera.",
    6: "El trabajo diario, la salud y el servicio definen el logro. Año de esfuerzo sistemático y mejora de procesos. La salud puede ser el tema que todo lo determina.",
    7: "Las asociaciones, contratos y el 'otro significativo' como palanca principal. Posible matrimonio o sociedad de negocios. El adversario también tiene poder este año.",
    8: "Transformación profunda a través de asuntos ajenos: herencias, créditos, deudas, crisis. El poder viene de manejar recursos de terceros o atravesar crisis regeneradoras.",
    9: "Expansión intelectual y espiritual como eje: viajes largos, estudios superiores, publicaciones, contacto con el extranjero. El conocimiento abre puertas.",
    10: "Cima profesional. Año de máximo reconocimiento público y autoridad. La reputación está en juego; grandes oportunidades y también grandes responsabilidades.",
    11: "Los amigos, grupos y proyectos colectivos como protagonistas. Redes sociales y esperanzas que se materializan. El éxito viene a través de otros.",
    12: "Trabajo en la sombra, retiro o reclusión como condición del año. Posibles hospitalizaciones, secretos o enemigos ocultos. Año de karma, cierre y preparación interior.",
}

# ─── Planetas en casas de RS (Volguine — principales) ────────────────────────────
PLANETA_EN_CASA_RS: dict[str, dict[int, str]] = {
    "sun": {
        1: "Año de gran vitalidad y autoafirmación. La salud robusta y la iniciativa personal dominan. El nativo brilla naturalmente.",
        2: "Los ingresos y posesiones materiales concentran la energía solar del año. Posibilidad de ganancias importantes.",
        3: "Comunicación, escritura y relaciones con hermanos en primer plano. Viajes cortos frecuentes.",
        4: "Transformaciones en el hogar y la familia. Posibles cambios de residencia o asuntos con la madre/padre.",
        5: "Año de creatividad, amor y placer. Posible llegada de hijos. Especulaciones favorables.",
        6: "Trabajo intenso y atención a la salud. El nativo puede agotarse si no pone límites.",
        7: "Asociaciones o matrimonio en el centro del año. El otro define el rumbo. Posibles conflictos abiertos.",
        8: "Transformación profunda a través de crisis, herencias o asuntos de otros. Atención a la salud en profundidad.",
        9: "Viajes largos, estudios superiores, espiritualidad. El horizonte se expande significativamente.",
        10: "Año de máximo éxito profesional y reconocimiento. Oportunidades extraordinarias de liderazgo.",
        11: "Amigos y redes sociales como catalizadores del año. Proyectos colectivos que prosperan.",
        12: "Año de recogimiento, trabajo oculto y posibles adversidades. Riesgo de hospitalizaciones. Fortaleza interior necesaria.",
    },
    "moon": {
        1: "Alta emotividad y popularidad. El nativo es muy sensible a su entorno; cambios frecuentes de estado de ánimo.",
        2: "Las finanzas fluctúan al ritmo de las emociones. Ingresos variables; relación ambigua con el dinero.",
        3: "Comunicación emocional, relaciones con hermanos cargadas de sentimiento. Escritura desde lo personal.",
        4: "Cambios importantes en el hogar. Embarazo posible. La madre cobra protagonismo.",
        5: "Amor y creatividad con gran carga emocional. Los hijos son el centro afectivo del año.",
        6: "Salud sensible a las emociones. Trabajo de cuidado de otros. Alimentación como tema.",
        7: "Las relaciones íntimas son el termómetro emocional del año. Posible matrimonio desde la necesidad afectiva.",
        8: "Ciclos emocionales de muerte/renacimiento. Secretos que afloran. Atención al sistema reproductivo.",
        9: "Espiritualidad intuitiva, sueños proféticos, viajes con significado emocional profundo.",
        10: "La carrera depende de la opinión pública y las conexiones emocionales. Popularidad que abre puertas.",
        11: "Amistades femeninas o muy emotivas. Los grupos dan contención afectiva.",
        12: "Vida emocional recluida. Imaginación desbordante. Riesgo de depresión o evasión.",
    },
    "mercury": {
        1: "Año de comunicación intensa, aprendizaje activo y versatilidad mental. La palabra es el arma.",
        2: "Ingresos a través de la escritura, el comercio o la información. Negocios de comunicación.",
        3: "Máxima actividad en comunicación, viajes cortos, contratos y hermanos.",
        4: "Conversaciones y decisiones importantes en el núcleo familiar. Estudios desde casa.",
        5: "Creatividad intelectual, juegos mentales, relaciones que nacen del diálogo.",
        6: "Trabajo que exige precisión mental. Salud a través de la información y el diagnóstico.",
        7: "Contratos y negociaciones como eje del año. Socio o pareja muy comunicativa.",
        8: "Investigación profunda, psicología, asuntos legales o financieros que requieren análisis.",
        9: "Estudios superiores, publicaciones, filosofía. El intelecto se expande.",
        10: "La mente como herramienta de éxito. Escritura o comunicación pública que da reconocimiento.",
        11: "Redes intelectuales, grupos de estudio, amigos que estimulan el pensamiento.",
        12: "Pensamiento introspectivo, estudios secretos, posibles confusiones mentales.",
    },
    "venus": {
        1: "Año de encanto personal, atractivo y apertura a la belleza. El amor llega con facilidad.",
        2: "Año financiero favorable. Ganancias a través del arte, la belleza o relaciones afectivas.",
        3: "Amor en el entorno cercano. Hermanos o vecinos traen afecto. Escritura creativa.",
        4: "Armonía en el hogar. Decoración, mudanza hermosa. Amor en familia.",
        5: "Año de gran amor romántico y creatividad artística. Los hijos traen alegría.",
        6: "Armonía en el trabajo. Relaciones afectivas con compañeros. Salud como autocuidado.",
        7: "Matrimonio o compromiso afectivo muy posible. Año de las grandes alianzas amorosas.",
        8: "Amor transformador, pasional y profundo. Herencias de personas queridas.",
        9: "Amor a distancia, con extranjeros o a través del arte y la filosofía.",
        10: "Éxito a través del encanto y las relaciones sociales. Carrera en artes o diplomacia.",
        11: "Amistades amorosas, grupos de arte. El amor llega a través de grupos o causas.",
        12: "Amor secreto. Relaciones ocultas o con personas casadas. Riesgo de sacrificio amoroso.",
    },
    "mars": {
        1: "Año de máxima energía física y combatividad. Riesgo de accidentes o conflictos si no se canaliza.",
        2: "Esfuerzo intenso para ganar dinero. Energía empresarial. Posibles disputas financieras.",
        3: "Argumentos con hermanos o vecinos. Escritura combativa. Viajes rápidos y frecuentes.",
        4: "Conflictos en el hogar o con la familia. Obras y reformas en casa. Energía doméstica intensa.",
        5: "Amor apasionado, aventuras amorosas. Deportes, juegos, riesgo en especulaciones.",
        6: "Trabajo intenso, sobrecarga laboral posible. Inflamaciones o problemas musculares.",
        7: "Conflictos abiertos con socios o pareja. Competencia intensa. Posibles rupturas.",
        8: "Crisis financieras o emocionales. Cirugías posibles. Energía de transformación radical.",
        9: "Combatividad ideológica. Viajes con propósito. Estudios con gran dedicación.",
        10: "Ambición profesional al máximo. Lucha por el éxito. Posibles conflictos con autoridades.",
        11: "Energía en grupos y proyectos colectivos. Amigos que compiten o generan conflicto.",
        12: "Energía reprimida. Conflictos ocultos. Trabajos agotadores sin reconocimiento. Riesgo de autoboicot.",
    },
    "jupiter": {
        1: "Año de expansión personal, optimismo y reconocimiento. Todo fluye con facilidad.",
        2: "Ganancias financieras importantes. Prosperidad material. Generosidad con el dinero.",
        3: "Aprendizaje y comunicación expansivos. Éxito en escritura, cursos y viajes cortos.",
        4: "Ampliación del hogar. Familia que prospera. Bienes raíces favorables.",
        5: "Gran suerte en amor, creatividad y especulaciones. Hijos que traen alegría.",
        6: "Trabajo satisfactorio y salud mejorada. Reconocimiento por el servicio.",
        7: "Matrimonio o asociación muy favorable. El otro trae abundancia.",
        8: "Herencias, inversiones y recursos de terceros favorables. Transformación beneficiosa.",
        9: "Expansión intelectual y espiritual máxima. Viajes transformadores. Publicaciones exitosas.",
        10: "Gran éxito profesional. Reconocimiento público. Oportunidades excepcionales.",
        11: "Amigos influyentes que abren puertas. Grupos que prosperan. Esperanzas cumplidas.",
        12: "Protección invisible. Trabajo espiritual que da frutos ocultos. Año de cierre con gracia.",
    },
    "saturn": {
        1: "Año de responsabilidades pesadas y restricciones en la identidad. Madurez forzada. Salud que requiere atención.",
        2: "Escasez financiera posible o gastos inevitables. Año de austeridad y ahorro forzado.",
        3: "Comunicación restringida. Relaciones difíciles con hermanos. Estudios con esfuerzo.",
        4: "Cargas familiares o restricciones en el hogar. Pérdidas en la familia. Trabajo en los cimientos.",
        5: "Amor serio y tardío. Hijos que demandan. Creatividad bloqueada temporalmente.",
        6: "Trabajo muy exigente. Enfermedades crónicas posibles. Disciplina en la rutina.",
        7: "Relaciones con personas mayores o muy serias. Matrimonio con responsabilidades. Socios exigentes.",
        8: "Crisis financieras o de transformación profunda. Asuntos de herencias complicados.",
        9: "Estudios serios y exigentes. Viajes con propósito. Filosofía como ancla.",
        10: "Consolidación profesional a través del esfuerzo. Posible caída de quienes no tienen base sólida.",
        11: "Amigos que se van o decepcionan. Grupos que imponen restricciones. Soledad social.",
        12: "Confinamiento, karma pesado, enfermedad crónica posible. Año de cierre de deudas del alma.",
    },
    "uranus": {
        1: "Año de cambios radicales en la identidad. Rupturas liberadoras. El nativo ya no es el mismo.",
        2: "Cambios súbitos en las finanzas. Ingresos irregulares. Innovación económica.",
        3: "Comunicación disruptiva. Ideas brillantes. Rupturas con hermanos o vecinos.",
        4: "Cambios repentinos en el hogar. Mudanzas inesperadas. Revelaciones familiares.",
        5: "Amor libre e inesperado. Creatividad radical. Hijos que sorprenden.",
        6: "Trabajo con tecnología o métodos innovadores. Salud con tratamientos alternativos.",
        7: "Rupturas en relaciones o alianzas inesperadas. Socios que llegan y se van.",
        8: "Transformaciones radicales. Crisis súbitas. Herencias inesperadas.",
        9: "Ideas filosóficas revolucionarias. Viajes imprevistos. Estudios fuera de lo convencional.",
        10: "Cambios súbitos en la carrera. Innovación profesional. Reputación que cambia radicalmente.",
        11: "Grupos y amigos que transforman la vida. Redes tecnológicas. Causas colectivas innovadoras.",
        12: "Liberación de patrones profundos. Revelaciones del inconsciente. Rupturas internas.",
    },
    "neptune": {
        1: "Año de sensibilidad extrema, espiritualidad e idealismo. Identidad difusa. Riesgo de confusión.",
        2: "Finanzas nebulosas. Riesgo de engaño económico. Ingresos artísticos o espirituales.",
        3: "Comunicación intuitiva o confusa. Escritura artística. Noticias dudosas.",
        4: "Hogar idealizado. Familia con secretos. Riesgo de engaños domésticos.",
        5: "Amor idealizado, ilusorio o espiritual. Creatividad artística elevada.",
        6: "Trabajo en servicio compasivo. Salud con componente emocional o psicosomático.",
        7: "Relaciones idealizadas. Pareja que decepciona o espiritualiza. Socios poco claros.",
        8: "Misterios profundos, asuntos ocultos. Herencias nebulosas. Espiritualidad intensa.",
        9: "Espiritualidad, misticismo y viajes espirituales. Filosofía mística.",
        10: "Carrera artística o espiritual. Fama nebulosa. Sacrificio por la vocación.",
        11: "Amigos idealistas o que decepcionan. Grupos espirituales o artísticos.",
        12: "Año de retiro espiritual profundo. Alta sensibilidad mística. Riesgo de evasión.",
    },
    "pluto": {
        1: "Transformación radical de la identidad. El nativo renace. Poder personal intenso.",
        2: "Transformación profunda de los valores y los recursos. Poder económico o crisis financiera.",
        3: "Comunicación profunda y transformadora. Investigación. Secretos que se revelan.",
        4: "Transformación del hogar y las raíces. Cambios generacionales en la familia.",
        5: "Amor obsesivo y transformador. Hijos que cambian la vida. Creatividad poderosa.",
        6: "Trabajo en transformación de sistemas. Salud con crisis profundas que sanan.",
        7: "Relaciones que transforman o destruyen. Socios muy poderosos. Luchas de poder.",
        8: "Casa natural de Plutón: transformación máxima, herencias, asuntos de vida/muerte.",
        9: "Transformación de creencias profundas. Estudios que cambian la cosmovisión.",
        10: "Poder en la carrera. Ascenso o caída dramáticos. El nativo deja huella.",
        11: "Grupos que transforman. Amigos poderosos. Causas que cambian el mundo.",
        12: "Transformación desde las profundidades del inconsciente. Secretos que salen. Karma intenso.",
    },
}

# ─── Figuras aspectuales (Tito Maciá) ────────────────────────────────────────────
FIGURAS_ASPECTUALES: dict[str, str] = {
    "T Cuadrada": (
        "FIGURA: T Cuadrada — Dos planetas en oposición con un tercero en cuadratura a ambos.\n"
        "TEMA CENTRAL: Las cargas más pesadas de la vida. El nativo accede a posiciones de poder "
        "pero siempre a costa de grandes esfuerzos. El planeta en el vértice (el que hace cuadratura) "
        "es el punto de mayor tensión y también de mayor potencial. La vida no regala nada: "
        "todo se gana con trabajo sostenido. Puede generar éxitos extraordinarios pero el precio "
        "en esfuerzo es proporcional."
    ),
    "Gran Cruz": (
        "FIGURA: Gran Cruz — Cuatro planetas en cuadratura mutua formando una cruz.\n"
        "TEMA CENTRAL: Tensión en cuatro frentes simultáneos. El nativo lleva cargas en "
        "todas las áreas de vida a la vez. Alta capacidad de trabajo y resistencia, "
        "pero agotamiento frecuente. El éxito es posible pero nunca llega sin costo máximo."
    ),
    "Gran Trígono": (
        "FIGURA: Gran Trígono — Tres planetas separados por 120° entre sí.\n"
        "TEMA CENTRAL: Energía fluida y talentos dados naturalmente. El camino está facilitado. "
        "Riesgo de pereza o complacencia: los dones no se desarrollan sin esfuerzo consciente. "
        "La persona puede lograr mucho si activa voluntariamente lo que el cosmos le da."
    ),
    "Gran Sextil": (
        "FIGURA: Gran Sextil — Seis planetas a 60° entre sí (estrella de David).\n"
        "TEMA CENTRAL: Alta energía fluida. La persona puede lograr lo que desea con relativa facilidad. "
        "ADVERTENCIA: Los logros personales a veces dañan la economía o las relaciones cercanas. "
        "'Cuidado con lo que deseas' — el éxito puede tener costos colaterales inesperados."
    ),
    "Sextil Cósmico": (
        "FIGURA: Sextil Cósmico — Variante del sextil masivo con intensa actividad mental.\n"
        "TEMA CENTRAL: La persona vive en su mente. Producción intelectual elevada, "
        "pensamiento acelerado y genial. Tendencia al aislamiento social: prefiere las ideas a las personas. "
        "Año de gran productividad mental pero posible soledad."
    ),
    "Dedo de Dios": (
        "FIGURA: Dedo de Dios (Yod) — Dos planetas en sextil, ambos en quincuncio (150°) a un tercero.\n"
        "TEMA CENTRAL: El planeta en el vértice representa la misión de vida. Sensación de ser "
        "'elegido' o señalado por el destino para algo específico. Alta movilidad geográfica y existencial. "
        "La persona puede sacrificar carrera o estabilidad en momentos inesperados, siguiendo un 'llamado'. "
        "Dificultad para establecerse; cambios de dirección forzados pero significativos."
    ),
    "Espigón Celeste": (
        "FIGURA: Espigón Celeste (Cradle/Lanzadera) — Oposición con sextiles y trígonos laterales.\n"
        "TEMA CENTRAL: Resultados rápidos y a veces forzados. La persona no puede 'calentarse' gradualmente: "
        "entra en acción de golpe. Ruptura súbita con proyectos anteriores. "
        "Los ciclos se cierran y abren con velocidad inusual."
    ),
    "Gran Espigón Celeste": (
        "FIGURA: Gran Espigón Celeste — Versión expandida del Espigón con más planetas.\n"
        "TEMA CENTRAL: Los esfuerzos personales siempre son recompensados. Figura de perseverancia "
        "que garantiza resultado proporcional al esfuerzo. Exige trabajo constante pero la cosecha llega."
    ),
    "Semicuadrado Cósmico": (
        "FIGURA: Semicuadrado Cósmico — Aspectos de 45° y 135° múltiples.\n"
        "TEMA CENTRAL: LA FIGURA MÁS PELIGROSA DEL CATÁLOGO. Mayor riesgo de fatalidad, "
        "accidente o situación límite. También asociada a inconvenientes amorosos que pueden "
        "destruir la vida organizada. En RS: año de máximo peligro; se requieren precauciones extremas "
        "en desplazamientos, salud y decisiones impulsivas."
    ),
    "Quincucio Cósmico": (
        "FIGURA: Quincucio Cósmico — Quincuncios (150°) múltiples entre planetas.\n"
        "TEMA CENTRAL: Conexiones fatales. La persona se ve forzada a ligarse con situaciones "
        "o personas que no habría elegido libremente. Renunciación casi inevitable de algo valioso. "
        "Sacrificio como tema central del período. En RS: año en que algo importante debe ser abandonado "
        "o se perderá sin poder evitarlo."
    ),
}

# ─── Aspectos y sus significados ─────────────────────────────────────────────────
TIPO_ASPECTO: dict[str, str] = {
    "conjunction": "conjunción (fusión, concentración de energías, inicio)",
    "opposition": "oposición (tensión entre extremos, conciencia del otro, polaridad)",
    "trine": "trígono (flujo armónico, talentos, facilidad)",
    "square": "cuadratura (tensión productiva, obstáculos que forjan, energía para actuar)",
    "sextile": "sextil (oportunidades que hay que aprovechar, cooperación)",
    "quincunx": "quincuncio (ajuste obligatorio, conexiones kármicas, renuncia necesaria)",
    "semisquare": "semicuadrado (fricciones, irritaciones menores pero persistentes)",
    "sesquisquare": "sesquicuadrado (tensión acumulada, puntos de quiebre)",
}

# ─── Dignidades y su impacto ──────────────────────────────────────────────────────
DIGNIDAD_INTERPRETACION: dict[str, str] = {
    "domicilio": "en domicilio: planeta en máxima expresión natural, fuerte y efectivo",
    "exaltación": "en exaltación: planeta potenciado al máximo, resultados extraordinarios pero posible exceso",
    "detrimento": "en detrimento: planeta debilitado, funciona con dificultad, necesita esfuerzo extra",
    "caída": "en caída: planeta en peor posición, resultados inconsistentes, energía mal expresada",
    "neutral": "en signo neutral: funciona según aspectos y casa",
}

# ─── Casas de la RS y su significado general ─────────────────────────────────────
CASAS_RS_DESCRIPCION: dict[int, str] = {
    1: "Casa 1 RS — El yo, la actitud vital del año, energía física disponible",
    2: "Casa 2 RS — Recursos, finanzas, posesiones, valores del año",
    3: "Casa 3 RS — Comunicación, desplazamientos, hermanos, contratos menores",
    4: "Casa 4 RS — Hogar, familia, raíces, fin del asunto anual",
    5: "Casa 5 RS — Creatividad, hijos, amor, placer, especulación",
    6: "Casa 6 RS — Trabajo diario, salud, servicio, empleados",
    7: "Casa 7 RS — Pareja, socios, contratos mayores, adversarios",
    8: "Casa 8 RS — Transformación, herencias, crisis, recursos ajenos",
    9: "Casa 9 RS — Expansión, viajes largos, estudios superiores, espiritualidad",
    10: "Casa 10 RS — Carrera, reputación, logros, autoridad",
    11: "Casa 11 RS — Amigos, grupos, proyectos futuros, esperanzas",
    12: "Casa 12 RS — Karma, reclusión, adversarios ocultos, trabajo en silencio",
}

# ─── Sistema de timing mensual (Volguine + Débonnaire) ───────────────────────────
TIMING_RS_MESES: str = """
TIMING DE LA REVOLUCIÓN SOLAR (sistema Volguine/Débonnaire):
- 1 año = 360° = 365 días
- El Sol de RS actúa como aguja del reloj anual:
  • Cuando el Sol de RS está en la Casa 1 de RS: mes 1 (primer mes del año de RS)
  • Cuando el Sol de RS está en la Casa 2 de RS: mes 2-3 (aproximadamente)
  • Y así sucesivamente por las 12 casas
- Cada casa de RS = aproximadamente 1 mes de vida real
- 2 horas de diferencia en el ASC de RS = 1 mes de diferencia en eventos
- El ASC progresado de RS avanza 5°10.7' por día → al cruzar cúspides, activa ese tema
- Los aspectos SEPARATIVOS en RS = eventos ya ocurridos después del aniversario
- Los aspectos APLICATIVOS en RS = eventos aún por producirse en el año
"""

# ─── RSP — Revolución Solar con Precesión (Froger) ───────────────────────────────
RSP_EXPLICACION: str = """
RSP (Revolución Solar con Precesión) — Método de Maurice Froger:
- La precesión de los equinoccios mueve el punto vernal ~50.29 arcseg/año (≈4'26"/año)
- Esto significa que el Sol tropical llega cada año antes al mismo punto sidéreo
- La RSP corrige esto: en lugar de retornar a la longitud tropical natal,
  el Sol retorna a la longitud SIDÉREA natal (= longitud natal + precesión acumulada)
- Efecto práctico a los 35 años: RSP llega ~12 horas después de la RS tropical
  → El MC se convierte en FC; la Luna avanza 6°-7° de RS a RSP
- Principio: las estrellas fijas son el marco de referencia verdadero del cosmos
- Froger propone usar siempre el lugar de nacimiento (no el de residencia)
- A mayor edad, mayor diferencia entre RS y RSP (y mayor relevancia)
"""

# ─── Los Mensales — Privat ───────────────────────────────────────────────────────
MENSALES_EXPLICACION: str = """
MENSALES (Revoluciones Lunares) — Sistema de Maurice Privat:
- Se usa la posición de la LUNA EN LA RS (no la Luna natal) como punto de retorno
- La Luna regresa a esa posición cada mes sidéreo (~27.32 días)
- Esto crea un sistema TRIDIMENSIONAL: natal + RS + Mensal
- Los Mensales son el "microscopio" astrológico: revelan el detalle mensual
- Interpretación triple: [casa RL en RS] × [casa RS en natal] × [planeta activado]
- Si la RS previene de un accidente grave y se quiere fechar, el Mensal indica el mes exacto
- Son difíciles de interpretar pero su rendimiento es "extraordinario, lleno de revelaciones"
- Privat recomienda el sistema de Plácido (el más científico según él)
- Máxima del sistema: "Los príncipes tenían un astrólogo dedicado solo a ellos —
  ahora sé por qué a ese sabio no le faltaba trabajo en todo el año"
"""

# ─── Nodos Lunares — misión y karma ──────────────────────────────────────────────
NODOS_SIGNIFICADO: dict[str, str] = {
    "norte_aries": "Misión: desarrollar autonomía, iniciativa y coraje. Karma: soltar la dependencia del grupo (Libra sur).",
    "norte_tauro": "Misión: construir seguridad material y valores propios. Karma: soltar la obsesión por la transformación radical.",
    "norte_geminis": "Misión: aprender, comunicar y ser curioso. Karma: soltar el dogmatismo o el pensamiento absoluto.",
    "norte_cancer": "Misión: nutrir, crear hogar y conectar emocionalmente. Karma: soltar la ambición pura sin raíces.",
    "norte_leo": "Misión: crear, liderar y brillar con autenticidad. Karma: soltar la disolución en el grupo.",
    "norte_virgo": "Misión: servir con precisión, discernir y mejorar. Karma: soltar el idealismo difuso.",
    "norte_libra": "Misión: crear relaciones equilibradas y hermosas. Karma: soltar el individualismo y la guerra.",
    "norte_escorpio": "Misión: transformarse, profundizar y soltar el apego material. Karma: soltar la acumulación.",
    "norte_sagitario": "Misión: expandirse, estudiar y creer en algo mayor. Karma: soltar el pragmatismo sin fe.",
    "norte_capricornio": "Misión: construir con autoridad y responsabilidad. Karma: soltar la vida doméstica como único mundo.",
    "norte_acuario": "Misión: innovar para el colectivo, ser original. Karma: soltar el ego solar.",
    "norte_piscis": "Misión: disolverte en lo trascendente, servir y creer. Karma: soltar el análisis obsesivo.",
}

# ─── ASC anual por casa NATAL (Volguine — indicador #1 en RS) ────────────────
# El signo del ASC anual en qué casa natal cae determina la TONALIDAD del año.
ASC_ANUAL_POR_CASA_NATAL: dict[int, str] = {
    1: (
        "ASC anual en Casa 1 natal — AÑO DE MÁXIMA AUTONOMÍA PERSONAL.\n"
        "Este es el año en que el nativo ejerce su máxima libertad de acción y voluntad. "
        "Los planetas en casa 1 sin conjunción al ASC anual indican que el nativo sufre eventos "
        "sin haberlos provocado. Si el ASC anual coincide con un planeta natal, el nativo es "
        "directamente el CAUSANTE de lo que acontece. Año de gran actividad personal, "
        "protagonismo y presencia en el mundo. Las cosas dependen de él más que nunca. "
        "Riesgo: egocentrismo, combatividad excesiva si hay planetas maléficos en ángulo."
    ),
    2: (
        "ASC anual en Casa 2 natal — AÑO DOMINADO POR LAS FINANZAS.\n"
        "Las cuestiones económicas y de recursos materiales marcan toda la tonalidad del año. "
        "El nativo concentra su energía en ganar, conservar o perder dinero. Los planetas "
        "benéficos en casa 2 anual prometen ganancias; los maléficos, pérdidas o gastos "
        "inevitables. El valor personal y la autoestima también están en juego. "
        "Es un año en que las posesiones materiales reflejan el estado interno."
    ),
    3: (
        "ASC anual en Casa 3 natal — AÑO DE COMUNICACIÓN, HERMANOS Y VIAJES CORTOS.\n"
        "El entorno inmediato cobra protagonismo: hermanos, vecinos, contratos locales, "
        "escritura, cursos y desplazamientos frecuentes. Nota de Volguine: en temas masculinos, "
        "la Casa 3 es la 'casa del amante' — puede señalar una aventura amorosa paralela "
        "a la relación principal. Año favorable para estudios, contratos y comunicación; "
        "desfavorable si el ASC anual recibe aspectos de maléficos (accidentes en trayectos)."
    ),
    4: (
        "ASC anual en Casa 4 natal — AÑO DEL HOGAR, LA FAMILIA Y LOS FINALES.\n"
        "Cambios en la residencia, transformaciones familiares profundas o asuntos con los padres. "
        "Este eje termina ciclos: negocios que se cierran, proyectos que llegan a su fin natural. "
        "ATENCIÓN: Volguine señala que la Casa 4 está asociada frecuentemente con el año de "
        "la muerte del nativo o de personas muy cercanas. No es determinante por sí sola, "
        "pero cuando coincide con planetas maléficos angulares refuerza este tema. "
        "También puede indicar herencias, compra de bienes raíces y retiro a lo privado."
    ),
    5: (
        "ASC anual en Casa 5 natal — AÑO DEL AMOR, LOS HIJOS Y LA CREATIVIDAD.\n"
        "Un año marcado por las grandes pasiones amorosas, la llegada de hijos, la expresión "
        "artística y el placer. Las especulaciones pueden ser favorables (con planetas benéficos) "
        "o ruinosas (con maléficos o planetas afligidos). El nativo brilla y disfruta. "
        "Atención especial a los asuntos del corazón: este año los define profundamente."
    ),
    6: (
        "ASC anual en Casa 6 natal — AÑO DESFAVORABLE PARA LA SALUD Y EL TRABAJO.\n"
        "Casa de las pruebas cotidianas: enfermedades, conflictos con empleados o superiores, "
        "sobrecarga de trabajo y obligaciones. Volguine la ubica en el arco '6ª-8ª' que "
        "generalmente es desfavorable. La salud requiere atención preventiva. "
        "Año de servicio y esfuerzo silencioso. Si los planetas están bien aspectados, "
        "el servicio genera recompensa; si están afligidos, el nativo se agota sin reconocimiento."
    ),
    7: (
        "ASC anual en Casa 7 natal — AÑO DE MATRIMONIO O CONFLICTO ABIERTO.\n"
        "El 'otro' domina el año: puede ser el cónyuge, el socio o el adversario. "
        "Si los planetas están bien aspectados: matrimonio, alianzas exitosas, contratos favorables. "
        "Si están afligidos: separación, litigios, enemigos que actúan a cara descubierta. "
        "Volguine señala el arco '6ª-8ª' como generalmente desfavorable: la Casa 7 "
        "puede traer confrontaciones necesarias. El nativo debe aprender a negociar y ceder."
    ),
    8: (
        "ASC anual en Casa 8 natal — AÑO DE CRISIS, TRANSFORMACIÓN Y ASUNTOS DE OTROS.\n"
        "Año de grandes intensidades: muertes en el entorno cercano, depresión emocional, "
        "pérdidas significativas. Pero también: herencias financieras, acceso a recursos "
        "de terceros, inversiones importantes. El espiritismo y lo oculto pueden tentarlo. "
        "Volguine advierte: este año puede ser de 'depresión o herencia' según los demás "
        "indicadores. La transformación es inevitable; el nativo emerge cambiado."
    ),
    9: (
        "ASC anual en Casa 9 natal — AÑO DE EXPANSIÓN, VIAJES Y FILOSOFÍA.\n"
        "Un viaje importante o contacto con el extranjero marca el año. Estudios superiores, "
        "publicaciones, asuntos legales o religiosos cobran protagonismo. "
        "El nativo amplía su visión del mundo y su horizonte intelectual/espiritual. "
        "Favorable para enseñanza, publicaciones y relaciones internacionales. "
        "Si hay maléficos afligidos: accidentes en viajes, conflictos legales o filosóficos."
    ),
    10: (
        "ASC anual en Casa 10 natal — AÑO DE MÁXIMO IMPACTO PROFESIONAL.\n"
        "La acción personal del nativo determina directamente un cambio en su situación "
        "profesional o de reputación. Es él quien toma las riendas de su carrera. "
        "Cuando el ASC anual cae en Casa 10 natal, los sucesos del año van directamente "
        "ligados a las decisiones del nativo. Nota de Volguine: 'Las cosas vienen al nativo "
        "sin esfuerzo cuando el MC anual cae en Casa 1 natal — más favorable que ASC en 10.' "
        "Año de alta visibilidad pública; la reputación está completamente expuesta."
    ),
    11: (
        "ASC anual en Casa 11 natal — AÑO DE AMIGOS, ALIADOS Y PROYECTOS GRUPALES.\n"
        "Los aliados juegan un papel decisivo: pueden abrir puertas inesperadas o traicionar "
        "en momentos críticos. Los grupos y asociaciones cobran protagonismo. "
        "El nativo logra sus metas a través de redes sociales y apoyo colectivo. "
        "Riesgo: amigos que no son lo que parecen; proyectos grupales que se disuelven. "
        "Si los planetas están bien dispuestos, es un año de realizaciones a través del colectivo."
    ),
    12: (
        "ASC anual en Casa 12 natal — AÑO DE PRUEBAS, RECLUSIÓN Y ENEMIGOS OCULTOS.\n"
        "El año más difícil en el ciclo de las Revoluciones Solares. Volguine lo describe como "
        "'año de pruebas, enfermedades crónicas, persecución de enemigos secretos y retirada'. "
        "El nativo puede verse hospitalizado, confinado o trabajando en el anonimato. "
        "Los enemigos actúan en la sombra y pueden causar daño real. "
        "Sin embargo, si los planetas están bien aspectados, este año puede ser de "
        "profunda purificación espiritual, trabajo interior intenso y karma saldado. "
        "El nativo necesita paciencia, prudencia y refugio interior."
    ),
}

# ─── Superposición de casas RS×natal — 144 combinaciones (Volguine) ──────────
# Formato: (casa_anual, casa_natal) -> interpretación
# Solo se incluyen las más significativas; la lógica es aditiva: combinar ambas casas.
SUPERPOSICION_CASAS_CLAVE: dict[tuple[int, int], str] = {
    (1, 1): "Máxima autonomía: el nativo concentra todo su poder personal en su propia identidad y desarrollo.",
    (1, 4): "La vitalidad del año se invierte en el hogar y la familia; posible mudanza o renovación de raíces.",
    (1, 7): "La energía personal se proyecta hacia el otro; año de relaciones que definen la identidad.",
    (1, 10): "Año de acción directa sobre la carrera; el nativo lidera su destino profesional.",
    (2, 1): "Los recursos propios sostienen el yo; año de construcción material basada en talentos propios.",
    (2, 8): "Los recursos del año provienen de terceros, herencias o inversiones; transformación financiera.",
    (5, 7): "El amor o la creatividad activan el área de las relaciones; posible romance o matrimonio.",
    (7, 4): "Las relaciones íntimas se desarrollan en el ámbito del hogar; pareja que vive con el nativo.",
    (7, 5): "El amor romántico o las asociaciones creativas; pareja que inspira creatividad.",
    (8, 1): "Recursos ajenos o crisis de transformación afectan directamente la identidad del nativo.",
    (8, 4): "Herencias o pérdidas en la familia; transformación del hogar a través de crisis.",
    (10, 1): "El éxito profesional viene directamente de la acción personal del nativo.",
    (10, 7): "La carrera depende de los socios o pareja; el otro es la clave del reconocimiento.",
    (12, 1): "El nativo trabaja en silencio; energía recluida que puede generar trabajo espiritual profundo.",
    (12, 6): "Doble energía de reclusión y servicio; posible hospitalización o trabajo en instituciones.",
    (12, 12): "Año de cierre kármico máximo; retiro, meditación, sacrificio y liberación de patrones profundos.",
}

# ─── Conjunciones planetarias en RS — significados clave (Volguine) ──────────
CONJUNCIONES_EN_RS: dict[str, str] = {
    "sol_luna": (
        "PUNTO NEURÁLGICO del año. La conjunción Sol-Luna en RS crea el nudo "
        "más tenso del tema anual. Si esta conjunción existía en el nacimiento, "
        "los eventos del año modificarán profundamente el destino. En todos los casos "
        "señala un hecho sobresaliente del año. La naturaleza del signo se expresa "
        "con gran fuerza (Aries=lucha, Tauro=esfuerzo tenaz, Cáncer=inquietudes familiares...)."
    ),
    "sol_marte": (
        "Configuración de violencia y brutalidad ejercida o sufrida. Si está en ASC o MC anual: "
        "el nativo es quien ejerce la violencia. Si está afligida: golpes, heridas, conflictos pasionales. "
        "Frecuente en años de rupturas, divorcios y tentativas de suicidio. "
        "En casas 6 y 12: intervenciones quirúrgicas."
    ),
    "sol_jupiter": (
        "Aumenta ambiciones y apetito de ganancias. Bien aspectado en 2ª, 10ª, 4ª, 8ª: prosperidad. "
        "En ASC: euforia irrazonable y provisional. Afligido por Marte: peligro para la salud "
        "(infecciones, inflamaciones, excesos)."
    ),
    "sol_saturno": (
        "Año de soledad moral y física, inquietudes continuas. El Sol representa al hombre en tema femenino "
        "→ penas causadas por el marido, padre o hijo. No suele afectar la salud directamente a menos "
        "que esté en casas 6 o 12. Obra de forma restrictiva, retrasando las cosas buenas. "
        "Excepción: si el ASC natal es Capricornio y Sol-Saturno estaban en buen aspecto natal → "
        "puede señalar un avance o agrandamiento importante."
    ),
    "sol_urano": (
        "Siempre anuncia transformación profunda y súbita en el área de la casa donde cae. "
        "Bien aspectado y natal en buen aspecto: hecho inesperado pero muy bueno. "
        "Mal aspectado o natal en cuadratura: catástrofe en esa área de vida."
    ),
    "sol_neptuno": (
        "Ambiente muy confuso y oscuro. El nativo vive en condiciones ambiguas, "
        "miedos o esperanzas que terminan en fracasos. Ideal: evitar decisiones importantes este año."
    ),
    "sol_pluton": (
        "Tendencias más prácticas y utilitarias. Necesidad de gastar y transformar recursos. "
        "A menudo índice de un suceso que supera las esperanzas del nativo."
    ),
    "luna_marte": (
        "Excesos e imprudencias de todo tipo. Falta de agilidad en las relaciones. "
        "Si alguno de los dos es regente del ASC: el nativo puede provocarse problemas serios. "
        "Más nociva en temas femeninos que en masculinos."
    ),
    "luna_jupiter": (
        "Siempre indica mejora de fortuna, entradas de dinero, regalos apreciables y ventajas materiales. "
        "Facilita los asuntos de la casa donde cae."
    ),
    "luna_saturno": (
        "Graves problemas provenientes de mujeres. En temas masculinos es tan significativa "
        "como Sol-Saturno en temas femeninos."
    ),
    "luna_urano": (
        "Desarrollo imprevisto de los hechos. Modifica toda la existencia. "
        "Frecuente en años de accidentes y operaciones. Siempre incita a los viajes."
    ),
    "venus_marte": (
        "PERJUDICA SIEMPRE la vida sentimental. Más nociva que la oposición. "
        "Incita a una ola de sensualidad que falsea el juicio. "
        "Muy frecuente en años de adulterio."
    ),
    "venus_jupiter": (
        "IMAGEN MÁS SEGURA DE ÉXITO Y PROSPERIDAD. En casas financieras o 10ª: prosperidad. "
        "En casas personales: felicidad. La reunión de dos benéficos es promesa de suerte. "
        "Nota: no todos los destinos contienen esta configuración en la vida."
    ),
    "venus_urano": (
        "ANUNCIA TORMENTA en la vida sentimental. Muy peligrosa en ángulos o en casa 5. "
        "A menudo señala un 'flechazo'. En casa 7: ruptura o grave perturbación conyugal."
    ),
    "marte_jupiter": (
        "Gran esfuerzo coronado de éxito, hazaña o performance. Los deportistas establecen récords. "
        "En un ángulo bien aspectado: gran triunfo. Mal aspectado: choques, conflictos, litigios."
    ),
    "marte_saturno": (
        "Gran esfuerzo sostenido, largo y penoso. El éxito no está garantizado: solo el conjunto "
        "del tema anual decide. En casas 6 y 12: reacción del organismo ante una enfermedad. "
        "También asociado a extracciones dentales y operaciones de huesos."
    ),
    "marte_urano": (
        "Anuncia accidente o hecho súbito y violento. Si uno de los dos es regente del ASC "
        "o la configuración está en el Oriente: el nativo lo provoca. "
        "Si está en otra posición: el evento cae sobre él sin que dependa de su voluntad."
    ),
    "jupiter_saturno": (
        "Estabiliza las cosas indicadas por la casa donde se encuentra. "
        "Si uno de los dos rige la casa 10: consolidación favorable de la situación."
    ),
    "jupiter_urano": (
        "Marca una nueva orientación en un dominio cualquiera, frecuentemente en negocios. "
        "Para quienes tienen esta conjunción natal, sus retornos cada 14 años son cruciales. "
        "A menudo señala una mejora de la existencia gracias a nuevas invenciones o tecnologías."
    ),
}

# ─── Planetas anuales cruzando posiciones natales (aforismos Volguine) ────────
PLANETA_ANUAL_EN_SIGNO_NATAL: dict[str, str] = {
    "saturno_en_signo_de_jupiter_natal": (
        "Buen año, herencia o donaciones, ganancias inesperadas. Si Mercurio está en mal aspecto: "
        "adversidad, procesos, querellas inopinadas."
    ),
    "saturno_en_signo_de_marte_natal": (
        "Mal año, contrariedades, penas, enemistades peligrosas, obstáculos en las empresas, "
        "inestabilidad de fortuna."
    ),
    "saturno_en_signo_de_venus_natal": (
        "Querellas conyugales, separación, obstáculos en las empresas, adversidades, disputas. "
        "En tema femenino: amenaza de aborto."
    ),
    "saturno_en_signo_de_luna_natal": (
        "Penas en matrimonio, separación, ruptura con amigos, calumnias, obstáculos en las empresas, "
        "enfermedades nerviosas, caída inopinada."
    ),
    "jupiter_en_signo_de_sol_natal": (
        "Ascenso de fortuna para personas de alto nacimiento. Para condición mediocre: "
        "despegamiento de penas, amistades serviciales, comienzo o aumento de fortuna "
        "(especialmente en horóscopo diurno)."
    ),
    "jupiter_en_signo_de_luna_natal": (
        "Año favorable, peligros evitados, donaciones provenientes de mujeres influyentes. "
        "Si está maleficiado: lo contrario."
    ),
    "marte_en_signo_de_saturno_natal": (
        "Mal año, procesos, decepciones, viajes peligrosos, enfermedades, peligros inopinados, "
        "pérdida de bienes. Si Marte está en Aries o Escorpio: atenuado (salvo en temas femeninos)."
    ),
    "marte_en_signo_de_venus_natal": (
        "Enemistades de mujeres, querellas conyugales, separaciones, enfermedades, adulterio peligroso, "
        "ruptura de amistades. Gran peligro de muerte para mujeres embarazadas."
    ),
    "marte_en_signo_de_luna_natal": (
        "Mal año, peligros numerosos, amenaza de herida por caída o hierro. "
        "Sediciones temibles, insurrecciones domésticas. Si la Luna es creciente: más peligroso."
    ),
    "venus_en_signo_de_saturno_natal": (
        "Discordias conyugales, separación, pérdida de reputación, enemistades, "
        "pasiones escandalosas. Obstáculos en las empresas."
    ),
    "venus_en_signo_de_jupiter_natal": "Buen año.",
    "luna_en_signo_de_saturno_natal": (
        "Año cargado de vicisitudes, muchos enemigos, obstáculos en las empresas. "
        "Enfermedades de la cabeza o intestinos. Si la Luna es occidental: peligro mayor."
    ),
    "luna_en_signo_de_jupiter_natal": (
        "Ascenso de fortuna, amistades serviciales, feliz casamiento, realización de esperanzas "
        "(si no hay ningún aspecto maléfico)."
    ),
    "luna_en_signo_de_venus_natal": (
        "Buen año. Si está en mal aspecto: penas, enfermedades, pérdida de bienes, "
        "celos crueles en matrimonio."
    ),
}

# ─── Retrogradación de planetas en RS (Volguine) ─────────────────────────────
RETROGRADACION_EN_RS: str = (
    "Los planetas retrógrados en RS no señalan generalmente sucesos nuevos, "
    "sino estados de cosas creados por hechos ANTERIORES al aniversario. "
    "Sus efectos disminuyen, contrarian y retardan las cosas buenas. "
    "Un gran número de planetas retrógrados en RS: factor contrario a la longevidad (natal). "
    "En RS, la retrogradación prolonga obstáculos y dificultades. "
    "Los planetas superiores en ángulos tienen máximo efecto (orden: 1ª, 10ª, 7ª, 4ª). "
    "IMPORTANTE: los aspectos separativos en RS = eventos ya ocurridos después del aniversario. "
    "Los aspectos aplicativos = eventos aún por producirse en el año."
)

# ─── Sistema de Mensales — timing y comparación (Privat) ─────────────────────
MENSALES_TIMING: str = (
    "TIMING CON MENSALES (Privat):\n"
    "- Cada Mensal dura aproximadamente 27.32 días (mes sidéreo).\n"
    "- El ASC del Mensal en la casa X de la RS señala una acción personal en ese dominio.\n"
    "- Si la RS indica un accidente grave y hay urgencia de datarlo: el Mensal revelará el mes exacto.\n"
    "- Los Mensales se leen en TRES CAPAS: [Mensal] × [RS] × [natal].\n"
    "- Si la 11ª de RS cae en la 12ª natal (la prisión de los amigos), el Mensal con ASC\n"
    "  en la 11ª de RS indicará 'acción personal que involucra amigos/secretos/reclusión'.\n"
    "- Son el instrumento más fino de todos: 'como el microscopio frente al telescopio'."
)

# ─── Tránsitos del Sol en RS (Volguine) ──────────────────────────────────────
TRANSITOS_SOL_EN_RS: str = (
    "EL SOL COMO AGUJA DEL RELOJ ANUAL (Volguine):\n"
    "- El Sol en tránsito sobre los factores de la RS es el principal datador de eventos.\n"
    "- Se usa más que los planetas superiores (que se usan en tránsitos sobre el natal).\n"
    "- El Sol transita las 12 casas de la RS en 1 año → cada casa = aprox. 1 mes.\n"
    "- La oposición del Sol al ASC anual provoca malestares, especialmente si ASC está en Leo/Aries.\n"
    "- El Sol en conjunción con el ASC de la RS: período de máxima intensidad personal.\n"
    "- Planetas con más planetas en Oriente (cerca del ASC): eventos en primera mitad del año.\n"
    "- Planetas agrupados cerca del MC: eventos hacia la mitad del año.\n"
    "- Planetas en la parte occidental: eventos en segunda mitad del año.\n"
    "- Planetas en Casa 4: eventos hacia el fin del año."
)

# ─── Magia astrológica — cambio de lugar en el aniversario (Volguine) ─────────
MAGIA_ASTROLOGICA: str = (
    "CAMBIO DE LUGAR PARA MEJORAR LA REVOLUCIÓN SOLAR (Volguine):\n"
    "Si el ASC anual cae sobre un planeta maléfico natal o genera configuraciones catastróficas,\n"
    "el nativo puede DESPLAZARSE el día de su cumpleaños para cambiar el ASC de su RS.\n"
    "Un desplazamiento de 400 km puede ser suficiente para modificar radicalmente el tema anual.\n"
    "El nativo debe pasar una JORNADA COMPLETA en el lugar escogido para impregnarse de sus influencias.\n"
    "Ejemplo: ASC anual en Acuario sobre Urano natal en Casa 6 → desplazarse al Este para\n"
    "llevar ese ASC a la Casa 7 natal (conflictos externos) en lugar de la Casa 6 (salud/trabajo).\n"
    "La técnica consiste en alejar los aspectos maléficos violentos de los ángulos.\n"
    "LIMITACIÓN: No se puede prescribir un viaje a las antípodas. Solo se pueden atenuar, no eliminar,\n"
    "las configuraciones. Esta es 'toda la magia astrológica: desviar lo maléfico de los ángulos'."
)

# ─── Los 4 Temperamentos (Hipócrates / Astrología Médica) ───────────────────
TEMPERAMENTOS: dict[str, dict] = {
    "colerico": {
        "nombre": "Temperamento Colérico (Bilioso)",
        "cualidades": "Caliente + Seco → Fuego",
        "humor": "Bilis amarilla",
        "descripcion": (
            "El Quente da: activo, dinámico, extrovertido, entusiasta, musculado. "
            "El Seco da: rigidez, dificultad de ajuste, foco, estructura, autonomía, difícil de influenciar. "
            "Personalidad: pionero, líder, audaz, destemido, conquistador, impaciente. "
            "Sombra: irritable, rudo, hostil, insensible, dominador, poco dado al estudio/investigación. "
            "CUERPO: estatura media-alta, robusto, musculado. Piel avermelhada o amarillada, áspera y caliente al tacto. "
            "Pelo más rojizo. Voz fuerte y enérgica (la más alta). Gestos bruscos y amplios. "
            "MÉDICO: No tiende a las enfermedades psicosomáticas. Afecciones súbitas e inflamatorias."
        ),
    },
    "sanguineo": {
        "nombre": "Temperamento Sanguíneo",
        "cualidades": "Caliente + Húmedo → Aire",
        "humor": "Sangre",
        "descripcion": (
            "El Quente da: activo, dinámico, extrovertido, expansivo. "
            "El Húmedo da: versatilidad, adaptabilidad, sociabilidad, curiosidad, maleabilidad. "
            "Personalidad: simpático, agradable, espontáneo, sensible, emotivo. "
            "Libera sus emociones fácilmente: llora, ríe, no guarda rencor. Naturalmente alegre. "
            "Sombra: oscilante, superficial, disperso, carece de objetividad y prioridades. "
            "CUERPO: alto y esbelto, curvilíneo pero no gordo. Piel lisa, cálida y húmida, tono blanco-rosado. "
            "Voz alta pero no tan brusca como el colérico. Gestos expresivos y graciosos. "
            "MÉDICO: Temas circulatorios y respiratorios. Riesgo de dispersión energética."
        ),
    },
    "melancolico": {
        "nombre": "Temperamento Melancólico",
        "cualidades": "Frío + Seco → Tierra",
        "humor": "Bilis negra (bazo)",
        "descripcion": (
            "El Frío da: introvertido, cerrado, silencioso, reservado, susceptible. "
            "El Seco da: rigidez, foco, determinación, estructura, persistencia. "
            "Personalidad: reflexivo, concentrado, pragmático, responsable, prudente, perfeccionista. "
            "Busca estabilidad y seguridad. Pocos lo consideran pero son profundos. "
            "Sombra: pessimista, depresivo, rancoroso, anti-social, acumula ressentimientos. "
            "Puede psicossomatizar. Obstinado y desconfiado. "
            "CUERPO: estatura media, constitución delgada, huesos salientes. Piel áspera y fría, color amarillo o apagado. "
            "Labios más finos. Poco pelo. Mirada depresiva. Gestos lentos y ponderados. "
            "MÉDICO: ALTA TENDENCIA psicosomática. Riesgo de depresión crónica."
        ),
    },
    "flematico": {
        "nombre": "Temperamento Flemático",
        "cualidades": "Frío + Húmedo → Agua",
        "humor": "Flema (mucosidades, linfa)",
        "descripcion": (
            "El Frío da: introvertido, poco expresivo, reservado, tímido. "
            "El Húmedo da: maleabilidad, adaptabilidad, receptividad, oscilación emocional. "
            "Es el más YIN de todos los temperamentos y el más receptivo. "
            "Personalidad: sensible, emocional, procura seguridad afectiva. "
            "Siente mucho pero expresa poco. Parece insensible aunque no lo es. "
            "Sombra: le falta estructura, foco, osadía, iniciativa y organización. Inestabilidad emocional. "
            "CUERPO: estatura media-baja, tendencia a la obesidad, formas redondeadas. "
            "Piel blanda y fría, color pálido. Hombros caídos. Voz más baja y hesitante. "
            "MÉDICO: Riesgo de enfermedades mucosas, linfáticas, obesidad, retención de líquidos."
        ),
    },
}

# ─── Astrología Médica — Planetas y órganos ──────────────────────────────────
ASTRO_MEDICA_PLANETAS: dict[str, str] = {
    "sol": "Vitalidad. Vista (ojo derecho), corazón, columna, lado izquierdo del cerebro. Núcleo celular.",
    "luna": "Metabolismo general. Digestión, sistema hormonal, ojo izquierdo, lado derecho del cerebro, epidermis. Membranas celulares.",
    "mercurio": "Transmisión y análisis. Nervios, pulmones, respiración, articulaciones, intestinos, hígado (función lisis).",
    "venus": "Riñones, afecciones cutáneas, sangre venosa, páncreas, sistema glucagón-insulina (metabolismo de azúcares).",
    "marte": "Sangre (hemoglobina), bilis, músculos (mioglobina), nariz, órganos sexuales masculinos. Mitocondrias celulares.",
    "jupiter": "Hígado (función síntesis), sangre arterial, semen, olfato. Ribosomas celulares (síntesis proteica).",
    "saturno": "Bazo, sistema óseo, minerales/calcio, oído, dermis.",
    "urano": "Sistema nervioso autónomo, electricidad corporal, espasmos. Tecnología médica.",
    "neptuno": "Sistema linfático, glándula pineal, pies, sistema inmune difuso. Farmacología y anestesia.",
    "pluton": "Órganos reproductivos profundos, sistema hormonal regenerativo, células madre.",
}

# ─── Astrología Médica — Signos y zonas anatómicas ───────────────────────────
ASTRO_MEDICA_SIGNOS: dict[str, str] = {
    "aries": "Cabeza, rostro, cerebro. Área de golpes, jaquecas e inflamaciones craneales.",
    "tauro": "Maxilar inferior, cuello, garganta, cerebelo, tiroides.",
    "geminis": "Pulmones, brazos, hombros, bronquios. Área de fracturas en extremidades superiores.",
    "cancer": "Estómago, páncreas, mamas, codos. Área digestiva y emocional.",
    "leo": "Corazón, espalda, columna vertebral. Área cardiovascular.",
    "virgo": "Intestinos, hígado (función de lisis/división de moléculas), bazo.",
    "libra": "Riñones, caderas. Área de equilibrio y filtración.",
    "escorpio": "Órganos sexuales, vejiga, nariz, colon, recto.",
    "sagitario": "Muslos, nalgas, caderas, hígado (función de síntesis).",
    "capricornio": "Rodillas, piel, huesos, articulaciones. Área de estructura y minerales.",
    "acuario": "Piernas, tobillos, sistema circulatorio periférico.",
    "piscis": "Pies, mucosas, sistema linfático, glándulas endocrinas difusas.",
}

# ─── Casas y sus temas de consulta (Astrología Horaria) ──────────────────────
HORARY_CASAS_TEMAS: dict[int, str] = {
    1: "El consultante mismo, su estado físico/mental, circunstancias personales. Si algo es bueno o malo.",
    2: "Dinero, propiedades, préstamos, inversiones en bolsa, negocios financieros.",
    3: "Medios de transporte, comunicaciones, rumores, noticias, internet, hermanos, estudios básicos.",
    4: "Vivienda, compra/venta de casas, objetos extraviados, padres, asuntos del hogar.",
    5: "Embarazo, hijos, fiestas, mensajeros, juego, diversión, educación y relación con alumnos.",
    6: "Enfermedades agudas, empleo, empleados, instalación de maquinaria en empresa.",
    7: "Pareja (¿me conviene?), socios, adversarios, competiciones, compras/ventas, amante oculto.",
    8: "Enfermedades graves, persona ausente (¿vive?), crisis económica, ayuda económica de terceros.",
    9: "Viajes largos, estudios superiores, legalidad de un negocio, ideología de alguien.",
    10: "Cargos de poder (¿seguiré?), imagen pública, ascensos, oposiciones, elecciones.",
    11: "Sinceridad de amigos, grupos de afinidad, ¿se cumplirán mis esperanzas?",
    12: "Enemigos ocultos, prisioneros, enfermedades crónicas, ¿debo desprenderme de algo?",
}

# ─── Planetas como tipos de personas en Horaria ─────────────────────────────
HORARY_PLANETAS_PERSONAS: dict[str, str] = {
    "sol": "Persona importante o poderosa, altos cargos, figuras de autoridad.",
    "luna": "Mujeres, niños, el público en general. Personas cambiantes o del pasado.",
    "mercurio": "Intelectuales, comunicadores, comerciantes, jóvenes, educadores, mensajeros.",
    "venus": "Mujeres jóvenes, artistas, diplomáticos, personas atractivas o seductoras.",
    "marte": "Deportistas, militares, personas rudas o agresivas, cirujanos, criminales.",
    "jupiter": "Personas honorables, sabias o prósperas. La ley, la justicia, el clero.",
    "saturno": "Agricultores, mineros, ancianos, viudos, personas de luto, amigos del pasado.",
    "urano": "Técnicos, informáticos, ingenieros, rebeldes, psicólogos, astrólogos. Nuevos amigos.",
    "neptuno": "Místicos, artistas, drogadictos, personas misteriosas, médiums, enfermos crónicos.",
    "pluton": "Manipuladores, jefes de organizaciones secretas, personas ocultas y poderosas.",
}

# ─── Indicadores de validez en Horaria ──────────────────────────────────────
HORARY_INVALIDADORES: list[str] = [
    "Luna vacía de curso (no hará nada de lo preguntado)",
    "Mercurio retrógrado (la opinión del consultante cambiará; resultado incierto)",
    "Saturno en casa 7 (el astrólogo tiene dificultad para emitir juicio)",
    "Luna en Vía Combusta (18° Géminis a 2° Cáncer, o 24° Sagitario a 2° Capricornio): tema ardiente",
    "ASC en los primeros 3° de un signo: pregunta prematura",
    "ASC en los últimos 3° de un signo: demasiado tarde, la suerte ya está echada",
]

# ─── Asteroides — Juno, Vesta, Ceres ─────────────────────────────────────────
ASTEROIDES_SIGNIFICADO: dict[str, str] = {
    "juno": (
        "JUNO — El asterismo del compromiso y el tipo de pareja.\n"
        "Juno indica qué tipo de pareja buscamos para un vínculo serio y comprometido. "
        "El signo de Juno describe las características del compañero/a ideal en largo plazo. "
        "Por casa natal: el área de vida donde el compromiso se expresa o se desea. "
        "Juno mal aspectado: conflictos en las alianzas, patrones de traición o posesión en pareja. "
        "Juno bien aspectado: capacidad de compromiso profundo y relaciones duraderas."
    ),
    "vesta": (
        "VESTA — El fuego interior, la devoción y lo que nos consume.\n"
        "Vesta indica hacia qué se dirige la devoción más pura del nativo, casi sacerdotal. "
        "El signo de Vesta describe la naturaleza de ese fuego interior. "
        "Por casa natal: el área donde el nativo puede trabajar con una entrega total. "
        "Vesta fuerte: capacidad de sacrificarse por una causa mayor. "
        "Vesta afligida: la devoción se vuelve autodestructiva o genera fanatismo."
    ),
    "ceres": (
        "CERES — El principio de nutrición y cuidado.\n"
        "Ceres describe CÓMO el nativo nutre, cuida y alimenta (a sí mismo y a otros). "
        "El signo de Ceres indica el estilo de crianza recibido y el que se da. "
        "Por casa natal: el área de vida donde el cuidado se expresa con más fuerza. "
        "Ceres mal aspectado: heridas de nutrición, abandono, necesidad insatisfecha de ser nutrido. "
        "Ceres bien aspectado: gran capacidad nutricia, conexión profunda con los ciclos naturales."
    ),
}

# ─── Lilith (Luna Negra) ──────────────────────────────────────────────────────
LILITH_SIGNIFICADO: str = (
    "LILITH (Luna Negra) — La rebeldía, lo reprimido y la sombra femenina.\n"
    "Lilith marca el área de vida donde el nativo rechaza la obediencia, el sometimiento "
    "y las reglas que siente injustas. Es la energía que irrumpe cuando ya no puede seguir callando. "
    "Por signo: el estilo en que se expresa (o reprime) esta energía rebelde. "
    "Por casa natal: el área donde la sombra aflora con más intensidad. "
    "Lilith bien integrada: autenticidad, poder personal, capacidad de romper patrones heredados. "
    "Lilith no integrada: comportamiento destructivo, provocación compulsiva, herida en lo femenino. "
    "En RS: si Lilith toca ángulos o luminarias, el año puede traer situaciones que desafíen las normas "
    "o en que el nativo deba reclamar su verdad más radical."
)

# ─── Elementos y Modalidades — palabras clave psicológicas ───────────────────
ELEMENTOS_PSICOLOGICOS: dict[str, dict] = {
    "fuego": {
        "signos": ["Aries", "Leo", "Sagitario"],
        "naturaleza": "Caliente + Seco",
        "keywords": ["acción", "entusiasmo", "iniciativa", "voluntad", "inspiración", "creatividad", "liderazgo"],
        "motivacion": "Actuar, conquistar, existir con intensidad",
        "sombra": "Impulsividad, agotamiento, egocentrismo",
        "cuerpo": "Sistema muscular, temperatura corporal, metabolismo activo",
    },
    "tierra": {
        "signos": ["Tauro", "Virgo", "Capricornio"],
        "naturaleza": "Frío + Seco",
        "keywords": ["practicidad", "estabilidad", "materialidad", "constancia", "sensorialidad", "estructura"],
        "motivacion": "Construir, poseer, administrar la realidad concreta",
        "sombra": "Rigidez, materialismo, resistencia al cambio",
        "cuerpo": "Sistema óseo, piel, digestión, tierra como base",
    },
    "aire": {
        "signos": ["Géminis", "Libra", "Acuario"],
        "naturaleza": "Caliente + Húmedo",
        "keywords": ["mente", "comunicación", "relación", "ideas", "versatilidad", "objetividad", "intercambio"],
        "motivacion": "Conectar, comprender, intercambiar ideas y personas",
        "sombra": "Superficialidad, dispersión, frialdad emocional",
        "cuerpo": "Sistema nervioso, pulmones, circulación",
    },
    "agua": {
        "signos": ["Cáncer", "Escorpio", "Piscis"],
        "naturaleza": "Frío + Húmedo",
        "keywords": ["emoción", "intuición", "profundidad", "empatía", "memoria", "transformación", "inconsciente"],
        "motivacion": "Sentir, conectar emocionalmente, transcender",
        "sombra": "Inestabilidad emocional, dependencia, evasión",
        "cuerpo": "Sistema linfático, mucosas, fluidos, sistema reproductivo",
    },
}

MODALIDADES: dict[str, dict] = {
    "cardinal": {
        "signos": ["Aries", "Cáncer", "Libra", "Capricornio"],
        "keywords": ["iniciativa", "acción", "comienzos", "empuje"],
        "descripcion": "Inician los ciclos. Energía de arranque y liderazgo.",
        "sombra": "Impulsividad, no terminan lo que empiezan",
        "en_horaria": "Eventos rápidos, que se resuelven pronto",
    },
    "fijo": {
        "signos": ["Tauro", "Leo", "Escorpio", "Acuario"],
        "keywords": ["perseverancia", "resistencia", "profundidad", "voluntad"],
        "descripcion": "Sostienen los ciclos. Energía de continuidad y determinación.",
        "sombra": "Terquedad, resistencia al cambio, inflexibilidad",
        "en_horaria": "Situaciones que duran, que se resuelven al final",
    },
    "mutable": {
        "signos": ["Géminis", "Virgo", "Sagitario", "Piscis"],
        "keywords": ["adaptación", "flexibilidad", "transición", "dispersión"],
        "descripcion": "Cierran los ciclos y preparan el cambio. Energía de adaptación.",
        "sombra": "Inconstancia, dificultad para comprometerse",
        "en_horaria": "Situaciones con avances y retrocesos, vaivenes",
    },
}

# ─── Tríada de personalidad (enfoque moderno) ─────────────────────────────────
TRIADA_PERSONALIDAD: str = (
    "TRÍADA ESENCIAL DEL HORÓSCOPO NATAL:\n\n"
    "SOL (esencia, ego y propósito vital): Lo que el nativo VIENE A SER en esta vida. "
    "El sol representa la identidad más profunda, el centro magnético de la personalidad. "
    "Se integra plenamente hacia los 35-40 años. "
    "Signo solar = tipo de energía central; casa = área donde se expresa esa esencia.\n\n"
    "ASCENDENTE (energía a integrar y máscara de presentación): "
    "Cómo el nativo APARECE ante el mundo y la energía que debe aprender a incorporar en esta vida. "
    "A diferencia de lo que se pensaba, el ASC no es solo la máscara: es la energía que el nativo "
    "necesita desarrollar y que en general le cuesta más que la solar. "
    "El signo ASC describe también rasgos físicos y el estilo de interacción inicial.\n\n"
    "LUNA (necesidades emocionales y patrones de seguridad): "
    "Lo que el nativo necesita para sentirse emocionalmente seguro y nutrido. "
    "Refleja el pasado, las memorias, los hábitos automáticos y la relación con la madre. "
    "El signo lunar = tipo de necesidad emocional; la casa = el área donde busca esa seguridad."
)

# ─── Capas planetarias (jerarquía de profundidad) ───────────────────────────
CAPAS_PLANETARIAS: dict[str, str] = {
    "luminarias": "Sol y Luna — El YO esencial y las necesidades emocionales. Los más personales.",
    "personales": "Mercurio, Venus, Marte — Estilo mental, amoroso y de acción. Se maduran hasta los 30.",
    "sociales": "Júpiter y Saturno — La relación con la sociedad, la ley y el tiempo. Ciclos de 12 y 29 años.",
    "quiron": "Quirón — La herida que no cierra del todo y que se convierte en medicina para otros. Entre lo personal y lo transpersonal.",
    "transpersonales": "Urano, Neptuno, Plutón — Fuerzas generacionales que transforman profundamente. Se expresan en puntos de quiebre vital.",
}

# ─── Rectificación de la hora natal ─────────────────────────────────────────
RECTIFICACION_HORA: str = (
    "RECTIFICACIÓN DE LA HORA NATAL (principios básicos):\n"
    "- Solo se usan eventos que el nativo NO pudo controlar (no sus decisiones libres).\n"
    "- Fuentes de datos: nacimientos de hijos, muertes de familiares, accidentes, bodas involuntarias.\n"
    "- La RS puede confirmar la hora rectificada: si el ASC de RS cuadra con el evento, la hora es correcta.\n"
    "- Incertidumbre máxima: hora totalmente desconocida → ±15 minutos es el mejor resultado posible.\n"
    "- Método práctico: usar 5 eventos comprobados y buscar la hora natal que active los indicadores "
    "correctos en todos los métodos predictivos (RS, direcciones primarias, progresiones).\n"
    "- NUNCA usar actos del propio nativo como eventos de rectificación."
)
