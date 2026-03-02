from __future__ import annotations

import json
import re
import time
from functools import lru_cache

import httpx

from app.config import get_settings
from app.models import PlanGenerateRequest, PlanResult, PlanWarning, Severity


def build_fallback_explanation(plan: PlanResult, request: PlanGenerateRequest) -> str:
    total_units = sum(term.units for term in plan.terms)
    term_count = len(plan.terms)
    blocked = request.planning_constraints.blocked_terms
    major_prep = plan.admission_checklist.major_prep_coverage_pct
    igetc_status = plan.admission_checklist.igetc_status
    blockers = plan.admission_checklist.missing_blockers

    lines = [
        "## PathwayIQ Plan Summary",
        f"- Target: {request.student_profile.target_major_id} at {request.student_profile.target_school_id}",
        f"- Generation mode: {plan.generation_mode}",
        f"- Planned terms: {term_count}",
        f"- Planned units: {total_units}",
        f"- Units waived from prior credit: {request.resolved_credit_map.units_waived}",
        f"- Major prep coverage: {major_prep}%",
        f"- IGETC status: {igetc_status}",
    ]

    if blocked:
        lines.append(f"- Blocked terms respected: {', '.join(blocked)}")
    if request.resolved_credit_map.pending_exam_names:
        lines.append(
            "- Pending exam assumptions: "
            + ", ".join(request.resolved_credit_map.pending_exam_names)
        )

    if blockers:
        lines.append("- Remaining blockers: " + ", ".join(blockers))
    else:
        lines.append("- Remaining blockers: none")

    if plan.warnings:
        lines.append("\n## Important Planner Warnings")
        for warning in plan.warnings[:5]:
            lines.append(f"- [{warning.code}] {warning.message}")

    lines.append("\n## Term-by-Term Snapshot")
    for term in plan.terms:
        course_ids = ", ".join(course.course_id for course in term.courses) if term.courses else "No courses"
        lines.append(f"- {term.term_id}: {term.units} units — {course_ids}")

    if plan.critical_path:
        lines.append("\n## Critical Path")
        for item in plan.critical_path[:8]:
            lines.append(f"- {item.course_id}: {item.note}")

    lines.append("\nCritical path courses drive earliest graduation and should be prioritized.")
    return "\n".join(lines)


def _call_gemini_explanation(plan: PlanResult, request: PlanGenerateRequest) -> str | None:
    settings = get_settings()
    if not settings.gemini_api_key:
        return None

    endpoint = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{settings.gemini_model}:generateContent?key={settings.gemini_api_key}"
    )

    context = {
        "student_profile": request.student_profile.model_dump(),
        "exam_credits": [exam.model_dump() for exam in request.exam_credits],
        "constraints": request.planning_constraints.model_dump(),
        "resolved_credit_map": request.resolved_credit_map.model_dump(),
        "terms": [
            {
                "term_id": term.term_id,
                "units": term.units,
                "courses": [course.course_id for course in term.courses],
                "notes": term.notes,
            }
            for term in plan.terms
        ],
        "critical_path": [item.course_id for item in plan.critical_path],
        "warnings": [warning.message for warning in plan.warnings],
    }

    prompt = (
        "You are an academic planning assistant. Summarize the student's semester-by-semester plan in markdown. "
        "Include: (1) why this sequence works, (2) high-risk bottlenecks, (3) AP/IB assumption risks, "
        "(4) transfer readiness and IGETC status when relevant, (5) next best adjustment if student needs lighter load."
    )

    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt},
                    {"text": json.dumps(context)},
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.2,
            "maxOutputTokens": 8192,
        },
    }

    try:
        with httpx.Client(timeout=90.0) as client:
            response = client.post(endpoint, json=payload)
            response.raise_for_status()
            body = response.json()
    except Exception:
        return None

    candidates = body.get("candidates") or []
    if not candidates:
        return None

    parts = candidates[0].get("content", {}).get("parts", [])
    text_parts = [part.get("text", "") for part in parts if isinstance(part, dict)]
    explanation = "\n".join([chunk for chunk in text_parts if chunk.strip()]).strip()
    return explanation or None


