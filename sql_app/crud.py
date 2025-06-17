from sqlalchemy.orm import Session, selectinload
from typing import List, Optional, Any, Union
from fastapi import HTTPException, status
from datetime import date
from fastapi.encoders import jsonable_encoder
from sqlalchemy import or_

from . import models, schemas, auth, rbac
from .models import RequestDuration
from .routers.requests import ADMIN_ROLE_CODE


# ------------- Department CRUD -------------

def get_department(db: Session, department_id: int) -> Optional[models.Department]:
    return db.query(models.Department).filter(models.Department.id == department_id).first()

def get_department_by_name(db: Session, name: str) -> Optional[models.Department]:
    # Note: Name might not be unique across different parent departments.
    return db.query(models.Department).filter(models.Department.name == name).first()

def get_departments(db: Session, skip: int = 0, limit: int = 100) -> list[type[models.Department]]:
    return db.query(models.Department).offset(skip).limit(limit).all()

def create_department(db: Session, department: schemas.DepartmentCreate) -> models.Department:
    db_department = models.Department(**department.model_dump())
    db.add(db_department)
    db.commit()
    db.refresh(db_department)
    return db_department

def update_department(db: Session, db_department: models.Department, department_in: schemas.DepartmentUpdate) -> models.Department:
    update_data = department_in.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_department, key, value)
    db.add(db_department) # db.add() is used to persist changes if db_department was detached or to add it if it's new.
                         # For an already persistent and modified object, db.commit() is often enough.
                         # However, using add is harmless and covers more cases.
    db.commit()
    db.refresh(db_department)
    return db_department

def delete_department(db: Session, db_department: models.Department) -> models.Department:
    db.delete(db_department)
    db.commit()
    # db_department is no longer valid after delete and commit.
    # Returning it might be misleading as its state is 'deleted'.
    # Common practice is to return None or the deleted object (before commit flushes it).
    # For consistency with other delete functions here, returning the object.
    return db_department

def get_department_users(db: Session, department_id: int, skip: int = 0, limit: int = 100) -> list[type[models.User]]:
    return db.query(models.User).filter(models.User.department_id == department_id).options(
        selectinload(models.User.role) # Eager load role
    ).offset(skip).limit(limit).all()

# ------------- Checkpoint CRUD -------------

def get_checkpoint(db: Session, checkpoint_id: int) -> Optional[models.Checkpoint]:
    return db.query(models.Checkpoint).filter(models.Checkpoint.id == checkpoint_id).first()

def get_checkpoint_by_code(db: Session, code: str) -> Optional[models.Checkpoint]:
    return db.query(models.Checkpoint).filter(models.Checkpoint.code == code).first()

def get_checkpoints(db: Session, skip: int = 0, limit: int = 100) -> list[type[models.Checkpoint]]:
    return db.query(models.Checkpoint).offset(skip).limit(limit).all()

def create_checkpoint(db: Session, checkpoint: schemas.CheckpointCreate) -> models.Checkpoint:
    db_checkpoint = models.Checkpoint(**checkpoint.model_dump())
    db.add(db_checkpoint)
    db.commit()
    db.refresh(db_checkpoint)
    return db_checkpoint

def update_checkpoint(db: Session, db_checkpoint: models.Checkpoint, checkpoint_in: schemas.CheckpointUpdate) -> models.Checkpoint:
    update_data = checkpoint_in.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_checkpoint, key, value)
    db.add(db_checkpoint)
    db.commit()
    db.refresh(db_checkpoint)
    return db_checkpoint

def delete_checkpoint(db: Session, db_checkpoint: models.Checkpoint) -> models.Checkpoint:
    db.delete(db_checkpoint)
    db.commit()
    return db_checkpoint

# ------------- Role CRUD (Modified) -------------

def get_role(db: Session, role_id: int) -> Optional[models.Role]:
    return db.query(models.Role).filter(models.Role.id == role_id).first()

def get_roles(db: Session, skip: int = 0, limit: int = 100) -> list[type[models.Role]]:
    return db.query(models.Role).offset(skip).limit(limit).all()

def get_role_by_name(db: Session, role_name: str) -> Optional[models.Role]:
    return db.query(models.Role).filter(models.Role.name == role_name).first()

def create_role(db: Session, role: schemas.RoleCreate) -> models.Role:
    db_role = models.Role(
        name=role.name,
        description=role.description,
        code=role.code
    )
    db.add(db_role)
    db.commit()
    db.refresh(db_role)
    return db_role

