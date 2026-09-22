import asyncio
import os
import tempfile
import traceback

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from ifc_material_takeoff import analyze_ifc

MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_MB", "100")) * 1024 * 1024
MAX_GEOMETRY_ELEMENTS = int(os.getenv("MAX_GEOMETRY_ELEMENTS", "400"))
ALLOW_GEOMETRY = os.getenv("ALLOW_GEOMETRY", "true").lower() in {"1", "true", "yes", "on"}
ANALYSIS_QUEUE_TIMEOUT = float(os.getenv("ANALYSIS_QUEUE_TIMEOUT", "15"))
_analysis_lock = asyncio.Semaphore(1)

app = FastAPI(title="BIM Material Takeoff API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["POST", "GET", "OPTIONS"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "bim-material-api",
        "max_upload_mb": MAX_UPLOAD_BYTES // (1024 * 1024),
    }


@app.get("/")
def root():
    return {"service": "bim-material-api", "status": "ok", "endpoint": "/api/material-takeoff"}


@app.post("/api/material-takeoff")
async def material_takeoff(request: Request):
    path = None
    lock_acquired = False
    try:
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                if int(content_length) > MAX_UPLOAD_BYTES:
                    return JSONResponse(
                        {"error": f"IFC 파일은 최대 {MAX_UPLOAD_BYTES // (1024 * 1024)}MB까지 분석할 수 있습니다."},
                        status_code=413,
                    )
            except ValueError:
                return JSONResponse({"error": "올바르지 않은 Content-Length입니다."}, status_code=400)

        received = 0
        with tempfile.NamedTemporaryFile(prefix="bim_takeoff_", suffix=".ifc", delete=False) as handle:
            path = handle.name
            async for chunk in request.stream():
                received += len(chunk)
                if received > MAX_UPLOAD_BYTES:
                    return JSONResponse(
                        {"error": f"IFC 파일은 최대 {MAX_UPLOAD_BYTES // (1024 * 1024)}MB까지 분석할 수 있습니다."},
                        status_code=413,
                    )
                handle.write(chunk)

        if received == 0:
            return JSONResponse({"error": "IFC 파일 내용이 비어 있습니다."}, status_code=400)
        with open(path, "rb") as handle:
            header = handle.read(4096).lstrip(b"\xef\xbb\xbf\x00\t\r\n ")
        if not header.startswith(b"ISO-10303-21;"):
            return JSONResponse({"error": "유효한 IFC STEP 파일이 아닙니다."}, status_code=422)

        try:
            await asyncio.wait_for(_analysis_lock.acquire(), timeout=ANALYSIS_QUEUE_TIMEOUT)
            lock_acquired = True
        except TimeoutError:
            return JSONResponse(
                {"error": "분석 서버가 다른 IFC를 처리 중입니다. 잠시 후 다시 시도해 주세요."},
                status_code=503,
                headers={"Retry-After": "10"},
            )

        # IfcOpenShell 분석은 CPU 작업이므로 이벤트 루프 밖에서 실행합니다.
        # QTO가 없는 IFC도 제한된 수의 벽 형상으로 체적을 보완합니다.
        return await asyncio.to_thread(
            analyze_ifc,
            path,
            allow_geometry=ALLOW_GEOMETRY,
            max_geometry_elements=MAX_GEOMETRY_ELEMENTS,
        )
    except Exception as exc:
        traceback.print_exc()
        return JSONResponse(
            {"error": str(exc), "type": type(exc).__name__},
            status_code=500,
        )
    finally:
        if lock_acquired:
            _analysis_lock.release()
        if path and os.path.exists(path):
            os.unlink(path)
