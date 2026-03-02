# Authoritative Raw Inputs

Place official snapshots in this folder before running ingestion.

You can auto-generate these files from public sources with:

```powershell
cd data-pipeline/scripts
python harvest_uc_majors_and_lpc_assist.py --policy-year AY-2025-26 --assist-fall-year 2025
```

Required files:
- `uc_majors.json`
- `lpc_uc_articulations.json`

## `uc_majors.json` shape

```json
[
  {
    "school_id": "ucsd",
    "major_key": "computer-science",
    "major_name": "Computer Science, B.S.",
    "department": "Computer Science and Engineering",
    "total_units": 180,
    "source_name": "UCSD General Catalog",
    "source_url": "https://catalog.ucsd.edu/...",
    "policy_year": "AY-2026-27"
  }
]
```

## `lpc_uc_articulations.json` shape

```json
[
  {
    "cc_id": "lpc",
    "university_id": "ucsd",
    "major_id": "ucsd-computer-science",
    "cc_course_id": "LPC-CS-1",
    "satisfies_requirement_id": "ucsd-computer-science-REQ-1",
    "source_name": "ASSIST.org",
    "source_url": "https://assist.org/...",
    "policy_year": "AY-2026-27"
  }
]
```

## Notes
- `major_id` must match the generated major identifier: `<uc_school_id>-<major_key>`.
- Ingestion validates UC-wide major coverage and LPC articulation coverage before writing output.
- Keep source URLs official and directly citable.
