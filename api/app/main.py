from __future__ import annotations

from io import BytesIO

from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from app.config import get_settings
from app.data.repository import Repository
from app.models import (
    ArticulationAgreement,
    ArticulationOption,
    CourseInventoryItem,
    CourseOfferingItem,
    CreditResolveRequest,
    CreditResolveResponse,
    IGETCAreaStatus,
    IGETCTrackerRequest,
    IGETCTrackerResponse,
    Major,
    PDFExportRequest,
    PlanWarning,
    PlanGenerateRequest,
    PlanRebuildRequest,
    PlanRebuildResponse,
    PlanValidationRequest,
    PolicyVersionResponse,
    School,
    SourceCitation,
    ValidationIssue,
    ValidationReport,
    Severity,
)
from app.services.credit_resolver import resolve_credits
from app.services.gemini import maybe_generate_explanation, maybe_generate_schedule_plan
from app.services.planner import generate_plan
from app.services.validator import validate_plan

settings = get_settings()
repo = Repository(settings.data_file)

app = FastAPI(title=settings.app_name, version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/v1/credits/resolve", response_model=CreditResolveResponse)
def credits_resolve(payload: CreditResolveRequest) -> CreditResolveResponse:
    return resolve_credits(payload, repo)


@app.post("/v1/plans/generate")
def plans_generate(payload: PlanGenerateRequest):
    try:
        deterministic_plan = generate_plan(payload, repo, explanation_markdown="")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    provisional_plan = deterministic_plan

    def _collect_validation_error_messages(validation_report: ValidationReport) -> list[str]:
        return [
            issue.message
            for issue in validation_report.issues
            if issue.severity == Severity.ERROR
        ]

    ai_candidate, ai_reason = maybe_generate_schedule_plan(deterministic_plan, payload)
    if ai_candidate:
        ai_validation = validate_plan(ai_candidate, repo)
        if ai_validation.valid:
            provisional_plan = ai_candidate.model_copy(update={"generation_mode": "gemini_optimized"})
        else:
            rejection_reasons = _collect_validation_error_messages(ai_validation)

            retry_candidate, retry_reason = maybe_generate_schedule_plan(
                deterministic_plan,
                payload,
                validation_feedback=rejection_reasons,
            )
            if retry_candidate:
                retry_validation = validate_plan(retry_candidate, repo)
                if retry_validation.valid:
                    provisional_plan = retry_candidate.model_copy(
                        update={
                            "generation_mode": "gemini_optimized",
                            "warnings": deterministic_plan.warnings
                            + [
                                PlanWarning(
                                    code="AI_SCHEDULE_RETRY_SUCCESS",
                                    message=(
                                        "Gemini first attempt violated scheduling rules; second attempt succeeded after validator feedback."
                                    ),
                                    severity=Severity.INFO,
                                )
                            ],
                        }
                    )
                    explanation = maybe_generate_explanation(provisional_plan, payload) if payload.include_explanation else ""
                    final_plan = provisional_plan.model_copy(update={"explanation_markdown": explanation})
                    validation = validate_plan(final_plan, repo)
                    return {
                        "plan": final_plan,
                        "validation": validation,
                    }

                rejection_reasons = _collect_validation_error_messages(retry_validation)
                if retry_reason:
                    ai_reason = f"{ai_reason or 'first-attempt-invalid'} | retry: {retry_reason}"
            elif retry_reason:
                ai_reason = f"{ai_reason or 'first-attempt-invalid'} | retry: {retry_reason}"

            reason_suffix = ""
            if rejection_reasons:
                reason_suffix = f" Reasons: {' | '.join(rejection_reasons[:3])}."
            provisional_plan = deterministic_plan.model_copy(
                update={
                    "generation_mode": "deterministic_fallback",
                    "warnings": deterministic_plan.warnings
                    + [
                        PlanWarning(
                            code="AI_SCHEDULE_REJECTED",
                            message=(
                                "Gemini schedule was generated but rejected by validation safeguards after retry with validator feedback."
                                f"{reason_suffix}"
                            ),
                            severity=Severity.INFO,
                        )
                    ]
                }
            )
    else:
        if not settings.gemini_enable_scheduling:
            provisional_plan = deterministic_plan.model_copy(
                update={
                    "generation_mode": "deterministic",
                    "warnings": deterministic_plan.warnings
                    + [
                        PlanWarning(
                            code="AI_SCHEDULE_DISABLED",
                            message="Gemini scheduling is disabled by configuration (GEMINI_ENABLE_SCHEDULING).",
                            severity=Severity.INFO,
                        )
                    ],
                }
            )
        elif not settings.gemini_api_key:
            provisional_plan = deterministic_plan.model_copy(
                update={
                    "generation_mode": "deterministic",
                    "warnings": deterministic_plan.warnings
                    + [
                        PlanWarning(
                            code="AI_SCHEDULE_NO_API_KEY",
                            message="Gemini scheduling skipped: GEMINI_API_KEY/GOOGLE_API_KEY not set.",
                            severity=Severity.INFO,
                        )
                    ],
                }
            )
        else:
            # Determine appropriate message based on reason
            reason_str = ai_reason or "unknown"
            if "quota-exceeded" in reason_str:
                ai_msg = (
                    "Gemini API quota temporarily exceeded — using optimized deterministic scheduler. "
                    "The plan is fully valid. Quota typically resets within minutes or daily."
                )
            else:
                ai_msg = (
                    "Gemini scheduling was attempted but no valid schedule was returned. "
                    f"Current model: {settings.gemini_model}. "
                    f"Reason: {reason_str}. "
                    "Using optimized deterministic scheduler instead."
                )
            provisional_plan = deterministic_plan.model_copy(
                update={
                    "generation_mode": "deterministic",
                    "warnings": deterministic_plan.warnings
                    + [
                        PlanWarning(
                            code="AI_SCHEDULE_UNAVAILABLE",
                            message=ai_msg,
                            severity=Severity.INFO,
                        )
                    ],
                }
            )

    explanation = maybe_generate_explanation(provisional_plan, payload) if payload.include_explanation else ""
    final_plan = provisional_plan.model_copy(update={"explanation_markdown": explanation})
    validation = validate_plan(final_plan, repo)
    return {
        "plan": final_plan,
        "validation": validation,
    }


@app.post("/v1/plans/rebuild", response_model=PlanRebuildResponse)
def plans_rebuild(payload: PlanRebuildRequest) -> PlanRebuildResponse:
    updated_request = payload.original_request.model_copy(deep=True)
    diff_summary: list[str] = []

    if payload.changes.removed_satisfied_courses:
        current = set(updated_request.resolved_credit_map.satisfied_courses)
        to_remove = set(payload.changes.removed_satisfied_courses)
        updated_request.resolved_credit_map.satisfied_courses = sorted(current - to_remove)
        diff_summary.append(
            "Removed assumed satisfied courses: " + ", ".join(sorted(to_remove))
        )

    if payload.changes.blocked_terms:
        merged = set(updated_request.planning_constraints.blocked_terms)
        merged.update(payload.changes.blocked_terms)
        updated_request.planning_constraints.blocked_terms = sorted(merged)
        diff_summary.append("Updated blocked terms")

    plan_bundle = plans_generate(updated_request)
    plan = plan_bundle["plan"]
    validation = plan_bundle["validation"]

    if payload.changes.move_course:
        move = payload.changes.move_course
        mutable_plan = plan.model_copy(deep=True)
        from_term = next((term for term in mutable_plan.terms if term.term_id == move.from_term_id), None)
        to_term = next((term for term in mutable_plan.terms if term.term_id == move.to_term_id), None)

        if from_term and to_term:
            moving = next((course for course in from_term.courses if course.course_id == move.course_id), None)
            if moving:
                from_term.courses = [course for course in from_term.courses if course.course_id != move.course_id]
                from_term.units = sum(course.units for course in from_term.courses)
                to_term.courses.append(moving)
                to_term.units = sum(course.units for course in to_term.courses)

                move_validation = validate_plan(mutable_plan, repo)
                if move_validation.valid:
                    plan = mutable_plan
                    validation = move_validation
                    diff_summary.append(
                        f"Moved {move.course_id} from {move.from_term_id} to {move.to_term_id}"
                    )
                else:
                    diff_summary.append(
                        f"Rejected move for {move.course_id}; validation failed"
                    )

    if payload.changes.swap_articulation_course:
        swap = payload.changes.swap_articulation_course
        mutable_plan = plan.model_copy(deep=True)
        target_term = next((term for term in mutable_plan.terms if term.term_id == swap.term_id), None)

        if target_term:
            original = next(
                (
                    course
                    for course in target_term.courses
                    if course.course_id == swap.from_course_id and course.requirement_id == swap.requirement_id
                ),
                None,
            )
            if original:
                cc_id = payload.original_request.student_profile.transfer_from_cc_id or ""
                articulation_rows = repo.list_articulation_options_for_requirement(
                    cc_id=cc_id,
                    university_id=payload.original_request.student_profile.target_school_id,
                    major_id=payload.original_request.student_profile.target_major_id,
                    requirement_id=swap.requirement_id,
                )
                selected = next((row for row in articulation_rows if row.get("cc_course_id") == swap.to_cc_course_id), None)

                if selected:
                    cc_course = repo.get_course(cc_id, swap.to_cc_course_id)
                    source = selected.get("source")
                    original.course_id = swap.to_cc_course_id
                    if cc_course:
                        original.course_name = cc_course.get("course_name", original.course_name)
                        original.units = int(cc_course.get("units", original.units))
                    original.justification = "Articulation-based LPC alternative selected for this UC requirement"
                    if isinstance(source, dict):
                        original.source = SourceCitation(
                            source_name=str(source.get("source_name", "ASSIST.org Major Agreement")),
                            source_url=source.get("source_url"),
                            policy_year=str(source.get("policy_year", repo.policy_version)),
                        )

                    target_term.units = sum(course.units for course in target_term.courses)
                    swap_validation = validate_plan(mutable_plan, repo)
                    if swap_validation.valid:
                        plan = mutable_plan
                        validation = swap_validation
                        diff_summary.append(
                            f"Swapped {swap.from_course_id} to articulated LPC course {swap.to_cc_course_id} in {swap.term_id}"
                        )
                    else:
                        diff_summary.append(
                            f"Rejected articulation swap to {swap.to_cc_course_id}; validation failed"
                        )
                else:
                    diff_summary.append(
                        f"Rejected articulation swap to {swap.to_cc_course_id}; no matching agreement found"
                    )

    if not validation.valid:
        diff_summary.append("Plan includes validation issues after rebuild")

    return PlanRebuildResponse(plan=plan, diff_summary=diff_summary)


@app.post("/v1/plans/validate", response_model=ValidationReport)
def plans_validate(payload: PlanValidationRequest) -> ValidationReport:
    return validate_plan(payload.plan, repo)


@app.get("/v1/metadata/schools", response_model=list[School])
def metadata_schools() -> list[School]:
    return [School.model_validate(row) for row in repo.list_schools()]


@app.get("/v1/metadata/majors", response_model=list[Major])
def metadata_majors(school_id: str) -> list[Major]:
    majors = repo.list_majors(school_id)
    if not majors:
        raise HTTPException(status_code=404, detail=f"No majors found for school {school_id}")
    majors_with_reqs = {req["major_id"] for req in repo._data.get("major_requirements", [])}
    result = []
    for row in majors:
        m = Major.model_validate(row)
        m.has_requirements = m.major_id in majors_with_reqs
        result.append(m)
    return sorted(result, key=lambda m: (not m.has_requirements, m.major_name))


@app.get("/v1/metadata/courses", response_model=list[CourseInventoryItem])
def metadata_courses(school_id: str) -> list[CourseInventoryItem]:
    courses = repo.list_courses(school_id)
    if not courses:
        raise HTTPException(status_code=404, detail=f"No courses found for school {school_id}")
    return [CourseInventoryItem.model_validate(row) for row in courses]


@app.get("/v1/metadata/course-offerings", response_model=list[CourseOfferingItem])
def metadata_course_offerings(school_id: str, season: str | None = None) -> list[CourseOfferingItem]:
    offerings = repo.list_course_offerings(school_id, season=season)
    if not offerings:
        if season:
            raise HTTPException(status_code=404, detail=f"No course offerings found for school {school_id} in {season}")
        raise HTTPException(status_code=404, detail=f"No course offerings found for school {school_id}")
    return [CourseOfferingItem.model_validate(row) for row in offerings]


@app.get("/v1/metadata/articulations", response_model=list[ArticulationAgreement])
def metadata_articulations(cc_id: str, university_id: str | None = None, major_id: str | None = None) -> list[ArticulationAgreement]:
    rows = repo.list_assist_articulations(cc_id=cc_id, university_id=university_id, major_id=major_id)
    if not rows:
        raise HTTPException(status_code=404, detail=f"No articulation agreements found for cc_id={cc_id}")
    return [ArticulationAgreement.model_validate(row) for row in rows]


@app.get("/v1/metadata/articulation-options", response_model=list[ArticulationOption])
def metadata_articulation_options(
    cc_id: str,
    university_id: str,
    major_id: str,
    requirement_id: str,
) -> list[ArticulationOption]:
    rows = repo.list_articulation_options_for_requirement(
        cc_id=cc_id,
        university_id=university_id,
        major_id=major_id,
        requirement_id=requirement_id,
    )
    if not rows:
        raise HTTPException(
            status_code=404,
            detail=(
                "No articulation options found for "
                f"cc_id={cc_id}, university_id={university_id}, major_id={major_id}, requirement_id={requirement_id}"
            ),
        )
    return [ArticulationOption.model_validate(row) for row in rows]


@app.get("/v1/policy/version", response_model=PolicyVersionResponse)
def policy_version() -> PolicyVersionResponse:
    return PolicyVersionResponse(
        policy_version=repo.policy_version,
        policy_updated_at=repo.policy_updated_at,
    )


@app.post("/v1/igetc/tracker", response_model=IGETCTrackerResponse)
def igetc_tracker(payload: IGETCTrackerRequest) -> IGETCTrackerResponse:
    courses = repo.list_igetc_courses(payload.cc_id)
    if not courses:
        raise HTTPException(status_code=404, detail=f"No IGETC data found for CC {payload.cc_id}")

    satisfied_areas = set(payload.satisfied_ge_areas)
    planned_course_ids = set(payload.planned_course_ids)

    by_area: dict[str, dict] = {}
    for row in courses:
        area = row["igetc_area"]
        if area not in by_area:
            by_area[area] = row

    area_statuses: list[IGETCAreaStatus] = []
    for area in sorted(by_area.keys()):
        row = by_area[area]
        if area in satisfied_areas:
            area_statuses.append(
                IGETCAreaStatus(
                    area=area,
                    status="satisfied",
                    source="credit",
                    course_id=row["course_id"],
                    course_name=row["course_name"],
                )
            )
            continue

        if row["course_id"] in planned_course_ids:
            area_statuses.append(
                IGETCAreaStatus(
                    area=area,
                    status="planned",
                    source="planned_course",
                    course_id=row["course_id"],
                    course_name=row["course_name"],
                )
            )
            continue

        area_statuses.append(
            IGETCAreaStatus(
                area=area,
                status="missing",
                source="none",
                course_id=row["course_id"],
                course_name=row["course_name"],
            )
        )

    return IGETCTrackerResponse(cc_id=payload.cc_id, areas=area_statuses)


@app.post("/v1/export/pdf")
def export_pdf(payload: PDFExportRequest) -> Response:
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)

    y = 760
    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(40, y, "PathwayIQ Plan Export")
    y -= 30

    pdf.setFont("Helvetica", 10)
    pdf.drawString(40, y, f"Target School: {payload.plan.target_school_id}")
    y -= 16
    pdf.drawString(40, y, f"Target Major: {payload.plan.target_major_id}")
    y -= 16
    pdf.drawString(40, y, f"Policy Version: {payload.plan.policy_version}")
    y -= 24

    for term in payload.plan.terms:
        if y < 80:
            pdf.showPage()
            y = 760
            pdf.setFont("Helvetica", 10)

        pdf.setFont("Helvetica-Bold", 11)
        pdf.drawString(40, y, f"{term.term_label} ({term.term_id}) - {term.units} units")
        y -= 14

        pdf.setFont("Helvetica", 10)
        for course in term.courses:
            pdf.drawString(60, y, f"- {course.course_id}: {course.course_name} ({course.units})")
            y -= 12

        if not term.courses:
            pdf.drawString(60, y, "- No courses")
            y -= 12

        y -= 6

    pdf.save()
    buffer.seek(0)

    return Response(
        content=buffer.read(),
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=pathwayiq-plan.pdf"},
    )


@app.get("/v1/openapi/contracts")
def contracts_snapshot() -> dict:
    return app.openapi()


@app.get("/v1/demo/validation-error", response_model=ValidationReport)
def demo_validation_error() -> ValidationReport:
    return ValidationReport(
        valid=False,
        issues=[
            ValidationIssue(
                code="DEMO",
                message="Demo validation error endpoint",
                severity=Severity.ERROR,
            )
        ],
    )
