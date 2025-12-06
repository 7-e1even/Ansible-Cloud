from fastapi import APIRouter, Depends, HTTPException
from typing import List, Dict, Any
import json

from app.services.workflow import WorkflowService, get_workflow_service
from app.services.tencent_cloud import TencentCloudService
from app.core.database import Database, get_db
from app.models.schemas import (
    WorkflowCreateRequest, 
    WorkflowBatchCreateRequest,
    WorkflowResponse, 
    WorkflowLogResponse,
    WorkflowLogSummary,
    ExtractTemplateRequest,
    TemplateResponse
)

router = APIRouter()

@router.post("/batch-create", response_model=Dict[str, Any])
async def batch_create_workflow(
    request: WorkflowBatchCreateRequest,
    workflow_service: WorkflowService = Depends(get_workflow_service),
    db: Database = Depends(get_db)
):
    """Batch create and start workflows"""
    # Fetch template
    template = db.get_template(request.template_id, type='workflow')
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    try:
        template_content = json.loads(template['content'])
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid template content JSON")

    if request.ansible_template_id:
        ansible_template = db.get_template(request.ansible_template_id, type='ansible')
        if not ansible_template:
             raise HTTPException(status_code=404, detail="Ansible Template not found")
        template_content['PlaybookContent'] = ansible_template['content']

    created_ids = []
    for idx, instance_params in enumerate(request.instances):
        # Generate a name if not provided or just use template name + index
        name = instance_params.get('name', f"{template['name']} - Instance {idx+1}")
        description = instance_params.get('description', f"Batch execution from template {template['name']}")
        
        workflow_id = workflow_service.create_workflow(
            name=name,
            description=description,
            template_content=template_content,
            params=instance_params
        )
        
        workflow_service.start_workflow(workflow_id)
        created_ids.append(workflow_id)
    
    return {"success": True, "workflow_ids": created_ids, "message": f"Started {len(created_ids)} workflows"}

@router.post("/create", response_model=Dict[str, Any])
async def create_workflow(
    request: WorkflowCreateRequest,
    workflow_service: WorkflowService = Depends(get_workflow_service),
    db: Database = Depends(get_db)
):
    """Create and start a new workflow"""
    # Fetch template
    template = db.get_template(request.template_id, type='workflow')
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    try:
        template_content = json.loads(template['content'])
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid template content JSON")

    if request.ansible_template_id:
        ansible_template = db.get_template(request.ansible_template_id, type='ansible')
        if not ansible_template:
             raise HTTPException(status_code=404, detail="Ansible Template not found")
        template_content['PlaybookContent'] = ansible_template['content']

    workflow_id = workflow_service.create_workflow(
        name=request.name,
        description=request.description,
        template_content=template_content,
        params=request.params
    )
    
    workflow_service.start_workflow(workflow_id)
    
    return {"success": True, "workflow_id": workflow_id, "message": "Workflow started"}

@router.get("", response_model=List[WorkflowResponse])
async def list_workflows(
    limit: int = 100,
    db: Database = Depends(get_db)
):
    """List workflows"""
    return db.get_workflows(limit=limit)

@router.get("/{workflow_id}", response_model=WorkflowResponse)
async def get_workflow(
    workflow_id: int,
    db: Database = Depends(get_db)
):
    """Get workflow details"""
    workflow = db.get_workflow(workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return workflow

@router.get("/{workflow_id}/logs", response_model=List[WorkflowLogSummary])
async def get_workflow_logs(
    workflow_id: int,
    db: Database = Depends(get_db)
):
    """Get workflow logs summary (without large details)"""
    return db.get_workflow_logs(workflow_id)

@router.get("/logs/{log_id}", response_model=WorkflowLogResponse)
async def get_workflow_log_detail(
    log_id: int,
    db: Database = Depends(get_db)
):
    """Get single workflow log with full details"""
    log = db.get_workflow_log_detail(log_id)
    if not log:
        raise HTTPException(status_code=404, detail="Log not found")
    return log

@router.post("/template-from-instance", response_model=Dict[str, Any])
async def create_template_from_instance(
    request: ExtractTemplateRequest,
    db: Database = Depends(get_db)
):
    """Extract template from existing instance"""
    tencent = TencentCloudService()
    try:
        template_data = tencent.extract_template_from_instance(request.instance_id, request.region)
        
        # Save as a new template
        name = f"Template from {request.instance_id}"
        description = f"Extracted from instance {request.instance_id} in {request.region}"
        
        new_template = {
            "name": name,
            "description": description,
            "content": json.dumps(template_data, indent=2),
            "type": "workflow"
        }
        
        template_id = db.add_template(new_template)
        return {"success": True, "template_id": template_id, "data": new_template}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
