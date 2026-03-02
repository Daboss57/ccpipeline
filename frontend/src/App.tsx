import { useEffect, useMemo, useState } from 'react'
import { Calendar, Clock, Code, FileText, User } from 'lucide-react'

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
import AnimatedHero from '@/components/ui/animated-hero'
import RadialOrbitalTimeline, { type TimelineItem } from '@/components/ui/radial-orbital-timeline'

type ExamInput = {
  id: number
  exam_type: 'AP' | 'IB' | 'CLEP'
  exam_name: string
  score: string
  status: 'earned' | 'pending'
}

type PathwayType = 'direct_4yr' | 'cc_transfer' | 'cc_only'
type PriorityType = 'fast' | 'balanced' | 'cost'
type Stage = 'landing' | 'intake' | 'loading' | 'credit' | 'plan'
type PlanWorkspaceTab = 'overview' | 'scenarios' | 'requirements' | 'adjust' | 'evidence'

type ScenarioSnapshot = {
  id: string
  name: string
  createdAt: string
  plan: PlanResult
}

type RequirementStatus = 'done' | 'planned' | 'missing'

type RequirementProgressItem = {
  label: string
  status: RequirementStatus
  detail?: string
}

type RequirementProgressGroup = {
  title: string
  items: RequirementProgressItem[]
}

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

