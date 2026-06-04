from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from .meta_snapshots import build_built_in_meta_snapshot_feed
from .regulations import DEFAULT_REGULATION_ID
from .service import (
    build_analysis_route_payload,
    build_builder_move_payload,
    build_builder_species_options_payload,
    build_regulation_catalog_payload,
)
from .version import __version__


CHANGELOG_PATH = Path(__file__).resolve().parents[1] / "CHANGELOG.md"


app = FastAPI(
    title="Pokemon Champions Analyzer API",
    version=__version__,
)


class AnalyzeRequest(BaseModel):
    teamText: str = ""
    regulationId: str = DEFAULT_REGULATION_ID


@app.get("/")
def read_root() -> dict[str, object]:
    return {
        "service": "pokemon-champions-analyzer",
        "status": "ok",
        "default_regulation_id": DEFAULT_REGULATION_ID,
    }


@app.get("/api/catalog")
def get_catalog(
    include_rules: bool = Query(default=False, alias="includeRules"),
    include_team_text: bool = Query(default=False, alias="includeTeamText"),
) -> dict[str, object]:
    return build_regulation_catalog_payload(
        include_team_text=include_team_text,
        include_rules=include_rules,
    )


@app.get("/api/meta-snapshot-source")
def get_meta_snapshot_source() -> dict[str, object]:
    return build_built_in_meta_snapshot_feed()


@app.get("/api/changelog")
def get_changelog() -> JSONResponse:
    try:
        changelog_content = CHANGELOG_PATH.read_text(encoding="utf-8")
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail="CHANGELOG.md not found.") from error

    return JSONResponse(
        {"content": changelog_content},
        headers={"Cache-Control": "no-store"},
    )


@app.post("/api/analyze")
def analyze_team(payload: AnalyzeRequest) -> JSONResponse:
    response_payload, status_code = build_analysis_route_payload(
        payload.teamText,
        regulation_id=payload.regulationId,
    )
    return JSONResponse(response_payload, status_code=status_code)


@app.get("/api/builder-species")
def get_builder_species(
    species: str = Query(..., min_length=1),
    regulation_id: str = Query(default=DEFAULT_REGULATION_ID, alias="regulationId"),
) -> dict[str, object]:
    try:
        return build_builder_species_options_payload(species, regulation_id=regulation_id)
    except (KeyError, LookupError) as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@app.get("/api/builder-move")
def get_builder_move(move: str = Query(..., min_length=1)) -> dict[str, object]:
    try:
        return build_builder_move_payload(move)
    except LookupError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error