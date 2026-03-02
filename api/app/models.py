from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class PathwayType(str, Enum):
    DIRECT_4YR = "direct_4yr"
    CC_TRANSFER = "cc_transfer"
    CC_ONLY = "cc_only"


class OptimizationPreference(str, Enum):
    FAST = "fast"
    BALANCED = "balanced"
    COST = "cost"


class Severity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class ExamCredit(BaseModel):
    exam_type: Literal["AP", "IB", "CLEP"]
    exam_name: str
    score: int | None = None
    status: Literal["earned", "pending"] = "earned"


class DualEnrollmentCourse(BaseModel):
    school_id: str
    course_id: str
    grade: str | None = None
    units: int = 0


class StudentProfile(BaseModel):
    current_grade_level: str
    enrollment_status: str
    pathway_type: PathwayType
    target_school_id: str
    target_major_id: str
    start_term: str = Field(description="YYYY-Season, e.g. 2026-Fall")
    target_graduation_term: str | None = None
    transfer_from_cc_id: str | None = None
    hs_active_terms: int = 0


class PlanningConstraints(BaseModel):
    max_units_regular: int = 16
    max_units_hs_active: int = 6
    blocked_terms: list[str] = Field(default_factory=list)
    priority: OptimizationPreference = OptimizationPreference.BALANCED


class ResolvedCreditMap(BaseModel):
    satisfied_courses: list[str] = Field(default_factory=list)
    satisfied_ge_areas: list[str] = Field(default_factory=list)
    units_waived: int = 0
    pending_exam_names: list[str] = Field(default_factory=list)
    condition_notes: list[str] = Field(default_factory=list)


class SourceCitation(BaseModel):
    source_name: str
    source_url: str | None = None
    policy_year: str


class ResolvedCreditItem(BaseModel):
    exam_type: Literal["AP", "IB", "CLEP"]
    exam_name: str
    status: Literal["earned", "pending"]
    score: int | None = None
    min_score: int
    units_granted: int
    courses_satisfied: list[str] = Field(default_factory=list)
    ge_areas_satisfied: list[str] = Field(default_factory=list)
    source: SourceCitation


class PendingCreditScenario(BaseModel):
    exam_name: str
    added_courses_if_no_credit: list[str]
    note: str


class ResolutionWarning(BaseModel):
    code: str
    message: str
    severity: Severity


class CreditResolveRequest(BaseModel):
    student_profile: StudentProfile
    exam_credits: list[ExamCredit] = Field(default_factory=list)
    dual_enrollments: list[DualEnrollmentCourse] = Field(default_factory=list)


class CreditResolveResponse(BaseModel):
    resolved_credit_map: ResolvedCreditMap
    resolved_items: list[ResolvedCreditItem] = Field(default_factory=list)
    pending_credit_scenarios: list[PendingCreditScenario] = Field(default_factory=list)
    warnings: list[ResolutionWarning] = Field(default_factory=list)
    policy_version: str


class PlannedCourse(BaseModel):
    requirement_id: str
    course_id: str
    course_name: str
    units: int
    course_type: Literal["major_req", "ge", "elective"] = "major_req"
    justification: str = "Required for target pathway"
    source: SourceCitation | None = None


class PlanTerm(BaseModel):
    term_id: str
    term_label: str
    campus_id: str
    courses: list[PlannedCourse] = Field(default_factory=list)
    units: int = 0
    notes: list[str] = Field(default_factory=list)
    hs_active: bool = False


class Milestone(BaseModel):
    milestone_id: str
    label: str
    term_id: str
    status: Literal["done", "pending"]


class PlanWarning(BaseModel):
    code: str
    message: str
    severity: Severity


class CriticalPathItem(BaseModel):
    course_id: str
    note: str


class AdmissionChecklist(BaseModel):
    major_prep_coverage_pct: float = 0.0
    transferable_units: int = 0
    igetc_status: Literal["complete", "in_progress", "not_applicable"] = "not_applicable"
    missing_blockers: list[str] = Field(default_factory=list)


