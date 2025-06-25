from fastapi import Depends, HTTPException, APIRouter, status, Query # Added status
from sqlalchemy.orm import Session
from typing import List, Optional
import os
from fastapi.security import OAuth2PasswordBearer # Added
from jose import JWTError, jwt # Added

from ..crud import create_audit_log
from ..dependencies import get_db
from .. import crud, models, schemas, rbac
from ..constants import *
from ..auth import decode_token as auth_decode_token
from ..auth_dependencies import (
    get_current_active_user,
    get_security_officer_user,
    get_usb_user, get_as_user
)
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


def parse_status_filter(
    raw: Optional[str] = Query(None, alias="status_filter")
) -> Optional[List[schemas.RequestStatusEnum]]:
    if not raw:
        return None
    parts = [p.strip() for p in raw.split(",") if p.strip()]
    try:
        return [schemas.RequestStatusEnum(p) for p in parts]
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status value: {e}"
        )

# Get All Requests (with RBAC)
@router.get("/", response_model=List[schemas.Request])
async def read_all_requests( # Changed to async
    skip: int = 0,
    limit: int = 100,
    statuses: Optional[List[schemas.RequestStatusEnum]] = Depends(parse_status_filter),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    requests = crud.get_requests(
        db,
        user=current_user,
        skip=skip,
        limit=limit,
        statuses=[s.value for s in statuses] if statuses else None,
    )
    return requests


# Обновленный эндпоинт создания заявки в routers/requests.py
@router.post("/", response_model=schemas.Request, status_code=status.HTTP_201_CREATED)
async def create_request_endpoint(
        request_in: schemas.RequestCreate,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_active_user)
):
    """
    Создание новой заявки с автоматической отправкой на одобрение.

    Заявка сразу направляется по соответствующему маршруту:
    - УСБ: для долгосрочных заявок, заявок с > 3 человек или с иностранцами
    - АС: для краткосрочных заявок с <= 3 гражданами КЗ

    Статус DRAFT больше не используется.
    """
    try:
        created_request = crud.create_request(db=db, request_in=request_in, creator=current_user)
        return created_request
    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"Unexpected error in create_request_endpoint: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="Internal server error during request creation.")


# Эндпоинт обновления теперь работает только для заявок в процессе одобрения
@router.patch("/{request_id}", response_model=schemas.Request)
async def update_request_endpoint(
        request_id: int,
        request_update: schemas.RequestUpdate,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_active_user)
):
    """
    Обновление заявки.

    Внимание: Заявки больше не создаются в статусе DRAFT.
    Этот эндпоинт может использоваться администраторами для корректировки
    заявок в особых случаях.
    """
    # Получаем заявку с проверкой прав доступа
    db_request = crud.get_request(db, request_id=request_id, user=current_user)
    if not db_request:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found or access denied.")

    # Только администратор может редактировать заявки после отправки
    if not rbac.is_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Только администраторы могут редактировать отправленные заявки."
        )

    # Запрещаем редактирование финализированных заявок
    final_statuses = [
        schemas.RequestStatusEnum.DECLINED_USB.value,
        schemas.RequestStatusEnum.DECLINED_AS.value,
        schemas.RequestStatusEnum.CLOSED.value
    ]
    if db_request.status in final_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Невозможно редактировать заявку в статусе: {db_request.status}"
        )

    try:
        # Используем существующую функцию update_request_draft, но переименуем её позже
        updated_request = crud.update_request_draft(db=db, request_id=request_id, request_update=request_update,
                                                    user=current_user)
        return updated_request
    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"Unexpected error in update_request_endpoint: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error.")


