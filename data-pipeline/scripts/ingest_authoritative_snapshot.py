from __future__ import annotations

import json
from pathlib import Path

from generate_seed_data import UC_SCHOOLS, build_seed

RAW_DIR = Path(__file__).resolve().parents[1] / "raw"
OUTPUT_PATHS = [
    Path(__file__).resolve().parents[1] / "seeds" / "seed_data.json",
    Path(__file__).resolve().parents[2] / "api" / "app" / "data" / "seed_data.json",
]


def _read_json(path: Path) -> list[dict]:
    if not path.exists():
        raise FileNotFoundError(f"Missing required file: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError(f"Expected top-level JSON array in {path}")
    return [row for row in payload if isinstance(row, dict)]


def _slug(text: str) -> str:
    return (
        text.lower()
        .replace("&", "and")
        .replace("/", "-")
        .replace(",", "")
        .replace(".", "")
        .replace(" ", "-")
    )


def _normalize_major_row(row: dict) -> dict:
    school_id = str(row["school_id"]).strip().lower()
    major_key = str(row.get("major_key") or _slug(str(row["major_name"]))).strip().lower()
    major_id = f"{school_id}-{major_key}"
    return {
        "major_id": major_id,
        "school_id": school_id,
        "major_key": major_key,
        "major_name": str(row["major_name"]).strip(),
        "department": str(row.get("department", "")).strip() or "Unknown",
        "total_units": int(row.get("total_units", 0) or 0),
        "source": {
            "source_name": str(row.get("source_name", "Official UC Catalog")).strip(),
            "source_url": row.get("source_url"),
            "policy_year": str(row.get("policy_year", "unknown")).strip(),
        },
    }


def _normalize_articulation_row(row: dict) -> dict:
    source_name = str(row.get("source_name", "ASSIST.org")).strip()
    policy_year = str(row.get("policy_year", "unknown")).strip()
    return {
        "cc_id": str(row["cc_id"]).strip().lower(),
        "university_id": str(row["university_id"]).strip().lower(),
        "major_id": str(row["major_id"]).strip().lower(),
        "cc_course_id": str(row["cc_course_id"]).strip(),
        "satisfies_requirement_id": str(row["satisfies_requirement_id"]).strip(),
        "agreement_label": str(row.get("agreement_label", "")).strip() or None,
        "agreement_key": str(row.get("agreement_key", "")).strip() or None,
        "source": {
            "source_name": source_name,
            "source_url": row.get("source_url"),
            "policy_year": policy_year,
        },
    }


def _validate_coverage(majors: list[dict], articulations: list[dict]) -> None:
    uc_ids = {school_id for school_id, _, _ in UC_SCHOOLS}

    majors_by_uc: dict[str, int] = {uc_id: 0 for uc_id in uc_ids}
    for major in majors:
        school_id = major["school_id"]
        if school_id in majors_by_uc:
            majors_by_uc[school_id] += 1

    missing_major_uc = [uc_id for uc_id, count in majors_by_uc.items() if count == 0]
    if missing_major_uc:
        raise ValueError(f"Missing majors for UC campuses: {', '.join(sorted(missing_major_uc))}")

    lpc_rows = [row for row in articulations if row["cc_id"] == "lpc"]
    if not lpc_rows:
        raise ValueError("No LPC articulation rows found.")

    lpc_uc_coverage = {uc_id: 0 for uc_id in uc_ids}
    for row in lpc_rows:
        uc_id = row["university_id"]
        if uc_id in lpc_uc_coverage:
            lpc_uc_coverage[uc_id] += 1

    missing_articulation_uc = [uc_id for uc_id, count in lpc_uc_coverage.items() if count == 0]
    if missing_articulation_uc:
        raise ValueError(
            "Missing LPC articulation coverage for UC campuses: " + ", ".join(sorted(missing_articulation_uc))
        )



def main() -> None:
    majors_raw = _read_json(RAW_DIR / "uc_majors.json")
    articulations_raw = _read_json(RAW_DIR / "lpc_uc_articulations.json")

    majors = [_normalize_major_row(row) for row in majors_raw]
    articulations = [_normalize_articulation_row(row) for row in articulations_raw]

    _validate_coverage(majors, articulations)

    seed = build_seed()

    merged_majors: dict[str, dict] = {
        row["major_id"]: row for row in seed.get("majors", []) if isinstance(row, dict)
    }
    for row in majors:
        merged_majors[row["major_id"]] = row
    seed["majors"] = sorted(merged_majors.values(), key=lambda row: row["major_id"])

    merged_articulations: dict[tuple[str, str, str, str, str], dict] = {}
    for row in seed.get("assist_articulations", []):
        if not isinstance(row, dict):
            continue
        key = (
            row.get("cc_id", ""),
            row.get("university_id", ""),
            row.get("major_id", ""),
            row.get("cc_course_id", ""),
            row.get("satisfies_requirement_id", ""),
        )
        merged_articulations[key] = row
    for row in articulations:
        key = (
            row.get("cc_id", ""),
            row.get("university_id", ""),
            row.get("major_id", ""),
            row.get("cc_course_id", ""),
            row.get("satisfies_requirement_id", ""),
        )
        merged_articulations[key] = row
    seed["assist_articulations"] = sorted(
        merged_articulations.values(),
        key=lambda row: (
            row.get("cc_id", ""),
            row.get("university_id", ""),
            row.get("major_id", ""),
            row.get("cc_course_id", ""),
        ),
    )

    policy_years = sorted(
        {
            major.get("source", {}).get("policy_year")
            for major in majors
            if isinstance(major.get("source"), dict)
        }
    )
    if policy_years:
        seed["policy_version"] = policy_years[-1]

    for output_path in OUTPUT_PATHS:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(seed, indent=2), encoding="utf-8")
        print(f"Wrote {output_path}")


if __name__ == "__main__":
    main()