def _extract_json_block(text: str) -> dict | None:
    def _repair_json_like(candidate: str) -> dict | None:
        cleaned = candidate.strip()
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned)
        cleaned = re.sub(r"\bTrue\b", "true", cleaned)
        cleaned = re.sub(r"\bFalse\b", "false", cleaned)
        cleaned = re.sub(r"\bNone\b", "null", cleaned)
        cleaned = re.sub(r"([\{,]\s*)([A-Za-z_][A-Za-z0-9_\-]*)(\s*:)", r'\1"\2"\3', cleaned)
        cleaned = cleaned.replace("'", '"')
        cleaned = re.sub(r",\s*([}\]])", r"\1", cleaned)

        try:
            parsed = json.loads(cleaned)
        except json.JSONDecodeError:
            return None

        if isinstance(parsed, dict):
            return parsed
        if isinstance(parsed, list):
            if all(isinstance(item, dict) and ("course_id" in item or "term_id" in item) for item in parsed):
                return {"assignments": parsed, "term_notes": []}
        return None

    def _try_parse(candidate: str) -> dict | None:
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError:
            return _repair_json_like(candidate)
        if isinstance(parsed, dict):
            return parsed
        if isinstance(parsed, list):
            if all(isinstance(item, dict) and ("course_id" in item or "term_id" in item) for item in parsed):
                return {"assignments": parsed, "term_notes": []}
        return None

    fenced_patterns = [
        r"```json\s*([\s\S]*?)\s*```",
        r"```\s*([\s\S]*?)\s*```",
    ]
    for pattern in fenced_patterns:
        for match in re.finditer(pattern, text, flags=re.IGNORECASE):
            parsed = _try_parse(match.group(1).strip())
            if parsed is not None:
                return parsed

    full_text_parsed = _try_parse(text.strip())
    if full_text_parsed is not None:
        return full_text_parsed

    stack = 0
    start_index: int | None = None
    for idx, char in enumerate(text):
        if char == "{":
            if stack == 0:
                start_index = idx
            stack += 1
        elif char == "}":
            if stack == 0:
                continue
            stack -= 1
            if stack == 0 and start_index is not None:
                candidate = text[start_index : idx + 1].strip()
                parsed = _try_parse(candidate)
                if parsed is not None:
                    return parsed

    return None


def _repair_truncated_json(text: str) -> dict | None:
    """Attempt to salvage a truncated JSON response from a thinking model.

    The model may return well-formed JSON that was cut short because
    maxOutputTokens was exhausted by thinking tokens.  We try to close
    any open brackets/braces so that the successfully-emitted prefix
    can still be parsed.
    """
    # Strip markdown fences if present
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)

    # Only attempt repair if it looks like it started as JSON
    if not cleaned or cleaned[0] not in ("{", "["):
        return None

    # Find last successfully closed array item boundary
    # Strategy: truncate to the last complete },  or } ] boundary,
    # then close out any remaining open structures.
    best = None
    # Try progressively shorter slices ending at "}" boundaries
    for match in re.finditer(r"\}", cleaned):
        candidate = cleaned[: match.end()]
        # Count open brackets
        opens = candidate.count("[") - candidate.count("]")
        braces = candidate.count("{") - candidate.count("}")
        suffix = "]" * opens + "}" * braces
        attempt = candidate + suffix
        try:
            parsed = json.loads(attempt)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            best = parsed
        elif isinstance(parsed, list):
            if all(isinstance(item, dict) and ("course_id" in item or "term_id" in item) for item in parsed):
                best = {"assignments": parsed, "term_notes": []}

    if best is not None:
        # Verify we got at least some assignments
        assignments = best.get("assignments", [])
        if isinstance(assignments, list) and len(assignments) > 0:
            return best
    return None


