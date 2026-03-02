from __future__ import annotations

from dataclasses import dataclass

from app.data.repository import Repository
from app.models import (
    AdmissionChecklist,
    CriticalPathItem,
    Milestone,
    PlanGenerateRequest,
    PlannedCourse,
    PlanResult,
    PlanTerm,
    PlanWarning,
    Severity,
    SourceCitation,
)

SEASON_ORDER = {
    "semester": ["Spring", "Summer", "Fall"],
    "quarter": ["Winter", "Spring", "Summer", "Fall"],
}


@dataclass
class RequirementNode:
    requirement_id: str
    course_id: str
    course_name: str
    units: int
    term_offerings: list[str]
    course_type: str = "major_req"
    justification: str = "Required for target pathway"
    source: SourceCitation | None = None
    articulated_cc_courses: list[str] | None = None


def _parse_term(term_id: str) -> tuple[int, str]:
    year_text, season = term_id.split("-", 1)
    return int(year_text), season.capitalize()


def _term_id(year: int, season: str) -> str:
    return f"{year}-{season}"


def _next_term(year: int, season: str, term_system: str) -> tuple[int, str]:
    seasons = SEASON_ORDER[term_system]
    idx = seasons.index(season)
    if idx == len(seasons) - 1:
        return year + 1, seasons[0]
    return year, seasons[idx + 1]


def generate_term_sequence(
    start_term: str,
    term_system: str,
    target_term: str | None,
    max_terms: int = 16,
) -> list[str]:
    year, season = _parse_term(start_term)
    if season not in SEASON_ORDER[term_system]:
        season = SEASON_ORDER[term_system][0]

    terms = []
    target_tuple = _parse_term(target_term) if target_term else None
    for _ in range(max_terms):
        terms.append(_term_id(year, season))
        if target_tuple and (year, season) == target_tuple:
            break
        year, season = _next_term(year, season, term_system)
    return terms


def _build_prereq_map(repo: Repository, school_id: str) -> dict[str, set[str]]:
    prereq_map: dict[str, set[str]] = {}
    for prereq in repo.get_prerequisites(school_id):
        prereq_map.setdefault(prereq["course_id"], set()).add(prereq["prerequisite_course_id"])
    return prereq_map


def _build_critical_path(remaining_courses: set[str], prereq_map: dict[str, set[str]]) -> list[CriticalPathItem]:
    memo: dict[str, list[str]] = {}

    def dfs(course_id: str) -> list[str]:
        if course_id in memo:
            return memo[course_id]
        prereqs = prereq_map.get(course_id, set())
        if not prereqs:
            memo[course_id] = [course_id]
            return memo[course_id]

        best_chain: list[str] = []
        for prereq in prereqs:
            chain = dfs(prereq)
            if len(chain) > len(best_chain):
                best_chain = chain
        memo[course_id] = best_chain + [course_id]
        return memo[course_id]

    longest: list[str] = []
    for course in sorted(remaining_courses):
        chain = dfs(course)
        if len(chain) > len(longest):
            longest = chain

    return [CriticalPathItem(course_id=course_id, note="Critical prerequisite sequence") for course_id in longest]


