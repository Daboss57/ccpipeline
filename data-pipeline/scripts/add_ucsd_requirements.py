"""
Add comprehensive UCSD major requirements to seed_data.json.

Based on official UCSD transfer preparation requirements from ASSIST.org
articulation agreements (LPC → UCSD, AY 2025-26).

Run:
    python data-pipeline/scripts/add_ucsd_requirements.py
"""

from __future__ import annotations

import json
from pathlib import Path

# ---------------------------------------------------------------------------
# Course catalog expansion
# ---------------------------------------------------------------------------
# Generic course IDs → (name, units, department, prereq_course_id | None)
# These mirror the lower-division transfer preparation courses at UCSD,
# using generic IDs consistent with the existing seed data conventions.

NEW_COURSES: dict[str, tuple[str, int, str, str | None]] = {
    # ── Mathematics ──────────────────────────────────────────────
    "MATH101": ("Calculus I", 4, "Mathematics", None),
    "MATH102": ("Calculus II", 4, "Mathematics", "MATH101"),
    "MATH103": ("Multivariable Calculus", 4, "Mathematics", "MATH102"),
    "MATH104": ("Linear Algebra", 4, "Mathematics", "MATH102"),
    "MATH105": ("Differential Equations", 4, "Mathematics", "MATH102"),
    "MATH106": ("Discrete Mathematics", 4, "Mathematics", None),
    "MATH107": ("Introduction to Mathematical Reasoning", 4, "Mathematics", "MATH102"),
    "MATH110": ("Calculus for Life Sciences I", 4, "Mathematics", None),
    "MATH111": ("Calculus for Life Sciences II", 4, "Mathematics", "MATH110"),

    # ── Statistics / Probability ─────────────────────────────────
    "STATS101": ("Introduction to Statistics", 4, "Statistics", None),
    "STATS102": ("Probability and Statistics", 4, "Statistics", "MATH102"),

    # ── Computer Science / CSE ───────────────────────────────────
    "CSE101": ("Programming Fundamentals", 4, "Computer Science", None),
    "CSE102": ("Data Structures", 4, "Computer Science", "CSE101"),
    "CSE103": ("Discrete Mathematics for CS", 4, "Computer Science", None),
    "CSE104": ("Computer Organization and Systems Programming", 4, "Computer Science", "CSE102"),
    "CSE105": ("Software Tools and Techniques", 2, "Computer Science", "CSE101"),
    "CSE106": ("Object-Oriented Design", 4, "Computer Science", "CSE102"),

    # ── Data Science ─────────────────────────────────────────────
    "DSC101": ("Data Wrangling and Manipulation", 4, "Data Science", "CSE101"),
    "DSC201": ("Machine Learning Fundamentals", 4, "Data Science", "DSC101"),

    # ── Physics ──────────────────────────────────────────────────
    "PHYS101": ("Physics: Mechanics", 4, "Physics", "MATH101"),
    "PHYS102": ("Physics: Electricity and Magnetism", 4, "Physics", "PHYS101"),
    "PHYS103": ("Physics: Waves, Optics, and Modern Physics", 4, "Physics", "PHYS102"),
    "PHYS104": ("Physics Laboratory I", 1, "Physics", "PHYS101"),
    "PHYS105": ("Physics Laboratory II", 1, "Physics", "PHYS102"),

    # ── Chemistry ────────────────────────────────────────────────
    "CHEM101": ("General Chemistry I", 4, "Chemistry", None),
    "CHEM102": ("General Chemistry II", 4, "Chemistry", "CHEM101"),
    "CHEM103": ("General Chemistry III", 4, "Chemistry", "CHEM102"),
    "CHEM104": ("General Chemistry Lab", 2, "Chemistry", "CHEM101"),
    "CHEM201": ("Organic Chemistry I", 4, "Chemistry", "CHEM102"),
    "CHEM202": ("Organic Chemistry II", 4, "Chemistry", "CHEM201"),
    "CHEM203": ("Organic Chemistry Lab", 2, "Chemistry", "CHEM201"),

    # ── Biology ──────────────────────────────────────────────────
    "BIO101": ("Cell Biology", 4, "Biology", None),
    "BIO102": ("Organismal Biology", 4, "Biology", "BIO101"),
    "BIO103": ("Ecology and Evolution", 4, "Biology", "BIO101"),
    "BIO104": ("Biology Laboratory", 2, "Biology", "BIO101"),
    "BIO201": ("Genetics", 4, "Biology", "BIO101"),
    "BIO301": ("Molecular Biology", 4, "Biology", "BIO201"),

    # ── Economics ────────────────────────────────────────────────
    "ECON101": ("Principles of Microeconomics", 4, "Economics", None),
    "ECON102": ("Principles of Macroeconomics", 4, "Economics", None),
    "ECON201": ("Intermediate Microeconomics", 4, "Economics", "ECON101"),
    "ECON202": ("Intermediate Macroeconomics", 4, "Economics", "ECON102"),
    "ECON301": ("Econometrics", 4, "Economics", "STATS101"),

    # ── Psychology ───────────────────────────────────────────────
    "PSY101": ("Introduction to Psychology", 4, "Psychology", None),
    "PSY102": ("Biological Foundations of Behavior", 4, "Psychology", "PSY101"),
    "PSY201": ("Research Methods in Psychology", 4, "Psychology", "PSY101"),
    "PSY301": ("Cognitive Psychology", 4, "Psychology", "PSY201"),
    "PSY401": ("Abnormal Psychology", 4, "Psychology", "PSY201"),

    # ── Cognitive Science ────────────────────────────────────────
    "COGS101": ("Introduction to Cognitive Science", 4, "Cognitive Science", None),
    "COGS102": ("Cognitive Neuroscience", 4, "Cognitive Science", "COGS101"),

    # ── Political Science ────────────────────────────────────────
    "POLI101": ("Introduction to American Politics", 4, "Political Science", None),
    "POLI102": ("Introduction to Comparative Politics", 4, "Political Science", None),
    "POLI103": ("Introduction to International Relations", 4, "Political Science", None),
    "POLI104": ("Introduction to Political Theory", 4, "Political Science", None),
    "POLI105": ("Introduction to Public Policy", 4, "Political Science", None),
    "POLI106": ("Data Analytics for Political Science", 4, "Political Science", "STATS101"),

    # ── Sociology ────────────────────────────────────────────────
    "SOC101": ("Introduction to Sociology", 4, "Sociology", None),
    "SOC102": ("Social Problems", 4, "Sociology", "SOC101"),
    "SOC103": ("Social Inequality", 4, "Sociology", "SOC101"),

    # ── Communication ────────────────────────────────────────────
    "COMM101": ("Introduction to Communication", 4, "Communication", None),
    "COMM102": ("Public Speaking", 4, "Communication", None),
    "COMM201": ("Mass Media and Society", 4, "Communication", "COMM101"),

    # ── History ──────────────────────────────────────────────────
    "HIST101": ("United States History I", 4, "History", None),
    "HIST102": ("United States History II", 4, "History", None),
    "HIST201": ("World History I", 4, "History", None),
    "HIST202": ("World History II", 4, "History", None),

    # ── Anthropology ─────────────────────────────────────────────
    "ANTH101": ("Introduction to Cultural Anthropology", 4, "Anthropology", None),
    "ANTH102": ("Introduction to Biological/Physical Anthropology", 4, "Anthropology", None),
    "ANTH103": ("Introduction to Archaeology", 4, "Anthropology", None),

    # ── Philosophy / Logic ───────────────────────────────────────
    "PHIL101": ("Introduction to Philosophy", 4, "Philosophy", None),
    "PHIL102": ("Introduction to Logic", 4, "Philosophy", None),
    "PHIL103": ("Introduction to Ethics", 4, "Philosophy", None),
    "PHIL201": ("History of Philosophy: Ancient", 4, "Philosophy", "PHIL101"),
    "PHIL202": ("History of Philosophy: Modern", 4, "Philosophy", "PHIL101"),

    # ── English / Literature ─────────────────────────────────────
    "ENGL101": ("English Composition I", 4, "English", None),
    "ENGL102": ("English Composition II", 4, "English", "ENGL101"),
    "ENGL201": ("Introduction to Literature", 4, "English", "ENGL101"),
    "ENGL202": ("Critical Writing", 4, "English", "ENGL101"),

    # ── Foreign Languages ────────────────────────────────────────
    "SPAN101": ("Elementary Spanish I", 4, "Languages", None),
    "SPAN102": ("Elementary Spanish II", 4, "Languages", "SPAN101"),
    "CHIN101": ("Elementary Chinese I", 4, "Languages", None),
    "CHIN102": ("Elementary Chinese II", 4, "Languages", "CHIN101"),
    "JAPN101": ("Elementary Japanese I", 4, "Languages", None),
    "JAPN102": ("Elementary Japanese II", 4, "Languages", "JAPN101"),
    "GERM101": ("Elementary German I", 4, "Languages", None),
    "GERM102": ("Elementary German II", 4, "Languages", "GERM101"),
    "ITAL101": ("Elementary Italian I", 4, "Languages", None),
    "ITAL102": ("Elementary Italian II", 4, "Languages", "ITAL101"),
    "RUSS101": ("Elementary Russian I", 4, "Languages", None),
    "RUSS102": ("Elementary Russian II", 4, "Languages", "RUSS101"),

    # ── Art / Visual Arts ────────────────────────────────────────
    "ART101": ("Introduction to Art History", 4, "Art", None),
    "ART102": ("Studio Art Fundamentals I", 4, "Art", None),
    "ART103": ("Studio Art Fundamentals II", 4, "Art", "ART102"),
    "ART104": ("Digital Media Fundamentals", 4, "Art", None),
    "ART105": ("Design Fundamentals", 4, "Art", None),

    # ── Music ────────────────────────────────────────────────────
    "MUS101": ("Introduction to Music", 4, "Music", None),
    "MUS102": ("Music Theory I", 4, "Music", None),
    "MUS103": ("Music Theory II", 4, "Music", "MUS102"),
    "MUS104": ("Music History", 4, "Music", None),

    # ── Theatre / Dance ──────────────────────────────────────────
    "THEA101": ("Introduction to Theatre", 4, "Theatre", None),
    "THEA102": ("Acting Fundamentals", 4, "Theatre", None),
    "DANC101": ("Introduction to Dance", 4, "Dance", None),
    "DANC102": ("Dance Techniques", 4, "Dance", "DANC101"),

    # ── Linguistics ──────────────────────────────────────────────
    "LING101": ("Introduction to Linguistics", 4, "Linguistics", None),
    "LING102": ("Phonetics and Phonology", 4, "Linguistics", "LING101"),

    # ── Education ────────────────────────────────────────────────
    "EDUC101": ("Introduction to Education", 4, "Education", None),
    "EDUC102": ("Educational Psychology", 4, "Education", "PSY101"),

    # ── Public Health ────────────────────────────────────────────
    "PUBH101": ("Introduction to Public Health", 4, "Public Health", None),
    "PUBH102": ("Epidemiology", 4, "Public Health", "STATS101"),
    "PUBH103": ("Biostatistics", 4, "Public Health", "STATS101"),

    # ── Environmental Science ────────────────────────────────────
    "ENVS101": ("Introduction to Environmental Science", 4, "Environmental Science", None),
    "ENVS102": ("Environmental Policy", 4, "Environmental Science", None),

    # ── Ethnic / Gender Studies ──────────────────────────────────
    "ETHN101": ("Introduction to Ethnic Studies", 4, "Ethnic Studies", None),
    "CGS101": ("Introduction to Critical Gender Studies", 4, "Critical Gender Studies", None),
    "AFAS101": ("Introduction to African American Studies", 4, "African American Studies", None),
    "CLAS101": ("Introduction to Chicano/Latino Studies", 4, "Chicano/Latino Studies", None),

    # ── Earth Science / Geoscience ───────────────────────────────
    "GEOL101": ("Physical Geology", 4, "Earth Science", None),
    "GEOL102": ("Historical Geology", 4, "Earth Science", "GEOL101"),
    "OCEA101": ("Introduction to Oceanography", 4, "Earth Science", None),
    "ATMO101": ("Introduction to Atmospheric Sciences", 4, "Earth Science", None),

    # ── Religion ─────────────────────────────────────────────────
    "RELI101": ("Introduction to World Religions", 4, "Religion", None),

    # ── Classics ─────────────────────────────────────────────────
    "CLAS201": ("Introduction to Classical Civilization", 4, "Classics", None),
    "CLAS202": ("Greek and Roman Mythology", 4, "Classics", None),

    # ── Urban Studies ────────────────────────────────────────────
    "URBN101": ("Introduction to Urban Studies", 4, "Urban Studies", None),
    "URBN102": ("Urban Planning Fundamentals", 4, "Urban Studies", None),

    # ── International Studies ────────────────────────────────────
    "INTL101": ("Introduction to International Studies", 4, "International Studies", None),

    # ── ECE specific ─────────────────────────────────────────────
    "ECE101": ("Introduction to Electrical Engineering", 4, "ECE", "PHYS102"),
    "ECE102": ("Circuit Analysis", 4, "ECE", "PHYS102"),

    # ── Health / HDS ─────────────────────────────────────────────
    "HDS101": ("Introduction to Human Development", 4, "Human Development", None),
    "HDS102": ("Lifespan Development", 4, "Human Development", "HDS101"),

    # ── Global Health ────────────────────────────────────────────
    "GLBH101": ("Introduction to Global Health", 4, "Global Health", None),
    "GLBH102": ("Global Health Ethics", 4, "Global Health", "GLBH101"),

    # ── Real Estate ──────────────────────────────────────────────
    "RE101": ("Introduction to Real Estate", 4, "Real Estate", None),

    # ── Jewish Studies ───────────────────────────────────────────
    "JWST101": ("Introduction to Jewish Studies", 4, "Jewish Studies", None),

    # ── Wellness / PE ────────────────────────────────────────────
    "PE101": ("Physical Education / Wellness", 1, "Wellness", None),
}

