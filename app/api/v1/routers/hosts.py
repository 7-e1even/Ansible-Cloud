from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from app.core.database import Database, get_db
from app.models.schemas import HostCreate, HostUpdate, HostResponse
from app.api.deps import get_current_user

router = APIRouter()

@router.get("", response_model=List[HostResponse])
def get_hosts(
    group_name: str = None,
    db: Database = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get all hosts"""
    hosts = db.get_hosts(group_name=group_name)
    # Transformation handled by Pydantic model
    return hosts

@router.get("/groups", response_model=List[str])
def get_groups(
    db: Database = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get all host groups"""
    return db.get_groups()

@router.get("/{host_id}", response_model=HostResponse)
def get_host(
    host_id: int,
    db: Database = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get single host"""
    host = db.get_host(host_id)
    if not host:
        raise HTTPException(status_code=404, detail="Host not found")
    return host

import base64
import binascii

def try_decode_base64(s: str) -> str:
    """Try to decode base64 string, return original if failed"""
    if not s:
        return s
    try:
        # Check if it looks like base64
        # A valid base64 string should be a multiple of 4 length-wise (with padding), 
        # and only contain valid characters.
        # But user input might not be padded or might just happen to be valid base64.
        # The requirement implies we should try to decode.
        
        # We need to be careful not to decode normal passwords that happen to be valid base64.
        # But if the user says "Authentication still using base64 format", it implies they provided base64 
        # hoping it would be decoded.
        
        # Let's assume if it decodes to UTF-8 without error, we use the decoded value.
        # To be safer, maybe only if it has no spaces?
        
        decoded = base64.b64decode(s, validate=True).decode('utf-8')
        return decoded
    except (binascii.Error, UnicodeDecodeError):
        return s

@router.post("", status_code=status.HTTP_201_CREATED)
def add_host(
    host_data: HostCreate,
    db: Database = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Add single host"""
    # Manual validation if needed, but Pydantic handles required fields
    if host_data.auth_method == 'password' and not host_data.password:
         raise HTTPException(status_code=400, detail="Password is required for password authentication")
    
    # Try decode password if it is base64
    if host_data.password:
        host_data.password = try_decode_base64(host_data.password)

    host_id = db.add_host(host_data.dict())
    return {"message": "Host added successfully", "host_id": host_id}

@router.post("/batch")
def add_hosts_batch(
    hosts_data: List[HostCreate],
    db: Database = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Batch add hosts"""
    # Fetch existing hosts to check for duplicates
    existing_hosts = db.get_hosts()
    existing_ips = {h['address'] for h in existing_hosts}

    new_hosts_data = []
    for host in hosts_data:
        # Deduplicate based on IP
        if host.address in existing_ips:
            continue

        if host.auth_method == 'password' and not host.password:
            raise HTTPException(status_code=400, detail=f"Password required for host {host.address}")
        
        # Try decode password
        if host.password:
            host.password = try_decode_base64(host.password)
        
        new_hosts_data.append(host)

    if not new_hosts_data:
        return {"message": "No new hosts to add (all duplicates)", "count": 0}
            
    count = db.add_hosts_batch([h.dict() for h in new_hosts_data])
    return {"message": f"Successfully added {count} hosts", "count": count}

from app.services.ansible import AnsibleService, get_ansible_service

@router.post("/check-status")
def check_all_hosts_status(
    ansible: AnsibleService = Depends(get_ansible_service),
    db: Database = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Check status for all hosts"""
    try:
        results = ansible.check_host_connectivity()
        return {"message": "Status check completed", "results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{host_id}/check-status")
def check_host_status(
    host_id: int,
    ansible: AnsibleService = Depends(get_ansible_service),
    db: Database = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Check status for single host"""
    host = db.get_host(host_id)
    if not host:
        raise HTTPException(status_code=404, detail="Host not found")
        
    try:
        results = ansible.check_host_connectivity([host])
        return {"message": "Status check completed", "status": results.get(host_id, 'unknown')}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{host_id}")
def update_host(
    host_id: int,
    host_data: HostUpdate,
    db: Database = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Update host"""
    existing_host = db.get_host(host_id)
    if not existing_host:
        raise HTTPException(status_code=404, detail="Host not found")
        
    # Handle password update logic
    data_dict = host_data.dict(exclude_unset=True) # Only include sent fields
    
    if host_data.auth_method == 'password':
        if 'password' in data_dict and data_dict['password']:
             # New password provided, it will be encrypted in db.update_host
             pass
        elif 'password' not in data_dict or not data_dict['password']:
             # No new password provided, keep old one
             # We need to make sure we don't overwrite it with None/Empty
             # db.update_host expects the password field to be present if we want to update it
             # OR we can fetch the old one and pass it back?
             # Actually, db.update_host handles encryption. 
             # If we pass None/Empty string, it might be an issue depending on implementation.
             
             # Let's use the existing encrypted password from DB? 
             # db.update_host encrypts whatever is passed.
             # If we pass the decrypted old password, it will be re-encrypted (correct).
             # existing_host['password'] is decrypted by get_host()
             if existing_host['password']:
                data_dict['password'] = existing_host['password']
    
    # Merge with existing data to ensure all fields are present for the SQL query
    # (Since db.update_host uses fixed SQL with all fields)
    # We need to construct a full dict for db.update_host
    full_update_data = existing_host.copy()
    full_update_data.update(data_dict)
    
    # We need to be careful: existing_host keys might differ from what update_host expects?
    # db.get_host returns dict with keys matching columns.
    # db.update_host expects dict with keys: comment, address, username, port, password, auth_method
    
    db.update_host(host_id, full_update_data)
    return {"message": "Host updated successfully"}

@router.delete("/{host_id}")
def delete_host(
    host_id: int,
    db: Database = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Delete host"""
    if not db.get_host(host_id):
        raise HTTPException(status_code=404, detail="Host not found")
    db.delete_host(host_id)
    return {"message": "Host deleted successfully"}
