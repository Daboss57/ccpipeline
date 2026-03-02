# PathwayIQ MVP Monorepo

Accuracy-first MVP for AI-assisted California college pathway planning.

## Monorepo Layout

- `api/` FastAPI backend (credit resolution, planning, validation, metadata, PDF export)
- `frontend/` React + Tailwind web app (intake wizard, credit summary, timeline)
- `data-pipeline/` seed generation scripts and SQL schema
- `shared-schemas/` shared JSON contract snapshots
- `infra/` deployment notes

## Quick Start

### Backend

```powershell
cd api
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Backend runs at `http://localhost:8000`.

Optional Gemini configuration for AI schedule optimization and explanation generation:

```powershell
$env:GEMINI_API_KEY="<your_key>"
$env:GEMINI_MODEL="gemini-1.5-flash"
$env:GEMINI_ENABLE_SCHEDULING="true"
```

### Frontend

```powershell
cd frontend
npm install
npm run dev
```

Frontend runs at `http://localhost:5173`.

## API Endpoints

- `POST /v1/credits/resolve`
- `POST /v1/plans/generate`
- `POST /v1/plans/rebuild`
- `POST /v1/plans/validate`
- `POST /v1/igetc/tracker`
- `GET /v1/metadata/schools`
- `GET /v1/metadata/majors?school_id=...`
- `GET /v1/metadata/courses?school_id=...`
- `GET /v1/metadata/course-offerings?school_id=...&season=...`
- `GET /v1/policy/version`
- `POST /v1/export/pdf`

## Scope Included

- UC system + Las Positas College + San Joaquin Delta College
- 5 majors across UCs: CS, Data Science, Biology, Economics, Psychology
- Deterministic planner with prerequisite validation
- Policy-versioned output
- URL-shareable plan state + PDF export

## Notes

This implementation intentionally keeps policy data as seeded demo data and isolates ingestion logic in `data-pipeline/` for expansion.
