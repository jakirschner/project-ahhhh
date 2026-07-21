import os
import sqlite3
from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
from datetime import datetime, timezone

app = Flask(__name__)
CORS(app)

DB_PATH = os.environ.get("DB_PATH", "/data/ahhh.db")

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
        return jsonify({row["id"]: {"value": row["value"], "updated_at": row["updated_at"]} for row in rows})


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


init_db()

if __name__ == "__main__":
    app.run(debug=True, port=5099)
