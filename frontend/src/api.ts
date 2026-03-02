import type {
  ArticulationOption,
  CourseInventoryItem,
  CourseOfferingItem,
  IGETCTracker,
  Major,
  PlanResult,
  ResolvedCreditMap,
  School,
  ValidationReport,
} from './types'

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

export type CreditResolutionResponse = {
  resolved_credit_map: ResolvedCreditMap
  resolved_items: Array<{
    exam_type: 'AP' | 'IB' | 'CLEP'
    exam_name: string
    status: 'earned' | 'pending'
    score?: number
    min_score: number
    units_granted: number
    courses_satisfied: string[]
    ge_areas_satisfied: string[]
    source: {
      source_name: string
      source_url?: string
      policy_year: string
    }
  }>
  pending_credit_scenarios: Array<{ exam_name: string; added_courses_if_no_credit: string[]; note: string }>
  warnings: Array<{ code: string; message: string; severity: string }>
  policy_version: string
}

export async function fetchSchools(): Promise<School[]> {
  const response = await fetch(`${API_BASE}/v1/metadata/schools`)
  if (!response.ok) {
    throw new Error('Failed to fetch schools')
  }
  return response.json()
}

export async function fetchMajors(schoolId: string): Promise<Major[]> {
  const response = await fetch(`${API_BASE}/v1/metadata/majors?school_id=${encodeURIComponent(schoolId)}`)
  if (!response.ok) {
    throw new Error('Failed to fetch majors')
  }
  return response.json()
}

export async function fetchCourses(schoolId: string): Promise<CourseInventoryItem[]> {
  const response = await fetch(`${API_BASE}/v1/metadata/courses?school_id=${encodeURIComponent(schoolId)}`)
  if (!response.ok) {
    throw new Error('Failed to fetch courses')
  }
  return response.json()
}

export async function fetchCourseOfferings(schoolId: string, season?: string): Promise<CourseOfferingItem[]> {
  const query = season ? `&season=${encodeURIComponent(season)}` : ''
  const response = await fetch(`${API_BASE}/v1/metadata/course-offerings?school_id=${encodeURIComponent(schoolId)}${query}`)
  if (!response.ok) {
    throw new Error('Failed to fetch course offerings')
  }
  return response.json()
}

export async function fetchArticulationOptions(
  ccId: string,
  universityId: string,
  majorId: string,
  requirementId: string,
): Promise<ArticulationOption[]> {
  const query =
    `cc_id=${encodeURIComponent(ccId)}` +
    `&university_id=${encodeURIComponent(universityId)}` +
    `&major_id=${encodeURIComponent(majorId)}` +
    `&requirement_id=${encodeURIComponent(requirementId)}`
  const response = await fetch(`${API_BASE}/v1/metadata/articulation-options?${query}`)
  if (!response.ok) {
    throw new Error('Failed to fetch articulation options')
  }
  return response.json()
}

export async function resolveCredits(payload: unknown): Promise<CreditResolutionResponse> {
  const response = await fetch(`${API_BASE}/v1/credits/resolve`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  if (!response.ok) {
    throw new Error('Credit resolution failed')
  }
  return response.json()
}

export async function generatePlan(payload: unknown): Promise<{ plan: PlanResult; validation: ValidationReport }> {
  const response = await fetch(`${API_BASE}/v1/plans/generate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  if (!response.ok) {
    throw new Error('Plan generation failed')
  }
  return response.json()
}

export async function rebuildPlan(payload: unknown): Promise<{ plan: PlanResult; diff_summary: string[] }> {
  const response = await fetch(`${API_BASE}/v1/plans/rebuild`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  if (!response.ok) {
    throw new Error('Plan rebuild failed')
  }
  return response.json()
}

export async function validatePlan(payload: unknown): Promise<ValidationReport> {
  const response = await fetch(`${API_BASE}/v1/plans/validate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  if (!response.ok) {
    throw new Error('Plan validation failed')
  }
  return response.json()
}

export async function exportPdf(plan: PlanResult): Promise<Blob> {
  const response = await fetch(`${API_BASE}/v1/export/pdf`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ plan }),
  })
  if (!response.ok) {
    throw new Error('PDF export failed')
  }
  return response.blob()
}

export async function fetchIgetcTracker(payload: {
  cc_id: string
  satisfied_ge_areas: string[]
  planned_course_ids: string[]
}): Promise<IGETCTracker> {
  const response = await fetch(`${API_BASE}/v1/igetc/tracker`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  if (!response.ok) {
    throw new Error('Failed to fetch IGETC tracker')
  }
  return response.json()
}
