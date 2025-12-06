from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Union, Dict, Any
import json
from app.api.deps import get_current_user, get_ansible_service
from app.services.ansible import AnsibleService
from app.core.database import Database, get_db
from app.models.schemas import ExecuteRequest

router = APIRouter()

@router.post("/execute")
def execute_command(
    req: ExecuteRequest,
    ansible: AnsibleService = Depends(get_ansible_service),
    db: Database = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Execute shell command on hosts"""
    if req.hosts == 'all':
        target_hosts = db.get_hosts()
    else:
        target_hosts = []
        for host_id in req.hosts:
            host = db.get_host(host_id)
            if host:
                target_hosts.append(host)
            else:
                raise HTTPException(status_code=404, detail=f"Host not found: {host_id}")

    if not target_hosts:
        raise HTTPException(status_code=400, detail="No valid target hosts")

    results = ansible.execute_command(req.command, target_hosts)
    return results

@router.get("/hosts/{host_id}/facts")
def get_host_facts(
    host_id: int,
    ansible: AnsibleService = Depends(get_ansible_service),
    current_user: dict = Depends(get_current_user)
):
    """Get host facts"""
    facts = ansible.get_host_facts(host_id)
    if facts:
        return facts
    raise HTTPException(status_code=404, detail="Failed to get host facts")

@router.get("/hosts/{host_id}/ping")
def ping_host(
    host_id: int,
    db: Database = Depends(get_db),
    ansible: AnsibleService = Depends(get_ansible_service),
    current_user: dict = Depends(get_current_user)
):
    """Ping host"""
    host = db.get_host(host_id)
    if not host:
        raise HTTPException(status_code=404, detail="Host not found")
    
    results = ansible.execute_ping([host])
    
    host_address = host['address']
    if host_address in results['success']:
        return {'status': 'success', 'message': 'Connection successful'}
    elif host_address in results['unreachable']:
        return {'status': 'unreachable', 'message': 'Unreachable'}
    else:
        return {'status': 'failed', 'message': 'Failed'}

@router.post("/playbook/execute")
def execute_playbook(
    data: Dict[str, Any],
    ansible: AnsibleService = Depends(get_ansible_service),
    db: Database = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Execute custom Ansible Playbook"""
    playbook_content = data.get('playbook')
    host_ids = data.get('host_ids', [])
    timeout = data.get('timeout')
    
    if not playbook_content:
        raise HTTPException(status_code=400, detail="Playbook content required")
        
    target_hosts = None
    if host_ids:
        target_hosts = [db.get_host(host_id) for host_id in host_ids]
        target_hosts = [h for h in target_hosts if h]
        
    try:
        result = ansible.execute_custom_playbook(playbook_content, target_hosts, timeout=timeout)
        
        # Log results
        if target_hosts:
            for host in target_hosts:
                host_status = 'success'
                if host['address'] in result['summary']['failed']:
                    host_status = 'failed'
                elif host['address'] in result['summary']['unreachable']:
                    host_status = 'unreachable'
                
                db.log_command(
                    host['id'],
                    'Custom Playbook Execution',
                    json.dumps({'playbook_logs': result['logs']}),
                    host_status
                )
        else:
            db.log_command(
                None,
                'Custom Playbook Execution',
                json.dumps({'playbook_logs': result['logs']}),
                'success' if result['success'] else 'failed'
            )
            
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Playbook execution failed: {str(e)}")

@router.post("/tasks/execute")
def start_playbook_task(
    data: Dict[str, Any],
    ansible: AnsibleService = Depends(get_ansible_service),
    db: Database = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Start async playbook execution task"""
    playbook_content = data.get('playbook')
    host_ids = data.get('host_ids', [])
    group_name = data.get('group_name') # Support group selection
    timeout = data.get('timeout')
    
    if not playbook_content:
        raise HTTPException(status_code=400, detail="Playbook content required")
        
    target_hosts = []
    target_host_ids = []
    
    if group_name:
        target_hosts = db.get_hosts(group_name)
    elif host_ids:
        # Check if host_ids is 'all'
        if host_ids == 'all':
            target_hosts = db.get_hosts()
        else:
            for host_id in host_ids:
                host = db.get_host(host_id)
                if host:
                    target_hosts.append(host)
    
    if not target_hosts:
        raise HTTPException(status_code=400, detail="No target hosts found")
        
    target_host_ids = [h['id'] for h in target_hosts]
    
    # Create task
    task_id = db.add_task({
        'type': 'playbook',
        'name': data.get('name', 'Playbook Execution'),
        'status': 'pending',
        'target_hosts': json.dumps(target_host_ids),
        'params': json.dumps({'playbook': playbook_content, 'timeout': timeout}),
        'logs': json.dumps([])
    })
    
    # Start execution
    ansible.execute_playbook_async(task_id, playbook_content, target_hosts, timeout=timeout)
    
    return {"task_id": task_id, "message": "Task started"}

@router.get("/tasks")
def get_tasks(
    limit: int = 100,
    db: Database = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get recent tasks"""
    tasks = db.get_tasks(limit)
    # Parse JSON fields
    for task in tasks:
        if task.get('target_hosts'):
            try:
                task['target_hosts'] = json.loads(task['target_hosts'])
            except:
                pass
        if task.get('result'):
            try:
                task['result'] = json.loads(task['result'])
            except:
                pass
    return tasks

@router.get("/tasks/{task_id}")
def get_task(
    task_id: int,
    db: Database = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get task details"""
    task = db.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
        
    # Parse JSON fields
    if task.get('target_hosts'):
        try:
            task['target_hosts'] = json.loads(task['target_hosts'])
        except:
            pass
    if task.get('result'):
        try:
            task['result'] = json.loads(task['result'])
        except:
            pass
    if task.get('logs'):
        try:
            task['logs'] = json.loads(task['logs'])
        except:
            pass
            
    return task
