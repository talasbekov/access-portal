from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime

from .. import crud, models, schemas
from ..dependencies import get_db
from ..auth_dependencies import (
    get_current_user,
    get_current_active_user,
    get_admin_user,
    get_security_officer_user,
    get_checkpoint_operator_user
)
# Assuming a similar auth dependency structure as in requests.py
# If get_current_active_user is defined in a common auth module, import from there
# For now, copying the dependency function signature for clarity, will need to ensure it's available
# from .requests import get_current_active_user_for_req_router as get_current_active_user # Reusing from requests.py for now
# Or define a common one in dependencies.py if it makes more sense

# Role codes for access control (should ideally be imported from a central config/rbac module)
ADMIN_ROLE_CODE = "admin"
CHECKPOINT_OPERATOR_ROLE_PREFIX = "checkpoint_operator_cp" # e.g., checkpoint_operator_cp1


router = APIRouter(
    prefix="/visits",
    tags=["Visit Logs"],
    responses={404: {"description": "Not found"}}
)

def check_permission(current_user: models.User):
    """
    Basic permission check: User must be an admin or a checkpoint operator.
    More granular checks (e.g., specific checkpoint operator for a specific visit log's request)
    would be handled in a dedicated RBAC module.
    """
    if not current_user.role:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User role not defined.")

    is_admin = current_user.role.code == ADMIN_ROLE_CODE
    is_checkpoint_operator = current_user.role.code and current_user.role.code.startswith(CHECKPOINT_OPERATOR_ROLE_PREFIX)

    if not (is_admin or is_checkpoint_operator):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to manage visit logs.")


@router.patch("/{visit_log_id}", response_model=schemas.VisitLog)
async def update_visit_log_checkout(
    visit_log_id: int,
    visit_log_update: schemas.VisitLogUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user) # Using the aliased import
):
    """
    Update a visit log, primarily to set the check_out_time.
    Requires admin or checkpoint operator role.
    """
    check_permission(current_user)

    db_visit_log = crud.get_visit_log(db, visit_log_id=visit_log_id)
    if not db_visit_log:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Visit log not found.")

    # Ensure that the update schema actually contains check_out_time if that's the only field
    # The CRUD function handles the logic of only updating if visit_log_update.check_out_time is not None
    updated_log = crud.update_visit_log(db=db, visit_log_id=visit_log_id, visit_log_update=visit_log_update)

    if updated_log is None: # Should not happen if db_visit_log was found, but good practice
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Failed to update visit log or log not found after update attempt.")

    return updated_log