def _normalize_schedule_assignments(payload: dict, valid_term_ids: set[str]) -> tuple[list[dict[str, str]], dict[str, list[str]]]:
    assignments: list[dict[str, str]] = []
    term_notes_map: dict[str, list[str]] = {}

    direct_assignments = payload.get("assignments")
    if isinstance(direct_assignments, list):
        for item in direct_assignments:
            if not isinstance(item, dict):
                continue
            course_id = item.get("course_id")
            term_id = item.get("term_id")
            if isinstance(course_id, str) and isinstance(term_id, str):
                assignments.append({"course_id": course_id, "term_id": term_id})

    terms_list = payload.get("terms")
    if isinstance(terms_list, list):
        for term_item in terms_list:
            if not isinstance(term_item, dict):
                continue
            term_id = term_item.get("term_id")
            if not isinstance(term_id, str):
                continue
            if term_id not in valid_term_ids:
                continue
            course_ids = term_item.get("course_ids")
            courses = term_item.get("courses")
            if isinstance(course_ids, list):
                for course_id in course_ids:
                    if isinstance(course_id, str):
                        assignments.append({"course_id": course_id, "term_id": term_id})
            if isinstance(courses, list):
                for course_obj in courses:
                    if isinstance(course_obj, str):
                        assignments.append({"course_id": course_obj, "term_id": term_id})
                    elif isinstance(course_obj, dict):
                        course_id = course_obj.get("course_id")
                        if isinstance(course_id, str):
                            assignments.append({"course_id": course_id, "term_id": term_id})

    schedule_obj = payload.get("schedule")
    if isinstance(schedule_obj, dict):
        for term_id, values in schedule_obj.items():
            if not isinstance(term_id, str) or term_id not in valid_term_ids:
                continue
            if isinstance(values, list):
                for value in values:
                    if isinstance(value, str):
                        assignments.append({"course_id": value, "term_id": term_id})

    term_notes_payload = payload.get("term_notes", [])
    if isinstance(term_notes_payload, list):
        for item in term_notes_payload:
            if not isinstance(item, dict):
                continue
            term_id = item.get("term_id")
            note = item.get("note")
            if isinstance(term_id, str) and isinstance(note, str) and note.strip():
                term_notes_map.setdefault(term_id, []).append(note.strip())

    return assignments, term_notes_map


def _model_candidates(primary_model: str) -> list[str]:
    def _normalize(name: str) -> str:
        normalized = (name or "").strip()
        if normalized.startswith("models/"):
            normalized = normalized.split("/", 1)[1]
        return normalized

    candidates: list[str] = []
    normalized_primary = _normalize(primary_model)
    if normalized_primary:
        candidates.append(normalized_primary)

    for fallback in [
        "gemini-3-flash",
        "gemini-2.5-flash",
        "gemini-flash-latest",
        "gemini-3-flash-preview",
        "gemini-2.0-flash",
        "gemini-1.5-flash",
    ]:
        if fallback not in candidates:
            candidates.append(fallback)
    return candidates


def _endpoint_candidates(model_name: str, api_key: str) -> list[tuple[str, str]]:
    if model_name.endswith("-latest"):
        return [
            (
                "v1beta",
                f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}",
            )
        ]

    return [
        (
            "v1",
            f"https://generativelanguage.googleapis.com/v1/models/{model_name}:generateContent?key={api_key}",
        ),
        (
            "v1beta",
            f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}",
        ),
    ]


@lru_cache(maxsize=8)
def _available_generate_models(api_key: str, api_version: str) -> set[str]:
    endpoint = f"https://generativelanguage.googleapis.com/{api_version}/models?key={api_key}"
    try:
        with httpx.Client(timeout=12.0) as client:
            response = client.get(endpoint)
            response.raise_for_status()
            body = response.json()
    except Exception:
        return set()

    names: set[str] = set()
    for model in body.get("models", []) if isinstance(body, dict) else []:
        if not isinstance(model, dict):
            continue
        methods = model.get("supportedGenerationMethods") or []
        if "generateContent" not in methods:
            continue
        model_name = str(model.get("name", "")).strip()
        if model_name.startswith("models/"):
            model_name = model_name.split("/", 1)[1]
        if model_name:
            names.add(model_name)
    return names


def _schedule_payload(schedule_context: dict, include_response_mime: bool) -> dict:
    generation_config = {
        "temperature": 0.1,
        "maxOutputTokens": 8192,
    }
    if include_response_mime:
        generation_config["responseMimeType"] = "application/json"
        generation_config["responseSchema"] = {
            "type": "object",
            "properties": {
                "assignments": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "course_id": {"type": "string"},
                            "term_id": {"type": "string"},
                        },
                        "required": ["course_id", "term_id"],
                    },
                },
                "term_notes": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "term_id": {"type": "string"},
                            "note": {"type": "string"},
                        },
                        "required": ["term_id", "note"],
                    },
                },
            },
            "required": ["assignments"],
        }

    return {
        "contents": [
            {
                "parts": [
                    {
                        "text": (
                            "You optimize a college schedule by moving existing courses across existing terms only. "
                            "Return strict JSON with shape: {\"assignments\":[{\"course_id\":str,\"term_id\":str}],"
                            "\"term_notes\":[{\"term_id\":str,\"note\":str}]}. "
                            "Rules: use only given course_id values; use only given term_ids; never place courses in blocked terms; "
                            "assign every course exactly once; do not invent fields or prose. "
                            "Use exam_credits and resolved_credit_map as hard constraints for what is already satisfied or pending."
                        )
                    },
                    {"text": json.dumps(schedule_context)},
                ]
            }
        ],
        "generationConfig": generation_config,
    }


