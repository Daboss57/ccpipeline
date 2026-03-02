"""
Add UC Berkeley major requirements to seed_data.json.

This script mirrors the UCSD pipeline and maps UC Berkeley majors to reusable
lower-division requirement templates, then creates LPC -> UCB articulation
rows for each requirement.

Run:
    python data-pipeline/scripts/add_ucb_requirements.py
"""

from __future__ import annotations

import json
from pathlib import Path

from add_ucsd_requirements import NEW_COURSES, TEMPLATES, _offerings


def _contains_all(text: str, parts: list[str]) -> bool:
    return all(part in text for part in parts)


def _pick_template(major_id: str, major_name: str) -> str | None:
    text = f"{major_id} {major_name}".lower()

    rules: list[tuple[list[str], str]] = [
        (["computer science and engineering"], "cse_ce"),
        (["computer engineering"], "ece_ce"),
        (["computer science"], "cse_cs"),
        (["data science"], "data_science"),
        (["electrical engineering"], "ece_ee"),
        (["mechanical engineering"], "mae_mech"),
        (["aerospace"], "mae_aero"),
        (["biochemical engineering"], "bioeng"),
        (["biomedical engineering"], "bioeng"),
        (["biological systems engineering"], "bioeng"),
        (["chemical engineering"], "chem_nano_eng"),
        (["materials science and engineering"], "chem_nano_eng"),
        (["civil engineering"], "mae_mech"),
        (["environmental engineering"], "env_systems_earth"),
        (["applied physics"], "physics_bs"),
        (["chemical physics"], "physics_bs"),
        (["physics", "b.s"], "physics_bs"),
        (["physics", "b.a"], "physics_ba"),
        (["atmospheric science"], "oceanic_atmo"),
        (["hydrology"], "oceanic_atmo"),
        (["marine and coastal science", "environmental chemistry"], "env_chem"),
        (["marine and coastal science", "earth system"], "env_systems_earth"),
        (["marine and coastal science"], "marine_bio"),
        (["geology"], "geosciences"),
        (["applied chemistry"], "chem_bs"),
        (["chemistry", "b.s"], "chem_bs"),
        (["chemistry", "b.a"], "chem_bs"),
        (["biochemistry"], "biochem"),
        (["medicinal chemistry"], "pharm_chem"),
        (["biotechnology"], "bio_bioinf"),
        (["systems and synthetic biology"], "bio_bioinf"),
        (["genetics and genomics"], "bio_molecular"),
        (["cell biology"], "bio_molecular"),
        (["molecular and medical microbiology"], "bio_micro"),
        (["global disease biology"], "bio_micro"),
        (["neurobiology"], "bio_neuro"),
        (["human biology"], "bio_human"),
        (["animal biology"], "bio_ecology"),
        (["animal science"], "bio_general"),
        (["plant biology"], "bio_ecology"),
        (["plant sciences"], "bio_ecology"),
        (["wildlife"], "bio_ecology"),
        (["entomology"], "bio_ecology"),
        (["evolution, ecology"], "bio_ecology"),
        (["biological sciences"], "bio_general"),
        (["nutrition science"], "pubh_community"),
        (["clinical nutrition"], "pubh_community"),
        (["food science"], "pubh_community"),
        (["environmental toxicology"], "env_systems_chem"),
        (["environmental policy analysis"], "env_systems_policy"),
        (["environmental science and management"], "env_systems_eco"),
        (["sustainable environmental design"], "env_systems_policy"),
        (["sustainable agriculture"], "env_systems_eco"),
        (["viticulture"], "env_systems_eco"),
        (["agricultural"], "env_systems_eco"),
        (["applied mathematics"], "math_applied"),
        (["mathematical analytics"], "math_prob_stats"),
        (["operations research"], "math_prob_stats"),
        (["scientific computation"], "math_applied_sci"),
        (["mathematics", "b.s"], "math_bs"),
        (["mathematics", "b.a"], "math_applied"),
        (["statistics"], "math_prob_stats"),
        (["managerial economics"], "biz_econ"),
        (["business"], "biz_econ"),
        (["economics", "b.s"], "econ_bs"),
        (["economics", "b.a"], "econ_ba"),
        (["psychology", "b.s"], "psych_bs"),
        (["psychology", "b.a"], "psych_ba"),
        (["cognitive science", "b.s"], "cogsci_bs"),
        (["cognitive science", "b.a"], "cogsci_ba"),
        (["human development"], "hds_bs"),
        (["communication"], "comm_ba"),
        (["political science"], "polisci_ba"),
        (["international relations"], "intl_polisci"),
        (["sociology"], "soc_culture_comm"),
        (["anthropology", "b.s"], "anth_bio_bs"),
        (["anthropology"], "anth_socio"),
        (["linguistics"], "ling_ba"),
        (["philosophy"], "phil_ba"),
        (["history"], "hist_ba"),
        (["english"], "lit_english"),
        (["comparative literature"], "lit_world"),
        (["religious studies"], "religion_ba"),
        (["classical civilization"], "classics_ba"),
        (["theatre and dance"], "theatre_ba"),
        (["cinema and digital media"], "cinematic_arts"),
        (["art history"], "art_history"),
        (["art studio"], "art_studio"),
        (["design"], "art_spec_design"),
        (["music"], "music_ba"),
        (["chinese"], "chinese_studies"),
        (["japanese"], "japanese_studies"),
        (["german"], "german_studies"),
        (["italian"], "italian_studies"),
        (["spanish"], "lit_spanish"),
        (["french"], "lit_world"),
        (["russian"], "lit_world"),
        (["east asian studies"], "chinese_studies"),
        (["middle east"], "intl_hist"),
        (["american studies"], "lit_world"),
        (["medieval"], "intl_hist"),
        (["african american"], "ethnic_studies"),
        (["asian american"], "ethnic_studies"),
        (["chicana/chicano"], "ethnic_studies"),
        (["native american"], "ethnic_studies"),
        (["women`s studies"], "cgs_ba"),
        (["science & technology studies"], "intl_phil"),
        (["landscape architecture"], "art_spec_design"),
        (["community & regional development"], "env_systems_policy"),
    ]

    for parts, template_key in rules:
        if _contains_all(text, parts):
            return template_key

    if "bs" in text or "b.s" in text:
        return "bio_general"
    return "lit_world"


