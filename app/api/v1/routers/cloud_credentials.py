from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional
from app.models.schemas import (
    CloudCredentialCreate, 
    CloudCredentialUpdate, 
    CloudCredentialResponse, 
    CloudCredentialTestRequest
)
from app.core.database import get_db, Database
from app.api.deps import get_current_user
from app.services.tencent_cloud import TencentCloudService
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/cloud-credentials", response_model=CloudCredentialResponse)
def create_cloud_credential(
    cred: CloudCredentialCreate,
    db: Database = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    try:
        cred_id = db.add_cloud_credential(cred.dict())
        new_cred = db.get_cloud_credential(cred_id)
        if not new_cred:
             raise HTTPException(status_code=500, detail="Failed to create credential")
        return new_cred
    except Exception as e:
        logger.error(f"Error creating cloud credential: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/cloud-credentials", response_model=List[CloudCredentialResponse])
def get_cloud_credentials(
    provider: Optional[str] = None,
    db: Database = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    return db.get_cloud_credentials(provider)

@router.put("/cloud-credentials/{cred_id}", response_model=CloudCredentialResponse)
def update_cloud_credential(
    cred_id: int,
    cred: CloudCredentialUpdate,
    db: Database = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    existing = db.get_cloud_credential(cred_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Credential not found")
    
    try:
        db.update_cloud_credential(cred_id, cred.dict(exclude_unset=True))
        updated = db.get_cloud_credential(cred_id)
        return updated
    except Exception as e:
        logger.error(f"Error updating cloud credential: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/cloud-credentials/{cred_id}")
def delete_cloud_credential(
    cred_id: int,
    db: Database = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    existing = db.get_cloud_credential(cred_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Credential not found")
    
    db.delete_cloud_credential(cred_id)
    return {"success": True}

@router.post("/cloud-credentials/test")
def test_cloud_credential(
    req: CloudCredentialTestRequest,
    current_user: dict = Depends(get_current_user)
):
    if req.provider == 'tencent':
        try:
            service = TencentCloudService(secret_id=req.access_key, secret_key=req.secret_key)
            # Try a lightweight call, e.g., get regions or balance
            # describe_regions is good
            regions = service.describe_regions()
            if regions:
                return {"success": True, "message": "Connection successful"}
            else:
                return {"success": False, "message": "Connection failed: No regions found"}
        except Exception as e:
            return {"success": False, "message": f"Connection failed: {str(e)}"}
    else:
        return {"success": False, "message": f"Provider {req.provider} not supported for testing yet"}
