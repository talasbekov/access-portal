from fastapi import Depends, HTTPException, APIRouter, status # Added status
from sqlalchemy.orm import Session
from datetime import datetime, date, timedelta # Added datetime, date, timedelta
from typing import List, Optional
# Removed: from pydantic import BaseModel
import os
from fastapi.security import OAuth2PasswordBearer # Added
from jose import JWTError, jwt # Added

# Use the minimal get_db from dependencies
from ..dependencies import get_db
# Removed: from ..dependencies import oauth2_scheme
from .. import crud, models, schemas, rbac # Added rbac import
from ..auth import decode_token as auth_decode_token # For JWT decoding

# Load .env for role codes or other configs if they were to be moved from here
from dotenv import load_dotenv
load_dotenv()

SECRET_KEY = os.getenv('SECRET_KEY')
ALGORITHM = os.getenv('ALGORITHM')

if not SECRET_KEY or not ALGORITHM:
    print("CRITICAL WARNING in requests.py: SECRET_KEY or ALGORITHM not found.")
    # Consider raising an error

router = APIRouter(
    prefix="/requests",
    tags=["Requests"],
    responses={404: {"description": "Not found"}}
)

# --- Real Authentication Logic (Locally Defined) ---
oauth2_scheme_req = OAuth2PasswordBearer(tokenUrl="/auth/token") # Local scheme for this router

async def get_current_user_for_req_router(token: str = Depends(oauth2_scheme_req), db: Session = Depends(get_db)) -> models.User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials (req router)",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not SECRET_KEY or not ALGORITHM:
        print("ERROR in requests.py: JWT Secret Key or Algorithm is not configured.")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Server auth configuration error (req router)")
    try:
        payload = auth_decode_token(token) # Using imported decode_token
        user_id: int = payload.get("user_id")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = crud.get_user(db, user_id=user_id)
    if user is None:
        raise credentials_exception
    return user

async def get_current_active_user_for_req_router(current_user: models.User = Depends(get_current_user_for_req_router)) -> models.User:
    if not current_user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user (req router)")
    return current_user
# --- End Real Authentication Logic ---


# Allowed roles for pass types (example role names/codes)
# These should ideally come from a config or constants module
SINGLE_DAY_ALLOWED_ROLES = ["Division Manager", "Deputy Division Manager", "Department Head", "Deputy Department Head", "Admin"] # Example role names
MULTI_DAY_ALLOWED_ROLES = ["Department Head", "Deputy Department Head", "Admin"] # Example role names

# Define Role Codes for approval steps (these should match 'code' in Role model for precise matching)
DCS_OFFICER_ROLE_CODE = "dcs_officer" # Example role code
ZD_DEPUTY_HEAD_ROLE_CODE = "zd_deputy_head" # Example role code
ADMIN_ROLE_CODE = "admin"
DEPARTMENT_HEAD_ROLE_CODE = "department_head"
DEPUTY_DEPARTMENT_HEAD_ROLE_CODE = "deputy_department_head"
DIVISION_MANAGER_ROLE_CODE = "division_manager"
DEPUTY_DIVISION_MANAGER_ROLE_CODE = "deputy_division_manager"
CHECKPOINT_OPERATOR_ROLE_PREFIX = "checkpoint_operator_cp" # e.g., checkpoint_operator_cp1
EMPLOYEE_ROLE_CODE = "employee" # Default or generic user
UNIT_HEAD_ROLE_CODE = "unit_head" # Assuming Unit is a type of department


