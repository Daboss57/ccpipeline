from __future__ import annotations

import argparse
import json
import re
import time
from datetime import datetime
from html import unescape
from pathlib import Path
from typing import Iterable

import httpx

UC_CAMPUSES: dict[str, dict[str, str]] = {
    "ucb": {
        "name": "UC Berkeley",
        "landing_url": "https://admission.universityofcalifornia.edu/campuses-majors/berkeley/",
        "major_url": "https://guide.berkeley.edu/undergraduate/degree-programs/",
    },
    "ucd": {
        "name": "UC Davis",
        "landing_url": "https://admission.universityofcalifornia.edu/campuses-majors/davis/",
        "major_url": "https://www.ucdavis.edu/majors/",
    },
    "uci": {
        "name": "UC Irvine",
        "landing_url": "https://admission.universityofcalifornia.edu/campuses-majors/irvine/",
        "major_url": "https://catalogue.uci.edu/undergraduatedegrees/",
    },
    "ucla": {
        "name": "UCLA",
        "landing_url": "https://admission.universityofcalifornia.edu/campuses-majors/ucla/",
        "major_url": "https://admission.ucla.edu/apply/majors",
    },
    "ucm": {
        "name": "UC Merced",
        "landing_url": "https://admission.universityofcalifornia.edu/campuses-majors/merced/",
        "major_url": "https://www.ucmerced.edu/academics-undergraduate-majors-minors",
    },
    "ucr": {
        "name": "UC Riverside",
        "landing_url": "https://admission.universityofcalifornia.edu/campuses-majors/riverside/",
        "major_url": "https://www.ucr.edu/academics/undergraduate-majors",
    },
    "ucsd": {
        "name": "UC San Diego",
        "landing_url": "https://admission.universityofcalifornia.edu/campuses-majors/san-diego/",
        "major_url": "https://students.ucsd.edu/academics/advising/majors-minors/undergraduate-majors.html",
    },
    "ucsb": {
        "name": "UC Santa Barbara",
        "landing_url": "https://admission.universityofcalifornia.edu/campuses-majors/santa-barbara/",
        "major_url": "https://www.ucsb.edu/academics/undergraduate",
    },
    "ucsc": {
        "name": "UC Santa Cruz",
        "landing_url": "https://admission.universityofcalifornia.edu/campuses-majors/santa-cruz/",
        "major_url": "https://admissions.sa.ucsc.edu/majors/",
    },
}

UC_CODE_BY_ASSIST = {
    "UCB": "ucb",
    "UCD": "ucd",
    "UCI": "uci",
    "UCLA": "ucla",
    "UCM": "ucm",
    "UCR": "ucr",
    "UCSD": "ucsd",
    "UCSB": "ucsb",
    "UCSC": "ucsc",
}

RAW_DIR = Path(__file__).resolve().parents[1] / "raw"
MAJORS_RAW_PATH = RAW_DIR / "uc_majors.json"
ARTIC_RAW_PATH = RAW_DIR / "lpc_uc_articulations.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) PathwayIQDataHarvester/1.0",
    "Accept": "text/html,application/json;q=0.9,*/*;q=0.8",
}

MAJOR_BLACKLIST = {
    "minor",
    "certificate",
    "graduate",
    "master",
    "doctor",
    "phd",
    "school of",
    "department of",
    "college of",
    "admissions",
    "contact",
    "apply",
    "campus",
}


def _slug(text: str) -> str:
    return (
        text.lower()
        .replace("&", "and")
        .replace("/", "-")
        .replace(",", "")
        .replace(".", "")
        .replace("'", "")
        .replace("(", "")
        .replace(")", "")
        .replace(" ", "-")
    )


def _normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", unescape(text)).strip()


def _strip_tags(text: str) -> str:
    no_tags = re.sub(r"<[^>]+>", " ", text)
    return _normalize_whitespace(no_tags)


def _anchor_candidates(html: str) -> Iterable[tuple[str, str]]:
    pattern = re.compile(r"<a[^>]*href=[\"']([^\"']+)[\"'][^>]*>([\s\S]*?)</a>", re.IGNORECASE)
    for href, label_html in pattern.findall(html):
        label = _strip_tags(label_html)
        if label:
            yield label, href


def _looks_like_major(label: str, href: str) -> bool:
    text = label.lower()
    if len(label) < 3 or len(label) > 120:
        return False
    if any(token in text for token in MAJOR_BLACKLIST):
        return False

    major_keywords = [
        "major",
        "b.a",
        "b.s",
        "bachelor",
        "science",
        "engineering",
        "studies",
        "economics",
        "biology",
        "psychology",
        "mathematics",
        "history",
        "computer",
        "data",
        "physics",
        "chemistry",
        "business",
        "sociology",
        "english",
        "philosophy",
    ]

    href_lower = href.lower()
    if "major" in href_lower or "undergraduate" in href_lower or "degree" in href_lower:
        return True
    return any(keyword in text for keyword in major_keywords)


