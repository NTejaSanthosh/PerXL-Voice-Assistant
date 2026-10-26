import json
from collections import Counter
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
FRONTEND_FILE = BASE_DIR / "public" / "index.html"
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