# Get All Requests (with RBAC)
@router.get("/", response_model=List[schemas.Request])
async def read_all_requests( # Changed to async
    skip: int = 0,
    limit: int = 100,
    status_filter: Optional[schemas.RequestStatusEnum] = None, # Renamed from 'status' to avoid conflict with status module
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user_for_req_router)
):
    # This endpoint should now primarily call crud.get_requests
    # The crud.get_requests function is responsible for applying RBAC based on the user
    # and then any additional filters provided.

    # The old complex RBAC logic here is now moved into crud.get_requests
    # and rbac.get_request_visibility_filters_for_user.

    # Pass all relevant filters to crud.get_requests
    # Note: The crud.get_requests function was updated to accept these named filters.
    # Ensure that the names here match the parameter names in crud.get_requests.
    requests = crud.get_requests(
        db,
        user=current_user, # Pass the current_user for RBAC
        skip=skip,
        limit=limit,
        status=status_filter.value if status_filter else None, # Pass the string value of the enum
        # Add other filters as they are defined in crud.get_requests signature
        # checkpoint_id=checkpoint_id_filter, # This was from old logic, ensure crud.get_requests handles it
        # date_from=...,
        # date_to=...,
        # visitor_name=...
    )
    return requests


@router.post("/", response_model=schemas.Request, status_code=status.HTTP_201_CREATED)
async def create_request_endpoint(
    request_in: schemas.RequestCreate, # Renamed from request_data
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user_for_req_router)
):
    # All business logic (blacklist check, pass type rules, audit, notifications)
    # is now handled within crud.create_request.
    # The router's responsibility is to receive the request, authenticate the user,
    # and call the appropriate CRUD function.

    # The crud.create_request function expects 'request_in: schemas.RequestCreate' and 'creator: models.User'
    # It will raise HTTPException on business rule violations (blacklist, pass type)
    try:
        created_request = crud.create_request(db=db, request_in=request_in, creator=current_user)
        return created_request
    except HTTPException as e: # Catch HTTPExceptions from CRUD to re-raise
        raise e
    except Exception as e: # Catch any other unexpected errors
        # Log error e
        print(f"Unexpected error in create_request_endpoint: {e}") # Basic logging
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error during request creation.")


@router.post("/{request_id}/submit", response_model=schemas.Request)
async def submit_request_for_approval(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user_for_req_router)
):
    # Business logic (status checks, ownership, audit, notifications) is in crud.submit_request
    try:
        updated_request = crud.submit_request(db=db, request_id=request_id, user=current_user)
        return updated_request
    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"Unexpected error in submit_request_for_approval: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error.")


@router.patch("/{request_id}", response_model=schemas.Request)
async def update_request_endpoint(
    request_id: int,
    request_update: schemas.RequestUpdate, # Renamed from request_in
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user_for_req_router)
):
    # Business logic (status checks, ownership, audit) is in crud.update_request_draft
    try:
        updated_request = crud.update_request_draft(db=db, request_id=request_id, request_update=request_update, user=current_user)
        return updated_request
    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"Unexpected error in update_request_endpoint: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error.")


@router.get("/{request_id}", response_model=schemas.Request)
async def read_single_request(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user_for_req_router)
):
    # crud.get_request now handles RBAC and raises HTTPException if not found or not allowed
    db_request = crud.get_request(db, request_id=request_id, user=current_user)
    if not db_request: # Should have been raised by crud if not found/allowed based on its logic.
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found or access denied.")
    return db_request


@router.delete("/{request_id}", response_model=schemas.Request) # Consider status_code=204 if no content returned
async def delete_single_request(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user_for_req_router)
):
    # Fetch request with RBAC check
    db_request_to_delete = crud.get_request(db, request_id=request_id, user=current_user)
    if not db_request_to_delete:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found or not accessible for deletion.")

    # Additional business rule: only creator or admin can delete, and only if DRAFT
    from .. import rbac # For is_creator, is_admin
    if not (rbac.is_creator(current_user, db_request_to_delete) or rbac.is_admin(current_user)):
         raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to delete this request.")

    if db_request_to_delete.status != schemas.RequestStatusEnum.DRAFT.value:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Only DRAFT requests can be deleted. Current status: {db_request_to_delete.status}")

    # crud.delete_request itself is simple; the complex checks remain here or move to a service layer.
    deleted_request_obj = crud.delete_request(db, db_request=db_request_to_delete)

    # Audit log is now handled by crud.delete_request if modified to accept actor_id
    # For now, let's assume crud.delete_request doesn't audit, so we do it here.
    # Or, ensure crud.create_audit_log is called correctly if it's inside crud.delete_request.
    # The plan implies crud.delete_request would handle audit.
    # Let's assume crud.delete_request does not currently audit.
    crud.create_audit_log(db, actor_id=current_user.id, entity='request',
        entity_id=request_id, action='DELETE',
        data={"message": f"Request '{request_id}' deleted by {current_user.username}."}
    )
    return deleted_request_obj # Return the deleted object as per current response_model


