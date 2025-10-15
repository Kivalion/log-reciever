import json
import sqlite3
from contextlib import closing
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from flask import Flask, jsonify, render_template, request

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "logs.db"

app = Flask(__name__)


def ensure_schema(conn: sqlite3.Connection) -> None:
    desired_columns = ["id", "mac_address", "level", "message", "created_at", "extra"]
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mac_address TEXT NOT NULL,
            level TEXT,
            message TEXT,
            created_at TEXT NOT NULL,
            extra TEXT DEFAULT '{}'
        )
        """
    )

    columns_info = conn.execute("PRAGMA table_info(logs)").fetchall()
    column_names = [row[1] for row in columns_info]

    # Determine whether we need to rebuild the table to match the desired schema
    needs_rebuild = False
    if column_names != desired_columns:
        needs_rebuild = True
    else:
        # Check for NOT NULL constraint on message column (row[3] is notnull flag)
        for row in columns_info:
            if row[1] == "message" and row[3] == 1:
                needs_rebuild = True
                break

    if not needs_rebuild:
        return

    conn.execute("DROP TABLE IF EXISTS logs__new")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS logs__new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mac_address TEXT NOT NULL,
            level TEXT,
            message TEXT,
            created_at TEXT NOT NULL,
            extra TEXT DEFAULT '{}'
        )
        """
    )

    available_columns = set(column_names)
    select_extra = "extra" if "extra" in available_columns else "'{}' AS extra"
    select_message = "message" if "message" in available_columns else "NULL AS message"
    select_level = "level" if "level" in available_columns else "NULL AS level"

    conn.execute(
        f"""
        INSERT INTO logs__new (id, mac_address, level, message, created_at, extra)
        SELECT id, mac_address, {select_level}, {select_message}, created_at, {select_extra}
        FROM logs
        """
    )

    conn.execute("DROP TABLE logs")
    conn.execute("ALTER TABLE logs__new RENAME TO logs")


def init_db() -> None:
    with closing(sqlite3.connect(DB_PATH)) as conn:
        ensure_schema(conn)
        conn.commit()


def insert_log(payload: Dict[str, Any]) -> Dict[str, Any]:
    mac_address = payload.get("mac_address")
    message = payload.get("message")
    level = payload.get("level")
    extra_fields: Dict[str, Any] = {
        key: value
        for key, value in payload.items()
        if key not in {"mac_address", "level", "message"}
    }

    if not mac_address or not isinstance(mac_address, str):
        raise ValueError("mac_address is required and must be a string")
    if message is not None and not isinstance(message, str):
        raise ValueError("message must be a string if provided")
    if level is not None and not isinstance(level, str):
        raise ValueError("level must be a string if provided")

    created_at = datetime.utcnow().isoformat()

    try:
        extra_json = json.dumps(extra_fields or {})
    except (TypeError, ValueError) as exc:
        raise ValueError("additional fields must be JSON serializable") from exc

    with closing(sqlite3.connect(DB_PATH)) as conn:
        conn.execute(
            """
            INSERT INTO logs (mac_address, level, message, created_at, extra)
            VALUES (?, ?, ?, ?, ?)
            """,
            (mac_address, level, message, created_at, extra_json),
        )
        conn.commit()

    log = {
        "mac_address": mac_address,
        "level": level,
        "message": message,
        "created_at": created_at,
    }
    log.update(extra_fields)
    return log


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

    query = "SELECT mac_address, level, message, created_at, extra FROM logs"
    filters: List[str] = []
    params: List[Any] = []

    if mac:
        filters.append("mac_address = ?")
        params.append(mac)

    if search:
        filters.append(
            "(message LIKE ? OR level LIKE ? OR mac_address LIKE ? OR extra LIKE ?)"
        )
        search_term = f"%{search}%"
        params.extend([search_term, search_term, search_term, search_term])

    if filters:
        query += " WHERE " + " AND ".join(filters)

    query += f" ORDER BY {sort_by} {order}, id DESC"

    with closing(sqlite3.connect(DB_PATH)) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(query, params).fetchall()

    results: List[Dict[str, Any]] = []
    for row in rows:
        row_dict = dict(row)
        extra: Dict[str, Any] = {}
        raw_extra = row_dict.get("extra")
        if raw_extra:
            try:
                extra = json.loads(raw_extra)
            except json.JSONDecodeError:
                extra = {"extra": raw_extra}

        log = {
            "mac_address": row_dict.get("mac_address"),
            "level": row_dict.get("level"),
            "message": row_dict.get("message"),
            "created_at": row_dict.get("created_at"),
        }
        if isinstance(extra, dict):
            log.update(extra)
        else:
            log["extra"] = extra
        results.append(log)

    return results


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
