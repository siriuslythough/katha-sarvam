"""Read-only smoke checks against the running website and saved real recording."""
import io
import json
import urllib.error
import urllib.request
import wave
from sarvam_pipeline import LIBRARY, read_json

BASE = "http://127.0.0.1:8000"


def request(path, data=None, headers=None):
    body = json.dumps(data).encode() if data is not None else None
    return urllib.request.urlopen(urllib.request.Request(BASE + path, data=body,
                                  headers=headers or ({"Content-Type": "application/json"} if body else {})))


assert json.load(request("/api/health"))["ok"]
for path in ["/", "/app.js", "/style.css", "/folk.svg"]:
    assert request(path).status == 200
for path in ["/.env", "/sarvam_pipeline.py", "/media/../../.env"]:
    try:
        request(path)
        raise AssertionError(f"Private path exposed: {path}")
    except urllib.error.HTTPError as error:
        assert error.code == 404
papers = json.load(request("/api/library"))
assert papers and all(paper["pages"] > 0 for paper in papers)
paper = next(paper for paper in papers if (LIBRARY / paper["id"] / "hi-IN" / "story.json").exists())
story = read_json(LIBRARY / paper["id"] / "hi-IN" / "story.json")
audio = request(story["audio_url"]).read()
with wave.open(io.BytesIO(audio), "rb") as wav:
    duration = wav.getnframes() / wav.getframerate()
    assert abs(duration - story["duration"]) < .01
assert 120 <= duration <= 180
assert story["segments"][0]["start"] == 0
assert abs(story["segments"][-1]["end"] - duration) < .01
for first, second in zip(story["segments"], story["segments"][1:]):
    assert first["start"] < first["end"] <= second["start"]
ranged = request(story["audio_url"], headers={"Range": "bytes=100-199"})
assert ranged.status == 206 and ranged.read() == audio[100:200]
try:
    request("/api/feedback", {"paper_id": paper["id"], "language": "hi-IN", "rating": 9, "understood": "Invalid rating test"})
    raise AssertionError("Invalid rating accepted")
except urllib.error.HTTPError as error:
    assert error.code == 400
print(f"PASS: website assets, private-file protection, paper metadata, {duration:.1f}s real audio, passage timestamps, seeking, and feedback validation.")
