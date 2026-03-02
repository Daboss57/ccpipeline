from __future__ import annotations

from app.data.repository import Repository
from app.models import PlanResult, ValidationIssue, ValidationReport, Severity


def validate_plan(plan: PlanResult, repo: Repository) -> ValidationReport:
    issues: list[ValidationIssue] = []
    missing_requirements: list[str] = []
    unit_overloads: list[str] = []

    school = repo.get_school(plan.target_school_id)
    if not school:
        issues.append(
            ValidationIssue(
                code="UNKNOWN_SCHOOL",
                message=f"Unknown school {plan.target_school_id}",
                severity=Severity.ERROR,
            )
        )
        return ValidationReport(valid=False, issues=issues)

    allowed_seasons = {
        "semester": {"Spring", "Summer", "Fall"},
        "quarter": {"Winter", "Spring", "Summer", "Fall"},
    }[plan.term_system]

    prereq_map: dict[str, set[str]] = {}
    for row in repo.get_prerequisites(plan.target_school_id):
        prereq_map.setdefault(row["course_id"], set()).add(row["prerequisite_course_id"])

    completed_courses: set[str] = set(plan.starting_satisfied_courses)

    for term in plan.terms:
        season = term.term_id.split("-", 1)[1]
        if season not in allowed_seasons:
            issues.append(
                ValidationIssue(
                    code="TERM_SYSTEM_MISMATCH",
                    message=f"{term.term_id} is invalid for {plan.term_system} calendar",
                    severity=Severity.ERROR,
                    term_id=term.term_id,
                )
            )

        cap = (
            plan.planning_constraints.max_units_hs_active
            if term.hs_active
            else plan.planning_constraints.max_units_regular
        )
        if term.units > cap:
            unit_overloads.append(term.term_id)
            issues.append(
                ValidationIssue(
                    code="UNIT_OVERLOAD",
                    message=f"{term.term_id} has {term.units} units over cap {cap}",
                    severity=Severity.ERROR,
                    term_id=term.term_id,
                )
            )

        for course in term.courses:
            offered_terms = repo.get_course_offered_terms(plan.target_school_id, course.course_id)
            if offered_terms and season not in offered_terms:
                issues.append(
                    ValidationIssue(
                        code="TERM_OFFERING_MISMATCH",
                        message=(
                            f"{course.course_id} is not offered in {season}; "
                            f"offered terms: {', '.join(offered_terms)}"
                        ),
                        severity=Severity.ERROR,
                        term_id=term.term_id,
                        course_id=course.course_id,
                    )
                )

            prereqs = prereq_map.get(course.course_id, set())
            if not prereqs.issubset(completed_courses):
                missing = sorted(prereqs - completed_courses)
                issues.append(
                    ValidationIssue(
                        code="PREREQ_VIOLATION",
                        message=f"{course.course_id} missing prereqs: {', '.join(missing)}",
                        severity=Severity.ERROR,
                        term_id=term.term_id,
                        course_id=course.course_id,
                    )
                )
            completed_courses.add(course.course_id)

    required_course_ids = {
        req["course_id"] for req in repo.get_major_requirements(plan.target_major_id)
    }
    unsatisfied = sorted(required_course_ids - completed_courses)
    if unsatisfied:
        missing_requirements.extend(unsatisfied)
        issues.append(
            ValidationIssue(
                code="MISSING_REQUIREMENTS",
                message=f"Plan is missing required courses: {', '.join(unsatisfied)}",
                severity=Severity.WARNING,
            )
        )

    valid = not any(issue.severity == Severity.ERROR for issue in issues)
    return ValidationReport(
        valid=valid,
        issues=issues,
        missing_requirements=missing_requirements,
        unit_overloads=unit_overloads,
    )
