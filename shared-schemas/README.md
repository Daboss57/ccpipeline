# Shared Schemas

This folder holds exported contract artifacts consumed by frontend and external clients.

- `openapi.json` is generated from the FastAPI app.

Generate:

```powershell
cd api
python -c "from app.main import app; import json; print(json.dumps(app.openapi(), indent=2))" > ..\shared-schemas\openapi.json
```