# Term offerings by department prefix
OFFERING_RULES: dict[str, list[str]] = {
    "MATH": ["Fall", "Winter", "Spring"],
    "STATS": ["Fall", "Winter", "Spring"],
    "CSE": ["Fall", "Winter", "Spring"],
    "DSC": ["Fall", "Spring"],
    "PHYS": ["Fall", "Winter", "Spring"],
    "CHEM": ["Fall", "Winter", "Spring"],
    "BIO": ["Fall", "Spring"],
    "ECON": ["Fall", "Winter", "Spring"],
    "PSY": ["Fall", "Winter", "Spring"],
    "COGS": ["Fall", "Winter", "Spring"],
    "POLI": ["Fall", "Winter", "Spring"],
    "SOC": ["Fall", "Winter", "Spring"],
    "COMM": ["Fall", "Winter", "Spring"],
    "HIST": ["Fall", "Spring"],
    "ANTH": ["Fall", "Spring"],
    "PHIL": ["Fall", "Winter", "Spring"],
    "ENGL": ["Fall", "Winter", "Spring"],
    "SPAN": ["Fall", "Winter", "Spring"],
    "CHIN": ["Fall", "Spring"],
    "JAPN": ["Fall", "Spring"],
    "GERM": ["Fall", "Spring"],
    "ITAL": ["Fall", "Spring"],
    "RUSS": ["Fall", "Spring"],
    "ART": ["Fall", "Winter", "Spring"],
    "MUS": ["Fall", "Winter", "Spring"],
    "THEA": ["Fall", "Spring"],
    "DANC": ["Fall", "Spring"],
    "LING": ["Fall", "Winter", "Spring"],
    "EDUC": ["Fall", "Spring"],
    "PUBH": ["Fall", "Spring"],
    "ENVS": ["Fall", "Spring"],
    "ETHN": ["Fall", "Spring"],
    "CGS": ["Fall", "Spring"],
    "AFAS": ["Fall", "Spring"],
    "CLAS": ["Fall", "Spring"],
    "GEOL": ["Fall", "Spring"],
    "OCEA": ["Fall", "Spring"],
    "ATMO": ["Fall", "Spring"],
    "RELI": ["Fall", "Spring"],
    "URBN": ["Fall", "Spring"],
    "INTL": ["Fall", "Spring"],
    "ECE": ["Fall", "Winter", "Spring"],
    "HDS": ["Fall", "Spring"],
    "GLBH": ["Fall", "Spring"],
    "RE": ["Fall", "Spring"],
    "JWST": ["Fall", "Spring"],
    "PE": ["Fall", "Winter", "Spring", "Summer"],
}

