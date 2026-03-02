"""Generate deterministic seed data for PathwayIQ MVP."""

from __future__ import annotations

import json
from pathlib import Path

UC_SCHOOLS = [
    ("ucb", "UC Berkeley", "semester"),
    ("ucla", "UCLA", "quarter"),
    ("ucsd", "UC San Diego", "quarter"),
    ("ucd", "UC Davis", "quarter"),
    ("ucsb", "UC Santa Barbara", "quarter"),
    ("uci", "UC Irvine", "quarter"),
    ("ucsc", "UC Santa Cruz", "quarter"),
    ("ucr", "UC Riverside", "quarter"),
    ("ucm", "UC Merced", "semester"),
]

CC_SCHOOLS = [
    ("lpc", "Las Positas College", "semester"),
    ("sjdc", "San Joaquin Delta College", "semester"),
]

MAJORS = [
    ("computer-science", "Computer Science"),
    ("data-science", "Data Science"),
    ("biology", "Biology"),
    ("economics", "Economics"),
    ("psychology", "Psychology"),
]

MAJOR_COURSE_CHAINS = {
    "computer-science": [
        ("MATH101", "Calculus I", 4, None),
        ("CSE101", "Programming Fundamentals", 4, "MATH101"),
        ("CSE102", "Data Structures", 4, "CSE101"),
        ("CSE201", "Computer Architecture", 4, "CSE102"),
        ("CSE202", "Algorithms", 4, "CSE102"),
    ],
    "data-science": [
        ("MATH101", "Calculus I", 4, None),
        ("STATS101", "Intro Statistics", 4, None),
        ("DSC101", "Data Wrangling", 4, "CSE101"),
        ("CSE101", "Programming Fundamentals", 4, "MATH101"),
        ("DSC201", "Machine Learning Fundamentals", 4, "DSC101"),
    ],
    "biology": [
        ("CHEM101", "General Chemistry I", 4, None),
        ("BIO101", "Cell Biology", 4, None),
        ("BIO201", "Genetics", 4, "BIO101"),
        ("CHEM201", "Organic Chemistry", 4, "CHEM101"),
        ("BIO301", "Molecular Biology", 4, "BIO201"),
    ],
    "economics": [
        ("MATH101", "Calculus I", 4, None),
        ("ECON101", "Microeconomics", 4, None),
        ("ECON102", "Macroeconomics", 4, None),
        ("ECON201", "Intermediate Microeconomics", 4, "ECON101"),
        ("ECON301", "Econometrics", 4, "STATS101"),
    ],
    "psychology": [
        ("PSY101", "Intro Psychology", 4, None),
        ("STATS101", "Intro Statistics", 4, None),
        ("PSY201", "Research Methods", 4, "PSY101"),
        ("PSY301", "Cognitive Psychology", 4, "PSY201"),
        ("PSY401", "Abnormal Psychology", 4, "PSY201"),
    ],
}

COURSE_OFFERING_RULES = {
    "MATH": ["Fall", "Winter", "Spring"],
    "CSE": ["Fall", "Winter", "Spring"],
    "DSC": ["Fall", "Spring"],
    "BIO": ["Fall", "Spring"],
    "CHEM": ["Fall", "Spring"],
    "STATS": ["Fall", "Winter", "Spring"],
    "ECON": ["Fall", "Winter", "Spring"],
    "PSY": ["Fall", "Winter", "Spring"],
    "ENGL": ["Fall", "Winter", "Spring"],
    "PE": ["Fall", "Winter", "Spring", "Summer"],
}

SUPPLEMENTAL_COURSES = [
    ("ENGL101", "English Composition I", 4, "English", "lower"),
    ("ENGL102", "English Composition II", 4, "English", "lower"),
    ("PE101", "Physical Education / Wellness", 1, "Wellness", "lower"),
]

