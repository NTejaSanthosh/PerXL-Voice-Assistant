
import json
from collections import Counter
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

DATA_DIR = Path(__file__).parent / "data"
EXCLUDED_WORDS = {"resource", "secret", "credential", "password"}

app = FastAPI(
    title="PerXL Data Review API",
    description="Local demonstration using exported JSON files",
    version="2.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5500",
        "http://127.0.0.1:8000",
        "http://localhost:8000",
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_available_collections():
    if not DATA_DIR.exists():
        return {}

    collections = {}

    for path in DATA_DIR.glob("*.json"):
        name_lower = path.stem.lower()

        if any(word in name_lower for word in EXCLUDED_WORDS):
            continue

        collections[path.stem] = path

    return collections


def load_collection(collection_name):
    collections = get_available_collections()

    if collection_name not in collections:
        raise HTTPException(
            status_code=404,
            detail="Collection not found or excluded from this demo.",
        )

    file_path = collections[collection_name]

    try:
        with file_path.open("r", encoding="utf-8-sig") as file:
            data = json.load(file)
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=f"Data file not found for collection: {collection_name}",
        ) from exc
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid JSON in collection: {collection_name}",
        ) from exc
    except OSError as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Unable to read collection: {collection_name}",
        ) from exc

    if isinstance(data, list):
        return data

    if isinstance(data, dict):
        for key in ("data", "results", "items", "tasks", "Tasks"):
            if isinstance(data.get(key), list):
                return data[key]

        return [data]

    raise HTTPException(
        status_code=422,
        detail=f"Unsupported JSON structure in collection: {collection_name}",
    )


def get_task_records():
    return load_collection("PTMTDB_Prod.Tasks")


def normalize_value(value):
    if isinstance(value, dict) and "$oid" in value:
        return str(value["$oid"])
    return str(value) if value is not None else ""


@app.get("/")
def home():
    return {
        "message": "PerXL Data Review API is running",
        "documentation": "/docs",
        "collections_endpoint": "/collections",
        "health": "ok",
    }


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "data_directory_exists": DATA_DIR.exists(),
        "available_collections": len(get_available_collections()),
    }


@app.get("/collections")
def list_collections():
    collections = get_available_collections()

    return {
        "count": len(collections),
        "collections": [
            {"name": name, "filename": path.name}
            for name, path in sorted(collections.items())
        ],
    }


@app.get("/collections/{collection_name}/schema")
def inspect_collection(collection_name: str):
    records = load_collection(collection_name)

    sample = next(
        (record for record in records if isinstance(record, dict)),
        None,
    )

    return {
        "collection": collection_name,
        "record_count": len(records),
        "fields": list(sample.keys()) if sample else [],
        "sample_record_available": sample is not None,
    }


@app.get("/collections/{collection_name}/records")
def list_records(
    collection_name: str,
    limit: int = Query(default=20, ge=1, le=100),
):
    records = load_collection(collection_name)

    return {
        "collection": collection_name,
        "total_records": len(records),
        "returned_records": min(limit, len(records)),
        "records": records[:limit],
    }


@app.get("/collections/{collection_name}/search")
def search_records(
    collection_name: str,
    field: str,
    value: str,
    limit: int = Query(default=20, ge=1, le=100),
):
    records = load_collection(collection_name)
    matches = []

    for record in records:
        if not isinstance(record, dict):
            continue

        if field in record and normalize_value(record[field]).casefold() == value.casefold():
            matches.append(record)

    return {
        "collection": collection_name,
        "field": field,
        "value": value,
        "match_count": len(matches),
        "returned_records": min(limit, len(matches)),
        "records": matches[:limit],
    }


@app.get("/tasks/summary")
def task_summary():
    tasks = get_task_records()

    statuses = Counter()
    priorities = Counter()
    closed_count = 0

    for task in tasks:
        if not isinstance(task, dict):
            continue

        status = task.get("Status")
        priority = task.get("Priority")

        statuses[normalize_value(status) or "Unknown"] += 1
        priorities[normalize_value(priority) or "Unknown"] += 1

        is_closed = str(task.get("IsClosed", "")).strip().lower()

        if is_closed in ("true", "1", "yes"):
            closed_count += 1

    return {
        "total_tasks": len(tasks),
        "closed_tasks": closed_count,
        "tasks_by_status": dict(statuses),
        "tasks_by_priority": dict(priorities),
    }


