from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import ProfileSlot
from app.db.session import get_db
from app.schemas.jobs import ApiResponse
from app.schemas.profiles import (
    PROFILE_SLOTS,
    ProfileSlotResponse,
    ProfileSlotUpdate,
    ResumeParseResponse,
    ResumeUploadResponse,
)
from app.services.profile_service import (
    apply_profile_update,
    ensure_profile_slots,
    save_resume_file,
    set_active_slot,
)
from app.services.resume_parser import extract_pdf_text, parse_resume_to_profile

router = APIRouter()


async def get_profile_or_404(slot: str, db: AsyncSession) -> ProfileSlot:
    await ensure_profile_slots(db)
    result = await db.execute(
        select(ProfileSlot)
        .options(
            selectinload(ProfileSlot.experiences),
            selectinload(ProfileSlot.educations),
        )
        .where(ProfileSlot.slot == slot)
    )
    profile = result.scalar_one_or_none()
    if profile is None:
        raise HTTPException(status_code=404, detail="Profile slot not found")
    return profile


@router.get("", response_model=ApiResponse[list[ProfileSlotResponse]])
async def list_profiles(db: AsyncSession = Depends(get_db)) -> dict:
    profiles = await ensure_profile_slots(db)
    return {"data": profiles}


@router.get("/{slot}", response_model=ApiResponse[ProfileSlotResponse])
async def get_profile(slot: str, db: AsyncSession = Depends(get_db)) -> dict:
    if slot not in PROFILE_SLOTS:
        raise HTTPException(status_code=404, detail="Profile slot not found")
    profile = await get_profile_or_404(slot, db)
    return {"data": profile}


@router.put("/{slot}", response_model=ApiResponse[ProfileSlotResponse])
async def update_profile(
    slot: str,
    payload: ProfileSlotUpdate,
    db: AsyncSession = Depends(get_db),
) -> dict:
    if slot not in PROFILE_SLOTS:
        raise HTTPException(status_code=404, detail="Profile slot not found")
    profile = await get_profile_or_404(slot, db)
    apply_profile_update(profile, payload)
    if payload.is_active:
        await set_active_slot(db, slot)
    await db.flush()
    profile = await get_profile_or_404(slot, db)
    return {"data": profile}


@router.put("/active/{slot}", response_model=ApiResponse[ProfileSlotResponse])
async def activate_profile(slot: str, db: AsyncSession = Depends(get_db)) -> dict:
    if slot not in PROFILE_SLOTS:
        raise HTTPException(status_code=404, detail="Profile slot not found")
    profile = await get_profile_or_404(slot, db)
    await set_active_slot(db, slot)
    await db.flush()
    profile = await get_profile_or_404(slot, db)
    return {"data": profile}


@router.post("/{slot}/resume", response_model=ApiResponse[ResumeUploadResponse])
async def upload_resume(
    slot: str,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
) -> dict:
    if slot not in PROFILE_SLOTS:
        raise HTTPException(status_code=404, detail="Profile slot not found")
    profile = await get_profile_or_404(slot, db)
    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Uploaded file was empty")
    filename, _ = save_resume_file(
        profile,
        file.filename or f"{slot}.pdf",
        file.content_type or "application/pdf",
        contents,
    )
    await db.flush()
    assert profile.resume_uploaded_at is not None
    return {
        "data": ResumeUploadResponse(
            slot=slot,
            resume_label=profile.resume_label,
            resume_filename=filename,
            resume_content_type=profile.resume_content_type or "application/pdf",
            resume_uploaded_at=profile.resume_uploaded_at,
        )
    }


@router.post("/{slot}/parse-resume", response_model=ApiResponse[ResumeParseResponse])
async def parse_resume(slot: str, db: AsyncSession = Depends(get_db)) -> dict:
    if slot not in PROFILE_SLOTS:
        raise HTTPException(status_code=404, detail="Profile slot not found")
    profile = await get_profile_or_404(slot, db)
    if not profile.resume_path:
        raise HTTPException(status_code=400, detail="No resume uploaded for this profile")

    resume_path = Path(profile.resume_path)
    text = extract_pdf_text(resume_path.read_bytes())
    if not text:
        raise HTTPException(status_code=422, detail="Could not extract text from PDF")

    parsed = parse_resume_to_profile(text, profile.display_name, profile.resume_label)
    parsed.is_active = profile.is_active
    return {"data": ResumeParseResponse(slot=slot, parsed_profile=parsed)}