def _call_gemini_schedule_assignments(
    base_plan: PlanResult,
    request: PlanGenerateRequest,
    validation_feedback: list[str] | None = None,
) -> tuple[dict | None, str | None]:
    settings = get_settings()
    if not settings.gemini_api_key or not settings.gemini_enable_scheduling:
        return None, "gemini-disabled-or-missing-key"

    term_ids = [term.term_id for term in base_plan.terms]
    blocked_terms = set(request.planning_constraints.blocked_terms)

    schedule_context = {
        "student_profile": request.student_profile.model_dump(),
        "exam_credits": [exam.model_dump() for exam in request.exam_credits],
        "constraints": request.planning_constraints.model_dump(),
        "resolved_credit_map": request.resolved_credit_map.model_dump(),
        "term_ids": term_ids,
        "blocked_terms": sorted(blocked_terms),
        "courses": [
            {
                "course_id": course.course_id,
                "course_name": course.course_name,
                "units": course.units,
                "current_term_id": term.term_id,
            }
            for term in base_plan.terms
            for course in term.courses
        ],
    }
    if validation_feedback:
        schedule_context["retry_guidance"] = {
            "message": (
                "Previous schedule attempt was invalid. You must fix these issues while still obeying all rules."
            ),
            "validation_errors": validation_feedback,
        }

    attempt_errors: list[str] = []
    available_by_version = {
        "v1beta": _available_generate_models(settings.gemini_api_key, "v1beta"),
        "v1": _available_generate_models(settings.gemini_api_key, "v1"),
    }

    for model_name in _model_candidates(settings.gemini_model):
        for api_version, endpoint in _endpoint_candidates(model_name, settings.gemini_api_key):
            available_models = available_by_version.get(api_version, set())
            if available_models and model_name not in available_models:
                attempt_errors.append(f"{model_name}@{api_version}: model-unavailable")
                continue

            payload_variants = [True, False] if api_version == "v1beta" else [False]
            for include_mime in payload_variants:
                payload = _schedule_payload(schedule_context, include_response_mime=include_mime)

                # Retry up to 2 times on 429 with backoff
                max_retries = 2
                for retry_idx in range(max_retries + 1):
                    try:
                        with httpx.Client(timeout=90.0) as client:
                            response = client.post(endpoint, json=payload)
                            response.raise_for_status()
                            body = response.json()
                        break  # success
                    except httpx.HTTPStatusError as exc:
                        status_code = exc.response.status_code if exc.response is not None else "unknown"
                        body_preview = ""
                        if exc.response is not None:
                            body_preview = exc.response.text[:220].replace("\n", " ").strip()
                        if status_code == 429 and retry_idx < max_retries:
                            # Extract retry delay from error if available
                            delay_match = re.search(r"retry in (\d+(?:\.\d+)?)s", body_preview)
                            delay = float(delay_match.group(1)) if delay_match else (5.0 * (retry_idx + 1))
                            delay = min(delay, 30.0)  # cap at 30s
                            time.sleep(delay)
                            continue
                        if status_code == 429:
                            preview_suffix = f": {body_preview}" if body_preview else ""
                            attempt_errors.append(f"{model_name}@{api_version}: quota-exceeded{preview_suffix}")
                            body = None
                            break
                        if "responseMimeType" in body_preview and include_mime:
                            attempt_errors.append(f"{model_name}@{api_version}: response-mime-unsupported")
                            body = None
                            break
                        if "responseSchema" in body_preview and include_mime:
                            attempt_errors.append(f"{model_name}@{api_version}: response-schema-unsupported")
                            body = None
                            break
                        preview_suffix = f": {body_preview}" if body_preview else ""
                        attempt_errors.append(
                            f"{model_name}@{api_version}: http-{status_code}{preview_suffix}"
                        )
                        body = None
                        break
                    except Exception as exc:
                        attempt_errors.append(
                            f"{model_name}@{api_version}: request-failed ({type(exc).__name__})"
                        )
                        body = None
                        break

                if not body:
                    continue

                candidates = body.get("candidates") or []
                if not candidates:
                    attempt_errors.append(f"{model_name}@{api_version}: no-candidates")
                    continue

                parts = candidates[0].get("content", {}).get("parts", [])
                text = "\n".join(part.get("text", "") for part in parts if isinstance(part, dict))
                if not text.strip():
                    attempt_errors.append(f"{model_name}@{api_version}: empty-response")
                    continue

                # Check for truncation: finishReason == MAX_TOKENS
                finish_reason = candidates[0].get("finishReason", "")

                parsed = _extract_json_block(text)
                if parsed:
                    if model_name != settings.gemini_model:
                        parsed["_fallback_model_used"] = model_name
                    return parsed, None

                # If truncated, try to complete the JSON
                if finish_reason in ("MAX_TOKENS", "STOP") and text.strip():
                    repaired = _repair_truncated_json(text)
                    if repaired:
                        if model_name != settings.gemini_model:
                            repaired["_fallback_model_used"] = model_name
                        return repaired, None

                if finish_reason == "MAX_TOKENS":
                    attempt_errors.append(f"{model_name}@{api_version}: truncated-json")
                else:
                    attempt_errors.append(f"{model_name}@{api_version}: invalid-json")

    if attempt_errors:
        deduped_errors = list(dict.fromkeys(attempt_errors))
        return None, " | ".join(deduped_errors[:4])
    return None, "unknown"


