"""
Pydantic schemas for the /jobs and /watcher endpoints.

JobBulkCreate  — request body for POST /jobs (1–50 URLs)
JobBulkResult  — one entry in the 207 response array
JobResponse    — serialized Job for GET responses
StatsResponse  — response for GET /jobs/stats
WatcherStatus  — response for GET /watcher/status
WatcherConfig  — request body for PUT /watcher/config
ApiResponse    — generic {data, error} envelope (unchanged)
"""

from datetime import datetime
from typing import Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    data: T | None = None
    error: str | None = None


class JobBulkCreate(BaseModel):
    urls: list[HttpUrl] = Field(min_length=1, max_length=50)


class JobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    url: str
    source: str
    source_type: str
    extracted_text: str | None
    parsed_json: dict | None
    status: str
    created_at: datetime
    updated_at: datetime


class JobBulkResult(BaseModel):
    url: str
    success: bool
    job: JobResponse | None = None
    skipped: bool = False
    error: str | None = None


class StatsResponse(BaseModel):
    total: int
    greenhouse: int
    lever: int
    unknown: int


class SyncProgress(BaseModel):
    current: int
    total: int


class WatcherStatus(BaseModel):
    enabled: bool
    path: str | None
    state: str  # "idle" | "syncing"
    last_synced_at: datetime | None
    urls_found: int
    sync_progress: SyncProgress
    new_job_ids: list[str]


class WatcherConfig(BaseModel):
    path: str