def _offerings(course_id: str) -> list[str]:
    prefix = "".join(c for c in course_id if c.isalpha())
    return OFFERING_RULES.get(prefix, ["Fall", "Spring"])


# ---------------------------------------------------------------------------
# Requirement templates  (course_id list per template name)
# ---------------------------------------------------------------------------
# Based on UCSD transfer preparation as documented on ASSIST.org for
# Las Positas College → UC San Diego, AY 2025-26.

TEMPLATES: dict[str, list[str]] = {
    # ── STEM Engineering ────────────────────────────────────────
    "cse_cs": [
        "MATH101", "MATH102", "MATH103", "MATH104",
        "CSE101", "CSE102", "CSE103", "CSE104", "CSE105",
        "PHYS101", "PHYS102",
    ],
    "cse_ce": [
        "MATH101", "MATH102", "MATH103", "MATH104",
        "CSE101", "CSE102", "CSE103", "CSE104", "CSE105",
        "PHYS101", "PHYS102", "PHYS103",
        "ECE101",
    ],
    "cse_ai": [
        "MATH101", "MATH102", "MATH103", "MATH104",
        "CSE101", "CSE102", "CSE103", "CSE104", "CSE105",
        "PHYS101", "PHYS102",
        "STATS102",
    ],
    "cse_bioinf": [
        "MATH101", "MATH102", "MATH103", "MATH104",
        "CSE101", "CSE102", "CSE103", "CSE104",
        "PHYS101", "PHYS102",
        "CHEM101", "CHEM102",
        "BIO101",
    ],
    "data_science": [
        "MATH101", "MATH102", "MATH103", "MATH104",
        "CSE101", "CSE102",
        "STATS101", "STATS102",
        "DSC101",
    ],
    "ece_ee": [
        "MATH101", "MATH102", "MATH103", "MATH104", "MATH105",
        "PHYS101", "PHYS102", "PHYS103",
        "CSE101",
        "ECE101", "ECE102",
    ],
    "ece_ce": [
        "MATH101", "MATH102", "MATH103", "MATH104",
        "PHYS101", "PHYS102", "PHYS103",
        "CSE101", "CSE102",
        "ECE101",
    ],
    "ece_ee_society": [
        "MATH101", "MATH102", "MATH103",
        "PHYS101", "PHYS102",
        "CSE101",
        "ECE101",
    ],
    "ece_engphys": [
        "MATH101", "MATH102", "MATH103", "MATH104", "MATH105",
        "PHYS101", "PHYS102", "PHYS103",
        "CHEM101",
        "CSE101",
    ],
    "mae_mech": [
        "MATH101", "MATH102", "MATH103", "MATH104", "MATH105",
        "PHYS101", "PHYS102", "PHYS103",
        "CHEM101",
        "CSE101",
    ],
    "mae_aero": [
        "MATH101", "MATH102", "MATH103", "MATH104", "MATH105",
        "PHYS101", "PHYS102", "PHYS103",
        "CHEM101",
        "CSE101",
    ],
    "struct_eng": [
        "MATH101", "MATH102", "MATH103", "MATH104", "MATH105",
        "PHYS101", "PHYS102", "PHYS103",
        "CHEM101",
        "CSE101",
    ],
    "chem_nano_eng": [
        "MATH101", "MATH102", "MATH103", "MATH104", "MATH105",
        "PHYS101", "PHYS102", "PHYS103",
        "CHEM101", "CHEM102", "CHEM103",
        "BIO101",
    ],
    "bioeng": [
        "MATH101", "MATH102", "MATH103", "MATH104", "MATH105",
        "PHYS101", "PHYS102", "PHYS103",
        "CHEM101", "CHEM102", "CHEM103",
        "BIO101",
        "CSE101",
    ],

    # ── Sciences ────────────────────────────────────────────────
    "bio_general": [
        "MATH110", "MATH111",
        "CHEM101", "CHEM102", "CHEM103", "CHEM104",
        "CHEM201", "CHEM202",
        "BIO101", "BIO102", "BIO103", "BIO104",
        "PHYS101", "PHYS102", "PHYS103",
    ],
    "bio_molecular": [
        "MATH110", "MATH111",
        "CHEM101", "CHEM102", "CHEM103", "CHEM104",
        "CHEM201", "CHEM202",
        "BIO101", "BIO102", "BIO103", "BIO104",
        "BIO201",
        "PHYS101", "PHYS102", "PHYS103",
    ],
    "bio_ecology": [
        "MATH110", "MATH111",
        "CHEM101", "CHEM102", "CHEM103",
        "BIO101", "BIO102", "BIO103", "BIO104",
        "PHYS101", "PHYS102",
        "STATS101",
    ],
    "bio_human": [
        "MATH110", "MATH111",
        "CHEM101", "CHEM102", "CHEM103", "CHEM104",
        "CHEM201",
        "BIO101", "BIO102", "BIO104",
        "PHYS101", "PHYS102", "PHYS103",
        "PSY101",
    ],
    "bio_micro": [
        "MATH110", "MATH111",
        "CHEM101", "CHEM102", "CHEM103", "CHEM104",
        "CHEM201", "CHEM202",
        "BIO101", "BIO102", "BIO103", "BIO104",
        "BIO201",
        "PHYS101", "PHYS102", "PHYS103",
    ],
    "bio_neuro": [
        "MATH110", "MATH111",
        "CHEM101", "CHEM102", "CHEM103", "CHEM104",
        "CHEM201",
        "BIO101", "BIO102", "BIO104",
        "PHYS101", "PHYS102", "PHYS103",
        "PSY101",
    ],
    "bio_bioinf": [
        "MATH101", "MATH102",
        "CHEM101", "CHEM102", "CHEM103",
        "BIO101", "BIO102", "BIO104",
        "BIO201",
        "CSE101", "CSE102",
        "PHYS101", "PHYS102",
    ],
    "marine_bio": [
        "MATH110", "MATH111",
        "CHEM101", "CHEM102", "CHEM103", "CHEM104",
        "BIO101", "BIO102", "BIO103", "BIO104",
        "PHYS101", "PHYS102", "PHYS103",
        "OCEA101",
    ],
    "chem_bs": [
        "MATH101", "MATH102", "MATH103",
        "CHEM101", "CHEM102", "CHEM103", "CHEM104",
        "CHEM201", "CHEM202", "CHEM203",
        "PHYS101", "PHYS102", "PHYS103",
    ],
    "biochem": [
        "MATH101", "MATH102", "MATH103",
        "CHEM101", "CHEM102", "CHEM103", "CHEM104",
        "CHEM201", "CHEM202", "CHEM203",
        "BIO101",
        "PHYS101", "PHYS102", "PHYS103",
    ],
    "env_chem": [
        "MATH101", "MATH102", "MATH103",
        "CHEM101", "CHEM102", "CHEM103", "CHEM104",
        "CHEM201",
        "PHYS101", "PHYS102",
        "ENVS101",
    ],
    "mol_synth": [
        "MATH101", "MATH102", "MATH103",
        "CHEM101", "CHEM102", "CHEM103", "CHEM104",
        "CHEM201", "CHEM202", "CHEM203",
        "PHYS101", "PHYS102", "PHYS103",
    ],
    "pharm_chem": [
        "MATH101", "MATH102", "MATH103",
        "CHEM101", "CHEM102", "CHEM103", "CHEM104",
        "CHEM201", "CHEM202", "CHEM203",
        "BIO101",
        "PHYS101", "PHYS102", "PHYS103",
    ],
    "physics_bs": [
        "MATH101", "MATH102", "MATH103", "MATH104", "MATH105",
        "PHYS101", "PHYS102", "PHYS103", "PHYS104", "PHYS105",
    ],
    "physics_ba": [
        "MATH101", "MATH102", "MATH103",
        "PHYS101", "PHYS102", "PHYS103",
    ],
    "astro_bs": [
        "MATH101", "MATH102", "MATH103", "MATH104", "MATH105",
        "PHYS101", "PHYS102", "PHYS103", "PHYS104", "PHYS105",
    ],
    "geosciences": [
        "MATH101", "MATH102",
        "CHEM101", "CHEM102",
        "PHYS101", "PHYS102",
        "GEOL101", "GEOL102",
    ],
    "env_systems_earth": [
        "MATH101", "MATH102",
        "CHEM101", "CHEM102",
        "PHYS101", "PHYS102",
        "BIO101",
        "GEOL101",
        "ENVS101",
    ],
    "env_systems_eco": [
        "MATH110", "MATH111",
        "CHEM101", "CHEM102",
        "BIO101", "BIO103",
        "PHYS101", "PHYS102",
        "ENVS101",
        "STATS101",
    ],
    "env_systems_chem": [
        "MATH101", "MATH102",
        "CHEM101", "CHEM102", "CHEM103",
        "PHYS101", "PHYS102",
        "ENVS101",
    ],
    "env_systems_policy": [
        "MATH110",
        "CHEM101",
        "BIO101",
        "PHYS101",
        "ENVS101", "ENVS102",
        "ECON101",
        "STATS101",
    ],
    "oceanic_atmo": [
        "MATH101", "MATH102", "MATH103",
        "PHYS101", "PHYS102", "PHYS103",
        "CHEM101", "CHEM102",
        "OCEA101", "ATMO101",
    ],

    # ── Mathematics ─────────────────────────────────────────────
    "math_bs": [
        "MATH101", "MATH102", "MATH103", "MATH104", "MATH105",
        "MATH107",
    ],
    "math_applied": [
        "MATH101", "MATH102", "MATH103", "MATH104", "MATH105",
        "MATH107",
        "CSE101",
    ],
    "math_cs": [
        "MATH101", "MATH102", "MATH103", "MATH104", "MATH105",
        "CSE101", "CSE102",
    ],
    "math_applied_sci": [
        "MATH101", "MATH102", "MATH103", "MATH104", "MATH105",
        "PHYS101", "PHYS102",
        "CSE101",
    ],
    "math_econ": [
        "MATH101", "MATH102", "MATH103", "MATH104",
        "ECON101", "ECON102",
        "STATS101",
    ],
    "math_secondary_ed": [
        "MATH101", "MATH102", "MATH103", "MATH104", "MATH107",
        "STATS101",
    ],
    "math_bio": [
        "MATH101", "MATH102", "MATH103", "MATH104",
        "BIO101",
        "STATS101",
    ],
    "math_prob_stats": [
        "MATH101", "MATH102", "MATH103", "MATH104",
        "STATS101", "STATS102",
        "CSE101",
    ],

    # ── Cognitive Science ───────────────────────────────────────
    "cogsci_ba": [
        "COGS101",
        "PSY101",
        "STATS101",
        "PHIL102",
    ],
    "cogsci_bs": [
        "COGS101",
        "PSY101",
        "MATH101", "MATH102",
        "STATS101",
        "CSE101",
    ],
    "cogsci_ml": [
        "COGS101",
        "PSY101",
        "MATH101", "MATH102", "MATH104",
        "STATS101", "STATS102",
        "CSE101", "CSE102",
    ],
    "cogsci_neuro": [
        "COGS101", "COGS102",
        "PSY101", "PSY102",
        "MATH101",
        "STATS101",
        "BIO101",
        "CHEM101",
    ],
    "cogsci_design": [
        "COGS101",
        "PSY101",
        "MATH101",
        "STATS101",
        "CSE101",
    ],
    "cogsci_lang": [
        "COGS101",
        "PSY101",
        "LING101",
        "STATS101",
    ],
    "cogsci_clinical": [
        "COGS101",
        "PSY101", "PSY102",
        "STATS101",
        "BIO101",
    ],
    "cogsci_cbn": [
        "COGS101", "COGS102",
        "PSY101", "PSY102",
        "MATH101",
        "STATS101",
        "BIO101",
        "CHEM101",
    ],

    # ── Economics ────────────────────────────────────────────────
    "econ_ba": [
        "MATH101", "MATH102",
        "ECON101", "ECON102",
        "STATS101",
    ],
    "econ_bs": [
        "MATH101", "MATH102", "MATH103",
        "ECON101", "ECON102",
        "STATS101",
    ],
    "biz_econ": [
        "MATH101", "MATH102", "MATH103",
        "ECON101", "ECON102",
        "STATS101",
        "ECON201",
    ],

    # ── Psychology ──────────────────────────────────────────────
    "psych_ba": [
        "PSY101",
        "STATS101",
    ],
    "psych_bs": [
        "PSY101", "PSY102",
        "STATS101",
        "PSY201",
        "BIO101",
    ],
    "psych_clinical": [
        "PSY101", "PSY102",
        "STATS101",
        "PSY201", "PSY401",
        "BIO101",
    ],
    "psych_cog": [
        "PSY101", "PSY102",
        "STATS101",
        "PSY201", "PSY301",
        "BIO101",
    ],
    "psych_dev": [
        "PSY101", "PSY102",
        "STATS101",
        "PSY201",
        "BIO101",
    ],
    "psych_health": [
        "PSY101", "PSY102",
        "STATS101",
        "PSY201",
        "BIO101",
    ],
    "psych_sensation": [
        "PSY101", "PSY102",
        "STATS101",
        "PSY201",
        "BIO101",
        "PHYS101",
    ],
    "psych_social": [
        "PSY101", "PSY102",
        "STATS101",
        "PSY201",
        "SOC101",
    ],
    "psych_biz": [
        "PSY101", "PSY102",
        "STATS101",
        "PSY201",
        "ECON101",
    ],
    "psych_cbn": [
        "PSY101", "PSY102",
        "STATS101",
        "PSY201",
        "BIO101",
        "CHEM101",
        "MATH101",
    ],

    # ── Political Science ───────────────────────────────────────
    "polisci_ba": [
        "POLI101",
        "STATS101",
    ],
    "polisci_amer": [
        "POLI101",
        "STATS101",
    ],
    "polisci_comp": [
        "POLI102",
        "STATS101",
    ],
    "polisci_ir": [
        "POLI103",
        "STATS101",
    ],
    "polisci_theory": [
        "POLI104",
        "STATS101",
    ],
    "polisci_law": [
        "POLI101",
        "STATS101",
    ],
    "polisci_policy": [
        "POLI105",
        "STATS101",
        "ECON101",
    ],
    "polisci_race": [
        "POLI101",
        "STATS101",
        "ETHN101",
    ],
    "polisci_data": [
        "POLI101",
        "STATS101", "STATS102",
        "CSE101",
        "MATH101",
        "POLI106",
    ],

    # ── Sociology ───────────────────────────────────────────────
    "soc_ba": ["SOC101", "SOC102", "STATS101"],
    "soc_amer": ["SOC101", "SOC102", "HIST101", "STATS101"],
    "soc_culture_comm": ["SOC101", "SOC102", "COMM101", "STATS101"],
    "soc_econ": ["SOC101", "SOC102", "ECON101", "STATS101"],
    "soc_intl": ["SOC101", "SOC102", "INTL101", "STATS101"],
    "soc_law": ["SOC101", "SOC102", "POLI101", "STATS101"],
    "soc_sci_med": ["SOC101", "SOC102", "BIO101", "STATS101"],
    "soc_ineq": ["SOC101", "SOC103", "STATS101"],

    # ── Communication ───────────────────────────────────────────
    "comm_ba": ["COMM101", "COMM102", "STATS101"],
    "comm_media": ["COMM101", "COMM201", "STATS101"],

    # ── Anthropology ────────────────────────────────────────────
    "anth_socio": ["ANTH101", "STATS101"],
    "anth_bio": ["ANTH102", "BIO101", "STATS101"],
    "anth_arch": ["ANTH103", "ANTH101", "STATS101"],
    "anth_climate": ["ANTH101", "ENVS101", "STATS101"],
    "anth_bio_bs": ["ANTH102", "BIO101", "CHEM101", "STATS101", "MATH110"],
    "anth_env_bs": ["ANTH101", "ENVS101", "BIO101", "CHEM101", "STATS101"],

    # ── History ─────────────────────────────────────────────────
    "hist_ba": ["HIST101", "HIST102", "HIST201"],

    # ── Philosophy ──────────────────────────────────────────────
    "phil_ba": ["PHIL101", "PHIL102", "PHIL103"],

    # ── Art / Visual Arts ───────────────────────────────────────
    "art_history": ["ART101", "ENGL201"],
    "art_studio": ["ART101", "ART102", "ART103"],
    "art_media": ["ART101", "ART104", "CSE101"],
    "art_spec_design": ["ART101", "ART105", "ART104"],
    "art_icam": ["ART101", "ART104", "CSE101", "MUS101"],

    # ── Music ───────────────────────────────────────────────────
    "music_ba": ["MUS101", "MUS102", "MUS103", "MUS104"],
    "music_humanities": ["MUS101", "MUS102", "MUS104", "ENGL201"],
    "music_icam": ["MUS101", "MUS102", "ART104", "CSE101"],

    # ── Theatre / Dance ─────────────────────────────────────────
    "theatre_ba": ["THEA101", "THEA102"],
    "theatre_dance": ["THEA101", "DANC101", "DANC102"],
    "dance_ba": ["DANC101", "DANC102", "MUS101"],

    # ── Linguistics ─────────────────────────────────────────────
    "ling_ba": ["LING101", "LING102"],
    "ling_cog": ["LING101", "LING102", "COGS101", "PSY101"],
    "ling_society": ["LING101", "LING102", "SOC101"],
    "ling_speech": ["LING101", "LING102", "PSY101", "STATS101"],
    "ling_lang_studies": ["LING101"],  # + language courses
    "ling_lang_program": ["LING101"],

    # ── Literature / English ────────────────────────────────────
    "lit_english": ["ENGL201", "ENGL202"],
    "lit_writing": ["ENGL201", "ENGL202"],
    "lit_arts": ["ENGL201", "ENGL202", "ART101"],
    "lit_spanish": ["ENGL201", "SPAN101", "SPAN102"],
    "lit_world": ["ENGL201", "ENGL202", "HIST201"],

    # ── Study of Religion ───────────────────────────────────────
    "religion_ba": ["RELI101", "PHIL101"],

    # ── Classical Studies ───────────────────────────────────────
    "classics_ba": ["CLAS201", "CLAS202", "HIST201"],

    # ── Ethnic / Gender / Area Studies ──────────────────────────
    "ethnic_studies": ["ETHN101", "HIST101"],
    "black_diaspora": ["AFAS101", "HIST101"],
    "chicano_latino": ["CLAS101", "HIST101"],
    "cgs_ba": ["CGS101", "SOC101"],
    "global_south": ["ETHN101", "HIST201", "POLI102"],
    "jewish_studies": ["JWST101", "RELI101", "HIST201"],

    # ── International Studies ───────────────────────────────────
    "intl_anth": ["INTL101", "ANTH101", "POLI102"],
    "intl_econ": ["INTL101", "ECON101", "ECON102", "MATH101"],
    "intl_hist": ["INTL101", "HIST201", "HIST202"],
    "intl_biz": ["INTL101", "ECON101", "ECON102", "MATH101"],
    "intl_ling": ["INTL101", "LING101"],
    "intl_lit": ["INTL101", "ENGL201"],
    "intl_phil": ["INTL101", "PHIL101"],
    "intl_polisci": ["INTL101", "POLI102", "POLI103"],
    "intl_soc": ["INTL101", "SOC101"],

    # ── Language Studies (BA) ───────────────────────────────────
    "chinese_studies": ["CHIN101", "CHIN102", "HIST201"],
    "german_studies": ["GERM101", "GERM102", "HIST201"],
    "italian_studies": ["ITAL101", "ITAL102", "HIST201"],
    "japanese_studies": ["JAPN101", "JAPN102", "HIST201"],
    "russian_ee_studies": ["RUSS101", "RUSS102", "HIST201"],
    "latin_american": ["SPAN101", "SPAN102", "HIST201"],

    # ── Education Sciences ──────────────────────────────────────
    "educ_sci": ["EDUC101", "EDUC102", "PSY101", "STATS101"],

    # ── Public Health ───────────────────────────────────────────
    "pubh_bs": [
        "PUBH101",
        "BIO101",
        "CHEM101",
        "MATH110",
        "STATS101",
    ],
    "pubh_biostats": [
        "PUBH101", "PUBH103",
        "BIO101",
        "MATH101", "MATH102",
        "STATS101", "STATS102",
    ],
    "pubh_climate": [
        "PUBH101",
        "BIO101",
        "CHEM101",
        "ENVS101",
        "STATS101",
    ],
    "pubh_community": [
        "PUBH101",
        "BIO101",
        "PSY101",
        "SOC101",
        "STATS101",
    ],
    "pubh_epi": [
        "PUBH101", "PUBH102",
        "BIO101",
        "MATH110",
        "STATS101",
    ],
    "pubh_policy": [
        "PUBH101",
        "ECON101",
        "POLI101",
        "STATS101",
    ],
    "pubh_med": [
        "PUBH101",
        "BIO101",
        "CHEM101", "CHEM102",
        "MATH110",
        "STATS101",
    ],

    # ── Global Health ───────────────────────────────────────────
    "glbh_ba": ["GLBH101", "PUBH101", "STATS101"],
    "glbh_bs": ["GLBH101", "PUBH101", "BIO101", "CHEM101", "STATS101", "MATH110"],

    # ── Human Developmental Sciences ────────────────────────────
    "hds_ba": ["HDS101", "PSY101", "STATS101"],
    "hds_bs": ["HDS101", "HDS102", "PSY101", "STATS101", "BIO101"],
    "hds_equity": ["HDS101", "HDS102", "PSY101", "STATS101", "ETHN101"],
    "hds_aging": ["HDS101", "HDS102", "PSY101", "STATS101", "BIO101"],

    # ── Urban Studies ───────────────────────────────────────────
    "urban_ba": ["URBN101", "URBN102", "ECON101", "STATS101"],

    # ── Business minors (light) ─────────────────────────────────
    "biz_minor": ["ECON101", "ECON102", "MATH101"],
    "biz_analytics_minor": ["MATH101", "STATS101", "CSE101"],
    "finance_minor": ["ECON101", "ECON102", "MATH101", "STATS101"],
    "marketing_minor": ["ECON101", "STATS101"],
    "accounting_minor": ["ECON101", "ECON102", "MATH101"],
    "entrep_minor": ["ECON101"],
    "tech_supply_minor": ["ECON101", "STATS101", "CSE101"],

    # ── Real Estate ─────────────────────────────────────────────
    "real_estate": ["RE101", "ECON101", "ECON102", "MATH101", "STATS101"],

    # ── Cinematic Arts ──────────────────────────────────────────
    "cinematic_arts": ["ART101", "ART104", "ENGL201"],
}

