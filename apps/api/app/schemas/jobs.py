"""
Pydantic schemas for the /jobs endpoints.

These are the public contract — what the API accepts and returns.
Kept separate from DB models so we can evolve storage without changing the API.

ApiResponse is a generic wrapper that gives every endpoint a consistent shape:
    {"data": <payload>, "error": <string|null>}
The frontend can always check `error` first, then read `data`.
"""

from datetime import datetime
from typing import Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, HttpUrl

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    data: T | None = None
    error: str | None = None


class JobCreate(BaseModel):
    url: HttpUrl


class JobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    url: str
    source: str
    extracted_text: str | None
    parsed_json: dict | None
    status: str
    created_at: datetime
    updated_at: datetime
