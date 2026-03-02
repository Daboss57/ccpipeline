from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _student_profile() -> dict:
    return {
        "current_grade_level": "12th",
        "enrollment_status": "Dual enrollment",
        "pathway_type": "cc_transfer",
        "target_school_id": "ucsd",
        "target_major_id": "ucsd-computer-science",
        "start_term": "2026-Spring",
        "target_graduation_term": "2027-Fall",
        "transfer_from_cc_id": "lpc",
        "hs_active_terms": 1,
    }


def _constraints() -> dict:
    return {
        "max_units_regular": 16,
        "max_units_hs_active": 6,
        "blocked_terms": ["2026-Summer"],
        "priority": "balanced",
    }


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_metadata() -> None:
    schools = client.get("/v1/metadata/schools")
    assert schools.status_code == 200
    assert len(schools.json()) == 11

    majors = client.get("/v1/metadata/majors", params={"school_id": "ucsd"})
    assert majors.status_code == 200
    assert len(majors.json()) > 5

    courses = client.get("/v1/metadata/courses", params={"school_id": "ucsd"})
    assert courses.status_code == 200
    assert len(courses.json()) > 0

    offerings = client.get("/v1/metadata/course-offerings", params={"school_id": "ucsd", "season": "Winter"})
    assert offerings.status_code == 200
    assert len(offerings.json()) > 0

    articulations = client.get("/v1/metadata/articulations", params={"cc_id": "lpc", "university_id": "ucsd"})
    assert articulations.status_code == 200
    articulation_rows = articulations.json()
    assert len(articulation_rows) > 0
    sample = articulation_rows[0]

    options = client.get(
        "/v1/metadata/articulation-options",
        params={
            "cc_id": "lpc",
            "university_id": "ucsd",
            "major_id": sample["major_id"],
            "requirement_id": sample["satisfies_requirement_id"],
        },
    )
    assert options.status_code == 200
    assert len(options.json()) > 0


def test_credit_resolution_and_plan_generation() -> None:
    resolve_payload = {
        "student_profile": _student_profile(),
        "exam_credits": [
            {"exam_type": "AP", "exam_name": "AP Calculus BC", "score": 5, "status": "earned"},
            {"exam_type": "AP", "exam_name": "AP Computer Science A", "status": "pending"},
        ],
        "dual_enrollments": [{"school_id": "lpc", "course_id": "CHEM101", "grade": "A", "units": 4}],
    }
    resolve_resp = client.post("/v1/credits/resolve", json=resolve_payload)
    assert resolve_resp.status_code == 200
    resolve_data = resolve_resp.json()
    resolved_map = resolve_data["resolved_credit_map"]
    assert "MATH101" in resolved_map["satisfied_courses"]
    assert len(resolve_data.get("resolved_items", [])) > 0
    assert resolve_data["resolved_items"][0]["source"]["source_name"]
    assert resolve_data["resolved_items"][0]["source"]["policy_year"]

    plan_payload = {
        "student_profile": _student_profile(),
        "resolved_credit_map": resolved_map,
        "planning_constraints": _constraints(),
        "include_explanation": True,
    }
    plan_resp = client.post("/v1/plans/generate", json=plan_payload)
    assert plan_resp.status_code == 200
    bundle = plan_resp.json()
    assert bundle["plan"]["policy_version"] == "AY-2025-26"
    first_course = None
    for term in bundle["plan"]["terms"]:
        if term["courses"]:
            first_course = term["courses"][0]
            break
    assert first_course is not None
    assert "source" in first_course
    assert first_course["source"]["source_name"]
    assert first_course["source"]["policy_year"]
    assert "admission_checklist" in bundle["plan"]
    assert "major_prep_coverage_pct" in bundle["plan"]["admission_checklist"]
    assert bundle["validation"]["valid"]


def test_plan_rebuild_and_pdf_export() -> None:
    resolved_map = {
        "satisfied_courses": ["MATH101"],
        "satisfied_ge_areas": ["2"],
        "units_waived": 4,
        "pending_exam_names": [],
        "condition_notes": [],
    }

    generate_payload = {
        "student_profile": _student_profile(),
        "resolved_credit_map": resolved_map,
        "planning_constraints": _constraints(),
        "include_explanation": False,
    }

    generated = client.post("/v1/plans/generate", json=generate_payload).json()
    plan = generated["plan"]

    rebuild_payload = {
        "original_request": generate_payload,
        "original_plan": plan,
        "changes": {
            "removed_satisfied_courses": ["MATH101"],
            "blocked_terms": ["2027-Spring"],
        },
    }

    rebuild = client.post("/v1/plans/rebuild", json=rebuild_payload)
    assert rebuild.status_code == 200
    rebuild_data = rebuild.json()
    assert rebuild_data["diff_summary"]

    validate = client.post("/v1/plans/validate", json={"plan": rebuild_data["plan"]})
    assert validate.status_code == 200

    pdf_resp = client.post("/v1/export/pdf", json={"plan": rebuild_data["plan"]})
    assert pdf_resp.status_code == 200
    assert pdf_resp.headers["content-type"].startswith("application/pdf")
    assert len(pdf_resp.content) > 100