def maybe_generate_schedule_plan(
    base_plan: PlanResult,
    request: PlanGenerateRequest,
    validation_feedback: list[str] | None = None,
) -> tuple[PlanResult | None, str | None]:
    assignment_payload, reason = _call_gemini_schedule_assignments(
        base_plan,
        request,
        validation_feedback=validation_feedback,
    )
    if not assignment_payload:
        return None, reason

    blocked_terms = set(request.planning_constraints.blocked_terms)
    valid_term_ids = {term.term_id for term in base_plan.terms}

    assignments, term_notes_map = _normalize_schedule_assignments(assignment_payload, valid_term_ids)
    if not assignments:
        return None, "no-usable-assignments"

    course_index = {
        course.course_id: course.model_copy(deep=True)
        for term in base_plan.terms
        for course in term.courses
    }
    original_term_by_course = {
        course.course_id: term.term_id
        for term in base_plan.terms
        for course in term.courses
    }

    remapped_term_by_course: dict[str, str] = {}
    for item in assignments:
        if not isinstance(item, dict):
            continue
        course_id = item.get("course_id")
        term_id = item.get("term_id")
        if not isinstance(course_id, str) or not isinstance(term_id, str):
            continue
        if course_id not in course_index:
            continue
        if term_id not in valid_term_ids or term_id in blocked_terms:
            continue
        remapped_term_by_course[course_id] = term_id

    if not remapped_term_by_course:
        return None, "no-valid-course-mappings"

    for course_id, original_term_id in original_term_by_course.items():
        remapped_term_by_course.setdefault(course_id, original_term_id)

    optimized = base_plan.model_copy(deep=True)
    for term in optimized.terms:
        term.courses = []
        term.units = 0
        notes = [note for note in term.notes if not note.startswith("AI optimization")]
        notes.extend(term_notes_map.get(term.term_id, []))
        term.notes = notes

    term_lookup = {term.term_id: term for term in optimized.terms}
    for course_id, term_id in remapped_term_by_course.items():
        term = term_lookup[term_id]
        course = course_index[course_id]
        term.courses.append(course)
        term.units += course.units

    for term in optimized.terms:
        term.courses = sorted(term.courses, key=lambda course: course.course_id)
        if term.courses:
            term.notes.append("AI optimization applied")

    optimized.warnings = list(optimized.warnings) + [
        PlanWarning(
            code="AI_SCHEDULE_OPTIMIZED",
            message="Gemini proposed schedule adjustments; plan was validated before returning.",
            severity=Severity.INFO,
        )
    ]
    fallback_model = assignment_payload.get("_fallback_model_used")
    if isinstance(fallback_model, str):
        optimized.warnings = list(optimized.warnings) + [
            PlanWarning(
                code="AI_SCHEDULE_MODEL_FALLBACK",
                message=(
                    "Primary Gemini model did not return valid scheduling JSON; "
                    f"used fallback model {fallback_model}."
                ),
                severity=Severity.INFO,
            )
        ]

    return optimized, None


def maybe_generate_explanation(plan: PlanResult, request: PlanGenerateRequest) -> str:
    generated = _call_gemini_explanation(plan, request)
    if generated:
        return generated
    return build_fallback_explanation(plan, request)