def _build_supplemental_requirements(
    request: PlanGenerateRequest,
    repo: Repository,
) -> list[RequirementNode]:
    supplemental: list[RequirementNode] = []

    baseline = [
        ("ENGL101", "English Composition I", 4, "ge", "General education English writing requirement"),
        ("ENGL102", "English Composition II", 4, "ge", "General education advanced composition requirement"),
        ("PE101", "Physical Education / Wellness", 1, "elective", "General education wellness / PE requirement"),
    ]
    for idx, (course_id, course_name, units, course_type, justification) in enumerate(baseline, start=1):
        supplemental.append(
            RequirementNode(
                requirement_id=f"GEN-{idx}",
                course_id=course_id,
                course_name=course_name,
                units=units,
                term_offerings=[],
                course_type=course_type,
                justification=justification,
                source=SourceCitation(
                    source_name="PathwayIQ Supplemental Rules",
                    source_url=None,
                    policy_year=repo.policy_version,
                ),
            )
        )

    if request.student_profile.pathway_type.value == "cc_transfer":
        cc_id = request.student_profile.transfer_from_cc_id or ""
        satisfied_ge_areas = set(request.resolved_credit_map.satisfied_ge_areas)
        for row in repo.list_igetc_courses(cc_id):
            area = row["igetc_area"]
            if area in satisfied_ge_areas:
                continue
            supplemental.append(
                RequirementNode(
                    requirement_id=f"IGETC-{cc_id}-{area}",
                    course_id=row["course_id"],
                    course_name=row["course_name"],
                    units=int(row.get("units", 3)),
                    term_offerings=[],
                    course_type="ge",
                    justification=f"Required to complete IGETC Area {area}",
                    source=SourceCitation(
                        source_name="IGETC Course List",
                        source_url=row.get("source_url"),
                        policy_year=str(row.get("policy_year", repo.policy_version)),
                    ),
                )
            )

    return supplemental


