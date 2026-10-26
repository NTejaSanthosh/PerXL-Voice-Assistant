import json
from collections import Counter
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
FRONTEND_FILE = BASE_DIR / "public" / "index.html"

app = FastAPI(
    title="PerXL Data Review API",
    description="PerXL Data Review API",
    version="2.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def home():
    if FRONTEND_FILE.exists():
        return FileResponse(FRONTEND_FILE)
    return {
        "message": "PerXL Data Review API is running",
        "documentation": "/docs",
        "health": "/health",
    }


@app.get("/health")
def health():
    return {"status": "ok"}


def get_available_collections():
    if not DATA_DIR.exists():
        return []

    return sorted(
        path.stem
        for path in DATA_DIR.glob("*.json")
        if path.is_file()
    )


def load_collection(collection_name):
    if not DATA_DIR.exists():
        raise HTTPException(
            status_code=404,
            detail="Data directory is not available on this deployment.",
        )

    safe_name = Path(collection_name).name
    file_path = DATA_DIR / (
        safe_name if safe_name.endswith(".json")
        else f"{safe_name}.json"
    )

    if not file_path.exists() or file_path.parent != DATA_DIR:
        raise HTTPException(
            status_code=404,
            detail=f"Collection '{collection_name}' was not found.",
        )

    try:
        with file_path.open("r", encoding="utf-8-sig") as file:
            data = json.load(file)
    except (json.JSONDecodeError, OSError):
        raise HTTPException(
            status_code=500,
            detail=f"Collection '{collection_name}' could not be read.",
        )

    if isinstance(data, list):
        return data

    if isinstance(data, dict):
        for key in ("records", "data", "items"):
            if isinstance(data.get(key), list):
                return data[key]
        return [data]

    return []


@app.get("/collections")
def collections():
    available = get_available_collections()
    return {
        "count": len(available),
        "collections": available,
    }


@app.get("/collections/{collection_name}/schema")
def collection_schema(collection_name: str):
    records = load_collection(collection_name)
    fields = sorted({
        key
        for record in records
        if isinstance(record, dict)
        for key in record.keys()
    })

    return {
        "collection": collection_name,
        "total_records": len(records),
        "fields": fields,
    }


@app.get("/collections/{collection_name}/records")
def collection_records(
    collection_name: str,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    records = load_collection(collection_name)

    return {
        "collection": collection_name,
        "total_records": len(records),
        "limit": limit,
        "offset": offset,
        "records": records[offset:offset + limit],
    }


@app.get("/collections/{collection_name}/search")
def search_collection(
    collection_name: str,
    q: str = Query(..., min_length=1),
    limit: int = Query(100, ge=1, le=1000),
):
    records = load_collection(collection_name)
    query = q.casefold()

    matches = [
        record
        for record in records
        if query in json.dumps(
            record,
            ensure_ascii=False,
            default=str,
        ).casefold()
    ]

    return {
        "collection": collection_name,
        "query": q,
        "total_matches": len(matches),
        "records": matches[:limit],
    }
    def get_task_records():
    return load_collection("PTMTDB_Prod.Tasks")


@app.get("/tasks/summary")
def task_summary():
    records = get_task_records()
    statuses = Counter(
        str(record.get("Status", "Unknown"))
        for record in records
        if isinstance(record, dict)
    )
    priorities = Counter(
        str(record.get("Priority", "Unknown"))
        for record in records
        if isinstance(record, dict)
    )

    closed_count = sum(
        1
        for record in records
        if isinstance(record, dict)
        and str(record.get("IsClosed", "")).casefold() == "true"
    )

    return {
        "total_tasks": len(records),
        "closed_tasks": closed_count,
        "tasks_by_status": dict(statuses),
        "tasks_by_priority": dict(priorities),
    }


@app.get("/tasks/by-status")
def tasks_by_status():
    records = get_task_records()
    counts = Counter(
        str(record.get("Status", "Unknown"))
        for record in records
        if isinstance(record, dict)
    )

    return {
        "total_tasks": len(records),
        "tasks_by_status": dict(counts),
    }


@app.get("/tasks/by-priority")
def tasks_by_priority():
    records = get_task_records()
    counts = Counter(
        str(record.get("Priority", "Unknown"))
        for record in records
        if isinstance(record, dict)
    )

    return {
        "total_tasks": len(records),
        "tasks_by_priority": dict(counts),
    }


@app.get("/tasks/by-space/{space_id}")
def tasks_by_space(space_id: str):
    records = get_task_records()
    matches = [
        record
        for record in records
        if isinstance(record, dict)
        and str(record.get("SpaceID", "")) == space_id
    ]

    return {
        "space_id": space_id,
        "total_tasks": len(matches),
        "tasks": matches,
    }


@app.get("/tasks/{task_id}/comments")
def task_comments(task_id: str):
    records = load_collection("PTMTDB_Prod.TaskComments")
    matches = [
        record
        for record in records
        if isinstance(record, dict)
        and str(record.get("TaskId", "")) == task_id
    ]

    return {
        "task_id": task_id,
        "total_comments": len(matches),
        "comments": matches,
    }


@app.get("/tasks/{task_id}/metrics")
def task_metrics(task_id: str):
    records = load_collection("PTMTDB_Prod.TasksPerformanceMetrics")
    matches = [
        record
        for record in records
        if isinstance(record, dict)
        and str(record.get("TaskId", "")) == task_id
    ]

    return {
        "task_id": task_id,
        "total_metrics": len(matches),
        "metrics": matches,
    }


@app.get("/tasks/{task_id}")
def get_task(task_id: str):
    records = get_task_records()

    for record in records:
        if not isinstance(record, dict):
            continue

        record_id = record.get("TaskId", record.get("_id", record.get("Id")))

        if str(record_id) == task_id:
            return record

    raise HTTPException(
        status_code=404,
        detail=f"Task '{task_id}' was not found.",
    )