type SharedPlanPayload = {
  version: 1
  created_at: string
  form_state: FormState
  plan: PlanResult
  validation: ValidationReport | null
  resolved_credit_map: ResolvedCreditMap | null
  igetc_tracker: IGETCTracker | null
  scenarios: ScenarioSnapshot[]
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

const termSeasonOrder: Record<string, number> = {
  Winter: 1,
  Spring: 2,
  Summer: 3,
  Fall: 4,
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

function encodeSharePayload(payload: SharedPlanPayload): string {
  const raw = JSON.stringify(payload)
  const bytes = new TextEncoder().encode(raw)
  let binary = ''
  bytes.forEach((value) => {
    binary += String.fromCharCode(value)
  })
  return btoa(binary).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/g, '')
}

function decodeSharePayload(value: string | null): SharedPlanPayload | null {
  if (!value) {
    return null
  }

  try {
    const normalized = value.replace(/-/g, '+').replace(/_/g, '/')
    const padded = normalized + '='.repeat((4 - (normalized.length % 4)) % 4)
    const binary = atob(padded)
    const bytes = Uint8Array.from(binary, (char) => char.charCodeAt(0))
    const decoded = new TextDecoder().decode(bytes)
    const parsed = JSON.parse(decoded) as SharedPlanPayload
    if (parsed?.version !== 1 || !parsed?.plan) {
      return null
    }
    return parsed
  } catch {
    return null
  }
}

function getTermSortKey(termId: string): number {
  const [yearPart, seasonPart] = termId.split('-')
  const year = Number(yearPart)
  const seasonOrder = termSeasonOrder[seasonPart] ?? 0
  if (!Number.isFinite(year)) {
    return -1
  }
  return year * 10 + seasonOrder
}

function App() {
  const [schools, setSchools] = useState<School[]>([])
  const [majors, setMajors] = useState<Major[]>([])
  const [courseInventory, setCourseInventory] = useState<CourseInventoryItem[]>([])
  const [formState, setFormState] = useState<FormState>(defaultState)
  const [currentStep, setCurrentStep] = useState(1)
  const [stage, setStage] = useState<Stage>('landing')

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
  const [planWorkspaceTab, setPlanWorkspaceTab] = useState<PlanWorkspaceTab>('overview')
  const [showTechnicalDetails, setShowTechnicalDetails] = useState(false)
  const [savedScenarios, setSavedScenarios] = useState<ScenarioSnapshot[]>([])
  const [compareLeftScenarioId, setCompareLeftScenarioId] = useState('')
  const [compareRightScenarioId, setCompareRightScenarioId] = useState('')
  const [isScenarioRunning, setIsScenarioRunning] = useState(false)
  const [scenarioRunLabel, setScenarioRunLabel] = useState('')
  const [tourVisible, setTourVisible] = useState(false)
  const [tourStep, setTourStep] = useState(0)
  const [isSharingPlan, setIsSharingPlan] = useState(false)

  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const sharedPayload = decodeSharePayload(params.get('shared'))
    if (sharedPayload) {
      setFormState(sharedPayload.form_state)
      setPlan(sharedPayload.plan)
      setValidation(sharedPayload.validation)
      setResolvedMap(sharedPayload.resolved_credit_map)
      setIgetcTracker(sharedPayload.igetc_tracker)
      setSavedScenarios(sharedPayload.scenarios ?? [])
      setStage('plan')
      setPlanWorkspaceTab('overview')
      setTourVisible(false)
      setStatus('Shared plan loaded successfully.')
    }

    const decoded = decodeState(params.get('state'))
    if (decoded && !sharedPayload) {
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

  useEffect(() => {
    if (stage !== 'plan') {
      return
    }

    const completed = window.localStorage.getItem('pathwayiq-tour-complete-v1') === '1'
    if (!completed) {
      setTourVisible(true)
      setTourStep(0)
      setPlanWorkspaceTab('overview')
    }
  }, [stage])

  const selectedSchool = useMemo(
    () => schools.find((school) => school.school_id === formState.schoolId),
    [schools, formState.schoolId],
  )

  const selectedMajor = useMemo(
    () => majors.find((major) => major.major_id === formState.majorId),
    [majors, formState.majorId],
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

  const requirementProgressGroups = useMemo<RequirementProgressGroup[]>(() => {
    if (!plan) {
      return []
    }

    const plannedCourseIds = new Set(allPlannedCourses.map((course) => course.course_id))
    const missingCourseIds = new Set(validation?.missing_requirements ?? [])

    const majorPlanned: RequirementProgressItem[] = allPlannedCourses
      .filter((course) => /-REQ-\d+$/.test(course.requirement_id))
      .map((course) => ({
        label: course.course_name,
        status: 'planned',
        detail: `${course.course_id} • ${course.term_label}`,
      }))

    const majorMissing: RequirementProgressItem[] = Array.from(missingCourseIds).map((courseId) => ({
      label: courseId,
      status: 'missing',
      detail: 'Not currently scheduled',
    }))

    const generalEdPlanned: RequirementProgressItem[] = allPlannedCourses
      .filter((course) => course.requirement_id.startsWith('GEN-'))
      .map((course) => ({
        label: course.course_name,
        status: 'planned',
        detail: `${course.course_id} • ${course.term_label}`,
      }))

    const igetcItems: RequirementProgressItem[] = (igetcTracker?.areas ?? []).map((area) => ({
      label: `IGETC Area ${area.area}: ${igetcAreaLabels[area.area] ?? 'General Education Area'}`,
      status: area.status === 'satisfied' ? 'done' : area.status === 'planned' ? 'planned' : 'missing',
      detail: area.course_id ?? (area.status === 'missing' ? 'No course assigned' : undefined),
    }))

    const waivedByCredit: RequirementProgressItem[] = (resolvedMap?.satisfied_courses ?? [])
      .filter((courseId) => !plannedCourseIds.has(courseId))
      .map((courseId) => ({
        label: courseId,
        status: 'done',
        detail: 'Satisfied by incoming credit',
      }))

    const groups: RequirementProgressGroup[] = [
      { title: 'Major Requirements', items: [...majorPlanned, ...majorMissing] },
      { title: 'General Education', items: generalEdPlanned },
      { title: 'IGETC Areas', items: igetcItems },
      { title: 'Waived by Credit', items: waivedByCredit },
    ]

    return groups.filter((group) => group.items.length > 0)
  }, [allPlannedCourses, igetcTracker, plan, resolvedMap, validation?.missing_requirements])

  const guidedNarrative = useMemo(() => {
    if (!plan) {
      return null
    }

    const doneCount = requirementProgressGroups
      .flatMap((group) => group.items)
      .filter((item) => item.status === 'done').length
    const plannedCount = requirementProgressGroups
      .flatMap((group) => group.items)
      .filter((item) => item.status === 'planned').length
    const missingCount = requirementProgressGroups
      .flatMap((group) => group.items)
      .filter((item) => item.status === 'missing').length

    const whatsDone = [
      `${plan.admission_checklist.major_prep_coverage_pct}% major prep coverage`,
      `${plan.admission_checklist.transferable_units} transferable units`,
      `${doneCount} completed requirements and ${plannedCount} planned requirements`,
    ]

    const whatsLeft = [
      ...plan.admission_checklist.missing_blockers,
      ...(validation?.missing_requirements ?? []).map((courseId) => `${courseId} still missing in current horizon`),
    ]

    let nextAction = 'Review the Adjust tab and rebalance terms to clear remaining blockers.'
    if (!whatsLeft.length) {
      nextAction = 'Export and share this plan. You are on-track with current assumptions.'
    } else if ((validation?.issues ?? []).some((issue) => issue.code === 'UNIT_OVERLOAD')) {
      nextAction = 'Open Adjust tab and move one course from overloaded terms first.'
    } else if ((validation?.issues ?? []).some((issue) => issue.code === 'PREREQ_VIOLATION')) {
      nextAction = 'Open Adjust tab and move prerequisite courses earlier before dependent courses.'
    }

    return {
      done: whatsDone,
      left: whatsLeft.length ? whatsLeft : ['No blockers currently detected.'],
      nextAction,
      missingCount,
    }
  }, [plan, requirementProgressGroups, validation])

  const admissionsReadiness = useMemo(() => {
    if (!plan) {
      return null
    }

    const blockersCount = plan.admission_checklist.missing_blockers.length
    const missingRequirementsCount = validation?.missing_requirements.length ?? 0

    const issueOverloadTerms = new Set(
      (validation?.issues ?? [])
        .filter((issue) => issue.code === 'UNIT_OVERLOAD')
        .map((issue) => issue.term_id)
        .filter((value): value is string => Boolean(value)),
    )
    const overloadTermsCount = new Set([...(validation?.unit_overloads ?? []), ...Array.from(issueOverloadTerms)]).size

    const targetGradTermKey = getTermSortKey(formState.gradTerm)
    const plannedTermsWithCourses = plan.terms.filter((term) => term.courses.length > 0)
    const lateTermsCount = plannedTermsWithCourses.filter((term) => getTermSortKey(term.term_id) > targetGradTermKey).length

    const scorePenalty =
      blockersCount * 15 +
      missingRequirementsCount * 6 +
      overloadTermsCount * 8 +
      lateTermsCount * 12 +
      (validation?.valid ? 0 : 5)

    const score = Math.max(0, Math.min(100, 100 - scorePenalty))

    const riskLevel: 'Low' | 'Medium' | 'High' =
      score < 55 || blockersCount >= 2 || lateTermsCount > 0
        ? 'High'
        : score < 75 || missingRequirementsCount > 0 || overloadTermsCount > 0
          ? 'Medium'
          : 'Low'

    const reasons: Array<{ label: string; severity: 'low' | 'medium' | 'high'; detail: string }> = []

    reasons.push({
      label: 'Missing blockers',
      severity: blockersCount >= 2 ? 'high' : blockersCount === 1 ? 'medium' : 'low',
      detail:
        blockersCount > 0
          ? `${blockersCount} blocker(s): ${plan.admission_checklist.missing_blockers.join(', ')}`
          : 'No blockers detected in the current plan.',
    })

    reasons.push({
      label: 'Timeline risk',
      severity: lateTermsCount > 0 ? 'high' : 'low',
      detail:
        lateTermsCount > 0
          ? `${lateTermsCount} planned term(s) extend past target graduation term ${formState.gradTerm}.`
          : `Current schedule finishes within target graduation term ${formState.gradTerm}.`,
    })

    reasons.push({
      label: 'Unit overload risk',
      severity: overloadTermsCount >= 2 ? 'high' : overloadTermsCount === 1 ? 'medium' : 'low',
      detail:
        overloadTermsCount > 0
          ? `${overloadTermsCount} term(s) exceed unit constraints and may require rebalancing.`
          : 'No overloaded terms detected.',
    })

    if (missingRequirementsCount > 0) {
      reasons.push({
        label: 'Requirement completion risk',
        severity: missingRequirementsCount >= 3 ? 'high' : 'medium',
        detail: `${missingRequirementsCount} required course(s) still missing in the current horizon.`,
      })
    }

    return {
      score,
      riskLevel,
      reasons,
      blockersCount,
      overloadTermsCount,
      lateTermsCount,
      missingRequirementsCount,
    }
  }, [formState.gradTerm, plan, validation])

  const compareLeftScenario = savedScenarios.find((scenario) => scenario.id === compareLeftScenarioId)
  const compareRightScenario = savedScenarios.find((scenario) => scenario.id === compareRightScenarioId)

  const scenarioDiff = useMemo(() => {
    if (!compareLeftScenario || !compareRightScenario) {
      return null
    }

    const flattenPlan = (scenarioPlan: PlanResult) =>
      scenarioPlan.terms.flatMap((term) =>
        term.courses.map((course) => ({
          course_id: course.course_id,
          course_name: course.course_name,
          term_id: term.term_id,
          term_label: term.term_label,
          units: course.units,
        })),
      )

    const leftCourses = flattenPlan(compareLeftScenario.plan)
    const rightCourses = flattenPlan(compareRightScenario.plan)

    const leftById = new Map(leftCourses.map((course) => [course.course_id, course]))
    const rightById = new Map(rightCourses.map((course) => [course.course_id, course]))

    const addedInRight = rightCourses.filter((course) => !leftById.has(course.course_id))
    const removedInRight = leftCourses.filter((course) => !rightById.has(course.course_id))
    const movedInRight = rightCourses
      .filter((course) => leftById.has(course.course_id))
      .filter((course) => {
        const left = leftById.get(course.course_id)
        return left?.term_id !== course.term_id
      })
      .map((course) => {
        const left = leftById.get(course.course_id)
        return {
          course_id: course.course_id,
          course_name: course.course_name,
          from_term: left?.term_label ?? 'Unknown term',
          to_term: course.term_label,
        }
      })

    const coverageDelta =
      compareRightScenario.plan.admission_checklist.major_prep_coverage_pct -
      compareLeftScenario.plan.admission_checklist.major_prep_coverage_pct
    const unitsDelta =
      compareRightScenario.plan.admission_checklist.transferable_units -
      compareLeftScenario.plan.admission_checklist.transferable_units
    const blockerDelta =
      compareRightScenario.plan.admission_checklist.missing_blockers.length -
      compareLeftScenario.plan.admission_checklist.missing_blockers.length

    const leftBlockers = new Set(compareLeftScenario.plan.admission_checklist.missing_blockers)
    const rightBlockers = new Set(compareRightScenario.plan.admission_checklist.missing_blockers)

    const blockersAddedInRight = Array.from(rightBlockers).filter((item) => !leftBlockers.has(item))
    const blockersRemovedInRight = Array.from(leftBlockers).filter((item) => !rightBlockers.has(item))

    return {
      addedInRight,
      removedInRight,
      movedInRight,
      coverageDelta,
      unitsDelta,
      blockerDelta,
      blockersAddedInRight,
      blockersRemovedInRight,
    }
  }, [compareLeftScenario, compareRightScenario])

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

  function saveScenarioSnapshot(name?: string, scenarioPlan?: PlanResult) {
    const planToSave = scenarioPlan ?? plan
    if (!planToSave) {
      return
    }

    const scenarioId = `${Date.now()}-${Math.random().toString(36).slice(2, 7)}`
    const scenarioName = name?.trim() || `Scenario ${savedScenarios.length + 1}`
    const snapshot: ScenarioSnapshot = {
      id: scenarioId,
      name: scenarioName,
      createdAt: new Date().toISOString(),
      plan: planToSave,
    }

    setSavedScenarios((items) => {
      const nextItems = [snapshot, ...items].slice(0, 8)
      if (!compareLeftScenarioId) {
        setCompareLeftScenarioId(snapshot.id)
      } else if (!compareRightScenarioId) {
        setCompareRightScenarioId(snapshot.id)
      }
      return nextItems
    })
  }

  function loadScenario(scenarioId: string) {
    const scenario = savedScenarios.find((item) => item.id === scenarioId)
    if (!scenario) {
      return
    }
    setPlan(scenario.plan)
    setStatus(`Loaded scenario: ${scenario.name}`)
  }

  function unlockScenarioButtons() {
    setIsScenarioRunning(false)
    setScenarioRunLabel('')
    setStatus('Scenario actions unlocked. You can run another one now.')
  }

  function closeTour() {
    setTourVisible(false)
    window.localStorage.setItem('pathwayiq-tour-complete-v1', '1')
  }

  function nextTourStep() {
    setTourStep((current) => {
      const next = current + 1
      if (next === 1) {
        setPlanWorkspaceTab('scenarios')
      } else if (next === 2) {
        setPlanWorkspaceTab('requirements')
      } else if (next === 3) {
        setPlanWorkspaceTab('adjust')
      } else if (next > 3) {
        closeTour()
        return current
      }
      return next
    })
  }

  async function buildScenario(kind: 'no-ap' | 'fast-track' | 'light-load') {
    if (!originalRequest || !plan) {
      return
    }

    const scenarioName = kind === 'no-ap' ? 'No AP' : kind === 'fast-track' ? 'Fast Track' : 'Light Load'
    setIsScenarioRunning(true)
    setScenarioRunLabel(scenarioName)
    setStatus(`Building ${scenarioName} scenario... this can take up to 60–90 seconds.`)

    try {
      const requestPayload = JSON.parse(JSON.stringify(originalRequest)) as {
        exam_credits?: Array<{ exam_type: string; exam_name: string; score: number | null; status: string | null }>
        planning_constraints?: {
          max_units_regular?: number
          max_units_hs_active?: number
          blocked_terms?: string[]
          priority?: 'fast' | 'balanced' | 'cost'
        }
      }

      if (!requestPayload.planning_constraints) {
        requestPayload.planning_constraints = {}
      }

      if (kind === 'no-ap') {
        requestPayload.exam_credits = (requestPayload.exam_credits ?? []).filter((exam) => exam.exam_type !== 'AP')
      }

      if (kind === 'fast-track') {
        requestPayload.planning_constraints.priority = 'fast'
        requestPayload.planning_constraints.max_units_regular = Math.max(
          requestPayload.planning_constraints.max_units_regular ?? formState.maxUnitsRegular,
          20,
        )
      }

      if (kind === 'light-load') {
        requestPayload.planning_constraints.priority = 'balanced'
        requestPayload.planning_constraints.max_units_regular = 12
        requestPayload.planning_constraints.max_units_hs_active = 3
      }

      const generated = (await Promise.race([
        generatePlan(requestPayload),
        new Promise<never>((_, reject) => {
          window.setTimeout(() => reject(new Error('Scenario generation timed out after 90 seconds.')), 90000)
        }),
      ])) as { plan: PlanResult; validation: ValidationReport }

      saveScenarioSnapshot(scenarioName, generated.plan)

      if (savedScenarios.length === 0) {
        saveScenarioSnapshot('Baseline', plan)
      }

      setStatus(`Generated ${scenarioName} scenario.`)
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Scenario generation failed.'
      setStatus(`Could not generate ${scenarioName} scenario: ${message}`)
    } finally {
      setIsScenarioRunning(false)
      setScenarioRunLabel('')
    }
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

  async function shareEntirePlan() {
    if (!plan) {
      return
    }

    setIsSharingPlan(true)
    try {
      const payload: SharedPlanPayload = {
        version: 1,
        created_at: new Date().toISOString(),
        form_state: formState,
        plan,
        validation,
        resolved_credit_map: resolvedMap,
        igetc_tracker: igetcTracker,
        scenarios: savedScenarios,
      }

      const encodedPayload = encodeSharePayload(payload)
      const url = new URL(window.location.href)
      url.searchParams.delete('state')
      url.searchParams.set('shared', encodedPayload)
      const shareLink = url.toString()

      if (shareLink.length > 12000) {
        setStatus('Plan is too large for a single URL link. Reduce saved scenarios and try sharing again.')
        return
      }

      if (navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(shareLink)
        setStatus('Share link copied to clipboard.')
      } else {
        window.prompt('Copy this share link:', shareLink)
        setStatus('Share link generated. Copy it from the prompt.')
      }
    } catch {
      setStatus('Failed to generate share link. Please try again.')
    } finally {
      setIsSharingPlan(false)
    }
  }

  function goNextStep() {
    setCurrentStep((step) => Math.min(5, step + 1))
  }

  function goPreviousStep() {
    setCurrentStep((step) => Math.max(1, step - 1))
  }

  const tourSteps = [
    {
      title: 'Welcome to Plan Workspace',
      body: 'Start in Overview for your progress summary and timeline. Then use the other tabs to make decisions.',
      tab: 'overview' as PlanWorkspaceTab,
    },
    {
      title: 'Run What-if Scenarios',
      body: 'Open Scenarios to generate No AP, Fast Track, and Light Load versions. Compare two options side-by-side.',
      tab: 'scenarios' as PlanWorkspaceTab,
    },
    {
      title: 'Check Requirement Status',
      body: 'Use Requirements to see what is done, planned, and missing in grouped checklists.',
      tab: 'requirements' as PlanWorkspaceTab,
    },
    {
      title: 'Fine-tune the Schedule',
      body: 'Go to Adjust to move courses and rebuild the schedule safely.',
      tab: 'adjust' as PlanWorkspaceTab,
    },
  ]

  const landingTimelineData: TimelineItem[] = [
    {
      id: 1,
      title: 'Planning',
      date: 'Step 1',
      content: 'Collect profile, goals, target school, and constraints for planning.',
      category: 'Planning',
      icon: Calendar,
      relatedIds: [2],
      status: 'completed',
      energy: 100,
    },
    {
      id: 2,
      title: 'Credit Map',
      date: 'Step 2',
      content: 'Resolve AP/IB/CLEP and transfer credits against policy data.',
      category: 'Credit',
      icon: FileText,
      relatedIds: [1, 3],
      status: 'completed',
      energy: 85,
    },
    {
      id: 3,
      title: 'Generate Plan',
      date: 'Step 3',
      content: 'Build and validate a term-by-term schedule with AI optimization.',
      category: 'Scheduling',
      icon: Code,
      relatedIds: [2, 4],
      status: 'in-progress',
      energy: 72,
    },
    {
      id: 4,
      title: 'Scenario Diff',
      date: 'Step 4',
      content: 'Compare No AP/Fast/Light variants and understand tradeoffs.',
      category: 'Scenarios',
      icon: User,
      relatedIds: [3, 5],
      status: 'pending',
      energy: 45,
    },
    {
      id: 5,
      title: 'Apply Ready',
      date: 'Step 5',
      content: 'Track readiness score, blockers, and finalize the path to submit.',
      category: 'Outcome',
      icon: Clock,
      relatedIds: [4],
      status: 'pending',
      energy: 25,
    },
  ]

  return (
    <>
    <div className="sticky top-0 z-40 border-b border-border bg-panel/95 backdrop-blur">
      <div className="mx-auto flex max-w-7xl flex-col items-start gap-3 px-4 py-3 sm:flex-row sm:flex-wrap sm:items-center sm:justify-between sm:px-6">
        <div className="flex items-center gap-3">
          <div className="h-7 w-0.5 bg-accent" />
          <div>
            <p className="font-serif text-base font-semibold leading-none text-brand">PathwayIQ</p>
            <p className="font-mono text-[10px] uppercase tracking-academic text-muted">College Pathway Platform</p>
          </div>
        </div>
        <nav className="flex w-full flex-wrap gap-1 sm:w-auto sm:justify-end">
          <button className={`min-h-[40px] w-full rounded-md px-4 py-2 text-sm font-medium sm:w-auto ${stage === 'landing' ? 'bg-brand text-white' : 'text-ink hover:bg-base'}`} onClick={() => setStage('landing')}>
            Home
          </button>
          <button
            className={`min-h-[40px] w-full rounded-md px-4 py-2 text-sm font-medium sm:w-auto ${stage !== 'landing' && stage !== 'plan' ? 'bg-brand text-white' : 'text-ink hover:bg-base'}`}
            onClick={() => setStage('intake')}
          >
            Planner
          </button>
          <button
            className={`min-h-[40px] w-full rounded-md px-4 py-2 text-sm font-medium sm:w-auto ${stage === 'plan' && planWorkspaceTab === 'scenarios' ? 'bg-brand text-white' : 'text-ink hover:bg-base'} disabled:opacity-40`}
            disabled={!plan}
            onClick={() => {
              if (!plan) return
              setStage('plan')
              setPlanWorkspaceTab('scenarios')
            }}
          >
            Scenarios
          </button>
          <button
            className={`min-h-[40px] w-full rounded-md px-4 py-2 text-sm font-medium sm:w-auto ${stage === 'plan' && planWorkspaceTab === 'requirements' ? 'bg-brand text-white' : 'text-ink hover:bg-base'} disabled:opacity-40`}
            disabled={!plan}
            onClick={() => {
              if (!plan) return
              setStage('plan')
              setPlanWorkspaceTab('requirements')
            }}
          >
            Requirements
          </button>
        </nav>
      </div>
    </div>

    <main className="mx-auto max-w-7xl px-4 py-6 text-ink sm:px-6">
      {stage !== 'landing' && (
      <header className="mb-8 rounded-2xl border border-border bg-panel p-6 sm:p-8">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="font-mono text-[10px] uppercase tracking-academic text-brand">PathwayIQ</p>
            <h1 className="mt-2 font-serif text-3xl font-semibold sm:text-4xl">AI-Powered College Pathway Planner</h1>
            <p className="mt-3 max-w-3xl text-sm text-muted">
              5-step intake → credit resolution summary → full pathway timeline.
            </p>
          </div>
          <button className="min-h-[44px] rounded-lg border border-accent bg-accent px-4 py-2.5 text-sm font-medium text-white hover:bg-accent/90" onClick={applyPrdExamplePreset}>
            Load PRD Example
          </button>
        </div>
        <p className="mt-4 font-mono text-xs text-accent">→ {status}</p>

        <div className="mt-4 flex flex-wrap gap-1.5 text-xs">
          {['intake', 'loading', 'credit', 'plan'].map((item) => (
            <span
              key={item}
              className={`rounded-md border px-3 py-1 font-mono text-[10px] uppercase tracking-wide ${stage === item ? 'border-brand bg-brand text-white' : 'border-border text-muted'}`}
            >
              {item === 'intake' ? 'Intake' : item === 'loading' ? 'Calculating' : item === 'credit' ? 'Credit Summary' : 'Full Plan'}
            </span>
          ))}
        </div>
      </header>
      )}

      {stage === 'landing' && (
        <section className="space-y-6">
          <AnimatedHero
            onStartPlanning={() => {
              setStage('intake')
              setCurrentStep(1)
            }}
            onExploreDemo={applyPrdExamplePreset}
            canResume={Boolean(plan)}
            onResumeLastPlan={() => {
              setStage('plan')
              setPlanWorkspaceTab('overview')
            }}
          />

          <div className="grid gap-4 md:grid-cols-3">
            <article className="rounded-xl border border-border bg-panel p-5">
              <p className="font-mono text-[10px] uppercase tracking-academic text-brand">Readiness Intelligence</p>
              <h3 className="mt-2 font-serif text-lg font-semibold">Score + Risk Forecast</h3>
              <p className="mt-2 text-sm text-muted">See one readiness score per target school/major with blockers, overload, and timeline reasons.</p>
            </article>
            <article className="rounded-xl border border-border bg-panel p-5">
              <p className="font-mono text-[10px] uppercase tracking-academic text-brand">Scenario Studio</p>
              <h3 className="mt-2 font-serif text-lg font-semibold">What-if Diffing</h3>
              <p className="mt-2 text-sm text-muted">Generate No AP/Fast/Light variants and compare added, removed, moved classes with metric deltas.</p>
            </article>
            <article className="rounded-xl border border-border bg-panel p-5">
              <p className="font-mono text-[10px] uppercase tracking-academic text-brand">Requirement Clarity</p>
              <h3 className="mt-2 font-serif text-lg font-semibold">Progress by Category</h3>
              <p className="mt-2 text-sm text-muted">Track done, planned, and missing requirements in grouped chips instead of dense technical tables.</p>
            </article>
          </div>

          <div className="rounded-xl border border-border bg-panel p-5">
            <p className="font-serif text-sm font-semibold">How it works</p>
            <div className="mt-3 grid gap-3 text-sm md:grid-cols-4">
              <div className="rounded-lg border border-border bg-base p-3"><span className="font-mono text-[10px] text-brand">01 —</span><br /><span className="mt-1 block">Enter profile, target school, and major.</span></div>
              <div className="rounded-lg border border-border bg-base p-3"><span className="font-mono text-[10px] text-brand">02 —</span><br /><span className="mt-1 block">Resolve AP/IB/CLEP and transfer credit.</span></div>
              <div className="rounded-lg border border-border bg-base p-3"><span className="font-mono text-[10px] text-brand">03 —</span><br /><span className="mt-1 block">Generate optimized schedule and risk score.</span></div>
              <div className="rounded-lg border border-border bg-base p-3"><span className="font-mono text-[10px] text-brand">04 —</span><br /><span className="mt-1 block">Compare scenarios and adjust before exporting.</span></div>
            </div>
          </div>

          <div className="rounded-xl border border-border bg-panel p-3 md:p-5">
            <p className="px-2 font-mono text-[10px] uppercase tracking-academic text-brand">Pathway Milestones</p>
            <h3 className="px-2 pt-2 font-serif text-xl font-semibold">Radial Orbital Timeline</h3>
            <p className="px-2 pt-2 text-sm text-muted">Interactive + animated orbit showing the full journey from intake to admission readiness.</p>
            <div className="mt-3 overflow-hidden rounded-xl">
              <RadialOrbitalTimeline timelineData={landingTimelineData} />
            </div>
          </div>
        </section>
      )}

      {stage === 'intake' && (
        <section className="rounded-2xl border border-border bg-panel p-6 sm:p-8">
          <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="font-mono text-[10px] uppercase tracking-academic text-brand">Step {currentStep} of 5</p>
              <h2 className="mt-1 font-serif text-2xl font-semibold">{stepLabels[currentStep - 1]}</h2>
              <p className="mt-1 text-sm text-muted">Complete this section, then continue to the next step.</p>
            </div>
            <div className="h-0.5 w-56 overflow-hidden rounded-full bg-base">
              <div className="h-full bg-brand transition-all duration-300" style={{ width: `${(currentStep / 5) * 100}%` }} />
            </div>
          </div>

          {currentStep === 1 && (
            <div className="grid gap-4 sm:grid-cols-2">
              <label className="block text-sm font-medium text-ink">
                Current grade level
                <select className="mt-1 w-full rounded-lg border border-border bg-panel p-2 text-ink focus:outline-none focus:ring-2 focus:ring-brand/30" value={formState.grade} onChange={(event) => setFormState((state) => ({ ...state, grade: event.target.value }))}>
                  {gradeOptions.map((grade) => (
                    <option key={grade} value={grade}>{grade}</option>
                  ))}
                </select>
              </label>
              <label className="block text-sm font-medium text-ink">
                Enrollment status
                <select className="mt-1 w-full rounded-lg border border-border bg-panel p-2 text-ink focus:outline-none focus:ring-2 focus:ring-brand/30" value={formState.enrollment} onChange={(event) => setFormState((state) => ({ ...state, enrollment: event.target.value }))}>
                  {enrollmentOptions.map((option) => (
                    <option key={option} value={option}>{option}</option>
                  ))}
                </select>
              </label>
              <label className="block text-sm font-medium text-ink">
                Start term
                <select className="mt-1 w-full rounded-lg border border-border bg-panel p-2 text-ink focus:outline-none focus:ring-2 focus:ring-brand/30" value={formState.startTerm} onChange={(event) => setFormState((state) => ({ ...state, startTerm: event.target.value }))}>
                  {termOptions.map((term) => (
                    <option key={term} value={term}>{term}</option>
                  ))}
                </select>
              </label>
              <label className="block text-sm font-medium text-ink">
                Target graduation term
                <select className="mt-1 w-full rounded-lg border border-border bg-panel p-2 text-ink focus:outline-none focus:ring-2 focus:ring-brand/30" value={formState.gradTerm} onChange={(event) => setFormState((state) => ({ ...state, gradTerm: event.target.value }))}>
                  {termOptions.map((term) => (
                    <option key={term} value={term}>{term}</option>
                  ))}
                </select>
              </label>
            </div>
          )}

          {currentStep === 2 && (
            <div>
              <h3 className="font-serif text-lg font-semibold">AP / IB / CLEP Credit Bank</h3>
              <div className="mt-3 space-y-3">
                {exams.map((exam) => (
                  <div key={exam.id} className="grid gap-2 rounded-xl border border-border bg-white p-3 sm:grid-cols-5">
                    <select className="rounded-lg border border-border bg-panel p-2 text-ink focus:outline-none focus:ring-2 focus:ring-brand/30" value={exam.exam_type} onChange={(event) => updateExam(exam.id, { exam_type: event.target.value as ExamInput['exam_type'] })}>
                      <option value="AP">AP</option>
                      <option value="IB">IB</option>
                      <option value="CLEP">CLEP</option>
                    </select>
                    <select className="rounded-lg border border-border bg-panel p-2 text-ink focus:outline-none focus:ring-2 focus:ring-brand/30 sm:col-span-2" value={exam.exam_name} onChange={(event) => updateExam(exam.id, { exam_name: event.target.value })}>
                      {examCatalog[exam.exam_type].map((name) => (
                        <option key={name} value={name}>{name}</option>
                      ))}
                    </select>
                    <select className="rounded-lg border border-border bg-panel p-2 text-ink focus:outline-none focus:ring-2 focus:ring-brand/30" value={exam.status} onChange={(event) => updateExam(exam.id, { status: event.target.value as ExamInput['status'] })}>
                      <option value="earned">Score earned</option>
                      <option value="pending">Score pending</option>
                    </select>
                    <div className="flex gap-2">
                      <input className="w-full rounded-lg border border-border bg-panel p-2 text-ink focus:outline-none focus:ring-2 focus:ring-brand/30" placeholder="Score" value={exam.score} disabled={exam.status === 'pending'} onChange={(event) => updateExam(exam.id, { score: event.target.value })} />
                      <button className="rounded-lg border border-border bg-base px-3 text-sm font-medium text-ink hover:bg-ink/5 transition-colors" onClick={() => removeExam(exam.id)}>Remove</button>
                    </div>
                  </div>
                ))}
              </div>

              <button className="mt-3 rounded-lg border border-border bg-base px-3 py-2 text-sm font-medium text-ink hover:bg-ink/5 transition-colors" onClick={addExam}>
                Add Exam
              </button>
            </div>
          )}

          {currentStep === 3 && (
            <div className="grid gap-4 sm:grid-cols-2">
              <label className="block text-sm font-medium text-ink sm:col-span-2">
                Pathway option
                <select className="mt-1 w-full rounded-lg border border-border bg-panel p-2 text-ink focus:outline-none focus:ring-2 focus:ring-brand/30" value={formState.pathway} onChange={(event) => setFormState((state) => ({ ...state, pathway: event.target.value as PathwayType }))}>
                  {pathwayOptions.map((option) => (
                    <option key={option.value} value={option.value}>{option.label}</option>
                  ))}
                </select>
              </label>

              {formState.pathway === 'cc_transfer' && (
                <label className="block text-sm font-medium text-ink sm:col-span-2">
                  Community college for transfer path
                  <select className="mt-1 w-full rounded-lg border border-border bg-panel p-2 text-ink focus:outline-none focus:ring-2 focus:ring-brand/30" value={formState.ccId} onChange={(event) => setFormState((state) => ({ ...state, ccId: event.target.value }))}>
                    <option value="lpc">Las Positas College</option>
                    <option value="sjdc">San Joaquin Delta College</option>
                  </select>
                </label>
              )}
            </div>
          )}

          {currentStep === 4 && (
            <div className="grid gap-4 sm:grid-cols-2">
              <label className="block text-sm font-medium text-ink">
                Target university
                <select className="mt-1 w-full rounded-lg border border-border bg-panel p-2 text-ink focus:outline-none focus:ring-2 focus:ring-brand/30" value={formState.schoolId} onChange={(event) => setFormState((state) => ({ ...state, schoolId: event.target.value }))}>
                  {schools.map((school) => (
                    <option key={school.school_id} value={school.school_id}>{school.name}</option>
                  ))}
                </select>
              </label>
              <label className="block text-sm font-medium text-ink">
                Target major
                <select className="mt-1 w-full rounded-lg border border-border bg-panel p-2 text-ink focus:outline-none focus:ring-2 focus:ring-brand/30" value={formState.majorId} onChange={(event) => setFormState((state) => ({ ...state, majorId: event.target.value }))}>
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
                <label className="block text-sm font-medium text-ink">
                  Max units (regular)
                  <select className="mt-1 w-full rounded-lg border border-border bg-panel p-2 text-ink focus:outline-none focus:ring-2 focus:ring-brand/30" value={formState.maxUnitsRegular} onChange={(event) => setFormState((state) => ({ ...state, maxUnitsRegular: Number(event.target.value) }))}>
                    {regularUnitOptions.map((option) => (
                      <option key={option} value={option}>{option}</option>
                    ))}
                  </select>
                </label>
                <label className="block text-sm font-medium text-ink">
                  Max units (HS active)
                  <select className="mt-1 w-full rounded-lg border border-border bg-panel p-2 text-ink focus:outline-none focus:ring-2 focus:ring-brand/30" value={formState.maxUnitsHs} onChange={(event) => setFormState((state) => ({ ...state, maxUnitsHs: Number(event.target.value) }))}>
                    {hsUnitOptions.map((option) => (
                      <option key={option} value={option}>{option}</option>
                    ))}
                  </select>
                </label>
                <label className="block text-sm font-medium text-ink">
                  HS-active terms
                  <select className="mt-1 w-full rounded-lg border border-border bg-panel p-2 text-ink focus:outline-none focus:ring-2 focus:ring-brand/30" value={formState.hsActiveTerms} onChange={(event) => setFormState((state) => ({ ...state, hsActiveTerms: Number(event.target.value) }))}>
                    {hsActiveTermOptions.map((option) => (
                      <option key={option} value={option}>{option}</option>
                    ))}
                  </select>
                </label>
                <label className="block text-sm font-medium text-ink">
                  Planning priority
                  <select className="mt-1 w-full rounded-lg border border-border bg-panel p-2 text-ink focus:outline-none focus:ring-2 focus:ring-brand/30" value={formState.priority} onChange={(event) => setFormState((state) => ({ ...state, priority: event.target.value as PriorityType }))}>
                    {priorityOptions.map((option) => (
                      <option key={option.value} value={option.value}>{option.label}</option>
                    ))}
                  </select>
                </label>
              </div>

              <div className="rounded-xl border border-border bg-base p-4">
                <p className="text-sm font-medium">Blocked Terms</p>
                <p className="text-xs text-muted">Select semesters to skip.</p>
                <div className="mt-2 max-h-36 overflow-y-auto pr-1">
                  <div className="grid gap-2 sm:grid-cols-3">
                    {termOptions.map((term) => (
                      <label key={term} className="flex items-center gap-2 rounded-lg border border-border px-2 py-1 text-sm">
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
            <button className="rounded-lg border border-border bg-base px-4 py-2 text-sm font-medium text-ink hover:bg-ink/5 transition-colors disabled:opacity-40" disabled={currentStep === 1} onClick={goPreviousStep}>
              Back
            </button>

            {currentStep < 5 ? (
              <button className="rounded-lg bg-brand px-4 py-2 text-sm font-medium text-white hover:bg-brand/90 transition-colors" onClick={goNextStep}>
                Continue
              </button>
            ) : (
              <button className="rounded-lg bg-brand px-5 py-2 text-sm font-medium text-white hover:bg-brand/90 transition-colors" onClick={() => void runPlanner()}>
                Build My Plan
              </button>
            )}
          </div>
        </section>
      )}

      {stage === 'loading' && (
        <section className="rounded-2xl border border-border bg-panel p-12 text-center">
          <p className="font-mono text-[10px] uppercase tracking-academic text-brand">Processing</p>
          <h2 className="mt-2 font-serif text-2xl font-semibold">Calculating your pathway...</h2>
          <p className="mt-2 text-sm text-muted">Resolving credit policies, prerequisites, and term-by-term sequencing.</p>
          <p className="mt-2 font-mono text-xs text-brand">{loadingDetails}</p>
          <div className="mx-auto mt-8 h-0.5 max-w-md overflow-hidden rounded-full bg-base">
            <div className="h-full w-2/3 animate-pulse bg-brand" />
          </div>
        </section>
      )}

      {stage === 'credit' && (
        <section className="space-y-6">
          <div className="rounded-2xl border border-border bg-panel p-6 sm:p-8">
            <p className="font-mono text-[10px] uppercase tracking-academic text-brand">Step 2 of 3</p>
            <h2 className="mt-1 font-serif text-2xl font-semibold">Credit Resolution Summary</h2>
            {!resolvedMap && <p className="mt-2 text-sm text-muted">No credit data available.</p>}
            {resolvedMap && (
              <div className="mt-4 grid gap-4 lg:grid-cols-2">
                <div className="rounded-xl border border-border bg-base p-4 text-sm">
                  <p><strong>Units waived:</strong> {resolvedMap.units_waived}</p>
                  <p className="mt-1"><strong>Courses satisfied:</strong> {resolvedMap.satisfied_courses.join(', ') || 'None'}</p>
                  <p className="mt-1"><strong>GE areas satisfied:</strong> {resolvedMap.satisfied_ge_areas.join(', ') || 'None'}</p>
                  <p className="mt-1"><strong>Pending exams:</strong> {resolvedMap.pending_exam_names.join(', ') || 'None'}</p>
                </div>
                <div className="rounded-xl border border-border bg-base p-4 text-sm">
                  <p className="font-semibold">Credit assumptions</p>
                  <ul className="mt-2 space-y-1">
                    {resolvedMap.condition_notes.map((note) => (
                      <li key={note} className="text-amber-700">• {note}</li>
                    ))}
                    {!resolvedMap.condition_notes.length && <li className="text-muted">No conditional notes.</li>}
                  </ul>
                </div>
              </div>
            )}

            {!!resolvedItems.length && (
              <div className="mt-4 rounded-xl border border-border bg-white p-4 text-sm">
                <p className="font-semibold">Resolved Credit Details (Source + Policy Year)</p>
                <div className="mt-3 overflow-x-auto">
                  <table className="min-w-full text-left text-sm">
                    <thead>
                      <tr className="border-b border-border text-muted">
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
                            <div className="text-xs text-muted">Min score {item.min_score} • {item.units_granted} units</div>
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
              <div className="mt-4 rounded-xl border border-border bg-white p-4 text-sm">
                <p className="font-semibold">Pending-score what-if impacts</p>
                <ul className="mt-2 space-y-2">
                  {pendingScenarios.map((scenario) => (
                    <li key={scenario.exam_name}>
                      <p className="font-medium">{scenario.exam_name}</p>
                      <p className="text-muted">If no credit: add {scenario.added_courses_if_no_credit.join(', ') || 'No additional courses'}</p>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            <div className="mt-6 flex flex-wrap gap-3">
              <button
                className="rounded-lg bg-brand px-4 py-2 text-sm font-medium text-white hover:bg-brand/90 transition-colors"
                onClick={() => {
                  setPlanWorkspaceTab('overview')
                  setStage('plan')
                }}
              >
                Continue to Full Plan
              </button>
              <button className="rounded-lg border border-border bg-base px-4 py-2 text-sm font-medium text-ink hover:bg-ink/5 transition-colors" onClick={startOver}>
                Edit Intake
              </button>
            </div>
          </div>
        </section>
      )}

      {stage === 'plan' && (
        <section className="space-y-6 pb-28 md:pb-0">
          <div className="rounded-2xl border border-border bg-panel p-6 sm:p-8">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <h2 className="font-serif text-2xl font-semibold">Full Pathway Plan</h2>
                <p className="mt-1 text-sm text-muted">
                  School: {selectedSchool?.name ?? formState.schoolId} • Term system: {selectedSchool?.term_system ?? 'unknown'}
                </p>
              </div>
              <div className="hidden gap-2 sm:flex">
                <button className="rounded-lg border border-accent bg-accent px-4 py-2 text-sm font-medium text-white hover:bg-accent/90 transition-colors disabled:opacity-40" disabled={!pendingScenarios.length || !plan} onClick={() => void runWithoutPendingCredit()}>
                  Toggle Without Pending Credit
                </button>
                <button className="rounded-lg border border-brand bg-brand px-4 py-2 text-sm font-medium text-white hover:bg-brand/90 transition-colors disabled:opacity-40" disabled={!plan || isSharingPlan} onClick={() => void shareEntirePlan()}>
                  {isSharingPlan ? 'Preparing link...' : 'Share Entire Plan'}
                </button>
                <button className="rounded-lg border border-ink bg-ink px-4 py-2 text-sm font-medium text-white hover:bg-ink/80 transition-colors disabled:opacity-40" disabled={!plan} onClick={() => void downloadPdf()}>
                  Export PDF
                </button>
              </div>
            </div>

            {!plan && <p className="mt-4 text-sm text-muted">No plan generated yet.</p>}
            {plan && (
              <>
                <div className="mt-4 rounded-xl border border-border bg-white p-3 text-sm">
                  <p className="font-mono text-[10px] uppercase tracking-academic text-muted">Schedule generation mode</p>
                  {plan.generation_mode === 'gemini_optimized' && (
                    <p className="mt-1 text-emerald-700">Gemini was used to optimize term assignments (validated before returning).</p>
                  )}
                  {plan.generation_mode === 'deterministic_fallback' && (
                    <p className="mt-1 text-amber-700">Gemini attempted optimization, but result was rejected by validation. Deterministic schedule is shown.</p>
                  )}
                  {plan.generation_mode === 'deterministic' && (
                    <p className="mt-1 text-ink/70">Deterministic scheduler generated this plan (Gemini scheduling not applied). See Warnings for the exact reason.</p>
                  )}
                </div>

                <div className="mt-4 flex flex-wrap items-center gap-2">
                  <button
                    title="Summary, timeline, and next action"
                    className={`rounded-md border px-4 py-2 text-sm font-medium transition-colors ${planWorkspaceTab === 'overview' ? 'border-brand bg-brand text-white' : 'border-border text-muted hover:text-ink hover:border-ink/30'}`}
                    onClick={() => setPlanWorkspaceTab('overview')}
                  >
                    Overview
                  </button>
                  <button
                    title="Generate and compare what-if scenarios"
                    className={`rounded-md border px-4 py-2 text-sm font-medium transition-colors ${planWorkspaceTab === 'scenarios' ? 'border-brand bg-brand text-white' : 'border-border text-muted hover:text-ink hover:border-ink/30'}`}
                    onClick={() => setPlanWorkspaceTab('scenarios')}
                  >
                    Scenarios
                  </button>
                  <button
                    title="Track requirements by done, planned, and missing"
                    className={`rounded-md border px-4 py-2 text-sm font-medium transition-colors ${planWorkspaceTab === 'requirements' ? 'border-brand bg-brand text-white' : 'border-border text-muted hover:text-ink hover:border-ink/30'}`}
                    onClick={() => setPlanWorkspaceTab('requirements')}
                  >
                    Requirements
                  </button>
                  <button
                    title="Rebuild schedule with manual changes"
                    className={`rounded-md border px-4 py-2 text-sm font-medium transition-colors ${planWorkspaceTab === 'adjust' ? 'border-brand bg-brand text-white' : 'border-border text-muted hover:text-ink hover:border-ink/30'}`}
                    onClick={() => setPlanWorkspaceTab('adjust')}
                  >
                    Adjust
                  </button>
                  <button
                    title="Evidence and policy sources used by planner"
                    className={`rounded-md border px-4 py-2 text-sm font-medium transition-colors ${planWorkspaceTab === 'evidence' ? 'border-brand bg-brand text-white' : 'border-border text-muted hover:text-ink hover:border-ink/30'}`}
                    onClick={() => setPlanWorkspaceTab('evidence')}
                  >
                    Evidence
                  </button>
                  <button
                    className="ml-auto rounded-md border border-border px-3 py-2 font-mono text-[10px] uppercase tracking-wide text-muted hover:border-ink/30 transition-colors"
                    onClick={() => setShowTechnicalDetails((value) => !value)}
                  >
                    {showTechnicalDetails ? 'Hide technical details' : 'Show technical details'}
                  </button>
                </div>

                {tourVisible && tourSteps[tourStep] && (
                  <div className="mt-3 rounded-xl border border-brand/30 bg-brand/5 p-4 text-sm">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div>
                        <p className="font-semibold">{tourSteps[tourStep].title}</p>
                        <p className="mt-1 text-ink/70">{tourSteps[tourStep].body}</p>
                        <p className="mt-1 text-xs text-muted">Step {tourStep + 1} of {tourSteps.length}</p>
                      </div>
                      <div className="flex gap-2">
                        <button className="rounded-md border border-border bg-base px-3 py-1.5 text-xs font-medium text-ink hover:bg-ink/5 transition-colors" onClick={closeTour}>
                          Skip tour
                        </button>
                        <button className="rounded-md bg-brand px-3 py-1.5 text-xs font-medium text-white hover:bg-brand/90 transition-colors" onClick={nextTourStep}>
                          {tourStep + 1 === tourSteps.length ? 'Finish' : 'Next'}
                        </button>
                      </div>
                    </div>
                  </div>
                )}

                {planWorkspaceTab === 'overview' && (
                <div className="mt-4 space-y-4">
                  {admissionsReadiness && (
                    <div className="rounded-xl border border-border bg-base p-4">
                      <div className="flex flex-wrap items-center justify-between gap-3">
                        <div>
                          <h3 className="font-serif font-semibold">Admissions Readiness Score</h3>
                          <p className="mt-1 text-xs text-muted">
                            Target: {selectedSchool?.name ?? formState.schoolId} • {selectedMajor?.major_name ?? formState.majorId}
                          </p>
                        </div>
                        <div className="rounded-lg border border-border bg-base px-4 py-2 text-center">
                          <p className="text-2xl font-semibold">{admissionsReadiness.score}</p>
                          <p className="text-xs text-muted">/100</p>
                        </div>
                      </div>

                      <div className="mt-3 grid gap-2 sm:grid-cols-4">
                        <p className="rounded-md bg-base p-2 text-sm"><strong>Risk level:</strong> {admissionsReadiness.riskLevel}</p>
                        <p className="rounded-md bg-base p-2 text-sm"><strong>Blockers:</strong> {admissionsReadiness.blockersCount}</p>
                        <p className="rounded-md bg-base p-2 text-sm"><strong>Timeline late terms:</strong> {admissionsReadiness.lateTermsCount}</p>
                        <p className="rounded-md bg-base p-2 text-sm"><strong>Overload terms:</strong> {admissionsReadiness.overloadTermsCount}</p>
                      </div>

                      <div className="mt-3">
                        <p className="text-sm font-medium">Risk forecast — why this score</p>
                        <ul className="mt-2 space-y-2 text-sm">
                          {admissionsReadiness.reasons.map((reason) => (
                            <li key={reason.label} className="rounded-lg border border-border bg-base p-3">
                              <div className="flex items-center justify-between gap-2">
                                <p className="font-medium">{reason.label}</p>
                                <span
                                  className={`rounded-sm border px-2 py-0.5 font-mono text-[10px] uppercase tracking-wide ${
                                    reason.severity === 'high'
                                      ? 'border-red-300 bg-red-50 text-red-700'
                                      : reason.severity === 'medium'
                                        ? 'border-amber-300 bg-amber-50 text-amber-700'
                                        : 'border-green-300 bg-green-50 text-green-700'
                                  }`}
                                >
                                  {reason.severity}
                                </span>
                              </div>
                              <p className="mt-1 text-ink/70">{reason.detail}</p>
                            </li>
                          ))}
                        </ul>
                      </div>
                    </div>
                  )}

                  {guidedNarrative && (
                    <div className="rounded-xl border border-border bg-base p-4">
                      <h3 className="font-serif font-semibold">Guided Plan Workspace</h3>
                      <div className="mt-3 grid gap-3 lg:grid-cols-3">
                        <div className="rounded-lg border border-border bg-base p-3 text-sm">
                          <p className="font-medium">What’s done</p>
                          <ul className="mt-2 space-y-1 text-ink/70">
                            {guidedNarrative.done.map((item) => (
                              <li key={item}>• {item}</li>
                            ))}
                          </ul>
                        </div>
                        <div className="rounded-lg border border-border bg-base p-3 text-sm">
                          <p className="font-medium">What’s left</p>
                          <ul className="mt-2 space-y-1 text-ink/70">
                            {guidedNarrative.left.map((item) => (
                              <li key={item}>• {item}</li>
                            ))}
                          </ul>
                        </div>
                        <div className="rounded-lg border border-border bg-base p-3 text-sm">
                          <p className="font-medium">Next best action</p>
                          <p className="mt-2 text-ink/70">{guidedNarrative.nextAction}</p>
                          <p className="mt-3 text-xs text-muted">Missing requirements in current horizon: {guidedNarrative.missingCount}</p>
                        </div>
                      </div>
                    </div>
                  )}

                  <div className="rounded-xl border border-border bg-base p-4 text-sm">
                    <p className="font-serif font-semibold">Quick Guide</p>
                    <ul className="mt-2 space-y-1 text-ink/70">
                      <li>• Use <strong>Scenarios</strong> to generate what-if plans like No AP, Fast Track, and Light Load.</li>
                      <li>• Use <strong>Requirements</strong> to see done, planned, and missing requirements grouped by category.</li>
                      <li>• Use <strong>Adjust</strong> to manually move courses and rebuild.</li>
                    </ul>
                  </div>

                  <div className="grid grid-cols-1 gap-3 md:flex md:gap-3 md:overflow-x-auto md:pb-2">
                    {plan.terms.map((term) => (
                      <article key={term.term_id} className="rounded-xl border border-border bg-panel p-4 md:min-w-72">
                        <p className="text-sm font-semibold">{term.term_label}</p>
                        <p className="text-xs text-muted">
                          {term.term_id} • {term.units} units {term.hs_active ? '• HS active cap' : ''}
                        </p>
                        <ul className="mt-3 space-y-2 text-sm">
                          {term.courses.map((course) => (
                            <li key={`${term.term_id}-${course.course_id}`} className="rounded-md border border-border bg-base p-2 font-mono text-xs">
                              <span className="font-semibold">{course.course_id}</span> {course.course_name}
                            </li>
                          ))}
                          {!term.courses.length && <li className="text-muted">No courses</li>}
                        </ul>
                        {term.notes.map((note) => (
                          <p key={`${term.term_id}-${note}`} className="mt-2 text-xs text-amber-700">{note}</p>
                        ))}
                      </article>
                    ))}
                  </div>
                </div>
                )}

                {planWorkspaceTab === 'scenarios' && (
                <div className="mt-6 rounded-xl border border-border bg-white p-4">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <h3 className="font-serif font-semibold">Scenario Planner</h3>
                    <div className="flex flex-wrap gap-2">
                      <button className="rounded-md border border-border bg-base px-3 py-2 text-xs font-medium text-ink hover:bg-ink/5 transition-colors" title="Save current plan as a compare snapshot" onClick={() => saveScenarioSnapshot('Current Plan')}>
                        Save Current
                      </button>
                      <button className="rounded-md border border-ink bg-ink px-3 py-2 text-xs font-medium text-white hover:bg-ink/80 transition-colors disabled:opacity-40" title="Remove AP exams from inputs and regenerate" disabled={isScenarioRunning} onClick={() => void buildScenario('no-ap')}>
                        No AP
                      </button>
                      <button className="rounded-md border border-ink bg-ink px-3 py-2 text-xs font-medium text-white hover:bg-ink/80 transition-colors disabled:opacity-40" title="Increase speed and unit cap" disabled={isScenarioRunning} onClick={() => void buildScenario('fast-track')}>
                        Fast Track
                      </button>
                      <button className="rounded-md border border-ink bg-ink px-3 py-2 text-xs font-medium text-white hover:bg-ink/80 transition-colors disabled:opacity-40" title="Reduce term load for easier pacing" disabled={isScenarioRunning} onClick={() => void buildScenario('light-load')}>
                        Light Load
                      </button>
                      <button className="rounded-md border border-amber-300 bg-amber-50 px-3 py-2 text-xs font-medium text-amber-800 hover:bg-amber-100 transition-colors" title="Force unlock buttons if a request hangs" onClick={unlockScenarioButtons}>
                        Unlock
                      </button>
                    </div>
                  </div>

                  <p className="mt-2 text-xs text-muted">Tip: Run one scenario, then compare it against baseline using the selectors below.</p>
                  {isScenarioRunning && <p className="mt-2 text-xs text-amber-700">Running scenario: {scenarioRunLabel}...</p>}

                  <div className="mt-3 grid gap-2 md:grid-cols-3">
                    <select className="rounded-lg border border-border bg-panel p-2 text-sm text-ink focus:outline-none focus:ring-2 focus:ring-brand/30" title="Choose left side scenario" value={compareLeftScenarioId} onChange={(event) => setCompareLeftScenarioId(event.target.value)}>
                      <option value="">Left scenario</option>
                      {savedScenarios.map((scenario) => (
                        <option key={`left-${scenario.id}`} value={scenario.id}>
                          {scenario.name}
                        </option>
                      ))}
                    </select>
                    <select className="rounded-lg border border-border bg-panel p-2 text-sm text-ink focus:outline-none focus:ring-2 focus:ring-brand/30" title="Choose right side scenario" value={compareRightScenarioId} onChange={(event) => setCompareRightScenarioId(event.target.value)}>
                      <option value="">Right scenario</option>
                      {savedScenarios.map((scenario) => (
                        <option key={`right-${scenario.id}`} value={scenario.id}>
                          {scenario.name}
                        </option>
                      ))}
                    </select>
                    <select className="rounded-lg border border-border bg-panel p-2 text-sm text-ink focus:outline-none focus:ring-2 focus:ring-brand/30" title="Load a saved scenario into the main planner" onChange={(event) => loadScenario(event.target.value)} defaultValue="">
                      <option value="">Load scenario into planner</option>
                      {savedScenarios.map((scenario) => (
                        <option key={`load-${scenario.id}`} value={scenario.id}>
                          {scenario.name}
                        </option>
                      ))}
                    </select>
                  </div>

                  {compareLeftScenario && compareRightScenario && (
                    <div className="mt-4 space-y-3">
                      <div className="grid gap-3 lg:grid-cols-2">
                        <div className="rounded-lg border border-border p-3 text-sm">
                          <p className="font-medium">{compareLeftScenario.name}</p>
                          <p className="mt-1 text-ink/70">Coverage: {compareLeftScenario.plan.admission_checklist.major_prep_coverage_pct}%</p>
                          <p className="text-ink/70">Units: {compareLeftScenario.plan.admission_checklist.transferable_units}</p>
                          <p className="text-ink/70">Blockers: {compareLeftScenario.plan.admission_checklist.missing_blockers.length}</p>
                          <p className="text-ink/70">Terms used: {compareLeftScenario.plan.terms.filter((term) => term.courses.length > 0).length}</p>
                        </div>
                        <div className="rounded-lg border border-border p-3 text-sm">
                          <p className="font-medium">{compareRightScenario.name}</p>
                          <p className="mt-1 text-ink/70">Coverage: {compareRightScenario.plan.admission_checklist.major_prep_coverage_pct}%</p>
                          <p className="text-ink/70">Units: {compareRightScenario.plan.admission_checklist.transferable_units}</p>
                          <p className="text-ink/70">Blockers: {compareRightScenario.plan.admission_checklist.missing_blockers.length}</p>
                          <p className="text-ink/70">Terms used: {compareRightScenario.plan.terms.filter((term) => term.courses.length > 0).length}</p>
                        </div>
                      </div>

                      {scenarioDiff && (
                        <div className="rounded-lg border border-border p-3 text-sm">
                          <p className="font-medium">Diff ({compareLeftScenario.name} → {compareRightScenario.name})</p>
                          <div className="mt-2 grid gap-2 sm:grid-cols-3">
                            <p className="rounded-md bg-base p-2">Coverage delta: {scenarioDiff.coverageDelta >= 0 ? '+' : ''}{scenarioDiff.coverageDelta}%</p>
                            <p className="rounded-md bg-base p-2">Units delta: {scenarioDiff.unitsDelta >= 0 ? '+' : ''}{scenarioDiff.unitsDelta}</p>
                            <p className="rounded-md bg-base p-2">Blockers delta: {scenarioDiff.blockerDelta >= 0 ? '+' : ''}{scenarioDiff.blockerDelta}</p>
                          </div>

                          <div className="mt-3 grid gap-3 lg:grid-cols-3">
                            <div>
                              <p className="font-medium text-emerald-700">Added in right ({scenarioDiff.addedInRight.length})</p>
                              <ul className="mt-1 max-h-40 space-y-1 overflow-auto text-xs text-ink/70">
                                {scenarioDiff.addedInRight.map((item) => (
                                  <li key={`added-${item.course_id}`}>• {item.course_id} ({item.term_label})</li>
                                ))}
                                {!scenarioDiff.addedInRight.length && <li>None</li>}
                              </ul>
                            </div>
                            <div>
                              <p className="font-medium text-rose-700">Removed in right ({scenarioDiff.removedInRight.length})</p>
                              <ul className="mt-1 max-h-40 space-y-1 overflow-auto text-xs text-ink/70">
                                {scenarioDiff.removedInRight.map((item) => (
                                  <li key={`removed-${item.course_id}`}>• {item.course_id} ({item.term_label})</li>
                                ))}
                                {!scenarioDiff.removedInRight.length && <li>None</li>}
                              </ul>
                            </div>
                            <div>
                              <p className="font-medium text-sky-700">Moved term ({scenarioDiff.movedInRight.length})</p>
                              <ul className="mt-1 max-h-40 space-y-1 overflow-auto text-xs text-ink/70">
                                {scenarioDiff.movedInRight.map((item) => (
                                  <li key={`moved-${item.course_id}`}>• {item.course_id}: {item.from_term} → {item.to_term}</li>
                                ))}
                                {!scenarioDiff.movedInRight.length && <li>None</li>}
                              </ul>
                            </div>
                          </div>

                          <div className="mt-3 grid gap-3 sm:grid-cols-2">
                            <div>
                              <p className="font-medium text-rose-700">New blockers in right</p>
                              <ul className="mt-1 space-y-1 text-xs text-ink/70">
                                {scenarioDiff.blockersAddedInRight.map((item) => (
                                  <li key={`new-blocker-${item}`}>• {item}</li>
                                ))}
                                {!scenarioDiff.blockersAddedInRight.length && <li>None</li>}
                              </ul>
                            </div>
                            <div>
                              <p className="font-medium text-emerald-700">Blockers resolved in right</p>
                              <ul className="mt-1 space-y-1 text-xs text-ink/70">
                                {scenarioDiff.blockersRemovedInRight.map((item) => (
                                  <li key={`resolved-blocker-${item}`}>• {item}</li>
                                ))}
                                {!scenarioDiff.blockersRemovedInRight.length && <li>None</li>}
                              </ul>
                            </div>
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </div>
                )}

                {planWorkspaceTab === 'requirements' && (
                <div className="mt-6 rounded-xl border border-border bg-white p-4">
                  <h3 className="font-semibold">Requirement Progress Map</h3>
                  <p className="mt-1 text-xs text-muted">Grouped checklist with status chips for faster review.</p>
                  <div className="mt-3 space-y-3">
                    {requirementProgressGroups.map((group) => (
                      <div key={group.title} className="rounded-lg border border-border p-3">
                        <p className="text-sm font-medium">{group.title}</p>
                        <ul className="mt-2 grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
                          {group.items.map((item, index) => (
                            <li key={`${group.title}-${item.label}-${index}`} className="rounded-lg border border-border bg-base p-2.5 text-sm">
                              <div className="flex items-center justify-between gap-2">
                                <p className="font-medium">{item.label}</p>
                                <span
                                  className={`rounded-sm border px-2 py-0.5 font-mono text-[10px] uppercase tracking-wide ${
                                    item.status === 'done'
                                      ? 'border-green-300 bg-green-50 text-green-700'
                                      : item.status === 'planned'
                                        ? 'border-blue-300 bg-blue-50 text-blue-700'
                                        : 'border-red-300 bg-red-50 text-red-700'
                                  }`}
                                >
                                  {item.status}
                                </span>
                              </div>
                              {item.detail && <p className="mt-1 text-xs text-muted">{item.detail}</p>}
                            </li>
                          ))}
                        </ul>
                      </div>
                    ))}
                  </div>
                </div>
                )}

                {planWorkspaceTab === 'adjust' && (
                <div className="mt-6 grid gap-4 lg:grid-cols-2">
                  <div className="rounded-xl border border-border bg-base p-4">
                    <h3 className="font-semibold">Plan Adjustments</h3>
                    <div className="mt-3 grid gap-2 sm:grid-cols-3">
                      <select className="rounded-lg border border-border bg-panel p-2 text-sm text-ink focus:outline-none focus:ring-2 focus:ring-brand/30" value={moveCourseId} onChange={(event) => setMoveCourseId(event.target.value)}>
                        <option value="">Course</option>
                        {allPlannedCourses.map((course) => (
                          <option key={`${course.term_id}-${course.course_id}`} value={course.course_id}>
                            {course.course_id}
                          </option>
                        ))}
                      </select>
                      <select className="rounded-lg border border-border bg-panel p-2 text-sm text-ink focus:outline-none focus:ring-2 focus:ring-brand/30" value={moveFromTerm} onChange={(event) => setMoveFromTerm(event.target.value)}>
                        <option value="">From term</option>
                        {termIds.map((termId) => (
                          <option key={termId} value={termId}>{termId}</option>
                        ))}
                      </select>
                      <select className="rounded-lg border border-border bg-panel p-2 text-sm text-ink focus:outline-none focus:ring-2 focus:ring-brand/30" value={moveToTerm} onChange={(event) => setMoveToTerm(event.target.value)}>
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
                      <div className="mt-4 border-t border-border pt-3">
                        <p className="text-sm font-semibold">Course-level What-if (LPC articulation swap)</p>
                        <p className="mt-1 text-xs text-muted">Swap a planned UC course with an articulated LPC alternative and revalidate.</p>
                        <div className="mt-2 grid gap-2 sm:grid-cols-2">
                          <select
                            className="rounded-lg border border-border bg-panel p-2 text-sm text-ink focus:outline-none focus:ring-2 focus:ring-brand/30"
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
                          <select className="rounded-lg border border-border bg-panel p-2 text-sm text-ink focus:outline-none focus:ring-2 focus:ring-brand/30" value={swapToCourseId} onChange={(event) => setSwapToCourseId(event.target.value)}>
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

                  <div className="rounded-xl border border-border bg-base p-4">
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
                )}

                {planWorkspaceTab === 'overview' && (
                <div className="mt-6 rounded-xl border border-border bg-white p-4">
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
                )}

                {planWorkspaceTab === 'evidence' && (
                <div className="mt-6 rounded-xl border border-border bg-white p-4">
                  <h3 className="font-semibold">Course Evidence ({allPlannedCourses.length} classes)</h3>
                  <p className="mt-1 text-xs text-muted">Per course: schedule placement, rationale, and source citation.</p>
                  <div className="mt-3 overflow-x-auto">
                    <table className="min-w-full text-left text-sm">
                      <thead>
                        <tr className="border-b border-border text-muted">
                          <th className="px-2 py-2">Term</th>
                          <th className="px-2 py-2">Course ID</th>
                          <th className="px-2 py-2">Course Name</th>
                          <th className="px-2 py-2">Why This Course</th>
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
                            <td className="px-2 py-2">{course.justification}</td>
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
                            <td className="px-2 py-3 text-muted" colSpan={8}>No scheduled classes.</td>
                          </tr>
                        )}
                      </tbody>
                    </table>
                  </div>
                </div>
                )}

                {planWorkspaceTab === 'overview' && showTechnicalDetails && (
                <div className="mt-6 rounded-xl border border-border bg-white p-4">
                  <h3 className="font-semibold">Campus Course Inventory ({selectedSchool?.name ?? formState.schoolId})</h3>
                  <p className="mt-1 text-xs text-muted">
                    Real catalog metadata used by the planner for seasonal offering checks.
                  </p>
                  <div className="mt-3 max-h-72 overflow-y-auto overflow-x-auto">
                    <table className="min-w-full text-left text-sm">
                      <thead>
                        <tr className="border-b border-border text-muted">
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
                            <td className="px-2 py-3 text-muted" colSpan={4}>No course inventory found for selected campus.</td>
                          </tr>
                        )}
                      </tbody>
                    </table>
                  </div>
                </div>
                )}

                {planWorkspaceTab === 'overview' && showTechnicalDetails && (
                <div className="mt-6 grid gap-4 lg:grid-cols-3">
                  <div className="rounded-xl border border-border bg-base p-4">
                    <h3 className="font-semibold">Milestones</h3>
                    <ul className="mt-2 space-y-1 text-sm">
                      {plan.milestones.map((milestone) => (
                        <li key={milestone.milestone_id}>• {milestone.label} ({milestone.status}) in {milestone.term_id}</li>
                      ))}
                      {!plan.milestones.length && <li>None yet</li>}
                    </ul>
                  </div>
                  <div className="rounded-xl border border-border bg-base p-4">
                    <h3 className="font-semibold">Critical Path</h3>
                    <ul className="mt-2 space-y-1 text-sm">
                      {plan.critical_path.map((item) => (
                        <li key={item.course_id}>• {item.course_id}</li>
                      ))}
                    </ul>
                  </div>
                  <div className="rounded-xl border border-border bg-base p-4">
                    <h3 className="font-semibold">Warnings</h3>
                    <ul className="mt-2 space-y-1 text-sm">
                      {plan.warnings.map((warning) => (
                        <li key={warning.code}>• {warning.message}</li>
                      ))}
                      {!plan.warnings.length && <li>No warnings</li>}
                    </ul>
                  </div>
                </div>
                )}

                {planWorkspaceTab === 'overview' && formState.pathway === 'cc_transfer' && (
                  <div className="mt-6 rounded-xl border border-border bg-white p-4">
                    <h3 className="font-semibold">IGETC Tracker</h3>
                    <p className="mt-1 text-xs text-muted">
                      IGETC areas are transfer GE buckets used by UC/CSU articulation.
                    </p>
                    {!igetcTracker && <p className="mt-2 text-sm text-muted">No IGETC tracker data available.</p>}
                    {igetcTracker && (
                      <ul className="mt-3 grid gap-2 text-sm sm:grid-cols-2 lg:grid-cols-4">
                        {igetcTracker.areas.map((area) => (
                          <li key={area.area} className="rounded-lg border border-border bg-base p-2">
                            <p className="font-medium">Area {area.area}: {igetcAreaLabels[area.area] ?? 'General Education Area'}</p>
                            <p className="text-xs text-muted">
                              {area.status === 'satisfied'
                                ? 'Satisfied by existing credit'
                                : area.status === 'planned'
                                  ? 'Planned via course schedule'
                                  : 'Missing'}
                            </p>
                            {area.course_id && <p className="text-xs text-muted">{area.course_id}</p>}
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>
                )}

                {planWorkspaceTab === 'overview' && (
                <div className="mt-6 rounded-xl border border-brand/20 bg-brand/5 p-4 text-sm">
                  <h3 className="font-serif font-semibold">AI Explanation</h3>
                  <pre className="mt-2 whitespace-pre-wrap font-sans text-sm">{plan.explanation_markdown}</pre>
                </div>
                )}

                <div className="fixed inset-x-0 bottom-0 z-30 border-t border-border bg-panel/95 p-3 shadow-soft backdrop-blur md:hidden">
                  <div className="mx-auto max-w-7xl">
                    <div className="grid grid-cols-5 gap-2">
                      <button
                        className={`min-h-[44px] rounded-md border px-2.5 py-2 text-[10px] font-mono uppercase tracking-wide transition-colors ${planWorkspaceTab === 'overview' ? 'border-brand bg-brand text-white' : 'border-border text-muted'}`}
                        onClick={() => setPlanWorkspaceTab('overview')}
                      >
                        Overview
                      </button>
                      <button
                        className={`min-h-[44px] rounded-md border px-2.5 py-2 text-[10px] font-mono uppercase tracking-wide transition-colors ${planWorkspaceTab === 'scenarios' ? 'border-brand bg-brand text-white' : 'border-border text-muted'}`}
                        onClick={() => setPlanWorkspaceTab('scenarios')}
                      >
                        Scenarios
                      </button>
                      <button
                        className={`min-h-[44px] rounded-md border px-2.5 py-2 text-[10px] font-mono uppercase tracking-wide transition-colors ${planWorkspaceTab === 'requirements' ? 'border-brand bg-brand text-white' : 'border-border text-muted'}`}
                        onClick={() => setPlanWorkspaceTab('requirements')}
                      >
                        Reqs
                      </button>
                      <button
                        className={`min-h-[44px] rounded-md border px-2.5 py-2 text-[10px] font-mono uppercase tracking-wide transition-colors ${planWorkspaceTab === 'adjust' ? 'border-brand bg-brand text-white' : 'border-border text-muted'}`}
                        onClick={() => setPlanWorkspaceTab('adjust')}
                      >
                        Adjust
                      </button>
                      <button
                        className={`min-h-[44px] rounded-md border px-2.5 py-2 text-[10px] font-mono uppercase tracking-wide transition-colors ${planWorkspaceTab === 'evidence' ? 'border-brand bg-brand text-white' : 'border-border text-muted'}`}
                        onClick={() => setPlanWorkspaceTab('evidence')}
                      >
                        Evidence
                      </button>
                    </div>
                    <div className="mt-2 grid grid-cols-3 gap-2">
                      <button
                        className="min-h-[44px] rounded-md bg-accent px-3.5 py-2.5 font-mono text-[10px] uppercase tracking-wide text-white disabled:opacity-40 hover:bg-accent/90 transition-colors"
                        disabled={!pendingScenarios.length || !plan}
                        onClick={() => void runWithoutPendingCredit()}
                      >
                        Toggle Pending Credit
                      </button>
                      <button
                        className="min-h-[44px] rounded-md bg-brand px-3.5 py-2.5 font-mono text-[10px] uppercase tracking-wide text-white disabled:opacity-40 hover:bg-brand/90 transition-colors"
                        disabled={!plan || isSharingPlan}
                        onClick={() => void shareEntirePlan()}
                      >
                        {isSharingPlan ? 'Sharing...' : 'Share'}
                      </button>
                      <button
                        className="min-h-[44px] rounded-md bg-ink px-3.5 py-2.5 font-mono text-[10px] uppercase tracking-wide text-white disabled:opacity-40 hover:bg-ink/80 transition-colors"
                        disabled={!plan}
                        onClick={() => void downloadPdf()}
                      >
                        Export PDF
                      </button>
                    </div>
                  </div>
                </div>
              </>
            )}
          </div>
        </section>
      )}
    </main>
    </>
  )
}

export default App