# Эндпоинт удаления теперь доступен только администраторам
@router.delete("/{request_id}", response_model=schemas.Request)
async def delete_single_request(
        request_id: int,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_active_user)
):
    """
    Удаление заявки. Доступно только администраторам.

    Внимание: Удаление заявки может нарушить целостность данных журналов.
    Рекомендуется использовать отмену (CLOSED) вместо удаления.
    """
    # Проверка прав администратора
    if not rbac.is_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Только администраторы могут удалять заявки."
        )

    # Получаем заявку
    db_request_to_delete = crud.get_request(db, request_id=request_id, user=current_user)
    if not db_request_to_delete:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found.")

    # Предупреждение для важных статусов
    important_statuses = [
        schemas.RequestStatusEnum.APPROVED_AS.value,
        schemas.RequestStatusEnum.ISSUED.value
    ]
    if db_request_to_delete.status in important_statuses:
        # Можно добавить дополнительное подтверждение или логирование
        create_audit_log(
            db,
            actor_id=current_user.id,
            entity='request',
            entity_id=request_id,
            action='DELETE_IMPORTANT',
            data={
                "message": f"Администратор удалил заявку в статусе {db_request_to_delete.status}",
                "status": db_request_to_delete.status
            }
        )

    deleted_request_obj = crud.delete_request(db, db_request=db_request_to_delete)

    crud.create_audit_log(
        db,
        actor_id=current_user.id,
        entity='request',
        entity_id=request_id,
        action='DELETE',
        data={"message": f"Request '{request_id}' deleted by admin {current_user.username}."}
    )

    return deleted_request_obj