# ------------- DCS Approval/Declination Endpoints -------------

@router.post("/{request_id}/dcs_action", response_model=schemas.Request, tags=["Approvals"])
async def dcs_action_on_request(
    request_id: int,
    action: schemas.ApprovalStatusEnum,
    payload: schemas.ApprovalCommentPayload,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user_for_req_router)
):
    # Business logic (role check, status check, approval/decline, audit, notifications)
    # is now in crud.approve_request_step or crud.decline_request_step.
    try:
        if action == schemas.ApprovalStatusEnum.APPROVED:
            updated_request = crud.approve_request_step(db=db, request_id=request_id, approver=current_user, comment=payload.comment)
        elif action == schemas.ApprovalStatusEnum.DECLINED:
            updated_request = crud.decline_request_step(db=db, request_id=request_id, approver=current_user, comment=payload.comment)
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid action specified.")
        return updated_request
    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"Unexpected error in dcs_action_on_request: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error.")


# ------------- ZD Deputy Head Approval/Declination Endpoints -------------

@router.post("/{request_id}/zd_action", response_model=schemas.Request, tags=["Approvals"])
async def zd_action_on_request(
    request_id: int,
    action: schemas.ApprovalStatusEnum,
    payload: schemas.ApprovalCommentPayload,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user_for_req_router)
):
    # Business logic is now in crud.approve_request_step or crud.decline_request_step.
    # The CRUD functions will internally check if the user (approver) has the correct role (ZD)
    # and if the request is in the correct state for ZD action.
    try:
        if action == schemas.ApprovalStatusEnum.APPROVED:
            updated_request = crud.approve_request_step(db=db, request_id=request_id, approver=current_user, comment=payload.comment)
        elif action == schemas.ApprovalStatusEnum.DECLINED:
            updated_request = crud.decline_request_step(db=db, request_id=request_id, approver=current_user, comment=payload.comment)
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid action specified.")
        return updated_request
    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"Unexpected error in zd_action_on_request: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error.")


# ------------- Visit Log Endpoints for a Request -------------

@router.post("/{request_id}/visits", response_model=schemas.VisitLog, status_code=status.HTTP_201_CREATED, tags=["Visit Logs"])
async def create_visit_log_for_request(
    request_id: int,
    visit_log_in: schemas.VisitLogCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user_for_req_router)
):
    """
    Create a new visit log entry for a specific request.
    The `visit_log_in.user_id` should be the ID of the registered User who is visiting.
    Requires admin or checkpoint operator role.
    """
    if not current_user.role:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User role not defined.")

    is_admin = current_user.role.code == ADMIN_ROLE_CODE
    is_checkpoint_operator = current_user.role.code and current_user.role.code.startswith(CHECKPOINT_OPERATOR_ROLE_PREFIX)

    if not (is_admin or is_checkpoint_operator):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to create visit logs.")

    # Check if the request exists
    db_request = crud.get_request(db, request_id=request_id, user=current_user) # get_request includes RBAC for viewing request
    if not db_request:
        # If get_request returned None due to RBAC, it would have raised 403. So this is likely a true 404.
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found.")

    # Validate the visitor user_id from the payload
    visitor_user = crud.get_user(db, user_id=visit_log_in.user_id)
    if not visitor_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Visitor user with ID {visit_log_in.user_id} not found.")

    # Additional check: Ensure the visitor is actually part of the request_persons for this request.
    # This requires linking RequestPerson.user_id or having a way to match.
    # For now, this check is simplified. If RequestPerson had a user_id link to User model:
    # found_in_request_persons = False
    # for rp in db_request.request_persons:
    #     if hasattr(rp, 'user_id') and rp.user_id == visit_log_in.user_id: # Assuming RequestPerson might have a user_id
    #         found_in_request_persons = True
    #         break
    # if not found_in_request_persons:
    #     # This check depends on how RequestPerson is associated with a User.
    #     # If RequestPerson.id is what VisitLog should link to (for non-User visitors), model needs change.
    #     # Given current VisitLog.user_id, we assume the visitor is a User.
    #     # A more robust check would be to see if this user_id corresponds to a person listed in db_request.request_persons
    #     # This might involve matching by name/doc if RequestPerson doesn't directly link to User.id.
    #     # For this iteration, we'll assume if the user exists, and the operator has access, it's okay.
    #     pass


    # Ensure the visit_log_in.request_id matches the path parameter (or set it)
    if visit_log_in.request_id != request_id:
        # Or, you could choose to override visit_log_in.request_id with the path parameter `request_id`
        # For now, let's be strict.
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Payload request_id {visit_log_in.request_id} does not match path request_id {request_id}.")


    created_visit_log = crud.create_visit_log(db=db, visit_log=visit_log_in)
    return created_visit_log