def update_role(db: Session, db_role: models.Role, role_in: schemas.RoleUpdate) -> models.Role:
    update_data = role_in.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_role, key, value)
    db.add(db_role)
    db.commit()
    db.refresh(db_role)
    return db_role

def delete_role(db: Session, db_role: models.Role) -> models.Role:
    db.delete(db_role)
    db.commit()
    return db_role

# ------------- User CRUD (Modified) -------------

def get_user(db: Session, user_id: int) -> Optional[models.User]:
    return db.query(models.User).options(
        selectinload(models.User.role),
        selectinload(models.User.department)
    ).filter(models.User.id == user_id).first()

def get_user_by_username(db: Session, username: str) -> Optional[models.User]:
    return db.query(models.User).options(
        selectinload(models.User.role),
        selectinload(models.User.department)
    ).filter(models.User.username == username).first()

def authenticate_user(db: Session, username: str, password: str) -> Optional[models.User]:
    from . import auth # For verify_password
    user = get_user_by_username(db, username=username)
    if not user:
        return None
    if not auth.verify_password(password, user.hashed_password):
        return None
    return user

def get_user_by_email(db: Session, email: str) -> Optional[models.User]:
    return db.query(models.User).options(
        selectinload(models.User.role),
        selectinload(models.User.department)
    ).filter(models.User.email == email).first()

def get_users(db: Session, skip: int = 0, limit: int = 100) -> list[type[models.User]]:
    return db.query(models.User).options(
        selectinload(models.User.role),
        selectinload(models.User.department)
    ).offset(skip).limit(limit).all()

