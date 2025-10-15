# Log Receiver

A minimal Flask application for receiving JSON log entries over HTTP and visualising them in a simple web UI with filtering, sorting, and searching.

## Features

- `POST /api/logs` accepts JSON payloads with `mac_address` plus any additional fields you want to store (such as `message`, `level`, or device metrics).
- `GET /api/logs` returns stored logs with optional `mac`, `search`, `sort`, and `order` query parameters.
- Responsive HTML dashboard for inspecting logs with built-in filtering, sorting, and search controls.
- Logs are persisted in a local SQLite database (`logs.db`).

## Getting started

### Prerequisites

- Python 3.10+

### Installation

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Running the application

```bash
flask --app app run --host 0.0.0.0 --port 8000
```

The UI is available at `http://localhost:8000/` and the API endpoint for receiving logs is `http://localhost:8000/api/logs`.

### Example payload

```bash
curl -X POST http://localhost:8000/api/logs \
  -H "Content-Type: application/json" \
  -d '{
    "mac_address": "AA:BB:CC:DD:EE:FF",
    "message": "Device started",
    "battery": 97,
    "temperature": 21.4
  }'
```

Any extra fields are stored alongside the core metadata and automatically appear as new columns in the dashboard.

### Environment variables

No environment variables are required. A local SQLite database file (`logs.db`) is created automatically in the project directory.

## Development notes

- The database schema is created automatically on startup.
- To start fresh, delete `logs.db` before running the application.