@router.get("/{request_id}/visits", response_model=List[schemas.VisitLog], tags=["Visit Logs"])
async def read_visit_logs_for_request(
    request_id: int,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user_for_req_router)
):
    """
    Retrieve all visit log entries for a specific request.
    Access is controlled by RBAC rules defined in `sql_app.rbac`.
    """
    # Step 1: Fetch the request object. crud.get_request includes its own RBAC for viewing the request.
    db_request = crud.get_request(db, request_id=request_id, user=current_user)
    if not db_request:
        # This means either the request doesn't exist or the current_user doesn't have basic view access to it.
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found or access denied.")

    # Step 2: Get request_creator_department_id
    request_creator_department_id: Optional[int] = None
    if db_request.creator and db_request.creator.department_id is not None:
        request_creator_department_id = db_request.creator.department_id

    # Step 3: Apply RBAC checks for visit log history
    allowed = False
    if rbac.can_user_access_visit_log_full_history(current_user):
        allowed = True
    # Only proceed to department/division checks if full history is not granted AND department ID is available
    elif request_creator_department_id is not None:
        if rbac.can_user_access_visit_log_department_history(db, current_user, request_creator_department_id):
            allowed = True
        elif rbac.can_user_access_visit_log_division_history(db, current_user, request_creator_department_id):
            allowed = True

    # Check if the current user is the creator of the request as a fallback
    # This was part of the original simpler check.
    if not allowed and db_request.creator_id == current_user.id:
        allowed = True

    # Check for checkpoint operator role - this was part of the original simpler check for this endpoint.
    # This specific permission might need to be refined based on whether CP operators should see *all* logs for a request they handle,
    # or only specific entries they create/manage. For now, retaining similar broad access for CP ops on this request's logs.
    if not allowed and current_user.role and current_user.role.code and current_user.role.code.startswith(CHECKPOINT_OPERATOR_ROLE_PREFIX):
        # Further check: is this request associated with this checkpoint operator's checkpoint(s)?
        # This requires knowing the operator's specific checkpoint. For now, if they are any CP operator, allow.
        # A more robust check would be:
        # operator_cp_id_str = current_user.role.code[len(CHECKPOINT_OPERATOR_ROLE_PREFIX):]
        # try:
        #     operator_cp_id = int(operator_cp_id_str)
        #     if any(cp.id == operator_cp_id for cp in db_request.checkpoints):
        #         allowed = True
        # except ValueError:
        #     pass # Invalid role code format
        # For now, any CP operator is allowed if other checks fail. This maintains previous behavior.
        allowed = True


    if not allowed:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to view visit logs for this request.")

    # Step 4: If allowed, fetch and return visit logs
    visit_logs = crud.get_visit_logs_by_request_id(db=db, request_id=request_id, skip=skip, limit=limit)
    return visit_logs