def create_user(db: Session, user_in: schemas.UserCreate) -> models.User:
    # 1) hash the incoming plain‐text password
    hashed = auth.get_password_hash(user_in.hashed_password)

    # 2) build the User model with hashed_password
    db_user = models.User(
        username       = user_in.username,
        full_name      = user_in.full_name,
        email          = user_in.email,
        phone          = user_in.phone,
        role_id        = user_in.role_id,
        department_id  = user_in.department_id,
        is_active      = user_in.is_active,
        hashed_password= hashed,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def update_user(db: Session, db_user: models.User, user_in: schemas.UserUpdate) -> models.User:
    update_data = user_in.model_dump(exclude_unset=True)

    if "hashed_password" in update_data and update_data["hashed_password"] is None:
        del update_data["hashed_password"] # Avoid setting password to None if not provided
    elif "hashed_password" in update_data:
        # If password is provided, it should be hashed by the service/router layer
        pass # Assuming it's already hashed

    for key, value in update_data.items():
        setattr(db_user, key, value)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def delete_user(db: Session, db_user: models.User) -> models.User:
    db.delete(db_user)
    db.commit()
    return db_user

# ------------- RequestPerson CRUD -------------

def create_request_person(db: Session, request_person: schemas.RequestPersonBase, request_id: int) -> models.RequestPerson:
    # Assuming RequestPersonBase is used in RequestCreate.request_persons
    db_request_person = models.RequestPerson(
        **request_person.model_dump(),
        request_id=request_id
    )
    db.add(db_request_person)
    # Commit can be done in batch by the calling function (e.g., create_request)
    # db.commit()
    # db.refresh(db_request_person)
    return db_request_person

# ------------- Request CRUD (Modified) -------------

# Role constants for request creation logic (consider moving to rbac.py or constants.py later)
# These should align with the 'code' field in the Role model.
DIVISION_MANAGER_ROLE_CODE = "division_manager"
DEPUTY_DIVISION_MANAGER_ROLE_CODE = "deputy_division_manager"
DEPARTMENT_HEAD_ROLE_CODE = "department_head"
DEPUTY_DEPARTMENT_HEAD_ROLE_CODE = "deputy_department_head"
# ADMIN_ROLE_CODE = "admin" # Assuming admin can also create any type

# DCS_OFFICER_ROLE_CODE and ZD_DEPUTY_HEAD_ROLE_CODE for notifications
DCS_OFFICER_ROLE_CODE = "dcs_officer"
ZD_DEPUTY_HEAD_ROLE_CODE = "zd_deputy_head"


def create_request(db: Session, request_in: schemas.RequestCreate, creator: models.User) -> models.Request:
    # 1. Blacklist Check
    for person_schema in request_in.request_persons:
        if is_person_blacklisted(db, firstname=person_schema.firstname, lastname=person_schema.lastname, doc_number=person_schema.doc_number):
            # Log this attempt - actor_id is creator.id
            create_audit_log(db, actor_id=creator.id, entity="request_creation_attempt", entity_id=0,
                             action="CREATE_FAIL_BLACKLISTED",
                             data={"message": f"Attempt to create request with blacklisted person: {person_schema.full_name}"})
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail=f"Visitor '{person_schema.full_name}' is on the blacklist.")

    # 2. Pass Type/Creation Rules
    if not creator.role or not creator.department:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User role or department not defined.")

    creator_role_code = creator.role.code
    creator_department_type = creator.department.type # This is DepartmentType enum instance
    print(request_in.duration)

    can_create = False
    if request_in.duration == RequestDuration.LONG_TERM: # Multi-day pass
        # Creator must be Department Head or Deputy for any department type that is not a Division.
        # Or Division Manager/Deputy if their department IS a Division (implicitly a higher level).
        if creator_role_code in [DEPARTMENT_HEAD_ROLE_CODE, DEPUTY_DEPARTMENT_HEAD_ROLE_CODE, ADMIN_ROLE_CODE]:
            can_create = True
        # Implicitly, if a Div Manager creates a multi-day pass for their division, it's allowed.
        # This rule might need refinement: e.g. Dept Heads of depts within a Division.
        # Current TS: Multi-day: Creator must be Department Head or Deputy.
    elif request_in.duration == RequestDuration.SHORT_TERM: # Single-day pass
        # Creator must be Division Manager or Deputy. Department type must be DIVISION.
        # Or Department Head/Deputy for departments that are NOT divisions (implicitly lower level).
        if creator_role_code in [DIVISION_MANAGER_ROLE_CODE, DEPUTY_DIVISION_MANAGER_ROLE_CODE] and \
           creator_department_type == models.DepartmentType.DIVISION:
            can_create = True
        elif creator_role_code in [DEPARTMENT_HEAD_ROLE_CODE, DEPUTY_DEPARTMENT_HEAD_ROLE_CODE, ADMIN_ROLE_CODE] and \
             creator_department_type != models.DepartmentType.UNIT: # Dept head of a non-division unit
            can_create = True
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Неправильно указан duration {request_in.duration}. Определите вариант краткосрочная заявка или долгосрочная.")

    # Admin override - can create any type of pass
    if creator_role_code == ADMIN_ROLE_CODE:
       can_create = True

    if not can_create:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail=f"User role '{creator.role.name}' and department type '{creator_department_type.value}'. У вас нет допуска.")

    # 3. Create Request and RequestPerson objects
    # Initial status is DRAFT (from schema default) or PENDING_DCS if submitted directly.
    # This CRUD assumes RequestCreate implies a DRAFT unless status is overridden.
    # The router endpoint should handle if it's a direct submit changing status.
    # For now, using status from request_in, which defaults to DRAFT.

    # 1. Собираем объекты-модели Checkpoint по списку id
    if not request_in.checkpoint_ids:
        raise HTTPException(400, "Нужно хотя бы 1 checkpoint_id")
    checkpoints = (
        db.query(models.Checkpoint)
        .filter(models.Checkpoint.id.in_(request_in.checkpoint_ids))
        .all()
    )
    if len(checkpoints) != len(request_in.checkpoint_ids):
        raise HTTPException(404, "Некоторые checkpoints не найдены")

    db_request = models.Request(
        creator_id=creator.id,
        status=request_in.status.value,
        start_date=request_in.start_date,
        end_date=request_in.end_date,
        arrival_purpose=request_in.arrival_purpose,
        accompanying=request_in.accompanying,
        contacts_of_accompanying=request_in.contacts_of_accompanying,
        duration=request_in.duration.value,  # если duration тоже enum-поле
    )
    db_request.checkpoints = checkpoints # <— вот тут связываем many-to-many
    db.add(db_request)
    db.commit() # Commit to get db_request.id for RequestPersons

    for person_schema in request_in.request_persons:
        person_model = models.RequestPerson(**person_schema.model_dump(), request_id=db_request.id)
        db.add(person_model)
    db.commit() # Commit all new persons
    db.flush()
    db.refresh(db_request) # Refresh to get all relationships, including request_persons

    # 4. Audit Log
    create_audit_log(db, actor_id=creator.id, entity="request", entity_id=db_request.id,
                     action="CREATE", data={"status": db_request.status, "num_persons": len(db_request.request_persons)})

    # 5. Notification (Placeholder - actual user lookup for roles needed)
    # Example: notify DCS officers. This needs a way to find users by role.
    # dcs_officers = db.query(models.User).join(models.Role).filter(models.Role.code == DCS_OFFICER_ROLE_CODE).all()
    # for officer in dcs_officers:
    #    create_notification(db, user_id=officer.id, message=f"New request {db_request.id} pending your review.", request_id=db_request.id)
    # zd_deputy_heads = db.query(models.User).join(models.Role).filter(models.Role.code == ZD_DEPUTY_HEAD_ROLE_CODE).all()
    # for zd_head in zd_deputy_heads:
    #    create_notification(db, user_id=zd_head.id, message=f"New request {db_request.id} created, will require ZD approval if DCS approves.", request_id=db_request.id)

    return db_request

