from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import (
    ApplicationEvent,
    ApplicationSession,
    Job,
    ProfileEducation,
    ProfileExperience,
    ProfileSlot,
)
from app.db.session import get_db
from app.schemas.application_sessions import (
    ApplicationEventsCreate,
    ApplicationSessionCreate,
    ApplicationSessionResponse,
    ApplicationSessionResultUpdate,
    ExtensionPayloadResponse,
)
from app.schemas.jobs import ApiResponse
from app.services.profile_service import ensure_profile_slots, flattened_extension_profile

router = APIRouter()


async def get_session_or_404(session_id: UUID, db: AsyncSession) -> ApplicationSession:
    result = await db.execute(
        select(ApplicationSession)
        .execution_options(populate_existing=True)
        .options(selectinload(ApplicationSession.events))
        .where(ApplicationSession.id == session_id)
    )
    session = result.scalar_one_or_none()
    if session is None:
        raise HTTPException(status_code=404, detail="Application session not found")
    return session


@router.post("", response_model=ApiResponse[ApplicationSessionResponse])
async def create_session(
    payload: ApplicationSessionCreate,
    db: AsyncSession = Depends(get_db),
) -> dict:
    await ensure_profile_slots(db)
    profile = await db.get(ProfileSlot, payload.profile_slot)
    if profile is None:
        raise HTTPException(status_code=404, detail="Profile slot not found")
    if payload.job_id:
        job = await db.get(Job, payload.job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Job not found")

    session = ApplicationSession(
        profile_slot=payload.profile_slot,
        job_id=payload.job_id,
        page_url=payload.page_url,
        origin=payload.origin,
        state="started",
    )
    db.add(session)
    await db.flush()
    session = await get_session_or_404(session.id, db)
    return {"data": session}


@router.get("", response_model=ApiResponse[list[ApplicationSessionResponse]])
async def list_sessions(db: AsyncSession = Depends(get_db)) -> dict:
    result = await db.execute(
        select(ApplicationSession)
        .options(selectinload(ApplicationSession.events))
        .order_by(ApplicationSession.created_at.desc())
    )
    return {"data": result.scalars().unique().all()}


@router.get("/{session_id}", response_model=ApiResponse[ApplicationSessionResponse])
async def get_session(session_id: UUID, db: AsyncSession = Depends(get_db)) -> dict:
    session = await get_session_or_404(session_id, db)
    return {"data": session}


@router.get("/{session_id}/payload", response_model=ApiResponse[ExtensionPayloadResponse])
async def get_session_payload(session_id: UUID, db: AsyncSession = Depends(get_db)) -> dict:
    session = await get_session_or_404(session_id, db)
    profile_result = await db.execute(
        select(ProfileSlot)
        .options(
            selectinload(ProfileSlot.experiences),
            selectinload(ProfileSlot.educations),
        )
        .where(ProfileSlot.slot == session.profile_slot)
    )
    profile = profile_result.scalar_one_or_none()
    if profile is None:
        raise HTTPException(status_code=404, detail="Profile slot not found")
    job = await db.get(Job, session.job_id) if session.job_id else None
    return {
        "data": ExtensionPayloadResponse(
            session_id=session.id,
            profile_slot=session.profile_slot,
            profile=flattened_extension_profile(profile),
            profile_record=profile,
            job=(
                {
                    "id": str(job.id),
                    "url": job.url,
                    "source": job.source,
                    "status": job.status,
                    "parsed_json": job.parsed_json,
                }
                if job
                else None
            ),
        )
    }


@router.post("/{session_id}/events", response_model=ApiResponse[ApplicationSessionResponse])
async def create_events(
    session_id: UUID,
    payload: ApplicationEventsCreate,
    db: AsyncSession = Depends(get_db),
) -> dict:
    session = await get_session_or_404(session_id, db)
    for event in payload.events:
        db.add(
            ApplicationEvent(
                session_id=session.id,
                event_type=event.event_type,
                field_name=event.field_name,
                selector=event.selector,
                detail_json=event.detail_json,
            )
        )
    session.state = "filling"
    await db.flush()
    session = await get_session_or_404(session.id, db)
    return {"data": session}


@router.post("/{session_id}/result", response_model=ApiResponse[ApplicationSessionResponse])
async def update_result(
    session_id: UUID,
    payload: ApplicationSessionResultUpdate,
    db: AsyncSession = Depends(get_db),
) -> dict:
    session = await get_session_or_404(session_id, db)
    session.state = payload.state
    session.final_result = payload.final_result
    if payload.submitted:
        session.submitted_at = datetime.now(timezone.utc)
    await db.flush()
    session = await get_session_or_404(session.id, db)
    return {"data": session}
