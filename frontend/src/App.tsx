import { useEffect, useMemo, useState } from 'react'
import { SpeedInsights } from '@vercel/speed-insights/react'

import {
  type CreditResolutionResponse,
  exportPdf,
  fetchArticulationOptions,
  fetchCourses,
  fetchIgetcTracker,
  fetchMajors,
  fetchSchools,
  generatePlan,
  rebuildPlan,
  resolveCredits,
  validatePlan,
} from './api'
import type {
  ArticulationOption,
  CourseInventoryItem,
  IGETCTracker,
  Major,
  PlanResult,
  ResolvedCreditMap,
  School,
  ValidationReport,
} from './types'

type ExamInput = {
  id: number
  exam_type: 'AP' | 'IB' | 'CLEP'
  exam_name: string
  score: string
  status: 'earned' | 'pending'
}

type PathwayType = 'direct_4yr' | 'cc_transfer' | 'cc_only'
type PriorityType = 'fast' | 'balanced' | 'cost'
type Stage = 'intake' | 'loading' | 'credit' | 'plan'

type FormState = {
  grade: string
  enrollment: string
  pathway: PathwayType
  schoolId: string
  majorId: string
  startTerm: string
  gradTerm: string
  ccId: string
  hsActiveTerms: number
  maxUnitsRegular: number
  maxUnitsHs: number
  blockedTerms: string[]
  priority: PriorityType
}

const gradeOptions = ['9th', '10th', '11th', '12th', '1st year CC', '2nd year CC']
const enrollmentOptions = ['Full-time high school', 'Dual enrollment', 'CC only', 'Gap year']
const pathwayOptions: Array<{ value: PathwayType; label: string }> = [
  { value: 'direct_4yr', label: 'Direct 4-year university' },
  { value: 'cc_transfer', label: 'CC first then transfer' },
  { value: 'cc_only', label: 'CC only' },
]
const priorityOptions: Array<{ value: PriorityType; label: string }> = [
  { value: 'fast', label: 'Finish as fast as possible' },
  { value: 'balanced', label: 'Balanced load' },
  { value: 'cost', label: 'Minimize cost (more CC time)' },
]
const regularUnitOptions = [12, 16, 20]
const hsUnitOptions = [3, 6, 9]
const hsActiveTermOptions = [0, 1, 2, 3, 4]
const seasons = ['Winter', 'Spring', 'Summer', 'Fall']
const termOptions = Array.from({ length: 7 }, (_, idx) => 2025 + idx).flatMap((year) =>
  seasons.map((season) => `${year}-${season}`),
)

const examCatalog: Record<ExamInput['exam_type'], string[]> = {
  AP: [
    'AP Art History',
    'AP Biology',
    'AP Calculus AB',
    'AP Calculus BC',
    'AP Chemistry',
    'AP Chinese Language',
    'AP Computer Science A',
    'AP Computer Science Principles',
    'AP English Language',
    'AP English Literature',
    'AP Environmental Science',
    'AP European History',
    'AP French Language',
    'AP German Language',
    'AP Government & Politics (US)',
    'AP Government & Politics (Comparative)',
    'AP Human Geography',
    'AP Italian Language',
    'AP Japanese Language',
    'AP Latin',
    'AP Macroeconomics',
    'AP Microeconomics',
    'AP Music Theory',
    'AP Physics 1',
    'AP Physics 2',
    'AP Physics C: E&M',
    'AP Physics C: Mechanics',
    'AP Psychology',
    'AP Research',
    'AP Seminar',
    'AP Spanish Language',
    'AP Spanish Literature',
    'AP Statistics',
    'AP Studio Art: 2D',
    'AP Studio Art: 3D',
    'AP Studio Art: Drawing',
    'AP US History',
    'AP World History',
  ],
  IB: ['IB Mathematics HL'],
  CLEP: ['CLEP College Mathematics'],
}

const defaultState: FormState = {
  grade: '12th',
  enrollment: 'Dual enrollment',
  pathway: 'cc_transfer',
  schoolId: 'ucsd',
  majorId: 'ucsd-computer-science',
  startTerm: '2026-Spring',
  gradTerm: '2028-Spring',
  ccId: 'lpc',
  hsActiveTerms: 1,
  maxUnitsRegular: 16,
  maxUnitsHs: 6,
  blockedTerms: [],
  priority: 'balanced',
}

const prdExampleState: FormState = {
  grade: '12th',
  enrollment: 'Dual enrollment',
  pathway: 'cc_transfer',
  schoolId: 'ucsd',
  majorId: 'ucsd-computer-science',
  startTerm: '2026-Spring',
  gradTerm: '2029-Spring',
  ccId: 'lpc',
  hsActiveTerms: 2,
  maxUnitsRegular: 16,
  maxUnitsHs: 6,
  blockedTerms: [],
  priority: 'fast',
}

const defaultExams: ExamInput[] = [
  { id: 1, exam_type: 'AP', exam_name: 'AP Calculus BC', score: '5', status: 'earned' },
  { id: 2, exam_type: 'AP', exam_name: 'AP Computer Science A', score: '', status: 'pending' },
]

const prdExampleExams: ExamInput[] = [
  { id: 1, exam_type: 'AP', exam_name: 'AP Calculus BC', score: '5', status: 'earned' },
  { id: 2, exam_type: 'AP', exam_name: 'AP Computer Science A', score: '5', status: 'earned' },
  { id: 3, exam_type: 'AP', exam_name: 'AP Statistics', score: '5', status: 'earned' },
  { id: 4, exam_type: 'AP', exam_name: 'AP Biology', score: '', status: 'pending' },
  { id: 5, exam_type: 'AP', exam_name: 'AP Psychology', score: '', status: 'pending' },
  { id: 6, exam_type: 'IB', exam_name: 'IB Mathematics HL', score: '', status: 'pending' },
  { id: 7, exam_type: 'CLEP', exam_name: 'CLEP College Mathematics', score: '', status: 'pending' },
]

const stepLabels = ['Academic Background', 'Credit Bank', 'Pathway Choice', 'Major + School', 'Constraints']

const igetcAreaLabels: Record<string, string> = {
  '1': 'English Communication',
  '2': 'Mathematical Concepts and Quantitative Reasoning',
  '3': 'Arts and Humanities',
  '4': 'Social and Behavioral Sciences',
  '5': 'Physical and Biological Sciences',
  '6': 'Language Other Than English',
  '7': 'Ethnic Studies',
}

function encodeState(state: FormState): string {
  return btoa(JSON.stringify(state))
}