def _dedupe_names(names: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for name in names:
        normalized = _normalize_whitespace(name)
        key = normalized.lower()
        if not normalized or key in seen:
            continue
        seen.add(key)
        output.append(normalized)
    return output


def _discover_major_urls_from_landing(html: str) -> list[str]:
    urls: list[str] = []
    for label, href in _anchor_candidates(html):
        label_lower = label.lower()
        href_lower = href.lower()
        if "major" not in label_lower and "major" not in href_lower:
            continue
        if href_lower.startswith("mailto:") or href_lower.startswith("#"):
            continue
        urls.append(href)
    return _dedupe_names(urls)


def _candidate_major_source_urls(campus: dict[str, str], landing_html: str) -> list[str]:
    discovered = _discover_major_urls_from_landing(landing_html)
    preferred = []
    if campus.get("major_url"):
        preferred.append(campus["major_url"])
    preferred.extend(discovered)

    normalized: list[str] = []
    for href in preferred:
        value = href.strip()
        if value.startswith("//"):
            value = f"https:{value}"
        elif value.startswith("/"):
            value = f"https://admission.universityofcalifornia.edu{value}"
        if value and value not in normalized:
            normalized.append(value)
    return normalized


def fetch_uc_majors(policy_year: str) -> list[dict]:
    rows: list[dict] = []

    with httpx.Client(timeout=45.0, follow_redirects=True, headers=HEADERS) as client:
        for school_id, campus in UC_CAMPUSES.items():
            landing_url = campus["landing_url"]
            landing_response = client.get(landing_url)
            landing_response.raise_for_status()
            source_urls = _candidate_major_source_urls(campus, landing_response.text)

            unique_labels: list[str] = []
            used_url = campus.get("major_url") or landing_url
            for url in source_urls:
                try:
                    response = client.get(url)
                    if response.status_code >= 400:
                        continue
                    html = response.text
                    labels = [label for label, href in _anchor_candidates(html) if _looks_like_major(label, href)]
                    candidate_labels = _dedupe_names(labels)
                    if len(candidate_labels) >= 10:
                        unique_labels = candidate_labels
                        used_url = str(response.url)
                        break
                except Exception:
                    continue

            if not unique_labels:
                continue

            for label in unique_labels:
                major_key = _slug(label)
                rows.append(
                    {
                        "school_id": school_id,
                        "major_key": major_key,
                        "major_name": label,
                        "department": "Undergraduate Programs",
                        "total_units": 0,
                        "source_name": f"{campus['name']} Undergraduate Majors",
                        "source_url": used_url,
                        "policy_year": policy_year,
                    }
                )

    # final de-dup by (school_id, major_key)
    deduped: dict[tuple[str, str], dict] = {}
    for row in rows:
        deduped[(row["school_id"], row["major_key"])] = row

    return sorted(deduped.values(), key=lambda row: (row["school_id"], row["major_name"]))


def _find_latest_academic_year_id(client: httpx.Client, preferred_fall_year: int | None) -> int:
    years = client.get("https://assist.org/api/AcademicYears").json()
    if not isinstance(years, list) or not years:
        raise ValueError("ASSIST academic years response is empty")

    sorted_years = sorted(
        [row for row in years if isinstance(row, dict) and isinstance(row.get("FallYear"), int)],
        key=lambda row: int(row["FallYear"]),
        reverse=True,
    )
    if not sorted_years:
        raise ValueError("ASSIST academic years response missing valid FallYear values")

    if preferred_fall_year is not None:
        for row in sorted_years:
            if int(row["FallYear"]) == preferred_fall_year:
                return int(row["Id"])

    return int(sorted_years[0]["Id"])


def _institution_maps(client: httpx.Client) -> tuple[int, dict[int, str]]:
    data = client.get("https://assist.org/api/institutions").json()
    if not isinstance(data, list):
        raise ValueError("ASSIST institutions response is invalid")

    lpc_id: int | None = None
    uc_ids: dict[int, str] = {}

    for row in data:
        if not isinstance(row, dict):
            continue
        institution_id = row.get("id")
        code = str(row.get("code", "")).strip().upper()
        names = row.get("names", [])
        first_name = ""
        if isinstance(names, list) and names and isinstance(names[0], dict):
            first_name = str(names[0].get("name", ""))

        if code == "POSITAS" or "las positas" in first_name.lower():
            lpc_id = int(institution_id)

        uc_school_id = UC_CODE_BY_ASSIST.get(code)
        if uc_school_id:
            uc_ids[int(institution_id)] = uc_school_id

    if lpc_id is None:
        raise ValueError("Could not find Las Positas College in ASSIST institutions")

    missing = sorted(set(UC_CODE_BY_ASSIST.values()) - set(uc_ids.values()))
    if missing:
        raise ValueError(f"Missing UC campuses in ASSIST institutions payload: {', '.join(missing)}")

    return lpc_id, uc_ids


def fetch_lpc_uc_major_agreements(policy_year: str, preferred_fall_year: int | None = None) -> list[dict]:
    rows: list[dict] = []
    seen: set[tuple[str, str, str, str, str]] = set()

    def _get_json_with_retry(client: httpx.Client, url: str, params: dict, attempts: int = 8) -> dict:
        last_error: Exception | None = None
        for attempt in range(attempts):
            try:
                response = client.get(url, params=params)
                if response.status_code == 429:
                    wait_seconds = min(60, 2 ** attempt)
                    time.sleep(wait_seconds)
                    continue
                response.raise_for_status()
                payload = response.json()
                if isinstance(payload, dict):
                    return payload
                return {}
            except Exception as exc:
                last_error = exc
                wait_seconds = min(60, 2 ** attempt)
                time.sleep(wait_seconds)

        if last_error:
            raise last_error
        raise RuntimeError(f"Failed to fetch JSON from {url}")

    def _course_code(prefix: str | None, number: str | None) -> str | None:
        if not prefix or not number:
            return None
        left = re.sub(r"\s+", "", str(prefix).upper())
        right = re.sub(r"\s+", "", str(number).upper())
        if not left or not right:
            return None
        return f"{left}{right}"

    def _collect_sending_course_codes(node: dict) -> set[str]:
        codes: set[str] = set()
        if not isinstance(node, dict):
            return codes

        if "prefix" in node and "courseNumber" in node:
            code = _course_code(node.get("prefix"), node.get("courseNumber"))
            if code:
                codes.add(code)

        for child in node.get("items", []) if isinstance(node.get("items"), list) else []:
            if isinstance(child, dict):
                codes.update(_collect_sending_course_codes(child))

        course_obj = node.get("course")
        if isinstance(course_obj, dict):
            code = _course_code(course_obj.get("prefix"), course_obj.get("courseNumber"))
            if code:
                codes.add(code)

        return codes

    with httpx.Client(timeout=45.0, follow_redirects=True, headers=HEADERS) as client:
        academic_year_id = _find_latest_academic_year_id(client, preferred_fall_year)
        lpc_id, uc_ids = _institution_maps(client)

        for receiving_id, uc_school_id in sorted(uc_ids.items(), key=lambda kv: kv[1]):
            params = {
                "receivingInstitutionId": receiving_id,
                "sendingInstitutionId": lpc_id,
                "academicYearId": academic_year_id,
                "categoryCode": "major",
            }
            payload = _get_json_with_retry(client, "https://assist.org/api/agreements", params=params)
            all_reports = payload.get("allReports", []) if isinstance(payload, dict) else []
            all_majors_key = None
            if isinstance(all_reports, list):
                for report in all_reports:
                    if not isinstance(report, dict):
                        continue
                    key_value = str(report.get("key", "")).strip()
                    label_value = str(report.get("label", "")).strip().lower()
                    if "allmajors" in key_value.lower() or "all majors" in label_value:
                        all_majors_key = key_value
                        break

            if not all_majors_key:
                continue

            detail_url = "https://assist.org/api/articulation/Agreements"
            detail_payload = _get_json_with_retry(client, detail_url, params={"Key": all_majors_key})
            detail_result = detail_payload.get("result", {}) if isinstance(detail_payload, dict) else {}

            articulation_rows = []
            raw_articulations = detail_result.get("articulations")
            if isinstance(raw_articulations, str) and raw_articulations.strip().startswith("["):
                try:
                    parsed_rows = json.loads(raw_articulations)
                    if isinstance(parsed_rows, list):
                        articulation_rows = [row for row in parsed_rows if isinstance(row, dict)]
                except json.JSONDecodeError:
                    articulation_rows = []

            for articulation in articulation_rows:
                template_cell_id = str(articulation.get("templateCellId") or "unknown").strip()
                articulation_obj = articulation.get("articulation", {})
                if not isinstance(articulation_obj, dict):
                    continue

                sending = articulation_obj.get("sendingArticulation", {})
                sending_codes = _collect_sending_course_codes(sending if isinstance(sending, dict) else {})
                if not sending_codes:
                    continue

                course_obj = articulation_obj.get("course", {})
                pathways = course_obj.get("pathways", []) if isinstance(course_obj, dict) else []

                mapped_pathways = []
                if isinstance(pathways, list):
                    for pathway in pathways:
                        if not isinstance(pathway, dict):
                            continue
                        major_name = _normalize_whitespace(str(pathway.get("pathwayName") or pathway.get("pathwayCode") or ""))
                        if not major_name:
                            continue
                        major_key = _slug(major_name)
                        major_id = f"{uc_school_id}-{major_key}"
                        expectation_id = str(pathway.get("expectationId") or "0").strip()
                        requirement_id = f"EXPECTATION::{major_key}::{expectation_id}"
                        mapped_pathways.append((major_name, major_id, requirement_id))

                if not mapped_pathways:
                    mapped_pathways = [
                        (
                            "All Majors",
                            f"{uc_school_id}-all-majors",
                            f"TEMPLATE::{template_cell_id}",
                        )
                    ]

                for cc_course_id in sorted(sending_codes):
                    for major_name, major_id, requirement_id in mapped_pathways:
                        key = ("lpc", uc_school_id, major_id, cc_course_id, requirement_id)
                        if key in seen:
                            continue
                        seen.add(key)
                        rows.append(
                            {
                                "cc_id": "lpc",
                                "university_id": uc_school_id,
                                "major_id": major_id,
                                "cc_course_id": cc_course_id,
                                "satisfies_requirement_id": requirement_id,
                                "source_name": "ASSIST.org Major Agreement",
                                "source_url": f"https://assist.org/transfer/report/{all_majors_key}",
                                "policy_year": policy_year,
                                "major_name": major_name,
                                "agreement_label": "All Majors",
                                "agreement_key": all_majors_key,
                            }
                        )

    if not rows:
        raise ValueError("No LPC->UC major agreements were retrieved from ASSIST")

    coverage = {row["university_id"] for row in rows}
    missing_ucs = sorted(set(UC_CAMPUSES.keys()) - coverage)
    if missing_ucs:
        raise ValueError(f"Missing LPC agreement coverage for: {', '.join(missing_ucs)}")

    return sorted(rows, key=lambda row: (row["university_id"], row["agreement_label"]))


def _major_rows_from_assist_agreements(agreements: list[dict], policy_year: str) -> list[dict]:
    rows: list[dict] = []
    for row in agreements:
        major_id = str(row.get("major_id", "")).strip().lower()
        if "-" not in major_id:
            continue
        school_id, major_key = major_id.split("-", 1)
        major_name = str(row.get("major_name") or row.get("agreement_label") or major_key).strip()
        rows.append(
            {
                "school_id": school_id,
                "major_key": major_key,
                "major_name": major_name,
                "department": "Transfer Major Agreement",
                "total_units": 0,
                "source_name": "ASSIST.org Major Agreement",
                "source_url": row.get("source_url"),
                "policy_year": policy_year,
            }
        )
    deduped: dict[tuple[str, str], dict] = {}
    for row in rows:
        deduped[(row["school_id"], row["major_key"])] = row
    return sorted(deduped.values(), key=lambda row: (row["school_id"], row["major_name"]))


def write_json(path: Path, data: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Harvest UC majors and LPC->UC ASSIST major agreements")
    parser.add_argument("--policy-year", default=f"AY-{datetime.now().year}-{str(datetime.now().year + 1)[-2:]}")
    parser.add_argument("--assist-fall-year", type=int, default=None)
    parser.add_argument("--skip-uc", action="store_true")
    parser.add_argument("--skip-assist", action="store_true")
    args = parser.parse_args()

    articulations: list[dict] = []
    if not args.skip_assist:
        articulations = fetch_lpc_uc_major_agreements(
            policy_year=args.policy_year,
            preferred_fall_year=args.assist_fall_year,
        )
        write_json(ARTIC_RAW_PATH, articulations)
        print(f"Wrote {ARTIC_RAW_PATH} ({len(articulations)} rows)")

    if not args.skip_uc:
        uc_majors = fetch_uc_majors(policy_year=args.policy_year)

        if articulations:
            assist_majors = _major_rows_from_assist_agreements(articulations, policy_year=args.policy_year)
            merged: dict[tuple[str, str], dict] = {
                (row["school_id"], row["major_key"]): row for row in uc_majors
            }
            for row in assist_majors:
                merged.setdefault((row["school_id"], row["major_key"]), row)
            uc_majors = sorted(merged.values(), key=lambda row: (row["school_id"], row["major_name"]))

        by_school: dict[str, int] = {school_id: 0 for school_id in UC_CAMPUSES}
        for row in uc_majors:
            by_school[row["school_id"]] = by_school.get(row["school_id"], 0) + 1
        missing = [school_id for school_id, count in by_school.items() if count == 0]
        if missing:
            raise ValueError(
                "Major coverage still missing after merge for campuses: " + ", ".join(sorted(missing))
            )

        write_json(MAJORS_RAW_PATH, uc_majors)
        print(f"Wrote {MAJORS_RAW_PATH} ({len(uc_majors)} rows)")


if __name__ == "__main__":
    main()