class PlanResult(BaseModel):
    target_school_id: str
    target_major_id: str
    term_system: Literal["semester", "quarter"]
    planning_constraints: PlanningConstraints
    generation_mode: Literal["deterministic", "gemini_optimized", "deterministic_fallback"] = "deterministic"
    starting_satisfied_courses: list[str] = Field(default_factory=list)
    terms: list[PlanTerm]
    milestones: list[Milestone]
    critical_path: list[CriticalPathItem]
    admission_checklist: AdmissionChecklist = Field(default_factory=AdmissionChecklist)
    warnings: list[PlanWarning]
    policy_version: str
    explanation_markdown: str


class PlanGenerateRequest(BaseModel):
    student_profile: StudentProfile
    resolved_credit_map: ResolvedCreditMap
    planning_constraints: PlanningConstraints
    exam_credits: list[ExamCredit] = Field(default_factory=list)
    include_explanation: bool = True


class MoveCourseOperation(BaseModel):
    course_id: str
    from_term_id: str
    to_term_id: str


class SwapArticulationOperation(BaseModel):
    term_id: str
    requirement_id: str
    from_course_id: str
    to_cc_course_id: str


class PlanRebuildChange(BaseModel):
    removed_satisfied_courses: list[str] = Field(default_factory=list)
    blocked_terms: list[str] = Field(default_factory=list)
    move_course: MoveCourseOperation | None = None
    swap_articulation_course: SwapArticulationOperation | None = None


class PlanRebuildRequest(BaseModel):
    original_request: PlanGenerateRequest
    original_plan: PlanResult
    changes: PlanRebuildChange


class PlanRebuildResponse(BaseModel):
    plan: PlanResult
    diff_summary: list[str] = Field(default_factory=list)


class ValidationIssue(BaseModel):
    code: str
    message: str
    severity: Severity
    term_id: str | None = None
    course_id: str | None = None


class ValidationReport(BaseModel):
    valid: bool
    issues: list[ValidationIssue] = Field(default_factory=list)
    missing_requirements: list[str] = Field(default_factory=list)
    unit_overloads: list[str] = Field(default_factory=list)


class PlanValidationRequest(BaseModel):
    plan: PlanResult


class School(BaseModel):
    school_id: str
    name: str
    system: str
    term_system: Literal["semester", "quarter"]


class Major(BaseModel):
    major_id: str
    school_id: str
    major_key: str
    major_name: str
    department: str
    total_units: int
    has_requirements: bool = False
    source: SourceCitation | None = None


class CourseInventoryItem(BaseModel):
    school_id: str
    course_id: str
    course_name: str
    units: int
    department: str | None = None
    catalog_level: str | None = None
    description: str | None = None
    offered_terms: list[str] = Field(default_factory=list)


class CourseOfferingItem(BaseModel):
    school_id: str
    course_id: str
    offered_terms: list[str] = Field(default_factory=list)


class ArticulationAgreement(BaseModel):
    cc_id: str
    university_id: str
    major_id: str
    cc_course_id: str
    satisfies_requirement_id: str
    agreement_label: str | None = None
    agreement_key: str | None = None
    source: SourceCitation | None = None


class ArticulationOption(BaseModel):
    cc_course_id: str
    requirement_id: str
    source: SourceCitation | None = None


class PolicyVersionResponse(BaseModel):
    policy_version: str
    policy_updated_at: str


class IGETCTrackerRequest(BaseModel):
    cc_id: str
    satisfied_ge_areas: list[str] = Field(default_factory=list)
    planned_course_ids: list[str] = Field(default_factory=list)


class IGETCAreaStatus(BaseModel):
    area: str
    status: Literal["satisfied", "planned", "missing"]
    source: Literal["credit", "planned_course", "none"]
    course_id: str | None = None
    course_name: str | None = None


class IGETCTrackerResponse(BaseModel):
    cc_id: str
    areas: list[IGETCAreaStatus] = Field(default_factory=list)


class PDFExportRequest(BaseModel):
    plan: PlanResult
