# Infrastructure Notes

## Target Topology

- Frontend: Vercel
- API: Cloud Run
- Database: Supabase Postgres

## Environment Variables

API:
- `GOOGLE_API_KEY` (optional, Gemini integration)

Frontend:
- `VITE_API_BASE_URL` (default `http://localhost:8000`)

## Deployment Steps (MVP)

1. Deploy API container to Cloud Run.
2. Set `allow unauthenticated` for beta access.
3. Deploy frontend to Vercel.
4. Configure CORS origin allow list in API before production hardening.
