from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime

from .. import crud, models, schemas, rbac
from ..dependencies import get_db
from ..auth_dependencies import (
    get_current_user,
    get_current_active_user,
    # get_admin_user, # Will be used by existing endpoint
    # get_security_officer_user,
    # get_checkpoint_operator_user, # Will be used by existing endpoint
    get_kpp_user,  # New dependency for KPP role
)
from datetime import date, datetime, timezone  # For date comparisons and timezone
from .. import constants  # Import constants


router = APIRouter(
    prefix="/visits", tags=["Visit Logs"], responses={404: {"description": "Not found"}}
)


def check_permission(current_user: models.User):
    """
    Basic permission check: User must be an admin or a checkpoint operator.
    More granular checks (e.g., specific checkpoint operator for a specific visit log's request)
    would be handled in a dedicated RBAC module.
    """
    if not current_user.role:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="User role not defined."
        )

    is_admin = current_user.role.code == constants.ADMIN_ROLE_CODE
    is_usb = current_user.role.code == constants.USB_ROLE_CODE
    is_as = current_user.role.code == constants.AS_ROLE_CODE
    is_checkpoint_operator = (
        current_user.role.code
        and current_user.role.code.startswith(constants.KPP_ROLE_PREFIX)
    )

    if not (is_admin or is_checkpoint_operator or is_usb or is_as):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to manage visit logs.",
        )


@router.patch("/{visit_log_id}", response_model=schemas.VisitLog)
async def update_visit_log_checkout(
    visit_log_id: int,
    visit_log_update: schemas.VisitLogUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(
        get_current_active_user
    ),  # Using the aliased import
):
    """
    Update a visit log, primarily to set the check_out_time.
    Requires admin or checkpoint operator role.
    """
    check_permission(
        current_user
    )  # This is for the original admin/checkpoint operator endpoint

    db_visit_log = crud.get_visit_log(db, visit_log_id=visit_log_id)
    if not db_visit_log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Visit log not found."
        )

    # The CRUD function handles the logic of only updating if visit_log_update.check_out_time is not None
    updated_log = crud.update_visit_log(
        db=db, visit_log_id=visit_log_id, visit_log_update=visit_log_update
    )

    if updated_log is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Failed to update visit log or log not found after update attempt.",
        )

    return updated_log


# KPP Endpoints


@router.post(
    "/entry", response_model=schemas.VisitLog, status_code=status.HTTP_201_CREATED
)
async def record_visitor_entry(
    visit_log_in: schemas.VisitLogCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_kpp_user),
):
    """
    Record a visitor's entry. KPP role required.
    `visit_log_in` should contain `request_id` and `request_person_id`.
    """
    # 1. Verify RequestPerson
    db_request_person = (
        db.query(models.RequestPerson)
        .filter(models.RequestPerson.id == visit_log_in.request_person_id)
        .first()
    )

    if not db_request_person:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"RequestPerson with ID {visit_log_in.request_person_id} not found.",
        )

    # Ensure request_id in payload matches the one associated with RequestPerson
    if db_request_person.request_id != visit_log_in.request_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Payload request_id {visit_log_in.request_id} does not match request_id {db_request_person.request_id} of the RequestPerson.",
        )

    # 2. Verify Request
    # We need the user object to pass to crud.get_request for its internal RBAC,
    # even though KPP might not have general view rights, this is for data integrity.
    # A simpler db query could also work if RBAC for KPP on general request viewing is too complex here.
    db_request = crud.get_request(
        db, request_id=visit_log_in.request_id, user=current_user
    )  # Pass current_user for RBAC consistency
    if not db_request:
        # If get_request itself raises 403 due to KPP not having general view, this needs adjustment.
        # For now, assume KPP might not have view rights, so a direct query might be better if get_request is too restrictive.
        # Alternative direct query:
        db_request = (
            db.query(models.Request)
            .filter(models.Request.id == visit_log_in.request_id)
            .first()
        )
        if not db_request:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Request with ID {visit_log_in.request_id} not found.",
            )

    # 3. Validate RequestPerson status
    if db_request_person.status == models.RequestPersonStatus.DECLINED_USB:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Visitor (RequestPerson ID: {db_request_person.id}) has been rejected and cannot be processed for entry.",
        )
    if db_request_person.status == models.RequestPersonStatus.DECLINED_AS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Visitor (RequestPerson ID: {db_request_person.id}) has been rejected and cannot be processed for entry.",
        )
    if db_request_person.status != models.RequestPersonStatus.APPROVED_AS:
        # This covers PENDING or any other non-APPROVED status apart from REJECTED
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Visitor (RequestPerson ID: {db_request_person.id}) is not approved for entry (status: {db_request_person.status.value}).",
        )

    # 4. Validate Request status
    allowed_request_statuses = [
        schemas.RequestStatusEnum.APPROVED_AS.value,
        schemas.RequestStatusEnum.ISSUED.value,  # Assuming ISSUED means pass is active
    ]
    if db_request.status not in allowed_request_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Request ID {db_request.id} is not in an approved state for entry (current status: {db_request.status}).",
        )

    # 5. Validate date
    today = date.today()
    if not (db_request.start_date <= today <= db_request.end_date):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Visit is outside the allowed date range ({db_request.start_date} to {db_request.end_date}) for Request ID {db_request.id}.",
        )

    # 6. Check if already entered and not exited
    existing_log = (
        db.query(models.VisitLog)
        .filter(
            models.VisitLog.request_person_id == visit_log_in.request_person_id,
            models.VisitLog.request_id == visit_log_in.request_id,
            models.VisitLog.check_out_time == None,
        )
        .first()
    )
    if existing_log:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Visitor (RequestPerson ID: {visit_log_in.request_person_id}) has already entered and not exited for this request.",
        )

    # 7. Create VisitLog
    # The VisitLogCreate schema expects request_id, request_person_id, and checkpoint_id.

    kpp_checkpoint_id = rbac.get_request_filters_for_user(db, current_user)
    print(kpp_checkpoint_id, "kpp_checkpoint_id")
    if kpp_checkpoint_id is None:
        # This log helps identify if role codes are not set up like "KPP-1", "KPP-2", etc.
        print(
            f"[ERROR] KPP User {current_user.username} (ID: {current_user.id}) could not determine checkpoint ID from role: {current_user.role.code if current_user.role else 'NO_ROLE'}"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="KPP user role does not specify a valid checkpoint number (e.g., KPP-1).",
        )

    # Verify this checkpoint_id (derived from KPP user's role) exists in the DB
    checkpoint_id = kpp_checkpoint_id["checkpoint_id"]
    db_checkpoint = crud.get_checkpoint(db, checkpoint_id=checkpoint_id)
    if not db_checkpoint:
        print(
            f"[ERROR] KPP User {current_user.username} (ID: {current_user.id}) - Checkpoint ID {checkpoint_id} derived from role not found in DB."
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"KPP's assigned checkpoint (ID: {checkpoint_id}) is invalid or not found.",
        )

    # Ensure the request (db_request was fetched earlier) allows entry through this KPP user's checkpoint
    if not any(cp.id == checkpoint_id for cp in db_request.checkpoints):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Request ID {db_request.id} does not permit entry through checkpoint {db_checkpoint.name} (KPP user's assigned checkpoint).",
        )

    # Validate that the checkpoint_id in the payload matches the KPP user's derived checkpoint_id
    if visit_log_in.checkpoint_id != checkpoint_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Provided checkpoint_id {visit_log_in.checkpoint_id} in payload does not match KPP user's assigned checkpoint {checkpoint_id}.",
        )

    # All checks passed, create the visit log using the validated payload.
    # visit_log_in already contains request_id, request_person_id, and the (now validated) checkpoint_id.
    created_log = crud.create_visit_log(db=db, visit_log=visit_log_in)

    db_request_person.is_entered = True
    db.add(db_request_person)
    db.commit()
    db.refresh(db_request_person)

    print(
        f"[INFO] KPP User {current_user.username} (ID: {current_user.id}) recorded ENTRY for RequestPerson ID: {created_log.request_person_id}, VisitLog ID: {created_log.id}"
    )
    return created_log


