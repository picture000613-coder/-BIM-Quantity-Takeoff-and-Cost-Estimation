import os
import tempfile
import traceback

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


@app.get("/")
def root():
    return {"service": "bim-material-api", "status": "ok", "endpoint": "/api/material-takeoff"}


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
        # Render 공개 API는 QTO 값을 우선 사용한다. 형상 재생성은 요청마다
        # 메모리를 크게 사용하므로 로컬 분석에서만 명시적으로 활성화한다.
        return analyze_ifc(path, allow_geometry=False)
    except Exception as exc:
        traceback.print_exc()
        return JSONResponse(
            {"error": str(exc), "type": type(exc).__name__},
            status_code=500,
        )
    finally:
        if path and os.path.exists(path):
            os.unlink(path)
