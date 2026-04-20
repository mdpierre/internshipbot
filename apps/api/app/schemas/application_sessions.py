from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.profiles import ProfileSlotResponse


class ApplicationSessionCreate(BaseModel):
    profile_slot: str
    page_url: str
    origin: str = "extension"
    job_id: UUID | None = None


class ApplicationEventInput(BaseModel):
    event_type: str
    field_name: str | None = None
    selector: str | None = None
    detail_json: dict | list | None = None


class ApplicationEventsCreate(BaseModel):
    events: list[ApplicationEventInput] = Field(min_length=1)


class ApplicationSessionResultUpdate(BaseModel):
    state: str
    final_result: str | None = None
    submitted: bool = False


class ApplicationEventResponse(ApplicationEventInput):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime


class ApplicationSessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    profile_slot: str
    job_id: UUID | None
    page_url: str
    origin: str
    state: str
    final_result: str | None
    submitted_at: datetime | None
    created_at: datetime
    updated_at: datetime
    events: list[ApplicationEventResponse] = Field(default_factory=list)


class ExtensionPayloadResponse(BaseModel):
    session_id: UUID
    profile_slot: str
    profile: dict
    profile_record: ProfileSlotResponse
    job: dict | None = None


class ExtensionConfigResponse(BaseModel):
    api_base_url: str
    app_name: str
    app_version: str
    healthy: bool
    active_profile_slot: str
    dashboard_url: str
