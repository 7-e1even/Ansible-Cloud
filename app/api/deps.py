from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from typing import Optional
from app.services.auth import auth_service
from app.core.database import get_db, Database
from app.core.config import settings
from app.services.ansible import AnsibleService
from app.services.sftp import SFTPService
from app.services.tencent_cloud import TencentCloudService

# OAuth2PasswordBearer is standard, but we also want to support Cookies
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/login", auto_error=False)

def get_current_user(
    request: Request,
    token: Optional[str] = Depends(oauth2_scheme),
):
    # Check if login is enabled (hot reload)
    if not settings.is_login_enabled():
        # Return a mock user payload if login is disabled
        return {
            "user_id": "admin",
            "sub": "admin",
            "scope": "admin"
        }

    # Try to get token from Header (Bearer) first
    if not token:
        # Try to get token from Cookie
        token = request.cookies.get("token")
    
    if not token:
         raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    payload = auth_service.decode_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return payload

def get_ansible_service(db: Database = Depends(get_db)) -> AnsibleService:
    return AnsibleService(db)

def get_sftp_service(db: Database = Depends(get_db)) -> SFTPService:
    return SFTPService(db)

def get_tencent_service() -> TencentCloudService:
    return TencentCloudService()