import http.server
import json
import os
import socketserver
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ifc_material_takeoff import analyze_ifc

os.chdir(r"C:\Users\J32")
PORT = 8765
class BimRequestHandler(http.server.SimpleHTTPRequestHandler):
    extensions_map = {
        **http.server.SimpleHTTPRequestHandler.extensions_map,
        ".wasm": "application/wasm",
        ".ifc": "application/octet-stream",
        ".webmanifest": "application/manifest+json",
    }

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def do_POST(self):
        if self.path != "/api/material-takeoff":
            self.send_error(404)
            return
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0 or length > 500 * 1024 * 1024:
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
            result = analyze_ifc(temp_path)
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
    print(f"BIM viewer running at http://127.0.0.1:{PORT}/bim_wall_viewer.html", flush=True)
    httpd.serve_forever()
