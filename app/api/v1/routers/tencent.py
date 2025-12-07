from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from typing import List, Optional, Dict
from app.models.schemas import TencentInstanceCreate, TencentAccountInfo, TencentInstance, TencentBatchDeleteRequest, TencentSyncRequest
from app.services.tencent_cloud import TencentCloudService
from app.api.deps import get_current_user, get_tencent_service
from app.core.database import get_db, Database
import logging
import time

router = APIRouter(
    tags=["tencent"],
    responses={404: {"description": "Not found"}},
)

logger = logging.getLogger(__name__)

import paramiko
import socket

def check_ssh_connection(ip: str, port: int, username: str, password: str, timeout: int = 3) -> bool:
    """Check if SSH connection can be established"""
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(ip, port=port, username=username, password=password, timeout=timeout, banner_timeout=timeout)
        return True
    except Exception:
        return False
    finally:
        client.close()

def sync_instances_task(instance_passwords: Dict[str, str], region: str):
    """Background task to sync new instances to local DB"""
    instance_ids = list(instance_passwords.keys())
    logger.info(f"Starting background sync for instances: {instance_ids}")
    db = Database()
    service = TencentCloudService()
    
    remaining_ids = set(instance_ids)
    
    # Retry for up to 300 seconds (60 * 5s) - increased wait time for SSH
    for i in range(60):
        if not remaining_ids:
            break
            
        time.sleep(5)
        try:
            # Fetch all instances in region
            all_instances = service.describe_instances(region)
            
            # Filter relevant instances
            target_instances = [inst for inst in all_instances if inst['InstanceId'] in remaining_ids]
            
            for inst in target_instances:
                inst_id = inst['InstanceId']
                
                # Extract IP first
                ip = None
                if inst.get('PublicIpAddresses'):
                    ip = inst['PublicIpAddresses'][0]
                elif inst.get('PrivateIpAddresses'):
                    ip = inst['PrivateIpAddresses'][0]
                
                if ip: # Found IP, now try to add/sync
                    # Get password from request or DB
                    password = instance_passwords.get(inst_id)
                    
                    if not password:
                        # Try to find in existing hosts
                        existing_hosts = db.get_hosts()
                        existing_host = next((h for h in existing_hosts if h['address'] == ip), None)
                        if existing_host and existing_host.get('password'):
                            password = existing_host['password']
                            logger.info(f"Using existing password for host {ip}")

                    detected_username = 'root'
                    is_verified = False
                    
                    # Try to detect username if we have password
                    if password:
                        # 尝试常见的用户名
                        # Try common usernames
                        candidate_usernames = ['root', 'ubuntu', 'lighthouse']
                        for user in candidate_usernames:
                            if check_ssh_connection(ip, 22, user, password):
                                detected_username = user
                                is_verified = True
                                logger.info(f"Detected username for {ip}: {detected_username}")
                                break
                        
                        if not is_verified:
                             logger.debug(f"SSH not ready yet for {ip}, skipping this iteration")
                             continue # Retry in next loop iteration
                    else:
                        # No password provided, cannot verify, assume root or whatever default
                        # If we want to skip until password is provided, we should continue.
                        # But if it's an existing host without password, maybe we just proceed?
                        # Assuming if no password, we just add it as is (maybe key auth managed elsewhere?)
                        pass

                    # Prepare host data
                    host_data = {
                        'comment': inst.get('InstanceName', 'Tencent Cloud Instance'),
                        'address': ip,
                        'username': detected_username,
                        'port': 22,
                        'password': password or '',
                        'auth_method': 'password',
                        'group_name': 'tencent_cloud'
                    }

                    # Add to DB immediately
                    # Check duplicates
                    existing_hosts = db.get_hosts()
                    existing_host = next((h for h in existing_hosts if h['address'] == ip), None)
                    
                    if existing_host:
                            db.update_host(existing_host['id'], host_data)
                            logger.info(f"Updated host {ip} from sync task")
                    else:
                            db.add_host(host_data)
                            logger.info(f"Added host {ip} from sync task")
                    
                    remaining_ids.remove(inst_id)
                        
        except Exception as e:
            logger.error(f"Error in sync_instances_task iteration {i}: {e}")
            
    logger.info("Background sync task completed")

    # Process any remaining instances that couldn't be SSH verified
    if remaining_ids:
        logger.warning(f"Timeout waiting for SSH on instances: {remaining_ids}. Adding with default settings.")
        try:
            # We need to fetch details one last time or reuse
            all_instances = service.describe_instances(region)
            target_instances = [inst for inst in all_instances if inst['InstanceId'] in remaining_ids]
            
            for inst in target_instances:
                inst_id = inst['InstanceId']
                ip = None
                if inst.get('PublicIpAddresses'):
                    ip = inst['PublicIpAddresses'][0]
                elif inst.get('PrivateIpAddresses'):
                    ip = inst['PrivateIpAddresses'][0]
                
                if ip:
                    password = instance_passwords.get(inst_id, "")
                    host_data = {
                        'comment': f"{inst.get('InstanceName', 'Tencent Instance')} (Unverified)",
                        'address': ip,
                        'username': 'root', # Default fallback
                        'port': 22,
                        'password': password,
                        'auth_method': 'password',
                        'group_name': 'tencent_cloud'
                    }
                    
                    # Check duplicates
                    existing_hosts = db.get_hosts()
                    existing_host = next((h for h in existing_hosts if h['address'] == ip), None)
                    
                    if existing_host:
                         # Optional: Don't overwrite if it exists? Or overwrite?
                         # Let's overwrite to ensure it's in the group
                         db.update_host(existing_host['id'], host_data)
                    else:
                         db.add_host(host_data)
                    
                    logger.info(f"Force added unverified host {ip}")
                    
        except Exception as e:
             logger.error(f"Error adding remaining instances: {e}")

