"""
Extract conflictología sections from module manuals and build the index.
Each section is saved as a standalone file in data/conflictologia/
so the protocol search service can load only the relevant portion.
"""

from __future__ import annotations

import json
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
SOURCES = BASE / "data" / "processed_library" / "Diplomados" / "diplomado-terapia-holistica-1" / "sources"
OUT_DIR = BASE / "data" / "conflictologia"
OUT_DIR.mkdir(parents=True, exist_ok=True)

MODULES = [
    {
        "id": "respiratorio",
        "nombre": "Sistema Respiratorio",
        "subsystems": ["nasal", "laringea", "traqueal", "bronquial", "alveolar", "diafragmatica", "gripal", "tos", "asmatica", "apnea", "tabaquista", "transgeneracional_respiratorio"],
        "total_conflicts": 95,
        "source_file": "Protocolos_de_Rastreo_-_Módulo_1.txt",
        "extract_from_line": 1,
        "keywords": [
            "nariz", "olfato", "alergia nasal", "rinitis", "sinusitis", "estornudos",
            "laringe", "voz", "ronquera", "afonía", "garganta",
            "traquea", "traqueitis",
            "bronquios", "bronquitis", "broncoespasmo",
            "pulmones", "alveolos", "enfisema",
            "diafragma", "hipo",
            "gripe", "influenza", "resfriado",
            "tos", "tos crónica",
            "asma", "asmático", "asmatica",
            "apnea", "apnea del sueño",
            "tabaco", "tabaquismo", "fumar",
            "respiración", "respiratorio", "pulmonar", "pulmón",
            "falta de aire", "ahogo", "asfixia", "disnea",
        ],
    },
    {
        "id": "digestivo",
        "nombre": "Sistema Digestivo",
        "subsystems": ["bucal", "estomacal", "intestinal_delgada", "hepatica", "biliar", "intestinal_gruesa", "anal", "peritoneal", "quimo"],
        "total_conflicts": 200,
        "source_file": "Protocolos_de_Rastreo_-_Módulo_2.txt",
        "extract_from_line": 1,
        "keywords": [
            "boca", "bucal", "dientes", "encías", "lengua", "saliva", "masticar",
            "estómago", "gástrico", "gastritis", "úlcera", "acidez", "reflujo", "náusea", "vómito",
            "intestino delgado", "intestino grueso", "colon", "colitis", "diarrea", "estreñimiento",
            "hígado", "hepático", "hepatitis", "cirrosis",
            "vesícula", "biliar", "bilis", "cálculos biliares",
            "ano", "anal", "hemorroides", "fisura anal",
            "peritoneo", "peritonitis",
            "digestión", "digestivo", "abdomen", "abdominal",
            "inflamación intestinal", "hinchazón", "flatulencias", "gases",
            "síndrome de intestino irritable", "crohn",
        ],
    },
    {
        "id": "alimenticio",
        "nombre": "Sistema Alimenticio",
        "subsystems": ["sobrepeso", "obesidad", "anorexia", "bulimia"],
        "total_conflicts": None,
        "source_file": "Manual_del_Módulo_3.txt",
        "extract_from_line": 1284,
        "keywords": [
            "sobrepeso", "obesidad", "anorexia", "bulimia", "trastorno alimenticio",
            "trastorno de la conducta alimentaria", "compulsión al comer", "comer en exceso",
            "apetito", "hambre compulsiva", "no quiero comer", "miedo a engordar",
            "imagen corporal", "peso", "adelgazar", "dieta", "atracón",
            "vomitar", "purga", "ayuno",
        ],
    },
    {
        "id": "endocrino",
        "nombre": "Sistema Endócrino-Metabólico",
        "subsystems": ["hipofisiaria", "tiroidea", "paratiroidea", "pancreatica", "suprarrenal"],
        "total_conflicts": 58,
        "source_file": "Manual_del_Módulo_4.txt",
        "extract_from_line": 2466,
        "keywords": [
            "tiroides", "hipotiroidismo", "hipertiroidismo", "bocio",
            "diabetes", "insulina", "páncreas", "glucosa", "azúcar",
            "hipófisis", "pituitaria", "hormona",
            "suprarrenal", "cortisol", "adrenalina",
            "paratiroides", "calcio",
            "metabolismo", "metabólico", "endócrino", "glándula",
            "cansancio", "fatiga crónica", "hipoglucemia", "hiperglucemia",
        ],
    },
    {
        "id": "cardiovascular",
        "nombre": "Sistema Cardiovascular",
        "subsystems": ["miocardial", "valvular", "del_ritmo", "membranas", "arterial", "venosa", "presion", "adjunta", "lipidica"],
        "total_conflicts": 69,
        "source_file": "Manual_del_Módulo_5.txt",
        "extract_from_line": 3179,
        "keywords": [
            "corazón", "cardíaco", "infarto", "arritmia", "taquicardia", "bradicardia",
            "presión arterial", "hipertensión", "hipotensión", "presión alta", "presión baja",
            "arteria", "arterial", "vena", "venoso", "circulación",
            "colesterol", "triglicéridos", "lípidos",
            "válvula", "valvular", "pericardio",
            "angina", "dolor de pecho", "palpitaciones",
            "trombosis", "flebitis", "varices", "varicosas",
            "cardiovascular", "vascular",
        ],
    },
    {
        "id": "osteomuscular",
        "nombre": "Sistema Osteomuscular",
        "subsystems": ["general", "vertebral", "osea_diversa", "periostio", "articular", "ligamentos", "tendones", "muscular", "cabeza", "miembros_superiores", "tronco", "columna", "miembros_inferiores"],
        "total_conflicts": 159,
        "source_file": "Manual_del_Módulo_6.txt",
        "extract_from_line": 2555,
        "keywords": [
            "hueso", "óseo", "fractura", "osteoporosis", "articulación",
            "columna", "vertebral", "espalda", "lumbar", "cervical", "torácica", "hernia de disco",
            "rodilla", "cadera", "hombro", "codo", "muñeca", "tobillo", "pie",
            "músculo", "muscular", "contractura", "espasmo", "fibromialgia",
            "tendón", "tendinitis", "ligamento", "esguince",
            "artritis", "artrosis", "reumatismo", "reuma",
            "dolor de espalda", "dolor de huesos", "dolor articular",
            "periostio", "osteomuscular", "locomotor",
            "cuello", "cervicalgia", "lumbago", "escoliosis",
        ],
    },
    {
        "id": "dermato_lipofascial",
        "nombre": "Sistema Dermatológico-Lipofascial",
        "subsystems": ["desvalorizacion", "contacto_impuesto", "separacion"],
        "total_conflicts": 44,
        "source_file": "Manual_del_Módulo_7.txt",
        "extract_from_line": 3331,
        "keywords": [
            "piel", "dermatitis", "eczema", "psoriasis", "urticaria", "acné", "sarpullido",
            "picazón", "comezón", "prurito", "escozor",
            "herpes", "varicela", "zona", "herpes zóster",
            "manchas en la piel", "vitíligo", "leucoderma",
            "alergia cutánea", "alergia en la piel",
            "grasa", "lipoma", "celulitis", "fascia",
            "tejido conectivo", "tejido adiposo",
            "dermatológico", "cutáneo", "epidermis",
        ],
    },
    {
        "id": "reproductivo",
        "nombre": "Sistema Reproductivo",
        "subsystems": ["ovarica", "oviductal", "uterina", "menstrual", "vaginal", "del_escroto", "falica", "testicular", "prostatica", "sexual", "mamaria"],
        "total_conflicts": 125,
        "source_file": "Manual_del_Módulo_8.txt",
        "extract_from_line": 5304,
        "keywords": [
            "ovario", "ovarios", "quiste ovárico", "síndrome de ovario poliquístico",
            "útero", "uterino", "mioma", "endometriosis", "matriz",
            "menstruación", "ciclo menstrual", "menstrual", "regla", "período",
            "vagina", "vaginal", "flujo", "candidiasis",
            "próstata", "prostática", "hiperplasia prostática",
            "testículo", "testicular",
            "pene", "fálico", "disfunción eréctil", "impotencia sexual",
            "mama", "seno", "pecho", "mastitis", "tumor de mama",
            "fertilidad", "infertilidad", "embarazo", "aborto",
            "reproductivo", "sexual", "libido", "sexualidad",
            "menopausia", "climaterio", "amenorrea", "dismenorrea",
        ],
    },
    {
        "id": "urinario",
        "nombre": "Sistema Urinario",
        "subsystems": ["renal", "de_glomerulo", "de_vejiga"],
        "total_conflicts": 59,
        "source_file": "Manual_del_Módulo_9.txt",
        "extract_from_line": 1040,
        "keywords": [
            "riñón", "renal", "insuficiencia renal", "cálculos renales", "piedras en el riñón",
            "vejiga", "cistitis", "infección urinaria", "infección de vías urinarias",
            "uretra", "uretral", "uretritis",
            "orina", "orinar", "incontinencia urinaria", "retención urinaria",
            "urinario", "urológico", "glomérulo", "nefritis",
            "ardor al orinar", "frecuencia urinaria",
        ],
    },
    {
        "id": "inmunologico",
        "nombre": "Sistema Inmunológico",
        "subsystems": ["inmunologico", "esplenio", "amigdalino", "ganglionar", "timo", "leucocitario", "linfatico", "sida"],
        "total_conflicts": 73,
        "source_file": "Manual_del_Módulo_10.txt",
        "extract_from_line": 1264,
        "keywords": [
            "inmune", "inmunológico", "sistema inmune", "defensas bajas",
            "alergias", "alergia", "alérgico",
            "bazo", "esplénico",
            "amígdalas", "amigdalitis", "anginas",
            "ganglios", "ganglionar", "linfoma",
            "timo", "leucocitos", "linfocitos",
            "linfático", "linfa",
            "VIH", "SIDA", "inmunodeficiencia",
            "autoinmune", "lupus", "esclerosis múltiple",
            "enfermedades autoinmunes", "artritis reumatoide",
        ],
    },
    {
        "id": "neurosensorial",
        "nombre": "Sistema Neurosensorial",
        "subsystems": ["tumoral", "cefalica", "alzheimer", "hemiplejica", "hemorragica", "insomnio", "nerviosa", "ocular", "auditiva"],
        "total_conflicts": 130,
        "source_file": "Manual_del_Módulo_11.txt",
        "extract_from_line": 2704,
        "keywords": [
            "cerebro", "neurológico", "sistema nervioso", "nervio",
            "dolor de cabeza", "migraña", "cefalea", "jaqueca",
            "vértigo", "mareo", "tinnitus", "zumbido de oídos",
            "insomnio", "no puedo dormir", "alteración del sueño",
            "ansiedad", "ataques de pánico", "angustia",
            "depresión", "tristeza profunda",
            "alzheimer", "demencia", "parkinson",
            "epilepsia", "convulsiones",
            "parálisis", "hemiplejia", "paresia",
            "accidente cerebrovascular", "derrame", "embolia",
            "ojo", "ocular", "visión", "miopía", "astigmatismo", "conjuntivitis", "glaucoma",
            "oído", "auditivo", "sordera", "hipoacusia",
            "estrés", "nervios", "tensión nerviosa",
            "tumor cerebral",
        ],
    },
]