def test_igetc_tracker() -> None:
    payload = {
        "cc_id": "lpc",
        "satisfied_ge_areas": ["2", "5"],
        "planned_course_ids": ["LPC-SPAN1"],
    }
    response = client.post("/v1/igetc/tracker", json=payload)
    assert response.status_code == 200

    tracker = response.json()
    assert tracker["cc_id"] == "lpc"
    assert len(tracker["areas"]) == 7

    by_area = {row["area"]: row for row in tracker["areas"]}
    assert by_area["2"]["status"] == "satisfied"
    assert by_area["6"]["status"] == "planned"
    assert by_area["1"]["status"] == "missing"


def test_validate_rejects_term_offering_mismatch() -> None:
    resolved_map = {
        "satisfied_courses": ["MATH101"],
        "satisfied_ge_areas": ["2"],
        "units_waived": 4,
        "pending_exam_names": [],
        "condition_notes": [],
    }

    generate_payload = {
        "student_profile": _student_profile(),
        "resolved_credit_map": resolved_map,
        "planning_constraints": _constraints(),
        "include_explanation": False,
    }

    generated = client.post("/v1/plans/generate", json=generate_payload)
    assert generated.status_code == 200
    plan = generated.json()["plan"]

    metadata_resp = client.get("/v1/metadata/courses", params={"school_id": "ucsd"})
    assert metadata_resp.status_code == 200
    courses = metadata_resp.json()
    offered_by_course = {
        row["course_id"]: set(row.get("offered_terms", [])) for row in courses
    }

    target_term = None
    target_course = None
    target_disallowed_season = None
    allowed_seasons = ["Spring", "Summer", "Fall"]

    for term in plan["terms"]:
        for course in term["courses"]:
            offered = offered_by_course.get(course["course_id"], set())
            if not offered:
                continue
            disallowed = next((season for season in allowed_seasons if season not in offered), None)
            if disallowed:
                target_term = term
                target_course = course
                target_disallowed_season = disallowed
                break
        if target_term is not None:
            break

    assert target_term is not None
    assert target_course is not None
    assert target_disallowed_season is not None

    term_year = target_term["term_id"].split("-", 1)[0]
    target_term["term_id"] = f"{term_year}-{target_disallowed_season}"

    validate_resp = client.post("/v1/plans/validate", json={"plan": plan})
    assert validate_resp.status_code == 200
    validation = validate_resp.json()
    issue_codes = {issue["code"] for issue in validation["issues"]}
    assert "TERM_OFFERING_MISMATCH" in issue_codes
    assert not validation["valid"]


def test_cc_articulation_satisfies_major_requirement() -> None:
    resolved_map = {
        "satisfied_courses": ["LPC-MATH101"],
        "satisfied_ge_areas": ["2"],
        "units_waived": 4,
        "pending_exam_names": [],
        "condition_notes": [],
    }

    payload = {
        "student_profile": _student_profile(),
        "resolved_credit_map": resolved_map,
        "planning_constraints": _constraints(),
        "include_explanation": False,
    }

    plan_resp = client.post("/v1/plans/generate", json=payload)
    assert plan_resp.status_code == 200
    plan = plan_resp.json()["plan"]

    assert "MATH101" in plan["starting_satisfied_courses"]

    scheduled_courses = {
        course["course_id"]
        for term in plan["terms"]
        for course in term["courses"]
    }
    assert "MATH101" not in scheduled_courses


def test_articulation_gap_warning_and_swap_rebuild() -> None:
    payload = {
        "student_profile": _student_profile(),
        "resolved_credit_map": {
            "satisfied_courses": ["LPC-UNKNOWN999"],
            "satisfied_ge_areas": [],
            "units_waived": 0,
            "pending_exam_names": [],
            "condition_notes": [],
        },
        "planning_constraints": _constraints(),
        "include_explanation": False,
    }

    generated = client.post("/v1/plans/generate", json=payload)
    assert generated.status_code == 200
    generated_bundle = generated.json()
    plan = generated_bundle["plan"]

    warning_codes = {warning["code"] for warning in plan["warnings"]}
    assert "ARTICULATION_GAP" in warning_codes

    target_term = None
    target_course = None
    for term in plan["terms"]:
        for course in term["courses"]:
            if course["course_type"] == "major_req":
                target_term = term
                target_course = course
                break
        if target_term and target_course:
            break

    assert target_term is not None
    assert target_course is not None

    options_resp = client.get(
        "/v1/metadata/articulation-options",
        params={
            "cc_id": "lpc",
            "university_id": "ucsd",
            "major_id": "ucsd-computer-science",
            "requirement_id": target_course["requirement_id"],
        },
    )
    assert options_resp.status_code == 200
    options = options_resp.json()
    assert options

    swap_payload = {
        "original_request": payload,
        "original_plan": plan,
        "changes": {
            "removed_satisfied_courses": [],
            "blocked_terms": [],
            "swap_articulation_course": {
                "term_id": target_term["term_id"],
                "requirement_id": target_course["requirement_id"],
                "from_course_id": target_course["course_id"],
                "to_cc_course_id": options[0]["cc_course_id"],
            },
        },
    }
    rebuild_resp = client.post("/v1/plans/rebuild", json=swap_payload)
    assert rebuild_resp.status_code == 200
    rebuild_data = rebuild_resp.json()

    swapped_term = next(term for term in rebuild_data["plan"]["terms"] if term["term_id"] == target_term["term_id"])
    swapped_course = next(course for course in swapped_term["courses"] if course["requirement_id"] == target_course["requirement_id"])
    assert swapped_course["course_id"] == options[0]["cc_course_id"]