@router.patch("/exit/{visit_log_id}", response_model=schemas.VisitLog)
async def record_visitor_exit(
    visit_log_id: int,
    visit_log_update: schemas.VisitLogUpdate,  # Should ideally only contain check_out_time
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_kpp_user),
):
    """
    Record a visitor's exit by updating the check_out_time. KPP role required.
    `visit_log_update` should provide the `check_out_time`.
    """
    db_visit_log = crud.get_visit_log(db, visit_log_id=visit_log_id)
    if not db_visit_log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Visit log not found."
        )

    if db_visit_log.check_out_time is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Visitor has already checked out for this visit log entry.",
        )

    if visit_log_update.check_out_time is None:
        # Default to now if not provided. The field in schema is Optional.
        visit_log_update.check_out_time = datetime.now(timezone.utc)

    updated_log = crud.update_visit_log(
        db=db, visit_log_id=visit_log_id, visit_log_update=visit_log_update
    )

    # (Optional) Update RequestPerson.is_entered status
    db_request_person = (
        db.query(models.RequestPerson)
        .filter(models.RequestPerson.id == db_visit_log.request_person_id)
        .first()
    )
    if db_request_person:
        db_request_person.is_entered = False
        db.add(db_request_person)
        db.commit()

    if updated_log is None:  # Should not happen if db_visit_log was found
        print(
            f"[ERROR] KPP User {current_user.username} (ID: {current_user.id}) failed to update VisitLog ID: {visit_log_id} for EXIT."
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update visit log.",
        )

    print(
        f"[INFO] KPP User {current_user.username} (ID: {current_user.id}) recorded EXIT for VisitLog ID: {updated_log.id}, RequestPerson ID: {updated_log.request_person_id}"
    )
    return updated_log


@router.get("/", response_model=List[schemas.VisitLog], tags=["Visit Logs General"])
async def read_visit_logs(
    skip: int = 0,
    limit: int = 100,
    check_in: Optional[date] = None,
    check_out: Optional[date] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    """
    Retrieve visit logs with RBAC, filtering, and pagination.
    - DCS/ZD/Admin: Can see all logs.
    - Managers (Dept Head/Deputy, Unit Head/Deputy, Division Manager/Deputy):
      Can see logs for visits associated with requests created by users in their
      respective departments/units/divisions (including sub-departments).
    - Other users: Will receive an empty list or an error if not covered by specific rules.
    """
    # The CRUD function handles all RBAC logic, filtering, and pagination.
    visit_logs_db = crud.get_visit_logs_with_rbac(
        db=db,
        current_user=current_user,
        skip=skip,
        limit=limit,
        start_date=check_in,
        end_date=check_out,
    )

    # The schemas.VisitLog already defines how to serialize from the model,
    # including the nested RequestForVisitLog and RequestPersonForVisitLog.
    # FastAPI will handle the conversion.
    return visit_logs_db