@app.get("/tasks/by-status")
def tasks_by_status(
    status: str = Query(..., min_length=1),
    limit: int = Query(default=20, ge=1, le=100),
):
    if not status.strip():
        raise HTTPException(
            status_code=422,
            detail="Status cannot be empty.",
        )

    tasks = get_task_records()

    matches = [
        task
        for task in tasks
        if isinstance(task, dict)
        and normalize_value(task.get("Status")).casefold() == status.strip().casefold()
    ]

    return {
        "status": status.strip(),
        "match_count": len(matches),
        "returned_records": min(limit, len(matches)),
        "tasks": matches[:limit],
    }


@app.get("/tasks/by-priority")
def tasks_by_priority(
    priority: str = Query(..., min_length=1),
    limit: int = Query(default=20, ge=1, le=100),
):
    tasks = get_task_records()

    matches = [
        task
        for task in tasks
        if isinstance(task, dict)
        and normalize_value(task.get("Priority")).casefold() == priority.strip().casefold()
    ]

    return {
        "priority": priority,
        "match_count": len(matches),
        "returned_records": min(limit, len(matches)),
        "tasks": matches[:limit],
    }


@app.get("/tasks/by-space/{space_id}")
def tasks_by_space(
    space_id: str,
    limit: int = Query(default=20, ge=1, le=100),
):
    tasks = get_task_records()

    matches = [
        task
        for task in tasks
        if isinstance(task, dict)
        and normalize_value(task.get("SpaceID")) == space_id
    ]

    return {
        "space_id": space_id,
        "match_count": len(matches),
        "returned_records": min(limit, len(matches)),
        "tasks": matches[:limit],
    }


@app.get("/tasks/{task_id}/comments")
def comments_for_task(
    task_id: str,
    limit: int = Query(default=20, ge=1, le=100),
):
    records = load_collection("PTMTDB_Prod.TaskComments")

    matches = [
        record
        for record in records
        if isinstance(record, dict)
        and normalize_value(record.get("TaskId")) == task_id
    ]

    return {
        "task_id": task_id,
        "match_count": len(matches),
        "returned_records": min(limit, len(matches)),
        "comments": matches[:limit],
    }


@app.get("/tasks/{task_id}/metrics")
def metrics_for_task(
    task_id: str,
    limit: int = Query(default=20, ge=1, le=100),
):
    records = load_collection("PTMTDB_Prod.TasksPerformanceMetrics")

    matches = [
        record
        for record in records
        if isinstance(record, dict)
        and normalize_value(record.get("TaskId")) == task_id
    ]

    return {
        "task_id": task_id,
        "match_count": len(matches),
        "returned_records": min(limit, len(matches)),
        "metrics": matches[:limit],
    }


@app.get("/tasks/{task_id}")
def task_by_id(task_id: str):
    tasks = get_task_records()

    for task in tasks:
        if isinstance(task, dict) and normalize_value(task.get("_id")) == task_id:
            return task

    raise HTTPException(
        status_code=404,
        detail="Task not found. Check the task _id.",
    )


@app.get("/sections")
def list_sections(
    limit: int = Query(default=20, ge=1, le=100),
):
    records = load_collection("PTMTDB_Prod.Sections")

    return {
        "total_records": len(records),
        "returned_records": min(limit, len(records)),
        "sections": records[:limit],
    }


@app.get("/sections/by-space/{space_id}")
def sections_by_space(
    space_id: str,
    limit: int = Query(default=20, ge=1, le=100),
):
    records = load_collection("PTMTDB_Prod.Sections")

    matches = [
        record
        for record in records
        if isinstance(record, dict)
        and normalize_value(record.get("SpaceID")) == space_id
    ]

    return {
        "space_id": space_id,
        "match_count": len(matches),
        "returned_records": min(limit, len(matches)),
        "sections": matches[:limit],
    }


@app.get("/spaces")
def list_spaces(
    limit: int = Query(default=20, ge=1, le=100),
):
    records = load_collection("PTMTDB_Prod.Space")

    return {
        "total_records": len(records),
        "returned_records": min(limit, len(records)),
        "spaces": records[:limit],
    }


@app.get("/spaces/by-workspace/{workspace_id}")
def spaces_by_workspace(
    workspace_id: str,
    limit: int = Query(default=20, ge=1, le=100),
):
    records = load_collection("PTMTDB_Prod.Space")

    matches = [
        record
        for record in records
        if isinstance(record, dict)
        and normalize_value(record.get("WorkSpaceID")) == workspace_id
    ]

    return {
        "workspace_id": workspace_id,
        "match_count": len(matches),
        "returned_records": min(limit, len(matches)),
        "spaces": matches[:limit],
    }