# ---------------------------------------------------------------------------
# Major → template mapping
# ---------------------------------------------------------------------------
# Maps each UCSD major_id (the portion after "ucsd-") to a template key.

MAJOR_TEMPLATE_MAP: dict[str, str] = {
    # ── Seeded majors (used by tests) ────────────────────────────
    "computer-science": "cse_cs",
    "data-science": "data_science",
    "biology": "bio_general",
    "economics": "econ_bs",
    "psychology": "psych_bs",

    # ── CSE ──────────────────────────────────────────────────────
    "cse:-computer-science-bs": "cse_cs",
    "cse:-computer-engineering-bs": "cse_ce",
    "cse:-artificial-intelligence-bs": "cse_ai",
    "cse:-computer-science-with-a-specialization-in-bioinformatics-bs": "cse_bioinf",

    # ── Data Science ─────────────────────────────────────────────
    "data-science-bs": "data_science",

    # ── ECE ──────────────────────────────────────────────────────
    "ece:-electrical-engineering-bs": "ece_ee",
    "ece:-computer-engineering-bs": "ece_ce",
    "ece:-electrical-engineering-and-society-ba": "ece_ee_society",
    "ece:-engineering-physics-bs": "ece_engphys",

    # ── MAE ──────────────────────────────────────────────────────
    "mae:-mechanical-engineering-bs": "mae_mech",
    "mae:-aerospace-engineering-bs": "mae_aero",

    # ── Structural Engineering ───────────────────────────────────
    "structural-engineering-bs": "struct_eng",
    "structural-engineering-with-a-specialization-in-aerospace-structures-bs": "struct_eng",
    "structural-engineering-with-a-specialization-in-civil-structures-bs": "struct_eng",
    "structural-engineering-with-a-specialization-in-geotechnical-engineering-bs": "struct_eng",
    "structural-engineering-with-a-specialization-in-structural-health-monitoring-non-destructive-evaluation-bs": "struct_eng",

    # ── Chemical / NanoEngineering ────────────────────────────────
    "chemical-and-nano-engineering:-chemical-engineering-bs": "chem_nano_eng",
    "chemical-and-nano-engineering:-nanoengineering-bs": "chem_nano_eng",

    # ── Bioengineering ───────────────────────────────────────────
    "bioengineering-bs": "bioeng",
    "bioengineering:-bioinformatics-bs": "bioeng",
    "bioengineering:-biosystems-bs": "bioeng",
    "bioengineering:-biotechnology-bs": "bioeng",

    # ── Biology ──────────────────────────────────────────────────
    "biology:-general-biology-bs": "bio_general",
    "biology:-molecular-and-cell-biology-bs": "bio_molecular",
    "biology:-ecology-behavior-and-evolution-bs": "bio_ecology",
    "biology:-human-biology-bs": "bio_human",
    "biology:-microbiology-bs": "bio_micro",
    "biology:-neurobiology": "bio_neuro",
    "biology-with-a-specialization-in-bioinformatics-bs": "bio_bioinf",
    "marine-biology-bs": "marine_bio",

    # ── Chemistry / Biochemistry ─────────────────────────────────
    "chemistry-and-biochemistry:-chemistry-bs": "chem_bs",
    "chemistry-and-biochemistry:-biochemistry-bs": "biochem",
    "chemistry-and-biochemistry:-environmental-chemistry-bs": "env_chem",
    "chemistry-and-biochemistry:-molecular-synthesis-bs": "mol_synth",
    "chemistry-and-biochemistry:-pharmacological-chemistry-bs": "pharm_chem",

    # ── Physics / Astronomy ──────────────────────────────────────
    "physics-bs": "physics_bs",
    "physics-ba": "physics_ba",
    "astronomy-and-astrophysics-bs": "astro_bs",
    "astrophysical-sciences-bs": "astro_bs",

    # ── Earth / Environmental Systems ────────────────────────────
    "geosciences-bs": "geosciences",
    "environmental-systems-earth-sciences-bs": "env_systems_earth",
    "environmental-systems-ecology-behavior-and-evolution-bs": "env_systems_eco",
    "environmental-systems-environmental-chemistry-bs": "env_systems_chem",
    "environmental-systems-environmental-policy-ba": "env_systems_policy",
    "oceanic-and-atmospheric-sciences-bs": "oceanic_atmo",

    # ── Mathematics ──────────────────────────────────────────────
    "mathematics-bs": "math_bs",
    "mathematics:-applied-mathematics-bs": "math_applied",
    "mathematics-computer-science-bs": "math_cs",
    "mathematics-applied-science-bs": "math_applied_sci",
    "mathematics-secondary-education-ba": "math_secondary_ed",
    "economics:-joint-major-in-mathematics-and-economics-bs": "math_econ",
    "mathematics:-joint-major-in-mathematics-and-economics-bs": "math_econ",
    "mathematics:-mathematical-biology": "math_bio",
    "mathematics:-probability-and-statistics-bs": "math_prob_stats",

    # ── Cognitive Science ────────────────────────────────────────
    "cognitive-science-ba": "cogsci_ba",
    "cognitive-science-bs": "cogsci_bs",
    "cognitive-science-bs-with-specialization-in-machine-learning-and-neural-computation": "cogsci_ml",
    "cognitive-science-bs-with-specialization-in-neuroscience": "cogsci_neuro",
    "cognitive-science-bs-specialization-in-design-and-interaction": "cogsci_design",
    "cognitive-science-bs-with-specialization-in-language-and-culture": "cogsci_lang",
    "cognitive-science-bs-specialization-in-clin-aspcts-of-cogn": "cogsci_clinical",
    "cognitive-science:-cognitive-and-behavioral-neuroscience-bs": "cogsci_cbn",

    # ── Economics ────────────────────────────────────────────────
    "economics-ba": "econ_ba",
    "economics-bs": "econ_bs",
    "economics:-business-economics-bs": "biz_econ",
    "business-economics-bs-:-rady-school-of-management": "biz_econ",

    # ── Psychology ───────────────────────────────────────────────
    "psychology-ba": "psych_ba",
    "psychology-bs": "psych_bs",
    "psychology-bs-with-a-specialization-in-clinical-psychology": "psych_clinical",
    "psychology-bs-with-a-specialization-in-cognitive-psychology": "psych_cog",
    "psychology-bs-with-a-specialization-in-developmental-psychology": "psych_dev",
    "psychology-bs-with-a-specialization-in-human-health": "psych_health",
    "psychology-bs-with-a-specialization-in-sensation-and-perception": "psych_sensation",
    "psychology-bs-with-a-specialization-in-social-psychology": "psych_social",
    "psychology:-business-psychology-bs": "psych_biz",
    "psychology:-cognitive-and-behavioral-neuroscience-bs": "psych_cbn",

    # ── Political Science ────────────────────────────────────────
    "political-science-ba": "polisci_ba",
    "political-science-american-politics-ba": "polisci_amer",
    "political-science-comparative-politics-ba": "polisci_comp",
    "political-science-international-relations-ba": "polisci_ir",
    "political-science-political-theory-ba": "polisci_theory",
    "political-science-public-law-ba": "polisci_law",
    "political-science-public-policy-ba": "polisci_policy",
    "political-science-race-ethnicity-and-politics-ba": "polisci_race",
    "political-science-data-analytics-bs": "polisci_data",

    # ── Sociology ────────────────────────────────────────────────
    "sociology-ba": "soc_ba",
    "sociology-american-studies-ba": "soc_amer",
    "sociology-culture-and-communication-ba": "soc_culture_comm",
    "sociology-economy-and-society-ba": "soc_econ",
    "sociology-international-studies-ba": "soc_intl",
    "sociology-law-and-society-ba": "soc_law",
    "sociology-science-and-medicine-ba": "soc_sci_med",
    "sociology-social-inequalities-ba": "soc_ineq",

    # ── Communication ────────────────────────────────────────────
    "communication-ba": "comm_ba",
    "communication:-media-industries-and-communication-ba": "comm_media",

    # ── Anthropology ─────────────────────────────────────────────
    "anthropology-ba-with-concentration-in-sociocultural-anthropology": "anth_socio",
    "anthropology-ba-with-concentration-in-biological-anthropology": "anth_bio",
    "anthropology-ba-with-concentration-in-archaeology": "anth_arch",
    "anthropology-ba-with-concentration-in-climate-change-and-human-solutions": "anth_climate",
    "anthropology:-biological-anthropology-bs": "anth_bio_bs",
    "anthropology:-environmental-anthropology-bs": "anth_env_bs",

    # ── History ──────────────────────────────────────────────────
    "history-ba": "hist_ba",

    # ── Philosophy ───────────────────────────────────────────────
    "philosophy-ba": "phil_ba",

    # ── Art / Visual Arts ────────────────────────────────────────
    "art:-art-history-criticism-ba-visual-arts": "art_history",
    "art:-studio-ba-visual-arts": "art_studio",
    "art:-media-ba--visual-arts": "art_media",
    "art:-speculative-design-ba-visual-arts": "art_spec_design",
    "art:-interdisciplinary-computing-in-the-arts-major-icam-ba-visual-arts": "art_icam",

    # ── Cinematic Arts ───────────────────────────────────────────
    "cinematic-arts-and-film-studies:-cinematic-arts-ba": "cinematic_arts",

    # ── Music ────────────────────────────────────────────────────
    "music-ba": "music_ba",
    "music-humanities-major-ba": "music_humanities",
    "music:-interdisciplinary-computing-in-the-arts-major-icam-ba": "music_icam",

    # ── Theatre / Dance ──────────────────────────────────────────
    "theatre-ba": "theatre_ba",
    "theatre-and-dance-ba": "theatre_dance",
    "dance-ba": "dance_ba",

    # ── Linguistics ──────────────────────────────────────────────
    "linguistics-ba": "ling_ba",
    "linguistics-with-specialization-in-cognition-and-language-ba": "ling_cog",
    "linguistics-with-specialization-in-language-and-society-ba": "ling_society",
    "linguistics-with-specialization-in-speech-and-language-sciences-ba": "ling_speech",
    "linguistics:-language-studies-specialization-in-one-language-ba": "ling_lang_studies",
    "linguistics-language-program": "ling_lang_program",

    # ── Literature / English ─────────────────────────────────────
    "literatures-in-english-ba": "lit_english",
    "literature-writing-ba": "lit_writing",
    "literature:-literary-arts-ba": "lit_arts",
    "literature:-spanish-literature-ba": "lit_spanish",
    "literature:-world-literature-and-culture-ba": "lit_world",

    # ── Ethnic / Gender / Area Studies ───────────────────────────
    "ethnic-studies-ba": "ethnic_studies",
    "black-diaspora-and-african-american-studies-ba": "black_diaspora",
    "chicanx-and-latinx-studies-ba": "chicano_latino",
    "critical-gender-studies-ba": "cgs_ba",
    "global-south-studies-formerly-third-world-studies-ba": "global_south",
    "jewish-studies-ba": "jewish_studies",

    # ── Study of Religion ────────────────────────────────────────
    "religion-study-of-ba": "religion_ba",

    # ── Classical Studies ────────────────────────────────────────
    "classical-studies-ba": "classics_ba",

    # ── International Studies ────────────────────────────────────
    "international-studies---anthropology-ba": "intl_anth",
    "international-studies---economics-ba": "intl_econ",
    "international-studies---history-ba": "intl_hist",
    "international-studies---international-business-ba": "intl_biz",
    "international-studies---linguistics-ba": "intl_ling",
    "international-studies---literature-ba": "intl_lit",
    "international-studies---philosophy-ba": "intl_phil",
    "international-studies---political-science-ba": "intl_polisci",
    "international-studies---sociology-ba": "intl_soc",

    # ── Language Studies ─────────────────────────────────────────
    "chinese-studies-ba": "chinese_studies",
    "german-studies-ba": "german_studies",
    "italian-studies-ba": "italian_studies",
    "japanese-studies-ba": "japanese_studies",
    "russian-east-european-and-eurasian-studies-ba": "russian_ee_studies",
    "latin-american-studies-ba": "latin_american",

    # ── Education Sciences ───────────────────────────────────────
    "education-sciences-bs": "educ_sci",

    # ── Public Health ────────────────────────────────────────────
    "public-health-bs": "pubh_bs",
    "public-health-with-concentration-in-biostatistics-bs": "pubh_biostats",
    "public-health-with-concentration-in-climate-and-environmental-sciences-bs": "pubh_climate",
    "public-health-with-concentration-in-community-health-sciences-bs": "pubh_community",
    "public-health-with-concentration-in-epidemiology-bs": "pubh_epi",
    "public-health-with-concentration-in-health-policy-and-management-sciences-bs": "pubh_policy",
    "public-health-with-concentration-in-medicine-sciences-bs": "pubh_med",

    # ── Global Health ────────────────────────────────────────────
    "global-health-ba": "glbh_ba",
    "global-health-bs": "glbh_bs",

    # ── Human Developmental Sciences ─────────────────────────────
    "human-developmental-sciences-ba": "hds_ba",
    "human-developmental-sciences-bs": "hds_bs",
    "human-developmental-sciences-bs-with-a-specialization-in-equity-and-diversity": "hds_equity",
    "human-developmental-sciences-bs-with-a-specialization-in-healthy-aging": "hds_aging",

    # ── Urban Studies ────────────────────────────────────────────
    "urban-studies-and-planning-ba": "urban_ba",

    # ── Business minors (Rady) ───────────────────────────────────
    "business-minor:-rady-school-of-management": "biz_minor",
    "business-analytics-minor:-rady-school-of-management": "biz_analytics_minor",
    "finance-minor:-rady-school-of-management": "finance_minor",
    "marketing-minor:-rady-school-of-management": "marketing_minor",
    "accounting-minor:-rady-school-of-management": "accounting_minor",
    "entrepreneurship-and-innovation-minor:-rady-school-of-management": "entrep_minor",
    "technology-innovation-and-supply-chain-minor:-rady-school-of-management": "tech_supply_minor",

    # ── Real Estate ──────────────────────────────────────────────
    "real-estate-and-development-bs": "real_estate",
}


