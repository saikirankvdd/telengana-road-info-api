from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from backend.database.connection import get_db
from backend.services.project_service import ProjectService
from backend.schemas.project import ProjectResponse

router = APIRouter(prefix="/projects", tags=["Projects"])

@router.get("", response_model=list[ProjectResponse], summary="List or search projects")
def list_projects(
    skip: int = 0,
    limit: int = 50,
    search: str | None = Query(None, description="Search term for project or road name"),
    db: Session = Depends(get_db)
):
    project_service = ProjectService(db)
    if search:
        results = project_service.search_projects(search)
        return [r["project"] for r in results]
    return project_service.list_projects(skip=skip, limit=limit)

@router.get("/{project_id}", response_model=ProjectResponse, summary="Get project details by DB ID or project code")
def get_project(project_id: str, db: Session = Depends(get_db)):
    project_service = ProjectService(db)
    # Check if project_id is numeric DB ID or string code
    project = None
    if project_id.isdigit():
        project = project_service.get_project_by_id(int(project_id))
    if not project:
        project = project_service.get_project_by_code(project_id)
        
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with ID/Code '{project_id}' not found."
        )
    return project