@router.get("/account", response_model=TencentAccountInfo)
def get_account_info(
    service: TencentCloudService = Depends(get_tencent_service),
    current_user: dict = Depends(get_current_user)
):
    """Get Tencent Cloud account balance"""
    try:
        return service.get_account_balance()
    except Exception as e:
        error_msg = str(e)
        if "Tencent Cloud credentials not configured" in error_msg:
            raise HTTPException(status_code=400, detail="Please configure Tencent Cloud Access Key and Secret Key in System Config first.")
        raise HTTPException(status_code=500, detail=error_msg)

@router.get("/regions")
def get_regions(
    service: TencentCloudService = Depends(get_tencent_service),
    current_user: dict = Depends(get_current_user)
):
    """Get available regions"""
    try:
        return service.describe_regions()
    except Exception as e:
        error_msg = str(e)
        if "Tencent Cloud credentials not configured" in error_msg:
            raise HTTPException(status_code=400, detail="Please configure Tencent Cloud Access Key and Secret Key in System Config first.")
        raise HTTPException(status_code=500, detail=error_msg)

@router.get("/zones")
def get_zones(
    region: str,
    service: TencentCloudService = Depends(get_tencent_service),
    current_user: dict = Depends(get_current_user)
):
    """Get available zones"""
    try:
        return service.describe_zones(region)
    except Exception as e:
        error_msg = str(e)
        if "Tencent Cloud credentials not configured" in error_msg:
            raise HTTPException(status_code=400, detail="Please configure Tencent Cloud Access Key and Secret Key in System Config first.")
        raise HTTPException(status_code=500, detail=error_msg)

@router.get("/images")
def get_images(
    region: str,
    architecture: str = "x86_64",
    os_name: str = "CentOS",
    service: TencentCloudService = Depends(get_tencent_service),
    current_user: dict = Depends(get_current_user)
):
    """Get available images"""
    try:
        return service.describe_images(architecture, os_name, region)
    except Exception as e:
        error_msg = str(e)
        if "Tencent Cloud credentials not configured" in error_msg:
            raise HTTPException(status_code=400, detail="Please configure Tencent Cloud Access Key and Secret Key in System Config first.")
        raise HTTPException(status_code=500, detail=error_msg)

@router.get("/instance-types")
def get_instance_types(
    zone: str,
    region: str,
    service: TencentCloudService = Depends(get_tencent_service),
    current_user: dict = Depends(get_current_user)
):
    """Get available instance types for a zone"""
    try:
        return service.describe_instance_types(zone, region)
    except Exception as e:
        error_msg = str(e)
        if "Tencent Cloud credentials not configured" in error_msg:
            raise HTTPException(status_code=400, detail="Please configure Tencent Cloud Access Key and Secret Key in System Config first.")
        raise HTTPException(status_code=500, detail=error_msg)