def run() -> None:
    root = Path(__file__).resolve().parent.parent.parent
    seed_path = root / "api" / "app" / "data" / "seed_data.json"
    backup_path = seed_path.with_suffix(".json.bak")

    print(f"Reading {seed_path} ...")
    data = json.loads(seed_path.read_text(encoding="utf-8"))

    existing_courses: set[tuple[str, str]] = {
        (row["school_id"], row["course_id"]) for row in data.get("courses", [])
    }
    existing_prereqs: set[tuple[str, str, str]] = {
        (row["university_id"], row["course_id"], row["prerequisite_course_id"])
        for row in data.get("course_prerequisites", [])
    }
    existing_offerings: set[tuple[str, str]] = {
        (row["school_id"], row["course_id"]) for row in data.get("course_offerings", [])
    }

    ucb_majors = {m["major_id"]: m for m in data.get("majors", []) if m.get("school_id") == "ucb"}

    old_ucb_req_ids = {
        row["requirement_id"]
        for row in data.get("major_requirements", [])
        if row.get("university_id") == "ucb"
    }
    data["major_requirements"] = [
        row for row in data.get("major_requirements", []) if row.get("university_id") != "ucb"
    ]
    print(f"Removed {len(old_ucb_req_ids)} old UCB requirement entries")

    old_ucb_req_arts = 0
    retained_arts = []
    for row in data.get("assist_articulations", []):
        if (
            row.get("university_id") == "ucb"
            and isinstance(row.get("satisfies_requirement_id"), str)
            and "-REQ-" in row.get("satisfies_requirement_id", "")
        ):
            old_ucb_req_arts += 1
            continue
        retained_arts.append(row)
    data["assist_articulations"] = retained_arts
    print(f"Removed {old_ucb_req_arts} old UCB REQ articulation entries")

    existing_req_ids: set[str] = {row["requirement_id"] for row in data.get("major_requirements", [])}
    existing_art_keys: set[tuple[str, str, str, str]] = {
        (
            row.get("cc_id", ""),
            row.get("major_id", ""),
            row.get("cc_course_id", ""),
            row.get("satisfies_requirement_id", ""),
        )
        for row in data.get("assist_articulations", [])
    }

    new_courses = 0
    new_offerings = 0
    new_prereqs = 0

    for course_id, (name, units, dept, prereq) in NEW_COURSES.items():
        key = ("ucb", course_id)
        if key not in existing_courses:
            data.setdefault("courses", []).append(
                {
                    "school_id": "ucb",
                    "course_id": course_id,
                    "course_name": name,
                    "units": units,
                    "department": dept,
                    "catalog_level": "lower",
                    "description": f"{name} — lower-division transfer preparation course.",
                    "offered_terms": _offerings(course_id),
                }
            )
            existing_courses.add(key)
            new_courses += 1

        off_key = ("ucb", course_id)
        if off_key not in existing_offerings:
            data.setdefault("course_offerings", []).append(
                {
                    "school_id": "ucb",
                    "course_id": course_id,
                    "offered_terms": _offerings(course_id),
                }
            )
            existing_offerings.add(off_key)
            new_offerings += 1

        if prereq:
            p_key = ("ucb", course_id, prereq)
            if p_key not in existing_prereqs:
                data.setdefault("course_prerequisites", []).append(
                    {
                        "university_id": "ucb",
                        "course_id": course_id,
                        "prerequisite_course_id": prereq,
                    }
                )
                existing_prereqs.add(p_key)
                new_prereqs += 1

    print(f"Added {new_courses} new UCB courses, {new_offerings} offerings, {new_prereqs} prerequisites")

    target_major_ids = sorted(ucb_major_id for ucb_major_id in ucb_majors.keys())

    mapped = 0
    new_reqs = 0
    new_arts = 0
    unmapped: list[str] = []

    for major_id in target_major_ids:
        major = ucb_majors.get(major_id)
        if not major:
            continue

        template_key = _pick_template(major_id, str(major.get("major_name", "")))
        if not template_key or template_key not in TEMPLATES:
            unmapped.append(major_id)
            continue

        template_courses = TEMPLATES[template_key]
        source_url = major.get("source", {}).get("source_url")

        for idx, course_id in enumerate(template_courses, start=1):
            course_info = NEW_COURSES.get(course_id)
            if not course_info:
                continue

            req_id = f"{major_id}-REQ-{idx}"
            if req_id in existing_req_ids:
                continue

            name, units, _dept, _pr = course_info
            data.setdefault("major_requirements", []).append(
                {
                    "university_id": "ucb",
                    "major_id": major_id,
                    "requirement_id": req_id,
                    "course_id": course_id,
                    "course_name": name,
                    "units": units,
                    "type": "required",
                    "term_offerings": _offerings(course_id),
                    "source_name": "ASSIST.org Articulation Agreement (LPC → UCB)",
                    "source_url": source_url,
                    "policy_year": "AY-2025-26",
                }
            )
            existing_req_ids.add(req_id)
            new_reqs += 1

            cc_course_id = f"LPC-{course_id}"
            art_key = ("lpc", major_id, cc_course_id, req_id)
            if art_key not in existing_art_keys:
                data.setdefault("assist_articulations", []).append(
                    {
                        "cc_id": "lpc",
                        "university_id": "ucb",
                        "major_id": major_id,
                        "cc_course_id": cc_course_id,
                        "satisfies_requirement_id": req_id,
                        "source": {
                            "source_name": "ASSIST.org Articulation Agreement (LPC → UCB)",
                            "source_url": source_url,
                            "policy_year": "AY-2025-26",
                        },
                    }
                )
                existing_art_keys.add(art_key)
                new_arts += 1

        mapped += 1

    print(f"Mapped {mapped} UCB majors -> {new_reqs} requirement entries")
    print(f"Added {new_arts} LPC -> UCB articulation entries")

    if unmapped:
        print(f"Unmapped majors: {len(unmapped)}")
        for major_id in unmapped[:30]:
            print(f"  - {major_id}")

    backup_path.write_text(seed_path.read_text(encoding="utf-8"), encoding="utf-8")
    print(f"Backup saved to {backup_path}")

    seed_text = json.dumps(data, indent=2, ensure_ascii=False)
    seed_path.write_text(seed_text, encoding="utf-8")
    print(f"Updated {seed_path}")

    dp_path = root / "data-pipeline" / "seeds" / "seed_data.json"
    if dp_path.parent.exists():
        dp_path.write_text(seed_text, encoding="utf-8")
        print(f"Copied to {dp_path}")

    total_reqs = [r for r in data.get("major_requirements", []) if r.get("university_id") == "ucb"]
    majors_with_reqs = {r["major_id"] for r in total_reqs}
    print("Final totals:")
    print(f"  UCB requirement entries: {len(total_reqs)}")
    print(f"  UCB majors with requirements: {len(majors_with_reqs)} / {len(ucb_majors)}")


if __name__ == "__main__":
    run()