def get_request(
    db: Session,
    request_id: int,
    user: models.User  # Добавили пользователя для RBAC
) -> Optional[models.Request]:
    # Сразу подгружаем все нужные связи
    request_obj = (
        db.query(models.Request)
          .options(
              selectinload(models.Request.creator)
                .options(
                    selectinload(models.User.role),
                    selectinload(models.User.department),
                ),
              selectinload(models.Request.checkpoints),        # many-to-many
              selectinload(models.Request.request_persons),
              selectinload(models.Request.approvals)
                .selectinload(models.Approval.approver)
          )
          .filter(models.Request.id == request_id)
          .first()
    )

    # RBAC: проверяем право просмотра
    if request_obj and not rbac.can_user_view_request(db, user, request_obj):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this request"
        )

    # Если request_obj is None, он уходит дальше как None (404 обрабатывается в роутере)
    return request_obj


def get_department_descendant_ids(db: Session, department_id: int) -> List[int]:
    """
    Helper function to get a list of IDs for a department and all its descendants.
    Uses a recursive CTE for full hierarchy traversal (PostgreSQL syntax).
    """
    from sqlalchemy import text
    from fastapi import status # For HTTPException, though it might be better to raise custom errors here

    if not isinstance(department_id, int):
        # Log this or raise a more specific internal error type
        print(f"Warning: get_department_descendant_ids called with non-integer department_id: {department_id}")
        return []

    # This CTE is for PostgreSQL.
    cte_query = text("""
        WITH RECURSIVE sub_departments AS (
            SELECT id FROM departments WHERE id = :dept_id
            UNION ALL
            SELECT d.id FROM departments d JOIN sub_departments sd ON d.parent_id = sd.id
        )
        SELECT id FROM sub_departments
    """)
    try:
        result = db.execute(cte_query, {"dept_id": department_id}).fetchall()
        return [row[0] for row in result]
    except Exception as e:
        print(f"Error executing CTE for department descendants (dept_id: {department_id}): {e}")
        # Depending on application design, either raise the raw DB error, a custom app error,
        # or an HTTPException if this function is very close to the API layer.
        # For a CRUD function, raising a custom DataAccessError or similar might be best.
        # For now, re-raising as a generic server error if it happens.
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Database error retrieving department hierarchy.")