@router.get("/{request_id}", response_model=schemas.Request)
async def read_single_request(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    # crud.get_request now handles RBAC and raises HTTPException if not found or not allowed
    db_request = crud.get_request(db, request_id=request_id, user=current_user)
    if not db_request: # Should have been raised by crud if not found/allowed based on its logic.
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found or access denied.")
    return db_request

# ------------- DCS Approval/Declination Endpoints -------------

@router.post("/{request_id}/dcs_action", response_model=schemas.Request, tags=["Approvals"])
async def dcs_action_on_request(
    request_id: int,
    action: schemas.ApprovalStatusEnum,
    payload: schemas.ApprovalCommentPayload,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
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
    current_user: models.User = Depends(get_current_active_user)
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
    current_user: models.User = Depends(get_current_active_user)
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
    current_user: models.User = Depends(get_current_active_user)
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
    if rbac.can_view_all_visit_logs(current_user):
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

    # Step 4: If allowed, fetch and prepare visit logs for response
    db_visit_logs = crud.get_visit_logs_by_request_id(db=db, request_id=request_id, skip=skip, limit=limit)

    response_visit_logs: List[schemas.VisitLog] = []
    for db_log in db_visit_logs:
        request_data = {}
        if db_log.request: # Ensure request object exists
            request_data = {
                "id": db_log.request.id,
                "status": db_log.request.status,
                "start_date": db_log.request.start_date,
                "end_date": db_log.request.end_date,
                # created_at is not in RequestForVisitLog, if needed, add to schema
            }
            if db_log.request.creator:
                request_data["creator_full_name"] = db_log.request.creator.full_name
                if db_log.request.creator.department:
                    request_data["creator_department_name"] = db_log.request.creator.department.name

        request_for_visit_log = schemas.RequestForVisitLog(**request_data) if request_data else None

        user_data = {}
        if db_log.user: # Ensure user (visitor) object exists
            user_data = {
                "id": db_log.user.id,
                "username": db_log.user.username,
                "full_name": db_log.user.full_name,
            }
        user_for_visit_log = schemas.UserForVisitLog(**user_data) if user_data else None

        visit_log_response = schemas.VisitLog(
            id=db_log.id,
            request_id=db_log.request_id,
            user_id=db_log.user_id, # visitor's id
            check_in_time=db_log.check_in_time,
            check_out_time=db_log.check_out_time,
            request=request_for_visit_log,
            user=user_for_visit_log
        )
        response_visit_logs.append(visit_log_response)

    return response_visit_logs

# ------------- Individual RequestPerson Approval/Rejection Schemas -------------

class RequestPersonRejectionPayload(schemas.BaseModel): # Use a common BaseModel from schemas
    rejection_reason: str # Field for Pydantic models, can add = Field(..., min_length=1) if needed


# ------------- Individual RequestPerson Approval/Rejection Endpoints -------------

@router.post("/{request_id}/persons/{person_id}/approve", response_model=schemas.RequestPerson, tags=["Request Persons Actions"])
async def approve_single_request_person(
    request_id: int,
    person_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_security_officer_user) # DCS, ZD, Admin
):
    # Verify person belongs to request
    db_person = crud.get_request_person(db, person_id)
    if not db_person or db_person.request_id != request_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"RequestPerson with ID {person_id} not found in Request {request_id}.")

    # TODO: Add check: Is the main Request in a status that allows individual approvals (e.g., PENDING_DCS, PENDING_ZD)?
    # This logic might be complex, e.g. if request is PENDING_DCS, only DCS can approve. If PENDING_ZD, only ZD.
    # For now, get_security_officer_user ensures the user has one of the high-level roles.
    # Specific step validation (e.g. DCS can only approve if main request is PENDING_DCS) should be added in CRUD or here.

    try:
        approved_person = crud.approve_request_person(db=db, request_person_id=person_id, approver=current_user)
        print(f"[INFO] User {current_user.username} (ID: {current_user.id}) APPROVED RequestPerson ID: {person_id} for Request ID: {request_id}")
        return approved_person
    except crud.ResourceNotFoundException as e: # Catch specific exception from CRUD
        print(f"[WARN] User {current_user.username} (ID: {current_user.id}) failed to APPROVE RequestPerson ID: {person_id} (Request ID: {request_id}). Reason: {str(e)}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except HTTPException as e:
        print(f"[WARN] User {current_user.username} (ID: {current_user.id}) failed to APPROVE RequestPerson ID: {person_id} (Request ID: {request_id}). HTTP Reason: {e.detail}")
        raise e
    except Exception as e:
        # Log error e
        print(f"Unexpected error in approve_single_request_person: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error.")


@router.post("/{request_id}/persons/{person_id}/reject", response_model=schemas.RequestPerson, tags=["Request Persons Actions"])
async def reject_single_request_person(
    request_id: int,
    person_id: int,
    payload: RequestPersonRejectionPayload,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_security_officer_user) # DCS, ZD, Admin
):
    # Verify person belongs to request
    db_person = crud.get_request_person(db, person_id)
    if not db_person or db_person.request_id != request_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"RequestPerson with ID {person_id} not found in Request {request_id}.")

    # TODO: Similar stage validation as in approve endpoint.

    if not payload.rejection_reason or len(payload.rejection_reason.strip()) == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Rejection reason cannot be empty.")

    try:
        rejected_person = crud.reject_request_person(
            db=db,
            request_person_id=person_id,
            reason=payload.rejection_reason,
            approver=current_user
        )
        print(f"[INFO] User {current_user.username} (ID: {current_user.id}) REJECTED RequestPerson ID: {person_id} (Request ID: {request_id}) with reason: '{payload.rejection_reason}'")
        return rejected_person
    except crud.ResourceNotFoundException as e:
        print(f"[WARN] User {current_user.username} (ID: {current_user.id}) failed to REJECT RequestPerson ID: {person_id} (Request ID: {request_id}). Reason: {str(e)}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except HTTPException as e: # Handles the 400 from crud if reason is empty there too
        print(f"[WARN] User {current_user.username} (ID: {current_user.id}) failed to REJECT RequestPerson ID: {person_id} (Request ID: {request_id}). HTTP Reason: {e.detail}")
        raise e
    except Exception as e:
        # Log error e
        print(f"[ERROR] User {current_user.username} (ID: {current_user.id}) encountered an unexpected error rejecting RequestPerson ID: {person_id} (Request ID: {request_id}). Error: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error.")

# ------------- USB Full Request Approval/Rejection Endpoints -------------

@router.post("/{request_id}/usb/approve-all", response_model=schemas.Request, tags=["USB Actions"])
async def usb_approve_entire_request(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_usb_user) # Specific USB role needed
):
    try:
        updated_request = crud.approve_request_usb(db=db, request_id=request_id, usb_user=current_user)
        print(f"[INFO] USB User {current_user.username} (ID: {current_user.id}) APPROVED entire Request ID: {request_id}. New status: {updated_request.status}")
        return updated_request
    except (crud.ResourceNotFoundException, crud.InvalidRequestStateException) as e:
        print(f"[WARN] USB User {current_user.username} (ID: {current_user.id}) failed to APPROVE ALL for Request ID: {request_id}. Reason: {str(e)}")
        if isinstance(e, crud.ResourceNotFoundException):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        else: # InvalidRequestStateException
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"[ERROR] USB User {current_user.username} (ID: {current_user.id}) - unexpected error APPROVE ALL Request ID: {request_id}. Error: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error.")


