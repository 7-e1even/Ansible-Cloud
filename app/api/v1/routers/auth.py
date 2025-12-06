from fastapi import APIRouter, Response, HTTPException, status, Depends
from typing import Dict, Any, List
from app.models.schemas import LoginRequest, TokenResponse, CurrentUser
from app.services.auth import auth_service
from app.core.config import settings
from app.core.database import Database, get_db
from app.api.deps import get_current_user
import time
import hmac
import hashlib

router = APIRouter()

@router.post("/login", response_model=TokenResponse)
def login(data: LoginRequest, response: Response):
    if auth_service.authenticate_user(data.username, data.password):
        token = auth_service.create_token('admin')
        
        # Set cookie as in original app
        response.set_cookie(
            key="token",
            value=token,
            max_age=settings.JWT_EXPIRATION_SECONDS,
            httponly=True,
            samesite="lax"
        )
        
        return {
            "success": True, 
            "message": "Login successful", 
            "token": token,
            "redirect_url": "/"  # Explicitly returning redirect URL
        }
    
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Incorrect username or password"
    )

@router.post("/login/outLogin")
def logout(response: Response):
    """Logout user"""
    response.delete_cookie("token")
    return {"success": True, "data": {}, "message": "Logout successful"}

@router.get("/currentUser")
def get_current_user_info(current_user: dict = Depends(get_current_user)):
    """Get current user info for Ant Design Pro"""
    return {
        "data": CurrentUser(
            name="Admin",
            userid="admin",
            email="admin@example.com",
            access="admin",
        )
    }

@router.get("/ws-token/{host_id}")
def get_ws_token(
    host_id: int,
    db: Database = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get WebSocket token"""
    host = db.get_host(host_id)
    if not host:
        raise HTTPException(status_code=404, detail="Host not found")

    timestamp = int(time.time())
    message = f"{host_id}:{timestamp}"
    
    signature = hmac.new(
        settings.SECRET_KEY.encode(),
        message.encode(),
        hashlib.sha256
    ).hexdigest()
    
    token = f"{host_id}:{timestamp}:{signature}"
    return {"token": token}

@router.get("/notices")
def get_notices(current_user: dict = Depends(get_current_user)):
    """Get notices (mock)"""
    return {
        "data": [],
        "total": 0,
        "success": True
    }
