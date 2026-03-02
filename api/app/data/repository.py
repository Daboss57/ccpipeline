from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class Repository:
    def __init__(self, seed_file: Path) -> None:
        if not seed_file.exists():
            raise FileNotFoundError(f"Seed file not found: {seed_file}")
        self._seed_file = seed_file
        self._data = json.loads(seed_file.read_text(encoding="utf-8"))

    def reload(self) -> None:
        self._data = json.loads(self._seed_file.read_text(encoding="utf-8"))

    @property
    def policy_version(self) -> str:
        return self._data["policy_version"]

    @property
    def policy_updated_at(self) -> str:
        return self._data["policy_updated_at"]

    def list_schools(self) -> list[dict[str, Any]]:
        return self._data["schools"]

    def get_school(self, school_id: str) -> dict[str, Any] | None:
        return next((school for school in self._data["schools"] if school["school_id"] == school_id), None)

    def list_majors(self, school_id: str) -> list[dict[str, Any]]:
        return [major for major in self._data["majors"] if major["school_id"] == school_id]

    def list_courses(self, school_id: str) -> list[dict[str, Any]]:
        return [course for course in self._data.get("courses", []) if course["school_id"] == school_id]

    def get_course(self, school_id: str, course_id: str) -> dict[str, Any] | None:
        return next(
            (
                course
                for course in self._data.get("courses", [])
                if course["school_id"] == school_id and course["course_id"] == course_id
            ),
            None,
        )

    def list_course_offerings(self, school_id: str, season: str | None = None) -> list[dict[str, Any]]:
        rows = [row for row in self._data.get("course_offerings", []) if row["school_id"] == school_id]
        if season is None:
            return rows
        target = season.capitalize()
        return [row for row in rows if target in row.get("offered_terms", [])]

    def get_course_offered_terms(self, school_id: str, course_id: str) -> list[str]:
        row = next(
            (
                offering
                for offering in self._data.get("course_offerings", [])
                if offering["school_id"] == school_id and offering["course_id"] == course_id
            ),
            None,
        )
        if row:
            return list(row.get("offered_terms", []))
        course = self.get_course(school_id, course_id)
        if not course:
            return []
        return list(course.get("offered_terms", []))

    def get_major_requirements(self, major_id: str) -> list[dict[str, Any]]:
        return [req for req in self._data["major_requirements"] if req["major_id"] == major_id]

    def get_prerequisites(self, school_id: str) -> list[dict[str, Any]]:
        return [pr for pr in self._data["course_prerequisites"] if pr["university_id"] == school_id]

    def get_exam_policy(self, school_id: str, exam_type: str, exam_name: str) -> dict[str, Any] | None:
        return next(
            (
                policy
                for policy in self._data["exam_credit_policies"]
                if policy["school_id"] == school_id
                and policy["exam_type"].upper() == exam_type.upper()
                and policy["exam_name"].strip().lower() == exam_name.strip().lower()
            ),
            None,
        )

    def list_igetc_areas(self, cc_id: str) -> list[str]:
        return sorted({row["igetc_area"] for row in self._data["igetc_courses"] if row["cc_id"] == cc_id})

    def list_igetc_courses(self, cc_id: str) -> list[dict[str, Any]]:
        return [row for row in self._data["igetc_courses"] if row["cc_id"] == cc_id]

    def get_requirement_by_course(self, major_id: str, course_id: str) -> dict[str, Any] | None:
        for req in self.get_major_requirements(major_id):
            if req["course_id"] == course_id:
                return req
        return None

    def list_assist_articulations(
        self,
        cc_id: str,
        university_id: str | None = None,
        major_id: str | None = None,
    ) -> list[dict[str, Any]]:
        rows = [row for row in self._data.get("assist_articulations", []) if row.get("cc_id") == cc_id]
        if university_id:
            rows = [row for row in rows if row.get("university_id") == university_id]
        if major_id:
            rows = [row for row in rows if row.get("major_id") == major_id]
        return rows

    def get_articulated_cc_courses_for_requirement(
        self,
        cc_id: str,
        university_id: str,
        major_id: str,
        requirement_id: str,
    ) -> list[str]:
        rows = [
            row
            for row in self._data.get("assist_articulations", [])
            if row.get("cc_id") == cc_id
            and row.get("university_id") == university_id
            and row.get("major_id") == major_id
            and row.get("satisfies_requirement_id") == requirement_id
        ]
        course_ids = [str(row.get("cc_course_id", "")).strip() for row in rows]
        return sorted({course_id for course_id in course_ids if course_id})

    def list_articulation_options_for_requirement(
        self,
        cc_id: str,
        university_id: str,
        major_id: str,
        requirement_id: str,
    ) -> list[dict[str, Any]]:
        rows = [
            row
            for row in self._data.get("assist_articulations", [])
            if row.get("cc_id") == cc_id
            and row.get("university_id") == university_id
            and row.get("major_id") == major_id
            and row.get("satisfies_requirement_id") == requirement_id
        ]

        options: list[dict[str, Any]] = []
        for row in rows:
            course_id = str(row.get("cc_course_id", "")).strip()
            if not course_id:
                continue
            options.append(
                {
                    "cc_course_id": course_id,
                    "requirement_id": requirement_id,
                    "source": row.get("source"),
                }
            )
        deduped: dict[str, dict[str, Any]] = {}
        for option in options:
            deduped[option["cc_course_id"]] = option
        return sorted(deduped.values(), key=lambda row: row["cc_course_id"])
