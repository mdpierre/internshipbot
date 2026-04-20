from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import ProfileEducation, ProfileExperience, ProfileSlot
from app.schemas.profiles import (
    PROFILE_SLOTS,
    ProfileEducationInput,
    ProfileExperienceInput,
    ProfileSlotUpdate,
)

UPLOAD_ROOT = Path(__file__).resolve().parents[3] / "profiles_uploads"


def default_profile_payload(slot: str, *, active: bool = False) -> ProfileSlotUpdate:
    label = {
        "profile_1": "Profile 1",
        "profile_2": "Profile 2",
        "profile_3": "Profile 3",
    }[slot]
    return ProfileSlotUpdate(
        display_name=label,
        profile_name=label,
        target_title="",
        experiences=[ProfileExperienceInput()],
        educations=[ProfileEducationInput()],
        is_active=active,
    )


async def ensure_profile_slots(db: AsyncSession) -> list[ProfileSlot]:
    result = await db.execute(
        select(ProfileSlot)
        .options(
            selectinload(ProfileSlot.experiences),
            selectinload(ProfileSlot.educations),
        )
        .order_by(ProfileSlot.slot)
    )
    slots = list(result.scalars().unique().all())
    existing = {slot.slot for slot in slots}
    created = False
    for index, slot_name in enumerate(PROFILE_SLOTS):
        if slot_name in existing:
            continue
        payload = default_profile_payload(slot_name, active=index == 0)
        slot = ProfileSlot(slot=slot_name)
        apply_profile_update(slot, payload)
        db.add(slot)
        slots.append(slot)
        created = True

    if created:
        await db.flush()
        await db.refresh(slots[0])

    active_slots = [slot for slot in slots if slot.is_active]
    if not active_slots and slots:
        slots[0].is_active = True
        await db.flush()

    result = await db.execute(
        select(ProfileSlot)
        .options(
            selectinload(ProfileSlot.experiences),
            selectinload(ProfileSlot.educations),
        )
        .order_by(ProfileSlot.slot)
    )
    return list(result.scalars().unique().all())


def apply_profile_update(profile: ProfileSlot, payload: ProfileSlotUpdate) -> None:
    profile.display_name = payload.display_name
    profile.profile_name = payload.profile_name
    profile.first_name = payload.first_name
    profile.last_name = payload.last_name
    profile.full_name = payload.full_name or " ".join(filter(None, [payload.first_name, payload.last_name])).strip()
    profile.email = payload.email
    profile.phone = payload.phone
    profile.city = payload.city
    profile.state = payload.state
    profile.zip = payload.zip
    profile.country = payload.country
    profile.linkedin = payload.linkedin
    profile.website = payload.website
    profile.github = payload.github
    profile.target_title = payload.target_title
    profile.target_salary = payload.target_salary
    profile.work_authorization = payload.work_authorization
    profile.require_sponsorship = payload.require_sponsorship
    profile.veteran = payload.veteran
    profile.disability = payload.disability
    profile.gender = payload.gender
    profile.ethnicity = payload.ethnicity
    profile.summary = payload.summary
    profile.resume_label = payload.resume_label
    profile.is_active = payload.is_active

    profile.experiences = [
        ProfileExperience(
            sort_order=index,
            employer=experience.employer,
            title=experience.title,
            start_date=experience.start_date,
            end_date=experience.end_date,
            location=experience.location,
            description=experience.description,
        )
        for index, experience in enumerate(payload.experiences or [ProfileExperienceInput()])
    ]
    profile.educations = [
        ProfileEducation(
            sort_order=index,
            school=education.school,
            degree=education.degree,
            major=education.major,
            graduation_year=education.graduation_year,
            gpa=education.gpa,
        )
        for index, education in enumerate(payload.educations or [ProfileEducationInput()])
    ]


async def set_active_slot(db: AsyncSession, slot_name: str) -> None:
    result = await db.execute(select(ProfileSlot))
    for slot in result.scalars().all():
        slot.is_active = slot.slot == slot_name
    await db.flush()


def save_resume_file(slot: ProfileSlot, filename: str, content_type: str, data: bytes) -> tuple[str, str]:
    UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)
    slot_dir = UPLOAD_ROOT / slot.slot
    slot_dir.mkdir(parents=True, exist_ok=True)
    safe_name = filename.replace("/", "_")
    destination = slot_dir / safe_name
    destination.write_bytes(data)

    slot.resume_label = safe_name
    slot.resume_filename = safe_name
    slot.resume_path = str(destination)
    slot.resume_content_type = content_type
    slot.resume_uploaded_at = datetime.now(timezone.utc)
    return safe_name, str(destination)


def flattened_extension_profile(profile: ProfileSlot) -> dict:
    experience = profile.experiences[0] if profile.experiences else None
    education = profile.educations[0] if profile.educations else None
    return {
        "slot": profile.slot,
        "displayName": profile.display_name,
        "profileName": profile.profile_name,
        "firstName": profile.first_name,
        "lastName": profile.last_name,
        "fullName": profile.full_name,
        "email": profile.email,
        "phone": profile.phone,
        "city": profile.city,
        "state": profile.state,
        "zip": profile.zip,
        "country": profile.country,
        "linkedin": profile.linkedin,
        "website": profile.website,
        "github": profile.github,
        "targetTitle": profile.target_title,
        "targetSalary": profile.target_salary,
        "workAuthorization": profile.work_authorization,
        "requireSponsorship": profile.require_sponsorship,
        "veteran": profile.veteran,
        "disability": profile.disability,
        "gender": profile.gender,
        "ethnicity": profile.ethnicity,
        "summary": profile.summary,
        "resumeLabel": profile.resume_label,
        "experiences": [
            {
                "employer": item.employer,
                "title": item.title,
                "startDate": item.start_date,
                "endDate": item.end_date,
                "location": item.location,
                "description": item.description,
            }
            for item in profile.experiences
        ],
        "educations": [
            {
                "school": item.school,
                "degree": item.degree,
                "major": item.major,
                "graduationYear": item.graduation_year,
                "gpa": item.gpa,
            }
            for item in profile.educations
        ],
        "currentEmployer": experience.employer if experience else "",
        "currentTitle": experience.title if experience else "",
        "school": education.school if education else "",
        "education": education.degree if education else "",
        "graduationYear": education.graduation_year if education else "",
        "gpa": education.gpa if education else "",
        "major": education.major if education else "",
    }