EXAM_POLICIES = [
    {
        "exam_type": "AP",
        "exam_name": "AP Calculus BC",
        "min_score": 4,
        "courses_satisfied": ["MATH101"],
        "ge_areas_satisfied": ["2"],
        "units_granted": 4,
    },
    {
        "exam_type": "AP",
        "exam_name": "AP Biology",
        "min_score": 4,
        "courses_satisfied": ["BIO101"],
        "ge_areas_satisfied": ["5"],
        "units_granted": 4,
    },
    {
        "exam_type": "AP",
        "exam_name": "AP Computer Science A",
        "min_score": 3,
        "courses_satisfied": ["CSE101"],
        "ge_areas_satisfied": [],
        "units_granted": 4,
    },
    {
        "exam_type": "AP",
        "exam_name": "AP Statistics",
        "min_score": 3,
        "courses_satisfied": ["STATS101"],
        "ge_areas_satisfied": ["2"],
        "units_granted": 4,
    },
    {
        "exam_type": "AP",
        "exam_name": "AP Psychology",
        "min_score": 3,
        "courses_satisfied": ["PSY101"],
        "ge_areas_satisfied": ["4"],
        "units_granted": 4,
    },
    {
        "exam_type": "IB",
        "exam_name": "IB Mathematics HL",
        "min_score": 5,
        "courses_satisfied": ["MATH101"],
        "ge_areas_satisfied": ["2"],
        "units_granted": 4,
    },
    {
        "exam_type": "CLEP",
        "exam_name": "CLEP College Mathematics",
        "min_score": 55,
        "courses_satisfied": ["MATH101"],
        "ge_areas_satisfied": ["2"],
        "units_granted": 3,
    },
]

IGETC_AREAS = ["1", "2", "3", "4", "5", "6", "7"]


def _course_prefix(course_id: str) -> str:
    return "".join(char for char in course_id if char.isalpha())


def _offered_terms(course_id: str, term_system: str) -> list[str]:
    prefix = _course_prefix(course_id)
    base = COURSE_OFFERING_RULES.get(prefix, ["Fall", "Spring"])
    if term_system == "semester":
        return [term for term in base if term in {"Spring", "Summer", "Fall"}] or ["Spring", "Fall"]
    return base


