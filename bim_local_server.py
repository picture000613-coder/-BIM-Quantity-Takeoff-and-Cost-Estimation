import http.server
import json
import os
import socketserver
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ifc_material_takeoff import analyze_ifc

APP_DIR = os.path.dirname(os.path.abspath(__file__))
MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_MB", "100")) * 1024 * 1024
PORT = int(os.getenv("PORT", "8765"))
os.chdir(APP_DIR)


class BimRequestHandler(http.server.SimpleHTTPRequestHandler):
    extensions_map = {
        **http.server.SimpleHTTPRequestHandler.extensions_map,
        ".wasm": "application/wasm",
        ".ifc": "application/octet-stream",
        ".webmanifest": "application/manifest+json",
    }

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(204)
        self.end_headers()

    def do_GET(self):
        if self.path == "/health":
            payload = json.dumps({
                "status": "ok",
                "service": "bim-material-api-local",
                "max_upload_mb": MAX_UPLOAD_BYTES // (1024 * 1024),
            }).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return
        super().do_GET()

    def do_POST(self):
        if self.path != "/api/material-takeoff":
            self.send_error(404)
            return
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0 or length > MAX_UPLOAD_BYTES:
            self.send_error(400, "Invalid IFC file size")
            return
        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(prefix="bim_takeoff_", suffix=".ifc", delete=False) as temp_file:
                temp_path = temp_file.name
                remaining = length
                while remaining:
                    chunk = self.rfile.read(min(1024 * 1024, remaining))
                    if not chunk:
                        raise ValueError("IFC upload ended unexpectedly")
                    temp_file.write(chunk)
                    remaining -= len(chunk)
            with open(temp_path, "rb") as uploaded:
                header = uploaded.read(4096).lstrip(b"\xef\xbb\xbf\x00\t\r\n ")
            if not header.startswith(b"ISO-10303-21;"):
                raise ValueError("유효한 IFC STEP 파일이 아닙니다.")
            result = analyze_ifc(temp_path, allow_geometry=True, max_geometry_elements=400)
            payload = json.dumps(result, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
        except Exception as error:
            payload = json.dumps({"error": str(error)}, ensure_ascii=False).encode("utf-8")
            self.send_response(500)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
        finally:
            if temp_path and os.path.exists(temp_path):
                os.unlink(temp_path)


with socketserver.TCPServer(("127.0.0.1", PORT), BimRequestHandler) as httpd:
    print(f"BIM viewer running at http://127.0.0.1:{PORT}/index.html", flush=True)
    httpd.serve_forever()
