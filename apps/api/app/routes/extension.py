from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.application_sessions import ExtensionConfigResponse
from app.services.profile_service import ensure_profile_slots

router = APIRouter()


@router.get("/config", response_model=ExtensionConfigResponse)
async def get_extension_config(db: AsyncSession = Depends(get_db)) -> ExtensionConfigResponse:
    slots = await ensure_profile_slots(db)
    active_slot = next((slot.slot for slot in slots if slot.is_active), "profile_1")
    return ExtensionConfigResponse(
        api_base_url="http://localhost:8000",
        app_name="applybot",
        app_version="0.1.0",
        healthy=True,
        active_profile_slot=active_slot,
        dashboard_url="http://localhost:3000/profiles",
    )