def build_seed() -> dict:
    policy_year = "AY-2025-26"

    schools = []
    for school_id, name, term_system in UC_SCHOOLS:
        schools.append(
            {
                "school_id": school_id,
                "name": name,
                "system": "UC",
                "term_system": term_system,
            }
        )
    for school_id, name, term_system in CC_SCHOOLS:
        schools.append(
            {
                "school_id": school_id,
                "name": name,
                "system": "CC",
                "term_system": term_system,
            }
        )

    majors = []
    for school_id, _, _ in UC_SCHOOLS:
        for major_id, major_name in MAJORS:
            majors.append(
                {
                    "major_id": f"{school_id}-{major_id}",
                    "school_id": school_id,
                    "major_key": major_id,
                    "major_name": major_name,
                    "department": "PathwayIQ Seed Catalog",
                    "total_units": 20,
                    "source": {
                        "source_name": "UC Campus Catalog (seeded)",
                        "source_url": None,
                        "policy_year": policy_year,
                    },
                }
            )

    major_requirements = []
    prerequisites = []
    courses = []
    course_offerings = []
    course_seen = set()
    for school_id, _, _ in UC_SCHOOLS:
        for major_key, _ in MAJORS:
            major_id = f"{school_id}-{major_key}"
            for idx, (course_id, course_name, units, prereq) in enumerate(MAJOR_COURSE_CHAINS[major_key], start=1):
                requirement_id = f"{major_id}-REQ-{idx}"
                major_requirements.append(
                    {
                        "university_id": school_id,
                        "major_id": major_id,
                        "requirement_id": requirement_id,
                        "course_id": course_id,
                        "course_name": course_name,
                        "units": units,
                        "type": "required",
                        "term_offerings": _offered_terms(course_id, next(term for sid, _, term in UC_SCHOOLS if sid == school_id)),
                        "source_name": "UC Catalog + ASSIST (seeded)",
                        "source_url": None,
                        "policy_year": policy_year,
                    }
                )
                if (school_id, course_id) not in course_seen:
                    course_seen.add((school_id, course_id))
                    term_system = next(term for sid, _, term in UC_SCHOOLS if sid == school_id)
                    offered_terms = _offered_terms(course_id, term_system)
                    courses.append(
                        {
                            "school_id": school_id,
                            "course_id": course_id,
                            "course_name": course_name,
                            "units": units,
                            "department": _course_prefix(course_id),
                            "catalog_level": "lower" if course_id.endswith("101") or course_id.endswith("102") else "upper",
                            "description": f"{course_name} at {school_id.upper()}.",
                            "offered_terms": offered_terms,
                        }
                    )
                    course_offerings.append(
                        {
                            "school_id": school_id,
                            "course_id": course_id,
                            "offered_terms": offered_terms,
                        }
                    )
                if prereq:
                    prerequisites.append(
                        {
                            "university_id": school_id,
                            "course_id": course_id,
                            "prerequisite_course_id": prereq,
                            "min_grade": "C",
                        }
                    )

        for course_id, course_name, units, department, level in SUPPLEMENTAL_COURSES:
            if (school_id, course_id) in course_seen:
                continue
            course_seen.add((school_id, course_id))
            term_system = next(term for sid, _, term in UC_SCHOOLS if sid == school_id)
            offered_terms = _offered_terms(course_id, term_system)
            courses.append(
                {
                    "school_id": school_id,
                    "course_id": course_id,
                    "course_name": course_name,
                    "units": units,
                    "department": department,
                    "catalog_level": level,
                    "description": f"{course_name} at {school_id.upper()}.",
                    "offered_terms": offered_terms,
                }
            )
            course_offerings.append(
                {
                    "school_id": school_id,
                    "course_id": course_id,
                    "offered_terms": offered_terms,
                }
            )

    ap_credit_policies = []
    for school_id, _, _ in UC_SCHOOLS:
        for policy in EXAM_POLICIES:
            ap_credit_policies.append(
                {
                    "school_id": school_id,
                    "exam_type": policy["exam_type"],
                    "exam_name": policy["exam_name"],
                    "min_score": policy["min_score"],
                    "units_granted": policy["units_granted"],
                    "courses_satisfied": policy["courses_satisfied"],
                    "ge_areas_satisfied": policy["ge_areas_satisfied"],
                    "source_name": "UC AP/IB/CLEP Credit Policy (seeded)",
                    "source_url": None,
                    "policy_year": policy_year,
                }
            )

    igetc_courses = []
    for cc_id, _, _ in CC_SCHOOLS:
        for area in IGETC_AREAS:
            cc_term_system = next(term for sid, _, term in CC_SCHOOLS if sid == cc_id)
            igetc_course_id = f"{cc_id.upper()}-IGETC-{area}"
            offered_terms = _offered_terms(igetc_course_id, cc_term_system)
            igetc_courses.append(
                {
                    "cc_id": cc_id,
                    "igetc_area": area,
                    "course_id": igetc_course_id,
                    "course_name": f"IGETC Area {area} Course",
                    "units": 3,
                    "offered_terms": offered_terms,
                    "source_url": None,
                    "policy_year": policy_year,
                }
            )
            courses.append(
                {
                    "school_id": cc_id,
                    "course_id": igetc_course_id,
                    "course_name": f"IGETC Area {area} Course",
                    "units": 3,
                    "department": "IGETC",
                    "catalog_level": "lower",
                    "description": f"Community college IGETC Area {area} course.",
                    "offered_terms": offered_terms,
                }
            )
            course_offerings.append(
                {
                    "school_id": cc_id,
                    "course_id": igetc_course_id,
                    "offered_terms": offered_terms,
                }
            )

    assist_articulations = []
    for cc_id, _, _ in CC_SCHOOLS:
        for uc_id, _, _ in UC_SCHOOLS:
            for major_key, _ in MAJORS:
                major_id = f"{uc_id}-{major_key}"
                chain = MAJOR_COURSE_CHAINS[major_key]
                for idx, (course_id, _, _, _) in enumerate(chain[:3], start=1):
                    assist_articulations.append(
                        {
                            "cc_id": cc_id,
                            "university_id": uc_id,
                            "major_id": major_id,
                            "cc_course_id": f"{cc_id.upper()}-{course_id}",
                            "satisfies_requirement_id": f"{major_id}-REQ-{idx}",
                            "source": {
                                "source_name": "ASSIST.org (seeded)",
                                "source_url": None,
                                "policy_year": policy_year,
                            },
                        }
                    )

    return {
        "policy_version": policy_year,
        "policy_updated_at": "2026-02-15",
        "schools": schools,
        "majors": majors,
        "courses": courses,
        "course_offerings": course_offerings,
        "major_requirements": major_requirements,
        "course_prerequisites": prerequisites,
        "exam_credit_policies": ap_credit_policies,
        "igetc_courses": igetc_courses,
        "assist_articulations": assist_articulations,
    }


def main() -> None:
    data = build_seed()
    output_paths = [
        Path(__file__).resolve().parents[1] / "seeds" / "seed_data.json",
        Path(__file__).resolve().parents[2] / "api" / "app" / "data" / "seed_data.json",
    ]
    for output_path in output_paths:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        print(f"Wrote {output_path}")


if __name__ == "__main__":
    main()