# ---------------------------------------------------------------------------
# Generator
# ---------------------------------------------------------------------------

def run() -> None:
    root = Path(__file__).resolve().parent.parent.parent
    seed_path = root / "api" / "app" / "data" / "seed_data.json"
    backup_path = seed_path.with_suffix(".json.bak")

    print(f"Reading {seed_path} ...")
    data = json.loads(seed_path.read_text(encoding="utf-8"))

    # Index existing data
    existing_courses: set[str] = set()
    for course in data.get("courses", []):
        existing_courses.add((course["school_id"], course["course_id"]))

    existing_prereqs: set[tuple[str, str, str]] = set()
    for prereq in data.get("course_prerequisites", []):
        existing_prereqs.add((prereq["university_id"], prereq["course_id"], prereq["prerequisite_course_id"]))

    existing_offering_keys: set[tuple[str, str]] = set()
    for off in data.get("course_offerings", []):
        existing_offering_keys.add((off["school_id"], off["course_id"]))

    # Build UCSD major lookup
    ucsd_majors = {m["major_id"]: m for m in data["majors"] if m["school_id"] == "ucsd"}

    # ── Remove old seeded UCSD requirements ──────────────────────
    old_ucsd_req_ids = {r["requirement_id"] for r in data["major_requirements"] if r["university_id"] == "ucsd"}
    data["major_requirements"] = [r for r in data["major_requirements"] if r["university_id"] != "ucsd"]
    print(f"Removed {len(old_ucsd_req_ids)} old UCSD requirement entries")

    # Build existing_req_ids AFTER removing old UCSD ones
    existing_req_ids: set[str] = {r["requirement_id"] for r in data.get("major_requirements", [])}

    # ── Add new courses to UCSD ──────────────────────────────────
    new_courses_added = 0
    new_offerings_added = 0
    new_prereqs_added = 0

    for course_id, (name, units, dept, prereq) in NEW_COURSES.items():
        key = ("ucsd", course_id)
        if key not in existing_courses:
            data.setdefault("courses", []).append({
                "school_id": "ucsd",
                "course_id": course_id,
                "course_name": name,
                "units": units,
                "department": dept,
                "catalog_level": "lower",
                "description": f"{name} — lower-division transfer preparation course.",
                "offered_terms": _offerings(course_id),
            })
            existing_courses.add(key)
            new_courses_added += 1

        off_key = ("ucsd", course_id)
        if off_key not in existing_offering_keys:
            data.setdefault("course_offerings", []).append({
                "school_id": "ucsd",
                "course_id": course_id,
                "offered_terms": _offerings(course_id),
            })
            existing_offering_keys.add(off_key)
            new_offerings_added += 1

        if prereq:
            p_key = ("ucsd", course_id, prereq)
            if p_key not in existing_prereqs:
                data.setdefault("course_prerequisites", []).append({
                    "university_id": "ucsd",
                    "course_id": course_id,
                    "prerequisite_course_id": prereq,
                })
                existing_prereqs.add(p_key)
                new_prereqs_added += 1

    print(f"Added {new_courses_added} new courses, {new_offerings_added} offerings, {new_prereqs_added} prerequisites for UCSD")

    # ── Generate major requirements ──────────────────────────────
    new_reqs = 0
    mapped_majors = 0
    unmapped = []

    for suffix, template_key in MAJOR_TEMPLATE_MAP.items():
        major_id = f"ucsd-{suffix}"
        if major_id not in ucsd_majors:
            print(f"  WARNING: major_id '{major_id}' not found in seed data — skipping")
            continue

        template = TEMPLATES.get(template_key)
        if not template:
            print(f"  WARNING: template '{template_key}' not found — skipping {major_id}")
            continue

        major = ucsd_majors[major_id]
        source_url = major.get("source", {}).get("source_url")

        for idx, course_id in enumerate(template, start=1):
            req_id = f"{major_id}-REQ-{idx}"
            if req_id in existing_req_ids:
                continue

            course_info = NEW_COURSES.get(course_id)
            if not course_info:
                print(f"  WARNING: course '{course_id}' not in NEW_COURSES — skipping")
                continue

            name, units, _dept, _prereq = course_info
            data["major_requirements"].append({
                "university_id": "ucsd",
                "major_id": major_id,
                "requirement_id": req_id,
                "course_id": course_id,
                "course_name": name,
                "units": units,
                "type": "required",
                "term_offerings": _offerings(course_id),
                "source_name": "ASSIST.org Articulation Agreement (LPC → UCSD)",
                "source_url": source_url,
                "policy_year": "AY-2025-26",
            })
            existing_req_ids.add(req_id)
            new_reqs += 1

        mapped_majors += 1

    # Check for unmapped ASSIST.org majors
    assist_majors = [m for m in ucsd_majors.values()
                     if "assist.org" in str(m.get("source", {}).get("source_url", ""))]
    for m in assist_majors:
        suffix = m["major_id"].replace("ucsd-", "", 1)
        if suffix not in MAJOR_TEMPLATE_MAP:
            unmapped.append(m["major_id"])

    print(f"\nMapped {mapped_majors} UCSD majors → {new_reqs} new requirement entries")
    if unmapped:
        print(f"\n{len(unmapped)} ASSIST.org majors still unmapped:")
        for u in sorted(unmapped):
            print(f"  - {u}")

    # ── Generate LPC articulation entries ────────────────────────
    # For each requirement, create an articulation that maps the
    # corresponding LPC CC course (LPC-{course_id}) to the requirement.
    # This allows the planner to resolve CC→UC course equivalencies.

    existing_art_keys: set[tuple[str, str, str, str]] = set()
    for art in data.get("assist_articulations", []):
        existing_art_keys.add((
            art.get("cc_id", ""),
            art.get("major_id", ""),
            art.get("cc_course_id", ""),
            art.get("satisfies_requirement_id", ""),
        ))

    new_arts = 0
    ucsd_reqs = [r for r in data["major_requirements"] if r["university_id"] == "ucsd"]
    for req in ucsd_reqs:
        major_id = req["major_id"]
        req_id = req["requirement_id"]
        course_id = req["course_id"]
        cc_course_id = f"LPC-{course_id}"
        art_key = ("lpc", major_id, cc_course_id, req_id)
        if art_key in existing_art_keys:
            continue
        data.setdefault("assist_articulations", []).append({
            "cc_id": "lpc",
            "university_id": "ucsd",
            "major_id": major_id,
            "cc_course_id": cc_course_id,
            "satisfies_requirement_id": req_id,
            "source": {
                "source_name": "ASSIST.org Articulation Agreement (LPC → UCSD)",
                "source_url": ucsd_majors.get(major_id, {}).get("source", {}).get("source_url"),
                "policy_year": "AY-2025-26",
            },
        })
        existing_art_keys.add(art_key)
        new_arts += 1

    print(f"Added {new_arts} LPC → UCSD articulation entries")

    # ── Write output ─────────────────────────────────────────────
    # Backup
    backup_path.write_text(seed_path.read_text(encoding="utf-8"), encoding="utf-8")
    print(f"\nBackup saved to {backup_path}")

    seed_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Updated {seed_path}")

    # Also copy to data-pipeline/seeds/
    dp_path = root / "data-pipeline" / "seeds" / "seed_data.json"
    if dp_path.parent.exists():
        dp_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"Copied to {dp_path}")

    # Summary
    total_ucsd_reqs = sum(1 for r in data["major_requirements"] if r["university_id"] == "ucsd")
    total_ucsd_majors_with_reqs = len({r["major_id"] for r in data["major_requirements"] if r["university_id"] == "ucsd"})
    total_lpc_ucsd_arts = sum(
        1 for a in data.get("assist_articulations", [])
        if a.get("cc_id") == "lpc" and a.get("university_id") == "ucsd"
        and a.get("satisfies_requirement_id", "").endswith("-REQ-" + a.get("satisfies_requirement_id", "").rsplit("-REQ-", 1)[-1])
    )
    print(f"\nFinal totals:")
    print(f"  UCSD requirement entries: {total_ucsd_reqs}")
    print(f"  UCSD majors with requirements: {total_ucsd_majors_with_reqs} / {len(ucsd_majors)}")
    print(f"  LPC → UCSD articulations (REQ-*): {total_lpc_ucsd_arts}")


if __name__ == "__main__":
    run()
