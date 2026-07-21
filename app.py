import os
import sqlite3
import threading
import cloudscraper
from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
from datetime import datetime, timezone

app = Flask(__name__)
CORS(app)

DB_PATH = os.environ.get("DB_PATH", "/data/ahhh.db")

# --- Platform status (read from status.learn.mit.edu) ---

STATUS_TO_VALUE = {"none": 0, "minor": 30, "major": 70, "critical": 100}
PLATFORM_CACHE_TTL = 60  # seconds

_platform_cache = {"value": 0, "description": "Checking...", "updated_at": None}
_platform_lock = threading.Lock()


def _fetch_platform_status():
    try:
        scraper = cloudscraper.create_scraper()
        resp = scraper.get(
            "https://status.learn.mit.edu/api/v2/status.json", timeout=10
        )
        data = resp.json()
        indicator = data["status"]["indicator"]
        description = data["status"]["description"]
        value = STATUS_TO_VALUE.get(indicator, 0)
        with _platform_lock:
            _platform_cache.update(
                value=value,
                description=description,
                updated_at=datetime.now(timezone.utc).isoformat(),
            )
    except Exception as e:
        print(f"Platform status fetch failed: {e}")


def get_platform_status():
    with _platform_lock:
        updated_at = _platform_cache.get("updated_at")
    stale = updated_at is None or (
        datetime.now(timezone.utc)
        - datetime.fromisoformat(updated_at)
    ).total_seconds() > PLATFORM_CACHE_TTL
    if stale:
        _fetch_platform_status()
    with _platform_lock:
        return dict(_platform_cache)

SCALES = [
    {"id": "jace", "label": "Jace", "group": "team"},
    {"id": "shelly", "label": "Shelly", "group": "team"},
    {"id": "shira", "label": "Shira", "group": "team"},
    {"id": "meredith", "label": "Meredith", "group": "team"},
    {"id": "kaleb", "label": "Kaleb", "group": "team"},
    {"id": "kyle", "label": "Kyle", "group": "team"},
    {"id": "engineering", "label": "Engineering", "group": "project"},
    {"id": "micromasters", "label": "MicroMasters", "group": "project"},
]
SCALE_IDS = {s["id"] for s in SCALES}


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with get_db() as conn:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS scales
               (id TEXT PRIMARY KEY, value INTEGER DEFAULT 0, updated_at TEXT)"""
        )
        for scale in SCALES:
            conn.execute(
                "INSERT OR IGNORE INTO scales (id, value, updated_at) VALUES (?, 0, ?)",
                (scale["id"], datetime.now(timezone.utc).isoformat()),
            )


@app.route("/")
def index():
    return render_template("index.html", scales=SCALES)


@app.route("/api/values")
def get_values():
    with get_db() as conn:
        rows = conn.execute("SELECT id, value, updated_at FROM scales").fetchall()
        data = {row["id"]: {"value": row["value"], "updated_at": row["updated_at"]} for row in rows}
    data["__platform__"] = get_platform_status()
    return jsonify(data)


@app.route("/api/values", methods=["POST"])
def set_value():
    data = request.get_json()
    scale_id = data.get("id")
    value = data.get("value")
    if scale_id not in SCALE_IDS:
        return jsonify({"error": "Unknown scale"}), 400
    value = max(0, min(100, int(value)))
    now = datetime.now(timezone.utc).isoformat()
    with get_db() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO scales (id, value, updated_at) VALUES (?, ?, ?)",
            (scale_id, value, now),
        )
    return jsonify({"ok": True, "id": scale_id, "value": value, "updated_at": now})


@app.route("/api/platform-status")
def platform_status_route():
    return jsonify(get_platform_status())


init_db()

if __name__ == "__main__":
    app.run(debug=True, port=5099)
