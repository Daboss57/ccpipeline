from __future__ import annotations

from app.data.repository import Repository
from app.models import (
    CreditResolveRequest,
    CreditResolveResponse,
    PendingCreditScenario,
    ResolvedCreditItem,
    ResolutionWarning,
    ResolvedCreditMap,
    Severity,
    SourceCitation,
)

AP_EXAMS_SUPPORTED = {
    "AP Art History",
    "AP Biology",
    "AP Calculus AB",
    "AP Calculus BC",
    "AP Chemistry",
    "AP Chinese Language",
    "AP Computer Science A",
    "AP Computer Science Principles",
    "AP English Language",
    "AP English Literature",
    "AP Environmental Science",
    "AP European History",
    "AP French Language",
    "AP German Language",
    "AP Government & Politics (US)",
    "AP Government & Politics (Comparative)",
    "AP Human Geography",
    "AP Italian Language",
    "AP Japanese Language",
    "AP Latin",
    "AP Macroeconomics",
    "AP Microeconomics",
    "AP Music Theory",
    "AP Physics 1",
    "AP Physics 2",
    "AP Physics C: E&M",
    "AP Physics C: Mechanics",
    "AP Psychology",
    "AP Research",
    "AP Seminar",
    "AP Spanish Language",
    "AP Spanish Literature",
    "AP Statistics",
    "AP Studio Art: 2D",
    "AP Studio Art: 3D",
    "AP Studio Art: Drawing",
    "AP US History",
    "AP World History",
}

AP_GE_AREA_FALLBACK = {
    "AP Biology": ["5"],
    "AP Chemistry": ["5"],
    "AP Environmental Science": ["5"],
    "AP Physics 1": ["5"],
    "AP Physics 2": ["5"],
    "AP Physics C: E&M": ["5"],
    "AP Physics C: Mechanics": ["5"],
    "AP Calculus AB": ["2"],
    "AP Calculus BC": ["2"],
    "AP Statistics": ["2"],
    "AP Computer Science A": ["2"],
    "AP Computer Science Principles": ["2"],
    "AP English Language": ["1"],
    "AP English Literature": ["1"],
    "AP French Language": ["6"],
    "AP German Language": ["6"],
    "AP Chinese Language": ["6"],
    "AP Italian Language": ["6"],
    "AP Japanese Language": ["6"],
    "AP Latin": ["6"],
    "AP Spanish Language": ["6"],
    "AP Spanish Literature": ["6"],
    "AP Art History": ["3"],
    "AP Music Theory": ["3"],
    "AP Studio Art: 2D": ["3"],
    "AP Studio Art: 3D": ["3"],
    "AP Studio Art: Drawing": ["3"],
    "AP European History": ["4"],
    "AP Government & Politics (US)": ["4"],
    "AP Government & Politics (Comparative)": ["4"],
    "AP Human Geography": ["4"],
    "AP Macroeconomics": ["4"],
    "AP Microeconomics": ["4"],
    "AP Psychology": ["4"],
    "AP US History": ["4"],
    "AP World History": ["4"],
    "AP Research": ["1"],
    "AP Seminar": ["1"],
}

AP_COURSE_FALLBACK = {
    "AP Calculus AB": ["MATH101", "MATH110"],
    "AP Calculus BC": ["MATH101", "MATH102", "MATH110", "MATH111"],
    "AP Computer Science A": ["CSE101"],
    "AP Statistics": ["STATS101"],
    "AP Biology": ["BIO101"],
    "AP Psychology": ["PSY101"],
}


def _fallback_exam_policy(repo: Repository, school_id: str, exam_type: str, exam_name: str) -> dict | None:
    if exam_type.upper() != "AP":
        return None

    school = repo.get_school(school_id)
    if not school or school.get("system") != "UC":
        return None

    if exam_name not in AP_EXAMS_SUPPORTED:
        return None

    return {
        "min_score": 3,
        "units_granted": 4,
        "courses_satisfied": AP_COURSE_FALLBACK.get(exam_name, []),
        "ge_areas_satisfied": AP_GE_AREA_FALLBACK.get(exam_name, []),
        "fallback": True,
    }


