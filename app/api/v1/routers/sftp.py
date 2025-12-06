from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from typing import List
from app.api.deps import get_current_user, get_sftp_service
from app.services.sftp import SFTPService
from app.models.schemas import SFTPMkdirRequest, SFTPRenameRequest, SFTPTouchRequest, SFTPWriteRequest, SFTPDeleteRequest
from fastapi.responses import FileResponse

router = APIRouter()

@router.get("/{host_id}/list")
def sftp_list(
    host_id: int,
    path: str = "/",
    sftp: SFTPService = Depends(get_sftp_service),
    current_user: dict = Depends(get_current_user)
):
    try:
        return sftp.list_files(host_id, path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{host_id}/mkdir")
def sftp_mkdir(
    host_id: int,
    data: SFTPMkdirRequest,
    sftp: SFTPService = Depends(get_sftp_service),
    current_user: dict = Depends(get_current_user)
):
    try:
        sftp.mkdir(host_id, data.path)
        return {"success": True}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{host_id}/upload")
def sftp_upload(
    host_id: int,
    path: str = Form("/"),
    files: List[UploadFile] = File(...),
    sftp: SFTPService = Depends(get_sftp_service),
    current_user: dict = Depends(get_current_user)
):
    try:
        sftp.upload(host_id, path, files)
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{host_id}/rename")
def sftp_rename(
    host_id: int,
    data: SFTPRenameRequest,
    sftp: SFTPService = Depends(get_sftp_service),
    current_user: dict = Depends(get_current_user)
):
    try:
        sftp.rename(host_id, data.old_path, data.new_path)
        return {"success": True}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{host_id}/touch")
def sftp_touch(
    host_id: int,
    data: SFTPTouchRequest,
    sftp: SFTPService = Depends(get_sftp_service),
    current_user: dict = Depends(get_current_user)
):
    try:
        sftp.touch(host_id, data.path)
        return {"success": True}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{host_id}/read")
def sftp_read(
    host_id: int,
    path: str,
    sftp: SFTPService = Depends(get_sftp_service),
    current_user: dict = Depends(get_current_user)
):
    try:
        content = sftp.read_file(host_id, path)
        return {"content": content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{host_id}/write")
def sftp_write(
    host_id: int,
    data: SFTPWriteRequest,
    sftp: SFTPService = Depends(get_sftp_service),
    current_user: dict = Depends(get_current_user)
):
    try:
        sftp.write_file(host_id, data.path, data.content)
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{host_id}/delete")
def sftp_delete(
    host_id: int,
    data: SFTPDeleteRequest,
    sftp: SFTPService = Depends(get_sftp_service),
    current_user: dict = Depends(get_current_user)
):
    try:
        sftp.delete(host_id, data.path, data.is_directory)
        return {"success": True}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{host_id}/download")
def sftp_download(
    host_id: int,
    path: str,
    sftp: SFTPService = Depends(get_sftp_service),
    current_user: dict = Depends(get_current_user)
):
    try:
        temp_path = sftp.download(host_id, path)
        # Background task to cleanup? FastAPI handles this with background tasks usually, 
        # but FileResponse with temp file needs care. 
        # For simplicity, we return FileResponse and hope OS cleans tmp or we add a background task to delete it.
        
        import os
        from starlette.background import BackgroundTask
        
        def cleanup():
            if os.path.exists(temp_path):
                os.remove(temp_path)

        return FileResponse(
            temp_path, 
            filename=os.path.basename(path),
            background=BackgroundTask(cleanup)
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
