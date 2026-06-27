from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

UPLOAD_DIR = BASE_DIR / "uploads"
EVIDENCE_DIR = BASE_DIR / "evidence"
REPORT_DIR = BASE_DIR / "reports"
TESTCASE_DIR = BASE_DIR / "testcases"
TEMP_DIR = BASE_DIR / "temp"

for p in [UPLOAD_DIR, EVIDENCE_DIR, REPORT_DIR, TESTCASE_DIR, TEMP_DIR]:
    p.mkdir(parents=True, exist_ok=True)

DEFAULT_YOLO_MODEL = "yolov8n.pt"
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "qwen3:4b"

METHODS = ["BDD", "ATDD", "TDD", "DDD"]

TARGET_CLASSES = {
    "person": "pedestrian",
    "traffic light": "traffic_light",
    "car": "vehicle",
    "bus": "vehicle",
    "truck": "vehicle",
    "motorcycle": "vehicle",
    "bicycle": "vehicle",
}