function decodeState(value: string | null): FormState | null {
  if (!value) {
    return null
  }
  try {
    const parsed = JSON.parse(atob(value)) as Partial<FormState>
    const blockedTermsValue = (parsed as { blockedTerms?: unknown }).blockedTerms
    const pathwayValue = (parsed as { pathway?: unknown }).pathway
    const priorityValue = (parsed as { priority?: unknown }).priority

    const safePathway: PathwayType =
      pathwayValue === 'direct_4yr' || pathwayValue === 'cc_transfer' || pathwayValue === 'cc_only'
        ? pathwayValue
        : defaultState.pathway
    const safePriority: PriorityType =
      priorityValue === 'fast' || priorityValue === 'balanced' || priorityValue === 'cost'
        ? priorityValue
        : defaultState.priority

    return {
      ...defaultState,
      ...parsed,
      pathway: safePathway,
      priority: safePriority,
      blockedTerms: Array.isArray(blockedTermsValue)
        ? blockedTermsValue.filter((term): term is string => typeof term === 'string')
        : defaultState.blockedTerms,
    }
  } catch {
    return null
  }
}

function formatRequirementLabel(courseName: string): string {
  return courseName
}

function App() {
  const [schools, setSchools] = useState<School[]>([])
  const [majors, setMajors] = useState<Major[]>([])
  const [courseInventory, setCourseInventory] = useState<CourseInventoryItem[]>([])
  const [formState, setFormState] = useState<FormState>(defaultState)
  const [currentStep, setCurrentStep] = useState(1)
  const [stage, setStage] = useState<Stage>('intake')

  const [exams, setExams] = useState<ExamInput[]>(defaultExams)
  const [nextExamId, setNextExamId] = useState(8)
  const [resolutionWarnings, setResolutionWarnings] = useState<Array<{ code: string; message: string; severity: string }>>([])
  const [pendingScenarios, setPendingScenarios] = useState<Array<{ exam_name: string; added_courses_if_no_credit: string[]; note: string }>>([])
  const [resolvedItems, setResolvedItems] = useState<CreditResolutionResponse['resolved_items']>([])

  const [resolvedMap, setResolvedMap] = useState<ResolvedCreditMap | null>(null)
  const [plan, setPlan] = useState<PlanResult | null>(null)
  const [validation, setValidation] = useState<ValidationReport | null>(null)
  const [igetcTracker, setIgetcTracker] = useState<IGETCTracker | null>(null)
  const [originalRequest, setOriginalRequest] = useState<unknown | null>(null)

  const [moveCourseId, setMoveCourseId] = useState('')
  const [moveFromTerm, setMoveFromTerm] = useState('')
  const [moveToTerm, setMoveToTerm] = useState('')
  const [swapCourseId, setSwapCourseId] = useState('')
  const [swapRequirementId, setSwapRequirementId] = useState('')
  const [swapTermId, setSwapTermId] = useState('')
  const [swapOptions, setSwapOptions] = useState<ArticulationOption[]>([])
  const [swapToCourseId, setSwapToCourseId] = useState('')
  const [status, setStatus] = useState('Load metadata to begin.')
  const [loadingDetails, setLoadingDetails] = useState('Preparing request...')

  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const decoded = decodeState(params.get('state'))
    if (decoded) {
      setFormState(decoded)
    }

    fetchSchools()
      .then((rows) => setSchools(rows))
      .catch(() => setStatus('Could not load schools. Is API running at localhost:8000?'))
  }, [])

  useEffect(() => {
    if (!formState.schoolId) {
      return
    }

    const selectedSchoolId = formState.schoolId
    let isActive = true

    setMajors([])
    setCourseInventory([])

    fetchMajors(selectedSchoolId)
      .then((rows) => {
        if (!isActive) {
          return
        }
        setMajors(rows)
        setFormState((previous) => {
          if (previous.schoolId !== selectedSchoolId) {
            return previous
          }
          if (rows.find((row) => row.major_id === previous.majorId)) {
            return previous
          }
          return { ...previous, majorId: rows[0]?.major_id ?? '' }
        })
      })
      .catch(() => {
        if (isActive) {
          setMajors([])
        }
      })

    fetchCourses(selectedSchoolId)
      .then((rows) => {
        if (isActive) {
          setCourseInventory(rows)
        }
      })
      .catch(() => {
        if (isActive) {
          setCourseInventory([])
        }
      })

    return () => {
      isActive = false
    }
  }, [formState.schoolId])

  useEffect(() => {
    if (formState.pathway !== 'cc_transfer' || !formState.ccId || !resolvedMap) {
      setIgetcTracker(null)
      return
    }

    const plannedCourseIds = plan ? plan.terms.flatMap((term) => term.courses.map((course) => course.course_id)) : []

    fetchIgetcTracker({
      cc_id: formState.ccId,
      satisfied_ge_areas: resolvedMap.satisfied_ge_areas,
      planned_course_ids: plannedCourseIds,
    })
      .then((tracker) => setIgetcTracker(tracker))
      .catch(() => setIgetcTracker(null))
  }, [formState.ccId, formState.pathway, plan, resolvedMap])

  useEffect(() => {
    if (stage !== 'loading') {
      return
    }

    const steps = [
      'Resolving credit map and prior coursework...',
      'Building deterministic baseline schedule...',
      'Sending schedule to Gemini for optimization...',
      'Validating AI schedule against prerequisites, term offerings, and unit caps...',
      'Finalizing best valid schedule...',
    ]

    let index = 0
    setLoadingDetails(steps[index])

    const intervalId = window.setInterval(() => {
      index = Math.min(index + 1, steps.length - 1)
      setLoadingDetails(steps[index])
    }, 1200)

    return () => {
      window.clearInterval(intervalId)
    }
  }, [stage])

  const selectedSchool = useMemo(
    () => schools.find((school) => school.school_id === formState.schoolId),
    [schools, formState.schoolId],
  )

  const allPlannedCourses = useMemo(() => {
    if (!plan) {
      return [] as Array<{
        term_id: string
        term_label: string
        requirement_id: string
        justification: string
        course_id: string
        course_name: string
        units: number
        source_name?: string
        source_url?: string
        policy_year?: string
      }>
    }

    return plan.terms.flatMap((term) =>
      term.courses.map((course) => ({
        term_id: term.term_id,
        term_label: term.term_label,
        requirement_id: course.requirement_id,
        justification: course.justification,
        course_id: course.course_id,
        course_name: course.course_name,
        units: course.units,
        source_name: course.source?.source_name,
        source_url: course.source?.source_url,
        policy_year: course.source?.policy_year,
      })),
    )
  }, [plan])

  const termIds = plan ? plan.terms.map((term) => term.term_id) : []

  function updateExam(id: number, patch: Partial<ExamInput>) {
    setExams((current) =>
      current.map((entry) => {
        if (entry.id !== id) {
          return entry
        }
        const nextEntry = { ...entry, ...patch }
        if (patch.exam_type) {
          const allowed = examCatalog[patch.exam_type]
          if (!allowed.includes(nextEntry.exam_name)) {
            nextEntry.exam_name = allowed[0] ?? ''
          }
        }
        return nextEntry
      }),
    )
  }

  function addExam() {
    const newId = nextExamId
    setExams((current) => [
      ...current,
      {
        id: newId,
        exam_type: 'AP',
        exam_name: examCatalog.AP[0],
        score: '',
        status: 'earned',
      },
    ])
    setNextExamId((value) => value + 1)
  }

  function removeExam(id: number) {
    setExams((current) => current.filter((entry) => entry.id !== id))
  }

  function toggleBlockedTerm(termId: string) {
    setFormState((state) => {
      const exists = state.blockedTerms.includes(termId)
      return {
        ...state,
        blockedTerms: exists ? state.blockedTerms.filter((value) => value !== termId) : [...state.blockedTerms, termId],
      }
    })
  }

  function applyPrdExamplePreset() {
    setFormState(prdExampleState)
    setExams(prdExampleExams)
    setNextExamId(8)
    setCurrentStep(1)
    setStage('intake')
    setStatus('PRD example loaded. Continue through the 5-step intake flow.')
  }

  function startOver() {
    setStage('intake')
    setCurrentStep(1)
  }

  async function runPlanner() {
    setStage('loading')
    setStatus('Resolving credit map...')
    setLoadingDetails('Resolving credit map and prior coursework...')

    const profile = {
      current_grade_level: formState.grade,
      enrollment_status: formState.enrollment,
      pathway_type: formState.pathway,
      target_school_id: formState.schoolId,
      target_major_id: formState.majorId,
      start_term: formState.startTerm,
      target_graduation_term: formState.gradTerm,
      transfer_from_cc_id: formState.pathway === 'cc_transfer' ? formState.ccId : null,
      hs_active_terms: Number(formState.hsActiveTerms),
    }

    try {
      const resolved = await resolveCredits({
        student_profile: profile,
        exam_credits: exams.map((exam) => ({
          exam_type: exam.exam_type,
          exam_name: exam.exam_name,
          score: exam.status === 'pending' ? null : exam.score ? Number(exam.score) : null,
          status: exam.status,
        })),
        dual_enrollments: [],
      })

      setResolvedMap(resolved.resolved_credit_map)
      setResolvedItems(resolved.resolved_items ?? [])
      setPendingScenarios(resolved.pending_credit_scenarios)
      setResolutionWarnings(resolved.warnings)

      const requestPayload = {
        student_profile: profile,
        resolved_credit_map: resolved.resolved_credit_map,
        planning_constraints: {
          max_units_regular: Number(formState.maxUnitsRegular),
          max_units_hs_active: Number(formState.maxUnitsHs),
          blocked_terms: formState.blockedTerms,
          priority: formState.priority,
        },
        exam_credits: exams.map((exam) => ({
          exam_type: exam.exam_type,
          exam_name: exam.exam_name,
          score: exam.status === 'pending' ? null : exam.score ? Number(exam.score) : null,
          status: exam.status,
        })),
        include_explanation: true,
      }

      setStatus('Generating full semester-by-semester pathway...')
      setLoadingDetails('Sending schedule to Gemini for optimization...')
      const generated = await generatePlan(requestPayload)
      setPlan(generated.plan)
      setValidation(generated.validation)
      setOriginalRequest(requestPayload)

      const allCourseIds = generated.plan.terms.flatMap((term) => term.courses.map((course) => course.course_id))
      setMoveCourseId(allCourseIds[0] ?? '')
      setMoveFromTerm(generated.plan.terms[0]?.term_id ?? '')
      setMoveToTerm(generated.plan.terms[1]?.term_id ?? generated.plan.terms[0]?.term_id ?? '')

      const url = new URL(window.location.href)
      url.searchParams.set('state', encodeState(formState))
      window.history.replaceState({}, '', url)

      setStage('credit')
      setStatus('Credit resolution complete. Review before continuing to full plan.')
    } catch {
      setStage('intake')
      setStatus('Planner request failed. Verify backend is running and try again.')
    }
  }

  async function runWithoutPendingCredit() {
    if (!plan || !originalRequest || !pendingScenarios.length) {
      return
    }

    const removeCourses = Array.from(new Set(pendingScenarios.flatMap((scenario) => scenario.added_courses_if_no_credit)))
    const rebuilt = await rebuildPlan({
      original_request: originalRequest,
      original_plan: plan,
      changes: {
        removed_satisfied_courses: removeCourses,
        blocked_terms: [],
      },
    })

    setPlan(rebuilt.plan)
    const report = await validatePlan({ plan: rebuilt.plan })
    setValidation(report)
    setStatus('Rebuilt plan without pending-credit assumptions.')
  }

  async function runMoveCourse() {
    if (!plan || !originalRequest || !moveCourseId || !moveFromTerm || !moveToTerm) {
      return
    }

    const rebuilt = await rebuildPlan({
      original_request: originalRequest,
      original_plan: plan,
      changes: {
        removed_satisfied_courses: [],
        blocked_terms: [],
        move_course: {
          course_id: moveCourseId,
          from_term_id: moveFromTerm,
          to_term_id: moveToTerm,
        },
      },
    })

    setPlan(rebuilt.plan)
    const report = await validatePlan({ plan: rebuilt.plan })
    setValidation(report)
    setStatus(rebuilt.diff_summary.join(' | ') || 'Move attempt completed.')
  }

  async function loadArticulationSwapOptions(selectedCourseId: string) {
    if (!plan || !selectedCourseId || formState.pathway !== 'cc_transfer' || !formState.ccId) {
      setSwapOptions([])
      setSwapToCourseId('')
      return
    }

    const selected = allPlannedCourses.find((course) => course.course_id === selectedCourseId)
    if (!selected) {
      setSwapOptions([])
      setSwapToCourseId('')
      return
    }

    setSwapRequirementId(selected.requirement_id)
    setSwapTermId(selected.term_id)

    try {
      const options = await fetchArticulationOptions(formState.ccId, formState.schoolId, formState.majorId, selected.requirement_id)
      setSwapOptions(options)
      setSwapToCourseId(options[0]?.cc_course_id ?? '')
    } catch {
      setSwapOptions([])
      setSwapToCourseId('')
    }
  }

  async function applyArticulationSwap() {
    if (!plan || !originalRequest || !swapCourseId || !swapRequirementId || !swapTermId || !swapToCourseId) {
      return
    }

    const rebuilt = await rebuildPlan({
      original_request: originalRequest,
      original_plan: plan,
      changes: {
        removed_satisfied_courses: [],
        blocked_terms: [],
        swap_articulation_course: {
          term_id: swapTermId,
          requirement_id: swapRequirementId,
          from_course_id: swapCourseId,
          to_cc_course_id: swapToCourseId,
        },
      },
    })

    setPlan(rebuilt.plan)
    const report = await validatePlan({ plan: rebuilt.plan })
    setValidation(report)
    setStatus(rebuilt.diff_summary.join(' | ') || 'Articulation swap attempt completed.')
  }

  async function downloadPdf() {
    if (!plan) {
      return
    }
    const blob = await exportPdf(plan)
    const url = URL.createObjectURL(blob)
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = 'pathwayiq-plan.pdf'
    anchor.click()
    URL.revokeObjectURL(url)
  }

  function goNextStep() {
    setCurrentStep((step) => Math.min(5, step + 1))
  }

  function goPreviousStep() {
    setCurrentStep((step) => Math.max(1, step - 1))
  }

  return (
    <>
    <main className="mx-auto max-w-7xl p-6 text-ink">
      <header className="mb-8 rounded-3xl bg-panel/90 p-8 shadow-soft backdrop-blur">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="text-sm uppercase tracking-[0.2em] text-brand">PathwayIQ</p>
            <h1 className="mt-2 text-4xl font-semibold">AI-Powered College Pathway Planner</h1>
            <p className="mt-3 max-w-3xl text-sm text-stone-700">
              PRD Flow: 5-step intake → credit resolution summary → full pathway timeline.
            </p>
          </div>
          <button className="rounded-xl bg-accent px-4 py-2 text-sm font-medium text-white" onClick={applyPrdExamplePreset}>
            Load PRD Example
          </button>
        </div>
        <p className="mt-4 text-sm font-medium text-accent">Status: {status}</p>

        <div className="mt-4 flex flex-wrap gap-2 text-xs">
          {['intake', 'loading', 'credit', 'plan'].map((item) => (
            <span
              key={item}
              className={`rounded-full px-3 py-1 ${stage === item ? 'bg-brand text-white' : 'bg-stone-200 text-stone-700'}`}
            >
              {item === 'intake' ? 'Intake' : item === 'loading' ? 'Calculating' : item === 'credit' ? 'Credit Summary' : 'Full Plan'}
            </span>
          ))}
        </div>
      </header>

      {stage === 'intake' && (
        <section className="rounded-3xl bg-panel p-6 shadow-soft">
          <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 className="text-2xl font-semibold">Step {currentStep} of 5 — {stepLabels[currentStep - 1]}</h2>
              <p className="mt-1 text-sm text-stone-600">Complete this section, then continue to the next step.</p>
            </div>
            <div className="h-2 w-56 overflow-hidden rounded-full bg-stone-200">
              <div className="h-full bg-brand" style={{ width: `${(currentStep / 5) * 100}%` }} />
            </div>
          </div>

          {currentStep === 1 && (
            <div className="grid gap-4 sm:grid-cols-2">
              <label className="text-sm">
                Current grade level
                <select className="mt-1 w-full rounded-lg border p-2" value={formState.grade} onChange={(event) => setFormState((state) => ({ ...state, grade: event.target.value }))}>
                  {gradeOptions.map((grade) => (
                    <option key={grade} value={grade}>{grade}</option>
                  ))}
                </select>
              </label>
              <label className="text-sm">
                Enrollment status
                <select className="mt-1 w-full rounded-lg border p-2" value={formState.enrollment} onChange={(event) => setFormState((state) => ({ ...state, enrollment: event.target.value }))}>
                  {enrollmentOptions.map((option) => (
                    <option key={option} value={option}>{option}</option>
                  ))}
                </select>
              </label>
              <label className="text-sm">
                Start term
                <select className="mt-1 w-full rounded-lg border p-2" value={formState.startTerm} onChange={(event) => setFormState((state) => ({ ...state, startTerm: event.target.value }))}>
                  {termOptions.map((term) => (
                    <option key={term} value={term}>{term}</option>
                  ))}
                </select>
              </label>
              <label className="text-sm">
                Target graduation term
                <select className="mt-1 w-full rounded-lg border p-2" value={formState.gradTerm} onChange={(event) => setFormState((state) => ({ ...state, gradTerm: event.target.value }))}>
                  {termOptions.map((term) => (
                    <option key={term} value={term}>{term}</option>
                  ))}
                </select>
              </label>
            </div>
          )}

          {currentStep === 2 && (
            <div>
              <h3 className="text-lg font-semibold">AP / IB / CLEP Credit Bank</h3>
              <div className="mt-3 space-y-3">
                {exams.map((exam) => (
                  <div key={exam.id} className="grid gap-2 rounded-xl border border-stone-200 bg-white p-3 sm:grid-cols-5">
                    <select className="rounded-lg border p-2" value={exam.exam_type} onChange={(event) => updateExam(exam.id, { exam_type: event.target.value as ExamInput['exam_type'] })}>
                      <option value="AP">AP</option>
                      <option value="IB">IB</option>
                      <option value="CLEP">CLEP</option>
                    </select>
                    <select className="rounded-lg border p-2 sm:col-span-2" value={exam.exam_name} onChange={(event) => updateExam(exam.id, { exam_name: event.target.value })}>
                      {examCatalog[exam.exam_type].map((name) => (
                        <option key={name} value={name}>{name}</option>
                      ))}
                    </select>
                    <select className="rounded-lg border p-2" value={exam.status} onChange={(event) => updateExam(exam.id, { status: event.target.value as ExamInput['status'] })}>
                      <option value="earned">Score earned</option>
                      <option value="pending">Score pending</option>
                    </select>
                    <div className="flex gap-2">
                      <input className="w-full rounded-lg border p-2" placeholder="Score" value={exam.score} disabled={exam.status === 'pending'} onChange={(event) => updateExam(exam.id, { score: event.target.value })} />
                      <button className="rounded-lg bg-stone-100 px-3 text-sm" onClick={() => removeExam(exam.id)}>Remove</button>
                    </div>
                  </div>
                ))}
              </div>

              <button className="mt-3 rounded-lg bg-stone-200 px-3 py-2 text-sm" onClick={addExam}>
                Add Exam
              </button>
            </div>
          )}

          {currentStep === 3 && (
            <div className="grid gap-4 sm:grid-cols-2">
              <label className="text-sm sm:col-span-2">
                Pathway option
                <select className="mt-1 w-full rounded-lg border p-2" value={formState.pathway} onChange={(event) => setFormState((state) => ({ ...state, pathway: event.target.value as PathwayType }))}>
                  {pathwayOptions.map((option) => (
                    <option key={option.value} value={option.value}>{option.label}</option>
                  ))}
                </select>
              </label>

              {formState.pathway === 'cc_transfer' && (
                <label className="text-sm sm:col-span-2">
                  Community college for transfer path
                  <select className="mt-1 w-full rounded-lg border p-2" value={formState.ccId} onChange={(event) => setFormState((state) => ({ ...state, ccId: event.target.value }))}>
                    <option value="lpc">Las Positas College</option>
                    <option value="sjdc">San Joaquin Delta College</option>
                  </select>
                </label>
              )}
            </div>
          )}

          {currentStep === 4 && (
            <div className="grid gap-4 sm:grid-cols-2">
              <label className="text-sm">
                Target university
                <select className="mt-1 w-full rounded-lg border p-2" value={formState.schoolId} onChange={(event) => setFormState((state) => ({ ...state, schoolId: event.target.value }))}>
                  {schools.map((school) => (
                    <option key={school.school_id} value={school.school_id}>{school.name}</option>
                  ))}
                </select>
              </label>
              <label className="text-sm">
                Target major
                <select className="mt-1 w-full rounded-lg border p-2" value={formState.majorId} onChange={(event) => setFormState((state) => ({ ...state, majorId: event.target.value }))}>
                  {majors.map((major) => (
                    <option key={major.major_id} value={major.major_id}>{major.has_requirements ? '\u2713 ' : ''}{major.major_name}</option>
                  ))}
                </select>
              </label>
            </div>
          )}

          {currentStep === 5 && (
            <div className="space-y-4">
              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                <label className="text-sm">
                  Max units (regular)
                  <select className="mt-1 w-full rounded-lg border p-2" value={formState.maxUnitsRegular} onChange={(event) => setFormState((state) => ({ ...state, maxUnitsRegular: Number(event.target.value) }))}>
                    {regularUnitOptions.map((option) => (
                      <option key={option} value={option}>{option}</option>
                    ))}
                  </select>
                </label>
                <label className="text-sm">
                  Max units (HS active)
                  <select className="mt-1 w-full rounded-lg border p-2" value={formState.maxUnitsHs} onChange={(event) => setFormState((state) => ({ ...state, maxUnitsHs: Number(event.target.value) }))}>
                    {hsUnitOptions.map((option) => (
                      <option key={option} value={option}>{option}</option>
                    ))}
                  </select>
                </label>
                <label className="text-sm">
                  HS-active terms
                  <select className="mt-1 w-full rounded-lg border p-2" value={formState.hsActiveTerms} onChange={(event) => setFormState((state) => ({ ...state, hsActiveTerms: Number(event.target.value) }))}>
                    {hsActiveTermOptions.map((option) => (
                      <option key={option} value={option}>{option}</option>
                    ))}
                  </select>
                </label>
                <label className="text-sm">
                  Planning priority
                  <select className="mt-1 w-full rounded-lg border p-2" value={formState.priority} onChange={(event) => setFormState((state) => ({ ...state, priority: event.target.value as PriorityType }))}>
                    {priorityOptions.map((option) => (
                      <option key={option.value} value={option.value}>{option.label}</option>
                    ))}
                  </select>
                </label>
              </div>

              <div className="rounded-xl border border-stone-200 bg-white p-4">
                <p className="text-sm font-medium">Blocked Terms</p>
                <p className="text-xs text-stone-500">Select semesters to skip.</p>
                <div className="mt-2 max-h-36 overflow-y-auto pr-1">
                  <div className="grid gap-2 sm:grid-cols-3">
                    {termOptions.map((term) => (
                      <label key={term} className="flex items-center gap-2 rounded-lg border border-stone-200 px-2 py-1 text-sm">
                        <input type="checkbox" checked={formState.blockedTerms.includes(term)} onChange={() => toggleBlockedTerm(term)} />
                        <span>{term}</span>
                      </label>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          )}

          <div className="mt-6 flex flex-wrap items-center gap-3">
            <button className="rounded-xl bg-stone-200 px-4 py-2 text-sm disabled:opacity-50" disabled={currentStep === 1} onClick={goPreviousStep}>
              Back
            </button>

            {currentStep < 5 ? (
              <button className="rounded-xl bg-brand px-4 py-2 text-sm text-white" onClick={goNextStep}>
                Continue
              </button>
            ) : (
              <button className="rounded-xl bg-brand px-5 py-2 text-sm font-medium text-white" onClick={() => void runPlanner()}>
                Build My Plan
              </button>
            )}
          </div>
        </section>
      )}

      {stage === 'loading' && (
        <section className="rounded-3xl bg-panel p-12 text-center shadow-soft">
          <h2 className="text-2xl font-semibold">Calculating your pathway...</h2>
          <p className="mt-2 text-sm text-stone-600">Resolving credit policies, prerequisites, and term-by-term sequencing.</p>
          <p className="mt-2 text-sm font-medium text-brand">{loadingDetails}</p>
          <div className="mx-auto mt-6 h-2 max-w-md overflow-hidden rounded-full bg-stone-200">
            <div className="h-full w-2/3 animate-pulse bg-brand" />
          </div>
        </section>
      )}

      {stage === 'credit' && (
        <section className="space-y-6">
          <div className="rounded-3xl bg-panel p-6 shadow-soft">
            <h2 className="text-2xl font-semibold">Credit Resolution Summary</h2>
            {!resolvedMap && <p className="mt-2 text-sm text-stone-600">No credit data available.</p>}
            {resolvedMap && (
              <div className="mt-4 grid gap-4 lg:grid-cols-2">
                <div className="rounded-xl border border-stone-200 bg-white p-4 text-sm">
                  <p><strong>Units waived:</strong> {resolvedMap.units_waived}</p>
                  <p className="mt-1"><strong>Courses satisfied:</strong> {resolvedMap.satisfied_courses.join(', ') || 'None'}</p>
                  <p className="mt-1"><strong>GE areas satisfied:</strong> {resolvedMap.satisfied_ge_areas.join(', ') || 'None'}</p>
                  <p className="mt-1"><strong>Pending exams:</strong> {resolvedMap.pending_exam_names.join(', ') || 'None'}</p>
                </div>
                <div className="rounded-xl border border-stone-200 bg-white p-4 text-sm">
                  <p className="font-semibold">Credit assumptions</p>
                  <ul className="mt-2 space-y-1">
                    {resolvedMap.condition_notes.map((note) => (
                      <li key={note} className="text-amber-700">• {note}</li>
                    ))}
                    {!resolvedMap.condition_notes.length && <li className="text-stone-600">No conditional notes.</li>}
                  </ul>
                </div>
              </div>
            )}

            {!!resolvedItems.length && (
              <div className="mt-4 rounded-xl border border-stone-200 bg-white p-4 text-sm">
                <p className="font-semibold">Resolved Credit Details (Source + Policy Year)</p>
                <div className="mt-3 overflow-x-auto">
                  <table className="min-w-full text-left text-sm">
                    <thead>
                      <tr className="border-b border-stone-200 text-stone-600">
                        <th className="px-2 py-2">Exam</th>
                        <th className="px-2 py-2">Applied Credit</th>
                        <th className="px-2 py-2">Source</th>
                        <th className="px-2 py-2">Policy Year</th>
                      </tr>
                    </thead>
                    <tbody>
                      {resolvedItems.map((item, index) => (
                        <tr key={`${item.exam_type}-${item.exam_name}-${index}`} className="border-b border-stone-100">
                          <td className="px-2 py-2">{item.exam_name} ({item.exam_type})</td>
                          <td className="px-2 py-2">
                            {item.courses_satisfied.join(', ') || 'No course direct-equivalent'}
                            <div className="text-xs text-stone-500">Min score {item.min_score} • {item.units_granted} units</div>
                          </td>
                          <td className="px-2 py-2">{item.source.source_name}</td>
                          <td className="px-2 py-2">{item.source.policy_year}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {!!resolutionWarnings.length && (
              <div className="mt-4 rounded-xl border border-amber-300 bg-white p-4 text-sm">
                <p className="font-semibold">Resolution warnings</p>
                <ul className="mt-2 space-y-1">
                  {resolutionWarnings.map((warning, index) => (
                    <li key={`${warning.code}-${index}`}>• {warning.message}</li>
                  ))}
                </ul>
              </div>
            )}

            {!!pendingScenarios.length && (
              <div className="mt-4 rounded-xl border border-stone-200 bg-white p-4 text-sm">
                <p className="font-semibold">Pending-score what-if impacts</p>
                <ul className="mt-2 space-y-2">
                  {pendingScenarios.map((scenario) => (
                    <li key={scenario.exam_name}>
                      <p className="font-medium">{scenario.exam_name}</p>
                      <p className="text-stone-600">If no credit: add {scenario.added_courses_if_no_credit.join(', ') || 'No additional courses'}</p>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            <div className="mt-6 flex flex-wrap gap-3">
              <button className="rounded-xl bg-brand px-4 py-2 text-sm text-white" onClick={() => setStage('plan')}>
                Continue to Full Plan
              </button>
              <button className="rounded-xl bg-stone-200 px-4 py-2 text-sm" onClick={startOver}>
                Edit Intake
              </button>
            </div>
          </div>
        </section>
      )}

      {stage === 'plan' && (
        <section className="space-y-6">
          <div className="rounded-3xl bg-panel p-6 shadow-soft">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <h2 className="text-2xl font-semibold">Full Pathway Plan</h2>
                <p className="mt-1 text-sm text-stone-600">
                  School: {selectedSchool?.name ?? formState.schoolId} • Term system: {selectedSchool?.term_system ?? 'unknown'}
                </p>
              </div>
              <div className="flex gap-2">
                <button className="rounded-xl bg-accent px-4 py-2 text-sm text-white disabled:opacity-50" disabled={!pendingScenarios.length || !plan} onClick={() => void runWithoutPendingCredit()}>
                  Toggle Without Pending Credit
                </button>
                <button className="rounded-xl bg-stone-800 px-4 py-2 text-sm text-white disabled:opacity-50" disabled={!plan} onClick={() => void downloadPdf()}>
                  Export PDF
                </button>
              </div>
            </div>

            {!plan && <p className="mt-4 text-sm text-stone-600">No plan generated yet.</p>}
            {plan && (
              <>
                <div className="mt-4 rounded-xl border border-stone-200 bg-white p-3 text-sm">
                  <p className="font-semibold">Schedule generation mode</p>
                  {plan.generation_mode === 'gemini_optimized' && (
                    <p className="mt-1 text-emerald-700">Gemini was used to optimize term assignments (validated before returning).</p>
                  )}
                  {plan.generation_mode === 'deterministic_fallback' && (
                    <p className="mt-1 text-amber-700">Gemini attempted optimization, but result was rejected by validation. Deterministic schedule is shown.</p>
                  )}
                  {plan.generation_mode === 'deterministic' && (
                    <p className="mt-1 text-stone-700">Deterministic scheduler generated this plan (Gemini scheduling not applied). See Warnings for the exact reason.</p>
                  )}
                </div>

                <div className="mt-4 flex gap-3 overflow-x-auto pb-2">
                  {plan.terms.map((term) => (
                    <article key={term.term_id} className="min-w-72 rounded-2xl border border-stone-200 bg-white p-4">
                      <p className="text-sm font-semibold">{term.term_label}</p>
                      <p className="text-xs text-stone-500">
                        {term.term_id} • {term.units} units {term.hs_active ? '• HS active cap' : ''}
                      </p>
                      <ul className="mt-3 space-y-2 text-sm">
                        {term.courses.map((course) => (
                          <li key={`${term.term_id}-${course.course_id}`} className="rounded-lg bg-base p-2">
                            <span className="font-semibold">{course.course_id}</span> {course.course_name}
                          </li>
                        ))}
                        {!term.courses.length && <li className="text-stone-500">No courses</li>}
                      </ul>
                      {term.notes.map((note) => (
                        <p key={`${term.term_id}-${note}`} className="mt-2 text-xs text-amber-700">{note}</p>
                      ))}
                    </article>
                  ))}
                </div>

                <div className="mt-6 grid gap-4 lg:grid-cols-2">
                  <div className="rounded-xl border border-stone-200 bg-white p-4">
                    <h3 className="font-semibold">Plan Adjustments</h3>
                    <div className="mt-3 grid gap-2 sm:grid-cols-3">
                      <select className="rounded-lg border p-2 text-sm" value={moveCourseId} onChange={(event) => setMoveCourseId(event.target.value)}>
                        <option value="">Course</option>
                        {allPlannedCourses.map((course) => (
                          <option key={`${course.term_id}-${course.course_id}`} value={course.course_id}>
                            {course.course_id}
                          </option>
                        ))}
                      </select>
                      <select className="rounded-lg border p-2 text-sm" value={moveFromTerm} onChange={(event) => setMoveFromTerm(event.target.value)}>
                        <option value="">From term</option>
                        {termIds.map((termId) => (
                          <option key={termId} value={termId}>{termId}</option>
                        ))}
                      </select>
                      <select className="rounded-lg border p-2 text-sm" value={moveToTerm} onChange={(event) => setMoveToTerm(event.target.value)}>
                        <option value="">To term</option>
                        {termIds.map((termId) => (
                          <option key={termId} value={termId}>{termId}</option>
                        ))}
                      </select>
                    </div>
                    <button className="mt-3 rounded-xl bg-stone-700 px-4 py-2 text-sm text-white" onClick={() => void runMoveCourse()}>
                      Rebuild with Move
                    </button>

                    {formState.pathway === 'cc_transfer' && (
                      <div className="mt-4 border-t border-stone-200 pt-3">
                        <p className="text-sm font-semibold">Course-level What-if (LPC articulation swap)</p>
                        <p className="mt-1 text-xs text-stone-600">Swap a planned UC course with an articulated LPC alternative and revalidate.</p>
                        <div className="mt-2 grid gap-2 sm:grid-cols-2">
                          <select
                            className="rounded-lg border p-2 text-sm"
                            value={swapCourseId}
                            onChange={(event) => {
                              const nextCourse = event.target.value
                              setSwapCourseId(nextCourse)
                              void loadArticulationSwapOptions(nextCourse)
                            }}
                          >
                            <option value="">Planned course</option>
                            {allPlannedCourses.map((course) => (
                              <option key={`swap-${course.term_id}-${course.course_id}`} value={course.course_id}>
                                {course.course_id} ({course.term_label})
                              </option>
                            ))}
                          </select>
                          <select className="rounded-lg border p-2 text-sm" value={swapToCourseId} onChange={(event) => setSwapToCourseId(event.target.value)}>
                            <option value="">LPC alternative</option>
                            {swapOptions.map((option) => (
                              <option key={option.cc_course_id} value={option.cc_course_id}>
                                {option.cc_course_id}
                              </option>
                            ))}
                          </select>
                        </div>
                        <button className="mt-3 rounded-xl bg-brand px-4 py-2 text-sm text-white disabled:opacity-50" disabled={!swapCourseId || !swapToCourseId} onClick={() => void applyArticulationSwap()}>
                          Apply Articulation Swap
                        </button>
                      </div>
                    )}
                  </div>

                  <div className="rounded-xl border border-stone-200 bg-white p-4">
                    <h3 className="font-semibold">Plan Health</h3>
                    <p className="mt-2 text-sm">Validation: {validation?.valid ? 'Valid' : 'Has Issues'}</p>
                    <ul className="mt-2 space-y-1 text-sm">
                      {validation?.issues.map((issue, index) => (
                        <li key={`${issue.code}-${index}`}>• {issue.code}: {issue.message}</li>
                      ))}
                      {!validation?.issues.length && <li>No validation issues.</li>}
                    </ul>
                  </div>
                </div>

                <div className="mt-6 rounded-xl border border-stone-200 bg-white p-4">
                  <h3 className="font-semibold">Admission-ready Checklist</h3>
                  <div className="mt-2 grid gap-2 text-sm sm:grid-cols-2 lg:grid-cols-4">
                    <p><strong>Major prep coverage:</strong> {plan.admission_checklist.major_prep_coverage_pct}%</p>
                    <p><strong>Transferable units:</strong> {plan.admission_checklist.transferable_units}</p>
                    <p><strong>IGETC status:</strong> {plan.admission_checklist.igetc_status}</p>
                    <p><strong>Blockers:</strong> {plan.admission_checklist.missing_blockers.length}</p>
                  </div>
                  <ul className="mt-3 space-y-1 text-sm">
                    {plan.admission_checklist.missing_blockers.map((blocker) => (
                      <li key={blocker}>• {blocker}</li>
                    ))}
                    {!plan.admission_checklist.missing_blockers.length && <li>No major blockers detected.</li>}
                  </ul>
                </div>

                <div className="mt-6 rounded-xl border border-stone-200 bg-white p-4">
                  <h3 className="font-semibold">Articulation Explainability</h3>
                  <p className="mt-1 text-xs text-stone-600">Per course: why it satisfies a UC requirement, with citation source + policy year.</p>
                  <div className="mt-3 overflow-x-auto">
                    <table className="min-w-full text-left text-sm">
                      <thead>
                        <tr className="border-b border-stone-200 text-stone-600">
                          <th className="px-2 py-2">Course</th>
                          <th className="px-2 py-2">Requirement</th>
                          <th className="px-2 py-2">Why</th>
                          <th className="px-2 py-2">Source</th>
                          <th className="px-2 py-2">Policy Year</th>
                        </tr>
                      </thead>
                      <tbody>
                        {allPlannedCourses.map((course) => (
                          <tr key={`why-${course.term_id}-${course.requirement_id}-${course.course_id}`} className="border-b border-stone-100">
                            <td className="px-2 py-2 font-medium">{course.course_id}</td>
                            <td className="px-2 py-2">
                              <span className="font-medium">{formatRequirementLabel(course.course_name)}</span>
                            </td>
                            <td className="px-2 py-2">{course.justification}</td>
                            <td className="px-2 py-2">
                              {course.source_url ? (
                                <a className="text-brand underline" href={course.source_url} target="_blank" rel="noreferrer">
                                  {course.source_name ?? 'Source'}
                                </a>
                              ) : (
                                (course.source_name ?? 'Not tagged')
                              )}
                            </td>
                            <td className="px-2 py-2">{course.policy_year ?? 'N/A'}</td>
                          </tr>
                        ))}
                        {!allPlannedCourses.length && (
                          <tr>
                            <td className="px-2 py-3 text-stone-500" colSpan={5}>No planned classes.</td>
                          </tr>
                        )}
                      </tbody>
                    </table>
                  </div>
                </div>

                <div className="mt-6 rounded-xl border border-stone-200 bg-white p-4">
                  <h3 className="font-semibold">Full Course List ({allPlannedCourses.length} classes)</h3>
                  <div className="mt-3 overflow-x-auto">
                    <table className="min-w-full text-left text-sm">
                      <thead>
                        <tr className="border-b border-stone-200 text-stone-600">
                          <th className="px-2 py-2">Term</th>
                          <th className="px-2 py-2">Course ID</th>
                          <th className="px-2 py-2">Course Name</th>
                          <th className="px-2 py-2">Units</th>
                          <th className="px-2 py-2">Source</th>
                          <th className="px-2 py-2">Source Link</th>
                          <th className="px-2 py-2">Policy Year</th>
                        </tr>
                      </thead>
                      <tbody>
                        {allPlannedCourses.map((course) => (
                          <tr key={`${course.term_id}-${course.course_id}`} className="border-b border-stone-100">
                            <td className="px-2 py-2">{course.term_label}</td>
                            <td className="px-2 py-2 font-medium">{course.course_id}</td>
                            <td className="px-2 py-2">{course.course_name}</td>
                            <td className="px-2 py-2">{course.units}</td>
                            <td className="px-2 py-2">{course.source_name ?? 'Not tagged'}</td>
                            <td className="px-2 py-2">
                              {course.source_url ? (
                                <a className="text-brand underline" href={course.source_url} target="_blank" rel="noreferrer">View</a>
                              ) : (
                                'N/A'
                              )}
                            </td>
                            <td className="px-2 py-2">{course.policy_year ?? 'N/A'}</td>
                          </tr>
                        ))}
                        {!allPlannedCourses.length && (
                          <tr>
                            <td className="px-2 py-3 text-stone-500" colSpan={7}>No scheduled classes.</td>
                          </tr>
                        )}
                      </tbody>
                    </table>
                  </div>
                </div>

                <div className="mt-6 rounded-xl border border-stone-200 bg-white p-4">
                  <h3 className="font-semibold">Campus Course Inventory ({selectedSchool?.name ?? formState.schoolId})</h3>
                  <p className="mt-1 text-xs text-stone-500">
                    Real catalog metadata used by the planner for seasonal offering checks.
                  </p>
                  <div className="mt-3 max-h-72 overflow-y-auto overflow-x-auto">
                    <table className="min-w-full text-left text-sm">
                      <thead>
                        <tr className="border-b border-stone-200 text-stone-600">
                          <th className="px-2 py-2">Course</th>
                          <th className="px-2 py-2">Name</th>
                          <th className="px-2 py-2">Units</th>
                          <th className="px-2 py-2">Offered Terms</th>
                        </tr>
                      </thead>
                      <tbody>
                        {courseInventory.map((course) => (
                          <tr key={`${course.school_id}-${course.course_id}`} className="border-b border-stone-100">
                            <td className="px-2 py-2 font-medium">{course.course_id}</td>
                            <td className="px-2 py-2">{course.course_name}</td>
                            <td className="px-2 py-2">{course.units}</td>
                            <td className="px-2 py-2">{course.offered_terms.join(', ') || 'Not listed'}</td>
                          </tr>
                        ))}
                        {!courseInventory.length && (
                          <tr>
                            <td className="px-2 py-3 text-stone-500" colSpan={4}>No course inventory found for selected campus.</td>
                          </tr>
                        )}
                      </tbody>
                    </table>
                  </div>
                </div>

                <div className="mt-6 grid gap-4 lg:grid-cols-3">
                  <div className="rounded-xl border border-stone-200 bg-white p-4">
                    <h3 className="font-semibold">Milestones</h3>
                    <ul className="mt-2 space-y-1 text-sm">
                      {plan.milestones.map((milestone) => (
                        <li key={milestone.milestone_id}>• {milestone.label} ({milestone.status}) in {milestone.term_id}</li>
                      ))}
                      {!plan.milestones.length && <li>None yet</li>}
                    </ul>
                  </div>
                  <div className="rounded-xl border border-stone-200 bg-white p-4">
                    <h3 className="font-semibold">Critical Path</h3>
                    <ul className="mt-2 space-y-1 text-sm">
                      {plan.critical_path.map((item) => (
                        <li key={item.course_id}>• {item.course_id}</li>
                      ))}
                    </ul>
                  </div>
                  <div className="rounded-xl border border-stone-200 bg-white p-4">
                    <h3 className="font-semibold">Warnings</h3>
                    <ul className="mt-2 space-y-1 text-sm">
                      {plan.warnings.map((warning) => (
                        <li key={warning.code}>• {warning.message}</li>
                      ))}
                      {!plan.warnings.length && <li>No warnings</li>}
                    </ul>
                  </div>
                </div>

                {formState.pathway === 'cc_transfer' && (
                  <div className="mt-6 rounded-xl border border-stone-200 bg-white p-4">
                    <h3 className="font-semibold">IGETC Tracker</h3>
                    <p className="mt-1 text-xs text-stone-500">
                      IGETC areas are transfer GE buckets used by UC/CSU articulation.
                    </p>
                    {!igetcTracker && <p className="mt-2 text-sm text-stone-600">No IGETC tracker data available.</p>}
                    {igetcTracker && (
                      <ul className="mt-3 grid gap-2 text-sm sm:grid-cols-2 lg:grid-cols-4">
                        {igetcTracker.areas.map((area) => (
                          <li key={area.area} className="rounded-lg border border-stone-200 bg-base p-2">
                            <p className="font-medium">Area {area.area}: {igetcAreaLabels[area.area] ?? 'General Education Area'}</p>
                            <p className="text-xs text-stone-600">
                              {area.status === 'satisfied'
                                ? 'Satisfied by existing credit'
                                : area.status === 'planned'
                                  ? 'Planned via course schedule'
                                  : 'Missing'}
                            </p>
                            {area.course_id && <p className="text-xs text-stone-500">{area.course_id}</p>}
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>
                )}

                <div className="mt-6 rounded-xl border border-brand/20 bg-brand/5 p-4 text-sm">
                  <h3 className="font-semibold">AI Explanation</h3>
                  <pre className="mt-2 whitespace-pre-wrap font-sans text-sm">{plan.explanation_markdown}</pre>
                </div>
              </>
            )}
          </div>
        </section>
      )}
    </main>
    <SpeedInsights />
    </>
  )
}

export default App
