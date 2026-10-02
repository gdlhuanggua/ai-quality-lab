import json
import os
import sqlite3
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated, Literal

from fastapi import FastAPI, HTTPException, Path as ApiPath, Query, Response
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.db import connect, initialize
from app.models import Asset, AssetInput, EvaluationRequest, QualityRequest
from app.quality import inspect_quality

ROOT = Path(__file__).resolve().parent.parent
AssetId = Annotated[int, ApiPath(gt=0)]


def create_app(db_path: Path | None = None, *, tools: bool = True) -> FastAPI:
    database = Path(db_path or os.getenv("DATABASE_PATH", ROOT / "data" / "assets.db")).resolve()

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        initialize(database)
        yield

    application = FastAPI(
        title="AI Quality Lab",
        description="Local demo: data assets, quality checks and isolated AI case validation.",
        version="0.1.0",
        lifespan=lifespan,
    )

    @application.get("/health")
    def health():
        with connect(database) as connection:
            connection.execute("SELECT 1")
        return {"status": "ok"}

    @application.get("/api/assets")
    def list_assets(
        q: Annotated[str, Query(max_length=80)] = "",
        limit: Annotated[int, Query(ge=1, le=100)] = 100,
        offset: Annotated[int, Query(ge=0)] = 0,
    ):
        escaped = q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        pattern = f"%{escaped}%"
        where = "WHERE asset_code LIKE ? ESCAPE '\\' OR name LIKE ? ESCAPE '\\' OR owner LIKE ? ESCAPE '\\'"
        with connect(database) as connection:
            total = connection.execute(
                f"SELECT COUNT(*) FROM assets {where}", (pattern,) * 3
            ).fetchone()[0]
            rows = connection.execute(
                f"SELECT * FROM assets {where} ORDER BY id DESC LIMIT ? OFFSET ?",
                (pattern, pattern, pattern, limit, offset),
            ).fetchall()
        return {"total": total, "items": [dict(row) for row in rows]}

    @application.get("/api/assets/{asset_id}", response_model=Asset)
    def get_asset(asset_id: AssetId):
        with connect(database) as connection:
            row = connection.execute("SELECT * FROM assets WHERE id = ?", (asset_id,)).fetchone()
        if row is None:
            raise HTTPException(404, "Asset not found")
        return dict(row)

    @application.post("/api/assets", response_model=Asset, status_code=201)
    def create_asset(asset: AssetInput):
        now = datetime.now(timezone.utc).isoformat()
        with connect(database) as connection:
            try:
                cursor = connection.execute(
                    "INSERT INTO assets (asset_code, name, owner, sensitivity, created_at) VALUES (?, ?, ?, ?, ?)",
                    (*asset.model_dump().values(), now),
                )
            except sqlite3.IntegrityError:
                raise HTTPException(409, "asset_code already exists") from None
        return {**asset.model_dump(), "id": cursor.lastrowid, "created_at": now}

    @application.put("/api/assets/{asset_id}", response_model=Asset)
    def update_asset(asset_id: AssetId, asset: AssetInput):
        with connect(database) as connection:
            if not connection.execute("SELECT 1 FROM assets WHERE id = ?", (asset_id,)).fetchone():
                raise HTTPException(404, "Asset not found")
            try:
                connection.execute(
                    "UPDATE assets SET asset_code = ?, name = ?, owner = ?, sensitivity = ? WHERE id = ?",
                    (*asset.model_dump().values(), asset_id),
                )
            except sqlite3.IntegrityError:
                raise HTTPException(409, "asset_code already exists") from None
            row = connection.execute("SELECT * FROM assets WHERE id = ?", (asset_id,)).fetchone()
        return dict(row)

    @application.delete("/api/assets/{asset_id}", status_code=204)
    def delete_asset(asset_id: AssetId):
        with connect(database) as connection:
            cursor = connection.execute("DELETE FROM assets WHERE id = ?", (asset_id,))
        if cursor.rowcount == 0:
            raise HTTPException(404, "Asset not found")
        return Response(status_code=204)

    if tools:
        @application.post("/api/quality/check")
        def check_quality(payload: QualityRequest):
            return inspect_quality(payload.records)

        @application.post("/api/cases/evaluate")
        def check_cases(payload: EvaluationRequest):
            from app.evaluation import evaluate_cases

            return evaluate_cases(payload.cases)

        @application.get("/api/examples/{kind}")
        def examples(kind: Literal["quality", "cases"]):
            return json.loads((ROOT / "examples" / f"{kind}.json").read_text(encoding="utf-8"))

        @application.get("/", include_in_schema=False)
        def index():
            return FileResponse(ROOT / "app" / "static" / "index.html")

        application.mount("/static", StaticFiles(directory=ROOT / "app" / "static"), name="static")
    return application


app = create_app()
