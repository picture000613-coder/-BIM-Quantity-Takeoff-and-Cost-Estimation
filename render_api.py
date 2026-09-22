import os
import tempfile

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from ifc_material_takeoff import analyze_ifc

app = FastAPI(title="BIM Material Takeoff API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["POST", "GET", "OPTIONS"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok", "service": "bim-material-api"}


@app.post("/api/material-takeoff")
async def material_takeoff(request: Request):
    body = await request.body()
    if not body or len(body) > 500 * 1024 * 1024:
        return JSONResponse({"error": "Invalid IFC file size"}, status_code=400)
    path = None
    try:
        with tempfile.NamedTemporaryFile(prefix="bim_takeoff_", suffix=".ifc", delete=False) as handle:
            path = handle.name
            handle.write(body)
        return analyze_ifc(path)
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=500)
    finally:
        if path and os.path.exists(path):
            os.unlink(path)