def extract_section(source_file: str, from_line: int) -> str:
    path = SOURCES / source_file
    if not path.exists():
        print(f"  [SKIP] {source_file} not found")
        return ""
    lines = path.read_text(encoding="utf-8").splitlines()
    section = lines[from_line - 1:]  # 1-indexed
    return "\n".join(section)


def main() -> None:
    index_data = {"version": "2.0", "systems": []}

    for mod in MODULES:
        system_id = mod["id"]
        source_file = mod["source_file"]
        from_line = mod.get("extract_from_line", 1)

        print(f"Processing {system_id} from {source_file} (line {from_line})...")
        text = extract_section(source_file, from_line)

        out_name = f"{system_id}.txt"
        out_path = OUT_DIR / out_name

        if text:
            out_path.write_text(text, encoding="utf-8")
            lines = text.splitlines()
            print(f"  → {out_name}: {len(lines)} lines extracted")
        else:
            print(f"  → no text extracted")

        index_entry = {
            "id": system_id,
            "nombre": mod["nombre"],
            "subsystems": mod["subsystems"],
            "total_conflicts": mod.get("total_conflicts"),
            "source_file": out_name,
            "keywords": mod["keywords"],
        }
        index_data["systems"].append(index_entry)

    index_path = OUT_DIR / "index.json"
    index_path.write_text(json.dumps(index_data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n✓ index.json written with {len(index_data['systems'])} systems")
    print(f"✓ files in {OUT_DIR}:")
    for f in sorted(OUT_DIR.iterdir()):
        print(f"  {f.name} ({f.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
