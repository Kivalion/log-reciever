import sqlite3
from contextlib import closing
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from flask import Flask, jsonify, render_template, request

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "logs.db"

app = Flask(__name__)


def init_db() -> None:
    with closing(sqlite3.connect(DB_PATH)) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                mac_address TEXT NOT NULL,
                level TEXT,
                message TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.commit()


def insert_log(payload: Dict[str, Any]) -> Dict[str, Any]:
    mac_address = payload.get("mac_address")
    message = payload.get("message")
    level = payload.get("level")

    if not mac_address or not isinstance(mac_address, str):
        raise ValueError("mac_address is required and must be a string")
    if not message or not isinstance(message, str):
        raise ValueError("message is required and must be a string")

    created_at = datetime.utcnow().isoformat()

    with closing(sqlite3.connect(DB_PATH)) as conn:
        conn.execute(
            "INSERT INTO logs (mac_address, level, message, created_at) VALUES (?, ?, ?, ?)",
            (mac_address, level, message, created_at),
        )
        conn.commit()

    return {
        "mac_address": mac_address,
        "level": level,
        "message": message,
        "created_at": created_at,
    }


def fetch_logs(
    mac: Optional[str] = None,
    search: Optional[str] = None,
    sort_by: str = "created_at",
    order: str = "desc",
) -> List[Dict[str, Any]]:
    valid_sort_fields = {"created_at", "mac_address", "level"}
    if sort_by not in valid_sort_fields:
        sort_by = "created_at"

    order = "DESC" if order.lower() == "desc" else "ASC"

    query = "SELECT mac_address, level, message, created_at FROM logs"
    filters: List[str] = []
    params: List[Any] = []

    if mac:
        filters.append("mac_address = ?")
        params.append(mac)

    if search:
        filters.append("(message LIKE ? OR level LIKE ? OR mac_address LIKE ?)")
        search_term = f"%{search}%"
        params.extend([search_term, search_term, search_term])

    if filters:
        query += " WHERE " + " AND ".join(filters)

    query += f" ORDER BY {sort_by} {order}, id DESC"

    with closing(sqlite3.connect(DB_PATH)) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(query, params).fetchall()

    return [dict(row) for row in rows]


init_db()


@app.route("/")
def index() -> str:
    return render_template("index.html")


@app.route("/api/logs", methods=["POST"])
def create_log():
    try:
        data = request.get_json(force=True)
    except Exception:
        return jsonify({"error": "Invalid JSON payload"}), 400

    try:
        log = insert_log(data or {})
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    return jsonify({"status": "ok", "log": log}), 201


@app.route("/api/logs", methods=["GET"])
def list_logs():
    mac = request.args.get("mac")
    search = request.args.get("search")
    sort_by = request.args.get("sort", "created_at")
    order = request.args.get("order", "desc")

    logs = fetch_logs(mac=mac, search=search, sort_by=sort_by, order=order)

    return jsonify({"logs": logs})


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=8000, debug=True)
