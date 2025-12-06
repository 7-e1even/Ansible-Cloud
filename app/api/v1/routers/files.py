from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from typing import List, Optional, Dict, Any
import json
import os
from werkzeug.utils import secure_filename
from app.api.deps import get_current_user, get_ansible_service
from app.services.ansible import AnsibleService
from app.core.database import Database, get_db
from app.core.config import settings

router = APIRouter()

@router.post("/upload")
def api_upload(
    file: UploadFile = File(...),
    remote_path: str = Form('/tmp/'),
    hosts: str = Form('all'), # 'all' or json list of IDs
    ansible: AnsibleService = Depends(get_ansible_service),
    db: Database = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Generic file upload to hosts"""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file selected")
        
    filename = secure_filename(file.filename)
    file_path = os.path.join(settings.UPLOAD_FOLDER, filename)
    
    try:
        # Save uploaded file locally first
        with open(file_path, "wb") as buffer:
            buffer.write(file.file.read())
            
        remote_file_path = os.path.join(remote_path, filename).replace('\\', '/')
        
        # Determine target hosts
        target_host_ids = []
        if hosts != 'all':
            try:
                target_host_ids = json.loads(hosts)
                if not target_host_ids:
                    raise HTTPException(status_code=400, detail="No hosts selected")
            except json.JSONDecodeError:
                raise HTTPException(status_code=400, detail="Invalid hosts format")
                
            # Verify hosts exist
            # (Logic is handled inside copy_file_to_hosts partially, but let's pass IDs)
            result = ansible.copy_file_to_hosts(file_path, remote_file_path, target_host_ids)
            
            # Calculate host_ids list for response
            host_ids = [str(h) for h in target_host_ids]
            all_hosts = db.get_hosts()
            host_map = {str(h['id']): h for h in all_hosts}
            
        else:
            result = ansible.copy_file_to_all(file_path, remote_file_path)
            all_hosts = db.get_hosts()
            host_map = {str(h['id']): h for h in all_hosts}
            host_ids = list(host_map.keys())

        # Process results (similar to original app)
        successful_hosts = []
        failed_hosts = {}

        for host_addr, res in result.get('success', {}).items():
            host_id = next((id for id, h in host_map.items() if h['address'] == host_addr), None)
            if host_id:
                successful_hosts.append(host_id)

        for host_addr, res in result.get('failed', {}).items():
            host_id = next((id for id, h in host_map.items() if h['address'] == host_addr), None)
            if host_id:
                failed_hosts[host_id] = res.get('msg', 'Unknown error')
        
        for host_addr, res in result.get('unreachable', {}).items():
            host_id = next((id for id, h in host_map.items() if h['address'] == host_addr), None)
            if host_id:
                failed_hosts[host_id] = 'Host unreachable'

        total = len(host_ids) if hosts == 'all' else len(target_host_ids)
        succeeded = len(successful_hosts)

        response_data = {
            'success': succeeded > 0,
            'message': 'File upload complete' if succeeded == total else 'File upload partial/failed',
            'details': {
                'succeeded': successful_hosts,
                'failed': failed_hosts
            }
        }
        
        if succeeded == total:
            return response_data
        elif succeeded > 0:
             # 207 Multi-Status not directly supported by FastAPI return typing, but we can return JSONResponse
             from fastapi.responses import JSONResponse
             return JSONResponse(content=response_data, status_code=207)
        else:
             from fastapi.responses import JSONResponse
             return JSONResponse(content=response_data, status_code=500)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)