def generate_plan(request: PlanGenerateRequest, repo: Repository, explanation_markdown: str) -> PlanResult:
    school = repo.get_school(request.student_profile.target_school_id)
    if not school:
        raise ValueError(f"Unknown school: {request.student_profile.target_school_id}")

    term_system = school["term_system"]
    major_requirements = repo.get_major_requirements(request.student_profile.target_major_id)

    warnings: list[PlanWarning] = []

    if not major_requirements:
        warnings.append(
            PlanWarning(
                code="NO_REQUIREMENTS_DATA",
                message=(
                    f"No course requirements have been mapped for \"{request.student_profile.target_major_id}\". "
                    "The plan will include only GE/IGETC courses. "
                    "Choose a major marked with \u2713 for a full plan."
                ),
                severity=Severity.WARNING,
            )
        )

    requirements = [
        RequirementNode(
            requirement_id=req["requirement_id"],
            course_id=req["course_id"],
            course_name=req["course_name"],
            units=int(req["units"]),
            term_offerings=(
                repo.get_course_offered_terms(request.student_profile.target_school_id, req["course_id"])
                or list(req.get("term_offerings", []))
            ),
            course_type="major_req",
            justification="Required major preparation course",
            source=SourceCitation(
                source_name=str(req.get("source_name", "PathwayIQ Requirement Catalog")),
                source_url=req.get("source_url"),
                policy_year=str(req.get("policy_year", repo.policy_version)),
            ),
        )
        for req in major_requirements
    ]

    transfer_cc_id = request.student_profile.transfer_from_cc_id or ""
    major_articulation_rows = []
    articulated_major_cc_courses: set[str] = set()
    if request.student_profile.pathway_type.value == "cc_transfer" and transfer_cc_id:
        major_articulation_rows = repo.list_assist_articulations(
            cc_id=transfer_cc_id,
            university_id=request.student_profile.target_school_id,
            major_id=request.student_profile.target_major_id,
        )
        articulated_major_cc_courses = {
            str(row.get("cc_course_id", "")).strip()
            for row in major_articulation_rows
            if str(row.get("cc_course_id", "")).strip()
        }
        for requirement in requirements:
            requirement.articulated_cc_courses = repo.get_articulated_cc_courses_for_requirement(
                cc_id=transfer_cc_id,
                university_id=request.student_profile.target_school_id,
                major_id=request.student_profile.target_major_id,
                requirement_id=requirement.requirement_id,
            )

    existing_course_ids = {req.course_id for req in requirements}
    for supplemental in _build_supplemental_requirements(request, repo):
        offered_terms = repo.get_course_offered_terms(request.student_profile.target_school_id, supplemental.course_id)
        if offered_terms:
            supplemental.term_offerings = offered_terms
        if supplemental.course_id in existing_course_ids:
            continue
        requirements.append(supplemental)
        existing_course_ids.add(supplemental.course_id)

    prereq_map = _build_prereq_map(repo, request.student_profile.target_school_id)
    satisfied_input = set(request.resolved_credit_map.satisfied_courses)
    satisfied = set(satisfied_input)

    effective_satisfied_major_courses: set[str] = set()
    unscheduled: dict[str, RequirementNode] = {}
    for req in requirements:
        direct_match = req.course_id in satisfied_input
        articulated_match = bool(req.articulated_cc_courses and set(req.articulated_cc_courses).intersection(satisfied_input))
        if direct_match or articulated_match:
            effective_satisfied_major_courses.add(req.course_id)
            continue
        unscheduled[req.requirement_id] = req

    satisfied.update(effective_satisfied_major_courses)

    terms: list[PlanTerm] = []

    if request.student_profile.pathway_type.value == "cc_transfer" and transfer_cc_id:
        cc_prefix = f"{transfer_cc_id.upper()}-"
        input_cc_courses = {
            course_id
            for course_id in satisfied_input
            if course_id.upper().startswith(cc_prefix)
        }
        unmatched_cc_courses = sorted(input_cc_courses - articulated_major_cc_courses)
        if unmatched_cc_courses:
            sample = ", ".join(unmatched_cc_courses[:5])
            more = "" if len(unmatched_cc_courses) <= 5 else f" (+{len(unmatched_cc_courses) - 5} more)"
            warnings.append(
                PlanWarning(
                    code="ARTICULATION_GAP",
                    message=(
                        "Some LPC courses were not counted toward the selected UC major because no articulation was found: "
                        f"{sample}{more}."
                    ),
                    severity=Severity.WARNING,
                )
            )

        if not major_articulation_rows:
            warnings.append(
                PlanWarning(
                    code="ARTICULATION_MAJOR_MISSING",
                    message="No articulation agreements were found for this CC→UC major combination.",
                    severity=Severity.WARNING,
                )
            )

    term_ids = generate_term_sequence(
        start_term=request.student_profile.start_term,
        term_system=term_system,
        target_term=request.student_profile.target_graduation_term,
    )

    for idx, term_id in enumerate(term_ids):
        year, season = _parse_term(term_id)
        is_blocked = term_id in request.planning_constraints.blocked_terms
        hs_active = idx < request.student_profile.hs_active_terms
        cap = request.planning_constraints.max_units_hs_active if hs_active else request.planning_constraints.max_units_regular
        completed_before_term = set(satisfied)
        completed_this_term: set[str] = set()

        term = PlanTerm(
            term_id=term_id,
            term_label=f"{season} {year}",
            campus_id=request.student_profile.target_school_id,
            courses=[],
            units=0,
            notes=[],
            hs_active=hs_active,
        )

        if is_blocked:
            term.notes.append("Term blocked by student preference")
            terms.append(term)
            continue

        available_ids = sorted(list(unscheduled.keys()))
        for requirement_id in available_ids:
            requirement = unscheduled[requirement_id]
            prereqs = prereq_map.get(requirement.course_id, set())
            if not prereqs.issubset(completed_before_term):
                continue

            if requirement.term_offerings and season not in requirement.term_offerings:
                continue

            if term.units + requirement.units > cap:
                continue

            term.courses.append(
                PlannedCourse(
                    requirement_id=requirement.requirement_id,
                    course_id=requirement.course_id,
                    course_name=requirement.course_name,
                    units=requirement.units,
                    course_type=requirement.course_type,
                    justification=requirement.justification,
                    source=requirement.source,
                )
            )
            term.units += requirement.units
            completed_this_term.add(requirement.course_id)
            del unscheduled[requirement_id]

        if not term.courses and not is_blocked:
            term.notes.append("No schedulable courses this term due to prerequisites or constraints")

        terms.append(term)
        satisfied.update(completed_this_term)
        if not unscheduled:
            break

    if unscheduled:
        warnings.append(
            PlanWarning(
                code="UNSCHEDULED_REQUIREMENTS",
                message=f"{len(unscheduled)} requirements remain unscheduled by current term horizon.",
                severity=Severity.WARNING,
            )
        )

    milestones: list[Milestone] = []
    unscheduled_major = [req for req in unscheduled.values() if req.course_type == "major_req"]
    if not unscheduled_major and terms:
        milestones.append(
            Milestone(
                milestone_id="major-prep-done",
                label="Major preparation complete",
                term_id=terms[-1].term_id,
                status="done",
            )
        )

    if request.student_profile.pathway_type.value == "cc_transfer":
        cc_id = request.student_profile.transfer_from_cc_id or ""
        igetc_rows = repo.list_igetc_courses(cc_id)
        required_areas = set(repo.list_igetc_areas(cc_id))

        area_by_course = {row["course_id"]: row["igetc_area"] for row in igetc_rows}
        scheduled_course_ids = {
            course.course_id
            for term in terms
            for course in term.courses
        }
        planned_areas = {area_by_course[course_id] for course_id in scheduled_course_ids if course_id in area_by_course}
        covered_areas = set(request.resolved_credit_map.satisfied_ge_areas) | planned_areas

        if required_areas and not required_areas.issubset(covered_areas):
            missing = sorted(required_areas - covered_areas)
            warnings.append(
                PlanWarning(
                    code="IGETC_INCOMPLETE",
                    message=f"Missing IGETC areas before transfer: {', '.join(missing)}",
                    severity=Severity.WARNING,
                )
            )
            milestones.append(
                Milestone(
                    milestone_id="igetc",
                    label="IGETC complete",
                    term_id=terms[-1].term_id if terms else request.student_profile.start_term,
                    status="pending",
                )
            )
        else:
            milestones.append(
                Milestone(
                    milestone_id="igetc",
                    label="IGETC complete",
                    term_id=terms[-1].term_id if terms else request.student_profile.start_term,
                    status="done",
                )
            )

    remaining = {req.course_id for req in unscheduled.values() if req.course_type == "major_req"}
    if not remaining:
        remaining = {
            req.course_id
            for req in requirements
            if req.course_type == "major_req"
            and req.course_id not in request.resolved_credit_map.satisfied_courses
        }
    critical_path = _build_critical_path(remaining, prereq_map)

    major_requirements_total = len([req for req in requirements if req.course_type == "major_req"])
    covered_major_ids = {
        req.course_id
        for req in requirements
        if req.course_type == "major_req" and req.requirement_id not in unscheduled
    }
    major_prep_coverage_pct = (
        round((len(covered_major_ids) / major_requirements_total) * 100, 1)
        if major_requirements_total
        else 100.0
    )

    planned_transfer_cc_units = 0
    if transfer_cc_id:
        cc_prefix = f"{transfer_cc_id.upper()}-"
        for term in terms:
            for course in term.courses:
                if course.course_id.upper().startswith(cc_prefix):
                    planned_transfer_cc_units += course.units

    igetc_status: str = "not_applicable"
    if request.student_profile.pathway_type.value == "cc_transfer":
        igetc_done = any(m.milestone_id == "igetc" and m.status == "done" for m in milestones)
        igetc_pending = any(m.milestone_id == "igetc" and m.status == "pending" for m in milestones)
        if igetc_done:
            igetc_status = "complete"
        elif igetc_pending:
            igetc_status = "in_progress"

    missing_blockers = sorted({warning.message for warning in warnings if warning.severity in {Severity.WARNING, Severity.ERROR}})

    checklist = AdmissionChecklist(
        major_prep_coverage_pct=major_prep_coverage_pct,
        transferable_units=int(request.resolved_credit_map.units_waived + planned_transfer_cc_units),
        igetc_status=igetc_status,
        missing_blockers=missing_blockers,
    )

    return PlanResult(
        target_school_id=request.student_profile.target_school_id,
        target_major_id=request.student_profile.target_major_id,
        term_system=term_system,
        planning_constraints=request.planning_constraints,
        generation_mode="deterministic",
        starting_satisfied_courses=sorted(satisfied),
        terms=terms,
        milestones=milestones,
        critical_path=critical_path,
        admission_checklist=checklist,
        warnings=warnings,
        policy_version=repo.policy_version,
        explanation_markdown=explanation_markdown,
    )
