# Data Pipeline

## Generate Seed Data

```powershell
cd data-pipeline
python scripts/generate_seed_data.py
```

Output goes to `seeds/seed_data.json`.

## Ingest Authoritative Snapshot (UC majors + LPC transfer agreements)

### Option A: Live harvest from public UC + ASSIST sources

```powershell
cd data-pipeline/scripts
python harvest_uc_majors_and_lpc_assist.py --policy-year AY-2025-26 --assist-fall-year 2025
```

This writes:
- `raw/uc_majors.json`
- `raw/lpc_uc_articulations.json`

Then ingest to seed files:

```powershell
python ingest_authoritative_snapshot.py
```

1. Place raw files in `raw/`:
	- `uc_majors.json`
	- `lpc_uc_articulations.json`
2. Run:

```powershell
cd data-pipeline/scripts
python ingest_authoritative_snapshot.py
```

The ingestion script validates:
- all 9 UC campuses have major coverage,
- LPC has articulation coverage for all 9 UC campuses.

On success, it writes to both:
- `data-pipeline/seeds/seed_data.json`
- `api/app/data/seed_data.json`

## Intent

- Keep policy sources versioned
- Separate ingestion from API runtime
- Allow manual review before publishing new policy-year snapshots
