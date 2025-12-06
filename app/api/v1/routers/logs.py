from fastapi import APIRouter, Depends, Query
from typing import List
from app.core.database import Database, get_db
from app.models.schemas import AccessLog, CommandLog
from app.api.deps import get_current_user

router = APIRouter()

@router.get("/logs", response_model=List[CommandLog])
def get_logs(
    limit: int = Query(100, gt=0),
    db: Database = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get command logs"""
    logs = db.get_command_logs(limit)
    return logs

@router.get("/access-logs", response_model=List[AccessLog])
def get_access_logs(
    limit: int = Query(100, gt=0),
    ip: str = Query(None, description="Filter by IP address"),
    path: str = Query(None, description="Filter by path"),
    db: Database = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get access logs"""
    logs = db.get_access_logs(limit=limit, ip=ip, path=path)
    return logs

@router.post("/access-logs/cleanup")
def cleanup_logs(
    db: Database = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Cleanup old access logs"""
    db.cleanup_old_logs()
    return {"message": "Cleaned up logs older than 7 days"}