def get_requests(
    db: Session,
    user: models.User,
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    checkpoints: Optional[List[int]] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    visitor_name: Optional[str] = None,
) -> Union[list[Any], list[type[models.Request]]]:
    # Базовый запрос с нужными eager-load
    query = db.query(models.Request).options(
        selectinload(models.Request.creator).selectinload(models.User.role),
        selectinload(models.Request.creator).selectinload(models.User.department),
        selectinload(models.Request.checkpoints),
        selectinload(models.Request.request_persons),
    )

    # RBAC: получаем набор фильтров видимости
    visibility_filters = rbac.get_request_visibility_filters_for_user(db, user)

    if not visibility_filters.get("is_unrestricted", False):
        conditions = []

        if "creator_id" in visibility_filters:
            conditions.append(models.Request.creator_id == visibility_filters["creator_id"])

        if "department_ids" in visibility_filters:
            conditions.append(
                models.Request.creator.has(
                    models.User.department_id.in_(visibility_filters["department_ids"])
                )
            )

        if "exact_department_id" in visibility_filters:
            conditions.append(
                models.Request.creator.has(
                    models.User.department_id == visibility_filters["exact_department_id"]
                )
            )

        if "checkpoint_ids" in visibility_filters:
            # many-to-many: any() на relationship
            conditions.append(
                models.Request.checkpoints.any(
                    models.Checkpoint.id == visibility_filters["checkpoint_ids"]
                )
            )
            if "target_statuses" in visibility_filters:
                conditions.append(models.Request.status.in_(visibility_filters["target_statuses"]))

        if not conditions:
            return []  # неразрешено ничего видеть
        query = query.filter(or_(*conditions))

    # Явные фильтры из параметров запроса (AND к видимости)
    if status:
        query = query.filter(models.Request.status == status)

    if checkpoints:
        # хотя бы один из переданных checkpoint_id должен быть у Request
        query = query.filter(
            models.Request.checkpoints.any(models.Checkpoint.id.in_(checkpoints))
        )

    if date_from:
        query = query.filter(models.Request.start_date >= date_from)

    if date_to:
        query = query.filter(models.Request.end_date <= date_to)

    if visitor_name:
        query = (
            query.join(models.RequestPerson)
                 .filter(models.RequestPerson.firstname.ilike(f"%{visitor_name}%"))
        )

    return (
        query
        .order_by(models.Request.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def update_request_draft(db: Session, request_id: int, request_update: schemas.RequestUpdate, user: models.User) -> models.Request:
    from fastapi import status as fastapi_status # Local import for HTTPException status
    # Use the existing get_request which includes RBAC check
    db_request = get_request(db, request_id=request_id, user=user)
    if not db_request:
        # get_request would have raised 403 if not allowed, or this means 404
        raise HTTPException(status_code=fastapi_status.HTTP_404_NOT_FOUND, detail="Request not found or not accessible.")

    if db_request.status != schemas.RequestStatusEnum.DRAFT.value:
        raise HTTPException(status_code=fastapi_status.HTTP_400_BAD_REQUEST, detail="Only DRAFT requests can be updated.")

    from . import rbac # Import rbac module for creator check
    if not rbac.is_creator(user, db_request) and not rbac.is_admin(user): # Allow admin to edit drafts too
        raise HTTPException(status_code=fastapi_status.HTTP_403_FORBIDDEN, detail="Not authorized to update this request.")

    update_data = request_update.model_dump(exclude_unset=True, exclude={"request_persons"})
    changed_fields_log = {}

    for key, value in update_data.items():
        if getattr(db_request, key) != value: # Check if value actually changed
            changed_fields_log[key] = {"old": getattr(db_request, key), "new": value}
            setattr(db_request, key, value)

    # Handle RequestPersons update (simple replacement: delete old, create new)
    if request_update.request_persons is not None:
        changed_fields_log["request_persons"] = "updated" # Simple log message for persons update
        # Delete existing persons for this request
        db.query(models.RequestPerson).filter(models.RequestPerson.request_id == db_request.id).delete(synchronize_session=False)
        # Add new persons
        for person_data in request_update.request_persons:
            db_person = models.RequestPerson(**person_data.model_dump(), request_id=db_request.id)
            db.add(db_person)

    if changed_fields_log: # Only commit if actual changes occurred to request or persons
        db.add(db_request) # Add db_request again in case it was modified
        db.commit()
        db.refresh(db_request)
        create_audit_log(db, actor_id=user.id, entity="request", entity_id=db_request.id, action="UPDATE_DRAFT", data=changed_fields_log)
    return db_request


def submit_request(db: Session, request_id: int, user: models.User) -> models.Request:
    from fastapi import status as fastapi_status
    db_request = get_request(db, request_id=request_id, user=user)
    if not db_request:
        raise HTTPException(status_code=fastapi_status.HTTP_404_NOT_FOUND, detail="Request not found or not accessible.")

    from . import rbac
    if not rbac.is_creator(user, db_request) and not rbac.is_admin(user):
        raise HTTPException(status_code=fastapi_status.HTTP_403_FORBIDDEN, detail="Not authorized to submit this request.")

    if db_request.status != schemas.RequestStatusEnum.DRAFT.value:
        raise HTTPException(status_code=fastapi_status.HTTP_400_BAD_REQUEST, detail="Request is not in DRAFT status.")

    print(len(db_request.request_persons))
    len_person_data = len(db_request.request_persons)
    if len_person_data <= 3:
        db_request.status = schemas.RequestStatusEnum.PENDING_ZD.value
    else:
        db_request.status = schemas.RequestStatusEnum.PENDING_DCS.value
    db.add(db_request)
    db.commit()
    db.refresh(db_request)
    create_audit_log(db, actor_id=user.id, entity="request", entity_id=db_request.id, action="SUBMIT", data={"new_status": db_request.status})

    # TODO: Notifications to DCS Officers and ZD Deputy Head (from plan)
    # dcs_users = db.query(models.User).join(models.Role).filter(models.Role.code == DCS_OFFICER_ROLE_CODE).all()
    # for dcs_user_notify in dcs_users:
    #     create_notification(db, user_id=dcs_user_notify.id, message=f"Request {db_request.id} submitted for DCS review.", request_id=db_request.id)
    # Similar for ZD if needed at this stage.
    return db_request


def approve_request_step(db: Session, request_id: int, approver: models.User, comment: Optional[str]) -> models.Request:
    from fastapi import status as fastapi_status
    db_request = get_request(db, request_id=request_id, user=approver)
    if not db_request:
        raise HTTPException(status_code=fastapi_status.HTTP_404_NOT_FOUND, detail="Request not found or not accessible.")

    from . import rbac
    new_status_val = ""
    approval_step: Optional[schemas.ApprovalStepEnum] = None

    current_status = db_request.status
    if current_status == schemas.RequestStatusEnum.PENDING_DCS.value:
        if not rbac.is_dcs_officer(approver):
            raise HTTPException(status_code=fastapi_status.HTTP_403_FORBIDDEN, detail="User not authorized for DCS approval.")
        new_status_val = schemas.RequestStatusEnum.APPROVED_DCS.value
        approval_step = schemas.ApprovalStepEnum.DCS
        # TODO: Notify ZD Deputy Head that request is ready for ZD approval
    elif current_status == schemas.RequestStatusEnum.APPROVED_DCS.value or \
         current_status == schemas.RequestStatusEnum.PENDING_ZD.value: # PENDING_ZD might be set if workflow requires explicit ZD queue
        if not rbac.is_zd_deputy_head(approver):
            raise HTTPException(status_code=fastapi_status.HTTP_403_FORBIDDEN, detail="User not authorized for ZD approval.")
        new_status_val = schemas.RequestStatusEnum.APPROVED_ZD.value
        approval_step = schemas.ApprovalStepEnum.ZD
        # TODO: Notify requestor and CP operators
    else:
        raise HTTPException(status_code=fastapi_status.HTTP_400_BAD_REQUEST, detail=f"Request not in a state for approval. Status: {current_status}")

    if not approval_step:
        raise HTTPException(status_code=fastapi_status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Approval step could not be determined.")

    db_request.status = new_status_val
    db_approval = models.Approval(
        request_id=request_id, approver_id=approver.id, step=approval_step.value,
        status=schemas.ApprovalStatusEnum.APPROVED.value, comment=comment
    )
    db.add(db_approval)
    db.add(db_request)
    db.commit()
    db.refresh(db_request)
    create_audit_log(db, actor_id=approver.id, entity="request", entity_id=db_request.id, action=f"APPROVE_{approval_step.value}", data={"new_status": new_status_val, "comment": comment})
    return db_request


def decline_request_step(db: Session, request_id: int, approver: models.User, comment: Optional[str]) -> models.Request:
    from fastapi import status as fastapi_status
    db_request = get_request(db, request_id=request_id, user=approver)
    if not db_request:
        raise HTTPException(status_code=fastapi_status.HTTP_404_NOT_FOUND, detail="Request not found or not accessible.")

    from . import rbac
    new_status_val = ""
    approval_step: Optional[schemas.ApprovalStepEnum] = None

    current_status = db_request.status
    if current_status == schemas.RequestStatusEnum.PENDING_DCS.value:
        if not rbac.is_dcs_officer(approver):
            raise HTTPException(status_code=fastapi_status.HTTP_403_FORBIDDEN, detail="User not authorized for DCS decline.")
        new_status_val = schemas.RequestStatusEnum.DECLINED_DCS.value
        approval_step = schemas.ApprovalStepEnum.DCS
        # TODO: Notify requestor
    elif current_status == schemas.RequestStatusEnum.APPROVED_DCS.value or \
         current_status == schemas.RequestStatusEnum.PENDING_ZD.value:
        if not rbac.is_zd_deputy_head(approver):
            raise HTTPException(status_code=fastapi_status.HTTP_403_FORBIDDEN, detail="User not authorized for ZD decline.")
        new_status_val = schemas.RequestStatusEnum.DECLINED_ZD.value
        approval_step = schemas.ApprovalStepEnum.ZD
        # TODO: Notify requestor
    else:
        raise HTTPException(status_code=fastapi_status.HTTP_400_BAD_REQUEST, detail=f"Request not in a state for decline. Status: {current_status}")

    if not approval_step:
        raise HTTPException(status_code=fastapi_status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Approval step could not be determined for decline.")

    db_request.status = new_status_val
    db_approval = models.Approval(
        request_id=request_id, approver_id=approver.id, step=approval_step.value,
        status=schemas.ApprovalStatusEnum.DECLINED.value, comment=comment
    )
    db.add(db_approval)
    db.add(db_request)
    db.commit()
    db.refresh(db_request)
    create_audit_log(db, actor_id=approver.id, entity="request", entity_id=db_request.id, action=f"DECLINE_{approval_step.value}", data={"new_status": new_status_val, "comment": comment})
    return db_request


def get_requests_for_checkpoint(db: Session, checkpoint_id: int, user: models.User) -> list[type[models.Request]]:
    from . import rbac
    from fastapi import status as fastapi_status

    if not (user.role and user.role.code.startswith(rbac.CHECKPOINT_OPERATOR_ROLE_PREFIX)):
         raise HTTPException(status_code=fastapi_status.HTTP_403_FORBIDDEN, detail="User not a checkpoint operator.")

    # Optional: More specific check if operator is for this specific checkpoint_id
    # expected_role_code = f"{rbac.CHECKPOINT_OPERATOR_ROLE_PREFIX}{checkpoint_id}"
    # if user.role.code != expected_role_code:
    #     raise HTTPException(status_code=fastapi_status.HTTP_403_FORBIDDEN, detail=f"User not authorized for checkpoint {checkpoint_id}.")

    query = (
        db.query(models.Request)
        .filter(
            models.Request.checkpoints.any(
                models.Checkpoint.id == checkpoint_id
            ),
            models.Request.status.in_([
                schemas.RequestStatusEnum.APPROVED_ZD.value,
                schemas.RequestStatusEnum.ISSUED.value
            ])
        )
        .options(
            selectinload(models.Request.creator)
            .selectinload(models.User.role),
            selectinload(models.Request.request_persons),
            selectinload(models.Request.checkpoints)  # если нужно подгрузить инфо о КПП
        )
        .order_by(models.Request.created_at.desc())
    )

    return query.all()

def delete_request(db: Session, db_request: models.Request) -> models.Request:
    db.query(models.Approval).filter(models.Approval.request_id == db_request.id).delete(synchronize_session=False)
    db.query(models.RequestPerson).filter(models.RequestPerson.request_id == db_request.id).delete(synchronize_session=False)
    db.delete(db_request)
    db.commit()
    return db_request

# ------------- Approval CRUD -------------

def create_approval(db: Session, approval: schemas.ApprovalCreate) -> models.Approval:
    db_approval = models.Approval(**approval.model_dump())
    # timestamp is server_default
    db.add(db_approval)
    db.commit()
    db.refresh(db_approval)
    return db_approval

def get_approval(db: Session, approval_id: int) -> Optional[models.Approval]:
    return db.query(models.Approval).options(
        selectinload(models.Approval.approver),
        selectinload(models.Approval.request) # Careful with depth here
    ).filter(models.Approval.id == approval_id).first()

def get_approvals_for_request(db: Session, request_id: int, skip: int = 0, limit: int = 100) -> list[type[models.Approval]]:
    return db.query(models.Approval).options(selectinload(models.Approval.approver)).filter(models.Approval.request_id == request_id).order_by(models.Approval.timestamp.desc()).offset(skip).limit(limit).all()

def update_approval(db: Session, db_approval: models.Approval, approval_in: schemas.ApprovalUpdate) -> models.Approval:
    update_data = approval_in.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_approval, key, value)
    db.add(db_approval)
    db.commit()
    db.refresh(db_approval)
    return db_approval

# ------------- AuditLog CRUD -------------

def create_audit_log(db: Session, actor_id: Optional[int], entity: str, entity_id: int, action: str, data: Optional[dict] = None) -> models.AuditLog:
    safe_data = jsonable_encoder(data)
    db_audit_log = models.AuditLog(
        actor_id=actor_id,
        entity=entity,
        entity_id=entity_id,
        action=action,
        data=safe_data
        # timestamp is server_default in model
    )
    db.add(db_audit_log)
    db.commit()
    db.refresh(db_audit_log)
    return db_audit_log

def get_audit_logs(db: Session, skip: int = 0, limit: int = 100) -> list[type[models.AuditLog]]:
    return db.query(models.AuditLog).options(selectinload(models.AuditLog.actor)).order_by(models.AuditLog.timestamp.desc()).offset(skip).limit(limit).all()

# ------------- Blacklist CRUD (Refactored) -------------

def create_blacklist_entry(db: Session, entry_in: schemas.BlackListCreate, adder_id: int) -> models.BlackList:
    db_entry = models.BlackList(
        **entry_in.model_dump(exclude={'added_by'}), # Exclude added_by if present, as we're setting it from adder_id
        added_by=adder_id
        # added_at is server_default
    )
    db.add(db_entry)
    db.commit()
    db.refresh(db_entry)
    create_audit_log(db, actor_id=adder_id, entity="blacklist", entity_id=db_entry.id, action="CREATE", data={"full_name": db_entry.firstname})
    return db_entry

def get_blacklist_entry(db: Session, entry_id: int) -> Optional[models.BlackList]:
    return db.query(models.BlackList).options(
        selectinload(models.BlackList.added_by_user),
        selectinload(models.BlackList.removed_by_user)
    ).filter(models.BlackList.id == entry_id).first()

def get_blacklist_entries(db: Session, skip: int = 0, limit: int = 100, active_only: bool = False) -> list[
    type[models.BlackList]]:
    query = db.query(models.BlackList).options(
        selectinload(models.BlackList.added_by_user),
        selectinload(models.BlackList.removed_by_user)
    )
    if active_only:
        query = query.filter(models.BlackList.status == 'ACTIVE')
    return query.order_by(models.BlackList.added_at.desc()).offset(skip).limit(limit).all()

def update_blacklist_entry(db: Session, db_entry: models.BlackList, entry_in: schemas.BlackListUpdate, actor_id: Optional[int]) -> models.BlackList:
    update_data = entry_in.model_dump(exclude_unset=True)
    changed_fields = {}
    for key, value in update_data.items():
        if getattr(db_entry, key) != value:
            changed_fields[key] = {"old": getattr(db_entry, key), "new": value}
        setattr(db_entry, key, value)

    if changed_fields: # Only commit and audit if there are actual changes
        db.add(db_entry)
        db.commit()
        db.refresh(db_entry)
        create_audit_log(db, actor_id=actor_id, entity="blacklist", entity_id=db_entry.id, action="UPDATE", data=changed_fields)
    return db_entry

def is_person_blacklisted(db: Session, firstname: str, lastname: str, doc_number: str) -> bool:
    query = db.query(models.BlackList).filter(
        models.BlackList.status == 'ACTIVE',
        models.BlackList.firstname == firstname,
         # Consider case-insensitive search here
    )
    if doc_number:
        query = query.filter(models.BlackList.doc_number == doc_number)
    # Not using lastname in the check for now as per original logic, but can be added.
    if lastname:
        query = query.filter(models.BlackList.lastname == lastname)
    return query.first() is not None

def remove_blacklist_entry(db: Session, entry_id: int, remover_id: int) -> Optional[models.BlackList]:
    """Soft deletes a blacklist entry by marking it as INACTIVE."""
    db_entry = get_blacklist_entry(db, entry_id=entry_id)
    if not db_entry:
        return None # Or raise HTTPException(404) if preferred by calling router

    if db_entry.status == "INACTIVE": # Already processed
        return db_entry

    db_entry.status = "INACTIVE"
    db_entry.removed_by = remover_id
    from sqlalchemy.sql import func
    db_entry.removed_at = func.now()
    db.add(db_entry)
    db.commit()
    db.refresh(db_entry)
    create_audit_log(db, actor_id=remover_id, entity="blacklist", entity_id=db_entry.id, action="REMOVE", data={"full_name": db_entry.firstname, "status": "INACTIVE"})
    return db_entry

def delete_blacklist_entry(db: Session, db_entry: models.BlackList, actor_id: Optional[int]) -> models.BlackList: # This is a hard delete
    # It's often better to soft delete (deactivate) sensitive data like blacklist entries.
    # If hard delete is truly required:
    entry_id = db_entry.id
    # full_name = db_entry.full_name
    db.delete(db_entry)
    db.commit()
    # Audit this action - actor_id might be tricky if current_user not passed. Consider adding.
    # create_audit_log(db, actor_id=None, entity="blacklist", entity_id=entry_id, action="HARD_DELETE", data={"full_name": full_name})
    return db_entry


# ------------- Notification CRUD -------------

def create_notification(db: Session, user_id: int, message: str, request_id: Optional[int] = None) -> models.Notification:
    db_notification = models.Notification(
        user_id=user_id,
        message=message,
        related_request_id=request_id
        # timestamp and is_read have defaults in model
    )
    db.add(db_notification)
    db.commit()
    db.refresh(db_notification)
    return db_notification

def get_user_notifications(db: Session, user_id: int, read: Optional[bool] = None, skip: int = 0, limit: int = 20) -> \
list[type[models.Notification]]:
    query = db.query(models.Notification).filter(models.Notification.user_id == user_id)
    if read is not None:
        query = query.filter(models.Notification.is_read == read)
    return query.order_by(models.Notification.timestamp.desc()).offset(skip).limit(limit).all()

def mark_notification_as_read(db: Session, notification_id: int, user_id: int) -> Optional[type[models.Notification]]:
    db_notification = db.query(models.Notification).filter(
        models.Notification.id == notification_id,
        models.Notification.user_id == user_id # Ensure user can only mark their own
    ).first()

    if db_notification:
        if not db_notification.is_read:
            db_notification.is_read = True
            db.commit()
            db.refresh(db_notification)
        return db_notification
    return None
