from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date

from .. import crud, models, schemas, constants
from ..dependencies import get_db
from ..auth_dependencies import get_current_active_user # General authenticated user

router = APIRouter(
    prefix="/audit-logs",
    tags=["Audit Logs"],
    responses={404: {"description": "Not found"}}
)

@router.get("/", response_model=List[schemas.AuditLog])
async def read_audit_logs_endpoint(
    skip: int = 0,
    limit: int = 100,
    actor_department_id: Optional[int] = Query(None, description="Filter by the department ID of the user who performed the action."),
    start_date: Optional[date] = Query(None, description="Filter logs from this date (inclusive)."),
    end_date: Optional[date] = Query(None, description="Filter logs up to this date (inclusive)."),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """
    Retrieve audit logs with RBAC, filtering, and pagination.
    - Admin/USB/AS: Can see all logs. Can optionally filter by actor_department_id.
    - Managers (Department/Unit/Division Heads): See logs for actors within their department hierarchy.
      If they provide actor_department_id, it must be within their allowed scope.
    """
    # The CRUD function handles RBAC and filtering logic
    try:
        audit_logs = crud.get_audit_logs_filtered(
            db=db,
            current_user=current_user,
            skip=skip,
            limit=limit,
            actor_department_id=actor_department_id,
            start_date=start_date,
            end_date=end_date
        )
        return audit_logs
    except HTTPException as e: # Catch permission errors from CRUD
        raise e
    # except Exception as e:
    #     # Log this error properly in a real application
    #     print(f"Unexpected error in read_audit_logs_endpoint: {e}")
    #     raise HTTPException(status_code=500, detail="Internal server error retrieving audit logs.")
