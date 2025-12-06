from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional
from app.core.database import Database, get_db
from app.models.schemas import TemplateCreate, TemplateUpdate, TemplateResponse
from app.api.deps import get_current_user

router = APIRouter()

@router.get("", response_model=List[TemplateResponse])
def get_templates(
    type: Optional[str] = None,
    db: Database = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get all templates"""
    return db.get_templates(type=type)

@router.get("/{template_id}", response_model=TemplateResponse)
def get_template(
    template_id: int,
    type: str = "ansible",
    db: Database = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get single template"""
    template = db.get_template(template_id, type=type)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return template

@router.post("", status_code=status.HTTP_201_CREATED)
def add_template(
    template_data: TemplateCreate,
    db: Database = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Add new template"""
    template_id = db.add_template(template_data.dict())
    return {"message": "Template added successfully", "template_id": template_id}

@router.put("/{template_id}")
def update_template(
    template_id: int,
    template_data: TemplateUpdate,
    db: Database = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Update template"""
    # We need type to know which table to check
    type = template_data.type if template_data.type else "ansible"
    existing = db.get_template(template_id, type=type)
    if not existing:
        raise HTTPException(status_code=404, detail="Template not found")
    
    db.update_template(template_id, template_data.dict())
    return {"message": "Template updated successfully"}

@router.delete("/{template_id}")
def delete_template(
    template_id: int,
    type: str = "ansible",
    db: Database = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Delete template"""
    existing = db.get_template(template_id, type=type)
    if not existing:
        raise HTTPException(status_code=404, detail="Template not found")
    
    db.delete_template(template_id, type=type)
    return {"message": "Template deleted successfully"}