@router.post("/{request_id}/usb/reject-all", response_model=schemas.Request, tags=["USB Actions"])
async def usb_reject_entire_request(
    request_id: int,
    payload: RequestPersonRejectionPayload, # Re-using for consistency, though it's for the whole request
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_usb_user) # Specific USB role needed
):
    if not payload.rejection_reason or len(payload.rejection_reason.strip()) == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Rejection reason cannot be empty.")
    try:
        updated_request = crud.decline_request_usb(db=db, request_id=request_id, usb_user=current_user, reason=payload.rejection_reason)
        print(f"[INFO] USB User {current_user.username} (ID: {current_user.id}) REJECTED entire Request ID: {request_id} with reason: '{payload.rejection_reason}'. New status: {updated_request.status}")
        return updated_request
    except (crud.ResourceNotFoundException, crud.InvalidRequestStateException) as e:
        print(f"[WARN] USB User {current_user.username} (ID: {current_user.id}) failed to REJECT ALL for Request ID: {request_id}. Reason: {str(e)}")
        if isinstance(e, crud.ResourceNotFoundException):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        else: # InvalidRequestStateException
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except HTTPException as e: # Catches 400 from CRUD if reason is empty there too
        raise e
    except Exception as e:
        print(f"[ERROR] USB User {current_user.username} (ID: {current_user.id}) - unexpected error REJECT ALL Request ID: {request_id}. Error: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error.")

# ------------- AS Full Request Approval/Rejection Endpoints -------------

@router.post("/{request_id}/as/approve-all", response_model=schemas.Request, tags=["AS Actions"])
async def as_approve_entire_request(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_as_user) # Specific AS role needed
):
    try:
        updated_request = crud.approve_request_as(db=db, request_id=request_id, as_user=current_user)
        print(f"[INFO] AS User {current_user.username} (ID: {current_user.id}) APPROVED entire Request ID: {request_id}. New status: {updated_request.status}")
        return updated_request
    except (crud.ResourceNotFoundException, crud.InvalidRequestStateException) as e:
        print(f"[WARN] AS User {current_user.username} (ID: {current_user.id}) failed to APPROVE ALL for Request ID: {request_id}. Reason: {str(e)}")
        if isinstance(e, crud.ResourceNotFoundException):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        else: # InvalidRequestStateException
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"[ERROR] AS User {current_user.username} (ID: {current_user.id}) - unexpected error APPROVE ALL Request ID: {request_id}. Error: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error.")


@router.post("/{request_id}/as/reject-all", response_model=schemas.Request, tags=["AS Actions"])
async def as_reject_entire_request(
    request_id: int,
    payload: RequestPersonRejectionPayload,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_as_user) # Specific AS role needed
):
    if not payload.rejection_reason or len(payload.rejection_reason.strip()) == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Rejection reason cannot be empty.")
    try:
        updated_request = crud.decline_request_as(db=db, request_id=request_id, as_user=current_user, reason=payload.rejection_reason)
        print(f"[INFO] AS User {current_user.username} (ID: {current_user.id}) REJECTED entire Request ID: {request_id} with reason: '{payload.rejection_reason}'. New status: {updated_request.status}")
        return updated_request
    except (crud.ResourceNotFoundException, crud.InvalidRequestStateException) as e:
        print(f"[WARN] AS User {current_user.username} (ID: {current_user.id}) failed to REJECT ALL for Request ID: {request_id}. Reason: {str(e)}")
        if isinstance(e, crud.ResourceNotFoundException):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        else: # InvalidRequestStateException
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"[ERROR] AS User {current_user.username} (ID: {current_user.id}) - unexpected error REJECT ALL Request ID: {request_id}. Error: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error.")
