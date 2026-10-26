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