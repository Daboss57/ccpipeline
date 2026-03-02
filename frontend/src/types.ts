export type School = {
  school_id: string
  name: string
  system: string
  term_system: 'semester' | 'quarter'
}

export type Major = {
  major_id: string
  school_id: string
  major_key: string
  major_name: string
  department: string
  total_units: number
  has_requirements?: boolean
  source?: {
    source_name: string
    source_url?: string
    policy_year: string
  }
}

export type SourceCitation = {
  source_name: string
  source_url?: string
  policy_year: string
}

export type CourseInventoryItem = {
  school_id: string
  course_id: string
  course_name: string
  units: number
  department?: string
  catalog_level?: string
  description?: string
  offered_terms: string[]
}

export type CourseOfferingItem = {
  school_id: string
  course_id: string
  offered_terms: string[]
}

export type ResolvedCreditMap = {
  satisfied_courses: string[]
  satisfied_ge_areas: string[]
  units_waived: number
  pending_exam_names: string[]
  condition_notes: string[]
}

export type PlanCourse = {
  requirement_id: string
  course_id: string
  course_name: string
  units: number
  course_type: 'major_req' | 'ge' | 'elective'
  justification: string
  source?: SourceCitation
}

export type PlanTerm = {
  term_id: string
  term_label: string
  campus_id: string
  courses: PlanCourse[]
  units: number
  notes: string[]
  hs_active: boolean
}

export type PlanWarning = {
  code: string
  message: string
  severity: 'info' | 'warning' | 'error'
}

export type PlanResult = {
  target_school_id: string
  target_major_id: string
  term_system: 'semester' | 'quarter'
  planning_constraints: {
    max_units_regular: number
    max_units_hs_active: number
    blocked_terms: string[]
    priority: 'fast' | 'balanced' | 'cost'
  }
  generation_mode: 'deterministic' | 'gemini_optimized' | 'deterministic_fallback'
  starting_satisfied_courses: string[]
  terms: PlanTerm[]
  milestones: Array<{
    milestone_id: string
    label: string
    term_id: string
    status: 'done' | 'pending'
  }>
  critical_path: Array<{ course_id: string; note: string }>
  admission_checklist: {
    major_prep_coverage_pct: number
    transferable_units: number
    igetc_status: 'complete' | 'in_progress' | 'not_applicable'
    missing_blockers: string[]
  }
  warnings: PlanWarning[]
  policy_version: string
  explanation_markdown: string
}

export type ValidationReport = {
  valid: boolean
  issues: Array<{
    code: string
    message: string
    severity: 'info' | 'warning' | 'error'
    term_id?: string
    course_id?: string
  }>
  missing_requirements: string[]
  unit_overloads: string[]
}

export type IGETCAreaStatus = {
  area: string
  status: 'satisfied' | 'planned' | 'missing'
  source: 'credit' | 'planned_course' | 'none'
  course_id?: string
  course_name?: string
}

export type IGETCTracker = {
  cc_id: string
  areas: IGETCAreaStatus[]
}

export type ArticulationOption = {
  cc_course_id: string
  requirement_id: string
  source?: {
    source_name: string
    source_url?: string
    policy_year: string
  }
}