def resolve_credits(request: CreditResolveRequest, repo: Repository) -> CreditResolveResponse:
    satisfied_courses: set[str] = set()
    satisfied_ge_areas: set[str] = set()
    units_waived = 0
    pending_exam_names: list[str] = []
    condition_notes: list[str] = []
    pending_scenarios: list[PendingCreditScenario] = []
    resolved_items: list[ResolvedCreditItem] = []
    warnings: list[ResolutionWarning] = []

    school_id = request.student_profile.target_school_id

    for exam in request.exam_credits:
        policy = repo.get_exam_policy(school_id, exam.exam_type, exam.exam_name)
        used_fallback = False
        if not policy:
            policy = _fallback_exam_policy(repo, school_id, exam.exam_type, exam.exam_name)
            used_fallback = policy is not None

        if not policy:
            warnings.append(
                ResolutionWarning(
                    code="EXAM_POLICY_NOT_FOUND",
                    message=f"No policy found for {exam.exam_type} {exam.exam_name} at {school_id}",
                    severity=Severity.WARNING,
                )
            )
            continue

        if used_fallback:
            warnings.append(
                ResolutionWarning(
                    code="EXAM_POLICY_FALLBACK",
                    message=(
                        f"Used fallback AP policy for {exam.exam_name} at {school_id}; "
                        "verify official campus policy for final advising."
                    ),
                    severity=Severity.INFO,
                )
            )

        courses = list(policy["courses_satisfied"])
        ge_areas = list(policy["ge_areas_satisfied"])
        source_name = str(policy.get("source_name", "PathwayIQ Policy Dataset"))
        source_url = policy.get("source_url")
        source_policy_year = str(policy.get("policy_year", repo.policy_version))

        resolved_items.append(
            ResolvedCreditItem(
                exam_type=exam.exam_type,
                exam_name=exam.exam_name,
                status=exam.status,
                score=exam.score,
                min_score=int(policy["min_score"]),
                units_granted=int(policy["units_granted"]),
                courses_satisfied=courses,
                ge_areas_satisfied=ge_areas,
                source=SourceCitation(
                    source_name=source_name,
                    source_url=source_url,
                    policy_year=source_policy_year,
                ),
            )
        )

        if exam.status == "pending":
            pending_exam_names.append(exam.exam_name)
            condition_notes.append(
                f"Assuming credit for {exam.exam_name}; if score is below {policy['min_score']}, extra coursework is required."
            )
            pending_scenarios.append(
                PendingCreditScenario(
                    exam_name=exam.exam_name,
                    added_courses_if_no_credit=courses,
                    note=f"Minimum score for credit is {policy['min_score']}.",
                )
            )
            satisfied_courses.update(courses)
            satisfied_ge_areas.update(ge_areas)
            units_waived += int(policy["units_granted"])
            continue

        if exam.score is None:
            warnings.append(
                ResolutionWarning(
                    code="MISSING_EXAM_SCORE",
                    message=f"Missing score for {exam.exam_name}; skipped credit resolution.",
                    severity=Severity.WARNING,
                )
            )
            continue

        if exam.score >= int(policy["min_score"]):
            satisfied_courses.update(courses)
            satisfied_ge_areas.update(ge_areas)
            units_waived += int(policy["units_granted"])
        else:
            warnings.append(
                ResolutionWarning(
                    code="EXAM_BELOW_THRESHOLD",
                    message=(
                        f"{exam.exam_name} score {exam.score} does not meet "
                        f"minimum score {policy['min_score']} for {school_id}."
                    ),
                    severity=Severity.INFO,
                )
            )

    for dual in request.dual_enrollments:
        if dual.grade and dual.grade.upper() in {"A", "A-", "B+", "B", "B-", "C+", "C"}:
            satisfied_courses.add(dual.course_id)
        else:
            warnings.append(
                ResolutionWarning(
                    code="DUAL_ENROLLMENT_GRADE_UNVERIFIED",
                    message=f"Dual enrollment {dual.course_id} not counted due to missing/low grade.",
                    severity=Severity.INFO,
                )
            )

    resolved_map = ResolvedCreditMap(
        satisfied_courses=sorted(satisfied_courses),
        satisfied_ge_areas=sorted(satisfied_ge_areas),
        units_waived=units_waived,
        pending_exam_names=pending_exam_names,
        condition_notes=condition_notes,
    )

    return CreditResolveResponse(
        resolved_credit_map=resolved_map,
        resolved_items=resolved_items,
        pending_credit_scenarios=pending_scenarios,
        warnings=warnings,
        policy_version=repo.policy_version,
    )
