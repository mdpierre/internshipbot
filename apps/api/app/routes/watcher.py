from fastapi import APIRouter

from app.schemas.jobs import ApiResponse, WatcherConfig, WatcherStatus
from app.services import watcher

router = APIRouter()


@router.get("/status", response_model=ApiResponse[WatcherStatus])
async def get_status() -> dict:
    return {"data": watcher.get_status()}


@router.put("/config", response_model=ApiResponse[WatcherStatus])
async def put_config(body: WatcherConfig) -> dict:
    return {"data": watcher.configure(body.path)}


@router.post("/sync", response_model=ApiResponse[WatcherStatus])
async def sync_now() -> dict:
    return {"data": watcher.sync_now()}
