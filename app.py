"""Run with python app.py, then open http://127.0.0.1:8000."""
import json
import mimetypes
import re
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, unquote

from sarvam_pipeline import ROOT, LIBRARY, LANGUAGES, analyse_pdf, generate_story, read_json, write_json

JOBS = {}
LOCK = threading.Lock()
PIPELINE_LOCK = threading.Lock()
STATIC = ROOT / "web"
ID = r"[a-f0-9]{24}"


def start_job(operation):
    job_id = uuid.uuid4().hex
    JOBS[job_id] = {"status": "running", "message": "Waiting to process…"}

    def progress(message):
        with LOCK:
            JOBS[job_id]["message"] = message

    def run():
        try:
            with PIPELINE_LOCK:
                result = operation(progress)
            with LOCK:
                JOBS[job_id] = {"status": "done", "result": result}
        except Exception as error:
            status = getattr(error, "status_code", None)
            if isinstance(error, ValueError):
                message = str(error)
            elif status in (401, 403):
                message = "Sarvam access was denied. Check your API key and access to Document AI, chat and TTS."
            elif status == 402:
                message = "Sarvam needs available credits. Add credits and retry."
            elif status == 429:
                message = "Sarvam is rate-limiting requests. Wait a moment and retry."
            else:
                message = f"Sarvam processing could not finish ({type(error).__name__}" + (f", HTTP {status}" if status else "") + "). Retry to resume saved work."
            with LOCK:
                JOBS[job_id] = {"status": "error", "message": message}
    threading.Thread(target=run, daemon=True).start()
    return {"job_id": job_id}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def json_response(self, data, status=200):
        content = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(content)

    def do_GET(self):
        path = urlparse(self.path).path
        try:
            if path == "/api/health":
                return self.json_response({"ok": True})
            if path == "/api/library":
                papers = []
                for file in sorted(LIBRARY.glob("*/analysis.json"), key=lambda p: p.stat().st_mtime, reverse=True):
                    paper = read_json(file)
                    paper["recordings"] = [read_json(p) for p in file.parent.glob("*/story.json")]
                    papers.append(paper)
                return self.json_response(papers)
            if path.startswith("/api/jobs/"):
                with LOCK:
                    job = dict(JOBS.get(path.rsplit("/", 1)[-1], {"status": "error", "message": "Job expired. Please retry."}))
                return self.json_response(job)
            match = re.fullmatch(rf"/media/({ID})/(hi-IN|en-IN|pa-IN|te-IN)/(narration.wav|transcript.txt)", path)
            if match:
                return self.send_file(LIBRARY.joinpath(*match.groups()))
            assets = {"/": "index.html", "/index.html": "index.html", "/app.js": "app.js", "/style.css": "style.css", "/folk.svg": "folk.svg"}
            if path in assets:
                return self.send_file(STATIC / assets[path])
            self.json_response({"error": "Not found"}, 404)
        except (FileNotFoundError, KeyError):
            self.json_response({"error": "Not found"}, 404)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def send_file(self, path):
        if not path.is_file():
            return self.json_response({"error": "File not ready"}, 404)
        size = path.stat().st_size
        start, end = 0, size - 1
        request_range = self.headers.get("Range", "")
        if request_range:
            match = re.fullmatch(r"bytes=(\d*)-(\d*)", request_range)
            if not match or not any(match.groups()):
                self.send_error(416); return
            if match[1]:
                start = int(match[1]); end = min(int(match[2]), end) if match[2] else end
            else:
                start = max(0, size - int(match[2]))
            if start > end or start >= size:
                self.send_error(416); return
        self.send_response(206 if request_range else 200)
        self.send_header("Content-Type", mimetypes.guess_type(path.name)[0] or "application/octet-stream")
        self.send_header("Content-Length", str(end - start + 1))
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("X-Content-Type-Options", "nosniff")
        if request_range:
            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.end_headers()
        with path.open("rb") as file:
            file.seek(start)
            remaining = end - start + 1
            while remaining:
                chunk = file.read(min(65536, remaining))
                if not chunk: break
                self.wfile.write(chunk)
                remaining -= len(chunk)

    def do_POST(self):
        origin = self.headers.get("Origin")
        if origin and origin not in {"http://127.0.0.1:8000", "http://localhost:8000"}:
            return self.json_response({"error": "Origin not allowed"}, 403)
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > 40 * 1024 * 1024:
                return self.json_response({"error": "Please upload a PDF smaller than 40 MB."}, 413)
            path = urlparse(self.path).path
            body = self.rfile.read(length)
            if path == "/api/upload":
                filename = unquote(self.headers.get("X-Filename", "paper.pdf"))
                language = self.headers.get("X-Paper-Language", "en-IN")
                if not body.startswith(b"%PDF-"):
                    raise ValueError("Please choose a valid PDF.")
                return self.json_response(start_job(lambda progress: analyse_pdf(body, filename, language, progress)), 202)
            if len(body) > 30000:
                raise ValueError("Request too large.")
            data = json.loads(body)
            paper_id = data.get("paper_id", "")
            language = data.get("language", "")
            if not re.fullmatch(ID, paper_id) or not (LIBRARY / paper_id / "analysis.json").exists():
                raise ValueError("Please process a paper first.")
            if language not in LANGUAGES:
                raise ValueError("Please choose a narration language.")
            if path == "/api/narrate":
                return self.json_response(start_job(lambda progress: generate_story(paper_id, language, progress)), 202)
            if path == "/api/feedback":
                rating = data.get("rating")
                understood = data.get("understood", "").strip()
                if type(rating) is not int or not 1 <= rating <= 5 or not 3 <= len(understood) <= 3000:
                    raise ValueError("Choose a rating and share what you understood (3–3000 characters).")
                if not (LIBRARY / paper_id / language / "story.json").exists():
                    raise ValueError("Please generate and listen to the story first.")
                record = {"paper_id": paper_id, "language": language, "rating": rating, "understood": understood, "created_at": time.time()}
                write_json(LIBRARY / "feedback" / f"{uuid.uuid4().hex}.json", record)
                return self.json_response({"saved": True})
            self.json_response({"error": "Not found"}, 404)
        except (ValueError, TypeError, AttributeError) as error:
            self.json_response({"error": str(error)}, 400)
        except (BrokenPipeError, ConnectionResetError):
            pass


if __name__ == "__main__":
    print("Katha is ready at http://127.0.0.1:8000", flush=True)
    ThreadingHTTPServer(("127.0.0.1", 8000), Handler).serve_forever()