@router.get("/instances", response_model=List[TencentInstance])
def get_instances(
    region: str,
    service: TencentCloudService = Depends(get_tencent_service),
    current_user: dict = Depends(get_current_user)
):
    """List Tencent Cloud instances"""
    try:
        return service.describe_instances(region)
    except Exception as e:
        error_msg = str(e)
        if "Tencent Cloud credentials not configured" in error_msg:
            raise HTTPException(status_code=400, detail="Please configure Tencent Cloud Access Key and Secret Key in System Config first.")
        raise HTTPException(status_code=500, detail=error_msg)

@router.post("/instances", status_code=status.HTTP_201_CREATED)
def create_instance(
    instance_data: TencentInstanceCreate,
    background_tasks: BackgroundTasks,
    service: TencentCloudService = Depends(get_tencent_service),
    db: Database = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Create a new Tencent Cloud Instance
    
    - **instance_data**: Instance creation parameters
    - **service**: Tencent Cloud service dependency
    - **current_user**: Current authenticated user
    
    Returns the created instance information.
    """
    try:
        logger.info(f"User {current_user.get('username')} initiating instance creation")
        result = service.create_instance(instance_data.dict())
        logger.info(f"Instance created successfully by {current_user.get('username')}")
        
        # Sync to local DB in background
        try:
            instance_id_set = result.get('InstanceIdSet') # Use .get() for dict
            if instance_id_set:
                passwords = {inst_id: instance_data.Password for inst_id in instance_id_set}
                background_tasks.add_task(
                    sync_instances_task, 
                    passwords, 
                    instance_data.Region
                )
        except Exception as e:
            logger.error(f"Failed to schedule background sync task: {e}")
            
        return result
    except ValueError as e:
        logger.warning(f"Validation error creating instance: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating instance: {str(e)}", exc_info=True)
        error_msg = str(e)
        if "Tencent Cloud credentials not configured" in error_msg:
            raise HTTPException(status_code=400, detail="Please configure Tencent Cloud Access Key and Secret Key in System Config first.")
        if "Tencent Cloud SDK Error" in error_msg:
             raise HTTPException(status_code=400, detail=error_msg)
        raise HTTPException(status_code=500, detail=f"Failed to create instance: {error_msg}")

@router.post("/instances/batch-delete")
def batch_delete_instances(
    data: TencentBatchDeleteRequest,
    service: TencentCloudService = Depends(get_tencent_service),
    current_user: dict = Depends(get_current_user)
):
    """Batch delete instances"""
    try:
        return service.terminate_instances(data.InstanceIds, data.Region)
    except Exception as e:
        error_msg = str(e)
        if "Tencent Cloud credentials not configured" in error_msg:
            raise HTTPException(status_code=400, detail="Please configure Tencent Cloud Access Key and Secret Key in System Config first.")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/instances/{instance_id}")
def delete_instance(
    instance_id: str,
    region: str = Query(..., description="Region"),
    service: TencentCloudService = Depends(get_tencent_service),
    current_user: dict = Depends(get_current_user)
):
    """Delete single instance"""
    try:
        return service.terminate_instances([instance_id], region)
    except Exception as e:
        error_msg = str(e)
        if "Tencent Cloud credentials not configured" in error_msg:
            raise HTTPException(status_code=400, detail="Please configure Tencent Cloud Access Key and Secret Key in System Config first.")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/sync")
def sync_instances(
    request: TencentSyncRequest,
    background_tasks: BackgroundTasks,
    service: TencentCloudService = Depends(get_tencent_service),
    db: Database = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Sync instances from Tencent Cloud to local inventory
    """
    try:
        # Pass passwords map to background task
        passwords = {item.InstanceId: item.Password for item in request.Instances}
        background_tasks.add_task(sync_instances_task, passwords, request.Region)
        return {"message": "Sync task started in background"}
    except Exception as e:
        error_msg = str(e)
        if "Tencent Cloud credentials not configured" in error_msg:
            raise HTTPException(status_code=400, detail="Please configure Tencent Cloud Access Key and Secret Key in System Config first.")
        raise HTTPException(status_code=500, detail=str(e))
