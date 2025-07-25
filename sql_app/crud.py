from sqlalchemy.orm import Session, selectinload, contains_eager
from typing import List, Optional, Any, Union
from fastapi import HTTPException, status
from datetime import date, timedelta, datetime, time
from fastapi.encoders import jsonable_encoder
from sqlalchemy import or_
from sqlalchemy.sql.functions import func

from . import models, schemas, auth, rbac, constants  # Added constants
from .models import RequestDuration

# from .routers.requests import ADMIN_ROLE_CODE # Will use constants.ADMIN_ROLE_CODE
from .error_handlers import (
    BlacklistedPersonException,
    ResourceNotFoundException,
    InvalidRequestStateException,
)


# ------------- Department CRUD -------------
def get_department(db: Session, department_id: int) -> Optional[models.Department]:
    return (
        db.query(models.Department)
        .filter(models.Department.id == department_id)
        .first()
    )


def get_department_by_name(db: Session, name: str) -> Optional[models.Department]:
    # Note: Name might not be unique across different parent departments.
    return db.query(models.Department).filter(models.Department.name == name).first()


def get_departments(
    db: Session, skip: int = 0, limit: int = 100
) -> list[type[models.Department]]:
    return db.query(models.Department).offset(skip).limit(limit).all()


def create_department(
    db: Session, department: schemas.DepartmentCreate
) -> models.Department:
    db_department = models.Department(**department.model_dump())
    db.add(db_department)
    db.commit()
    db.refresh(db_department)
    return db_department


def update_department(
    db: Session,
    db_department: models.Department,
    department_in: schemas.DepartmentUpdate,
) -> models.Department:
    update_data = department_in.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_department, key, value)
    db.add(
        db_department
    )  # db.add() is used to persist changes if db_department was detached or to add it if it's new.
    # For an already persistent and modified object, db.commit() is often enough.
    # However, using add is harmless and covers more cases.
    db.commit()
    db.refresh(db_department)
    return db_department


def delete_department(
    db: Session, db_department: models.Department
) -> models.Department:
    db.delete(db_department)
    db.commit()
    # db_department is no longer valid after delete and commit.
    # Returning it might be misleading as its state is 'deleted'.
    # Common practice is to return None or the deleted object (before commit flushes it).
    # For consistency with other delete functions here, returning the object.
    return db_department


def get_department_users(
    db: Session, department_id: int, skip: int = 0, limit: int = 100
) -> list[type[models.User]]:
    return (
        db.query(models.User)
        .filter(models.User.department_id == department_id)
        .options(selectinload(models.User.role))  # Eager load role
        .offset(skip)
        .limit(limit)
        .all()
    )


# ------------- Checkpoint CRUD -------------
def get_checkpoint(db: Session, checkpoint_id: int) -> Optional[models.Checkpoint]:
    return (
        db.query(models.Checkpoint)
        .filter(models.Checkpoint.id == checkpoint_id)
        .first()
    )


def get_checkpoint_by_code(db: Session, code: str) -> Optional[models.Checkpoint]:
    return db.query(models.Checkpoint).filter(models.Checkpoint.code == code).first()


def get_checkpoints(
    db: Session, skip: int = 0, limit: int = 100
) -> list[type[models.Checkpoint]]:
    return db.query(models.Checkpoint).offset(skip).limit(limit).all()


def create_checkpoint(
    db: Session, checkpoint: schemas.CheckpointCreate
) -> models.Checkpoint:
    db_checkpoint = models.Checkpoint(**checkpoint.model_dump())
    db.add(db_checkpoint)
    db.commit()
    db.refresh(db_checkpoint)
    return db_checkpoint


def update_checkpoint(
    db: Session,
    db_checkpoint: models.Checkpoint,
    checkpoint_in: schemas.CheckpointUpdate,
) -> models.Checkpoint:
    update_data = checkpoint_in.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_checkpoint, key, value)
    db.add(db_checkpoint)
    db.commit()
    db.refresh(db_checkpoint)
    return db_checkpoint


def delete_checkpoint(
    db: Session, db_checkpoint: models.Checkpoint
) -> models.Checkpoint:
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
    db_role = models.Role(name=role.name, description=role.description, code=role.code)
    db.add(db_role)
    db.commit()
    db.refresh(db_role)
    return db_role


def update_role(
    db: Session, db_role: models.Role, role_in: schemas.RoleUpdate
) -> models.Role:
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
    return (
        db.query(models.User)
        .options(selectinload(models.User.role), selectinload(models.User.department))
        .filter(models.User.id == user_id)
        .first()
    )


def get_user_by_username(db: Session, username: str) -> Optional[models.User]:
    return (
        db.query(models.User)
        .options(selectinload(models.User.role), selectinload(models.User.department))
        .filter(models.User.username == username)
        .first()
    )


def authenticate_user(
    db: Session, username: str, password: str
) -> Optional[models.User]:
    from . import auth

    user = get_user_by_username(db, username=username)
    if not user:
        return None
    if not auth.verify_password(password, user.hashed_password):
        return None
    return user


def get_user_by_email(db: Session, email: str) -> Optional[models.User]:
    return (
        db.query(models.User)
        .options(selectinload(models.User.role), selectinload(models.User.department))
        .filter(models.User.email == email)
        .first()
    )


def get_users(db: Session, skip: int = 0, limit: int = 100) -> list[type[models.User]]:
    return (
        db.query(models.User)
        .options(selectinload(models.User.role), selectinload(models.User.department))
        .offset(skip)
        .limit(limit)
        .all()
    )


def create_user(db: Session, user_in: schemas.UserCreate) -> models.User:
    # 1) hash the incoming plain‐text password
    hashed = auth.get_password_hash(user_in.hashed_password)

    # 2) build the User model with hashed_password
    db_user = models.User(
        username=user_in.username,
        full_name=user_in.full_name,
        email=user_in.email,
        phone=user_in.phone,
        role_id=user_in.role_id,
        department_id=user_in.department_id,
        is_active=user_in.is_active,
        hashed_password=hashed,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def update_user(
    db: Session, db_user: models.User, user_in: schemas.UserUpdate
) -> models.User:
    update_data = user_in.model_dump(exclude_unset=True)

    if "hashed_password" in update_data and update_data["hashed_password"] is None:
        del update_data[
            "hashed_password"
        ]  # Avoid setting password to None if not provided
    elif "hashed_password" in update_data:
        # If password is provided, it should be hashed by the service/router layer
        pass  # Assuming it's already hashed

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
def create_request_person(
    db: Session, request_person: schemas.RequestPersonBase, request_id: int
) -> models.RequestPerson:
    # Assuming RequestPersonBase is used in RequestCreate.request_persons
    db_request_person = models.RequestPerson(
        **request_person.model_dump(), request_id=request_id
    )
    db.add(db_request_person)
    # Commit can be done in batch by the calling function (e.g., create_request)
    # db.commit()
    # db.refresh(db_request_person)
    return db_request_person


def get_request_person(
    db: Session, request_person_id: int
) -> Optional[models.RequestPerson]:
    return (
        db.query(models.RequestPerson)
        .filter(models.RequestPerson.id == request_person_id)
        .first()
    )


def approve_request_person(
    db: Session, request_person_id: int, approver: models.User
) -> models.RequestPerson:
    db_person = get_request_person(db, request_person_id)
    if not db_person:
        raise ResourceNotFoundException("RequestPerson", request_person_id)

    # Check main request status
    db_request = (
        db.query(models.Request)
        .filter(models.Request.id == db_person.request_id)
        .first()
    )
    if not db_request:
        raise ResourceNotFoundException("Request", db_person.request_id)

    allowed_request_statuses_for_usb = [
        schemas.RequestStatusEnum.PENDING_USB.value,
        schemas.RequestStatusEnum.APPROVED_USB.value,
        schemas.RequestStatusEnum.DECLINED_USB.value,
    ]

    if (
        rbac.is_usb(approver)
        and db_request.status not in allowed_request_statuses_for_usb
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Вы не являетесь сотрудником УСБ или статус заявки не совпадает с нужным!",
        )

    allowed_request_statuses_for_as = [
        schemas.RequestStatusEnum.APPROVED_USB.value,
        schemas.RequestStatusEnum.PENDING_AS.value,
        schemas.RequestStatusEnum.APPROVED_AS.value,
        schemas.RequestStatusEnum.DECLINED_AS.value,
    ]

    if (
        rbac.is_as(approver)
        and db_request.status not in allowed_request_statuses_for_as
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Вы не являетесь сотрудником АС или статус заявки не совпадает с нужным!",
        )

    # Запретить АС изменять статус посетителей, которых УСБ отклонил
    if (
        rbac.is_as(approver)
        and db_person.status == models.RequestPersonStatus.DECLINED_USB
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Невозможно изменить статус посетителя, отклоненного УСБ!",
        )

    # Запретить АС работать с заявками, полностью отклоненными УСБ
    if (
        rbac.is_as(approver)
        and db_request.status == schemas.RequestStatusEnum.DECLINED_USB.value
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Невозможно изменить заявку, отклоненную УСБ!",
        )

    allowed_usb_statuses = {
        schemas.RequestPersonStatusEnum.PENDING_USB.value,
        schemas.RequestPersonStatusEnum.APPROVED_USB.value,
        schemas.RequestPersonStatusEnum.DECLINED_USB.value,
    }

    allowed_as_statuses = {
        schemas.RequestPersonStatusEnum.APPROVED_USB.value,
        schemas.RequestPersonStatusEnum.PENDING_AS.value,
        schemas.RequestPersonStatusEnum.APPROVED_AS.value,
        schemas.RequestPersonStatusEnum.DECLINED_AS.value,
    }

    # Debug current status
    print(f"Current status: {db_person.status!r}")

    # Approve based on role and allowed statuses
    if rbac.is_usb(approver) and db_person.status.value in allowed_usb_statuses:
        db_person.status = models.RequestPersonStatus.APPROVED_USB
        print(f"Updated status to: {db_person.status!r}")
    elif rbac.is_as(approver) and db_person.status.value in allowed_as_statuses:
        db_person.status = models.RequestPersonStatus.APPROVED_AS
        print(f"Updated status to: {db_person.status!r}")
    else:
        # Handle unauthorized or invalid transitions
        raise PermissionError(
            "You are not allowed to approve this request or the current status is invalid for your role."
        )
    db_person.rejection_reason = None  # Clear any previous rejection reason
    db.add(db_person)
    db.commit()
    db.refresh(db_person)
    _finalize_request_if_all_persons_processed(db, db_person.request_id, approver)
    create_audit_log(
        db,
        actor_id=approver.id,
        entity="request_person",
        entity_id=db_person.id,
        action="APPROVE",
        data={"request_id": db_person.request_id, "new_status": "APPROVED"},
    )
    return db_person


def reject_request_person(
    db: Session, request_person_id: int, reason: str, approver: models.User
) -> models.RequestPerson:
    db_person = get_request_person(db, request_person_id)
    if not db_person:
        raise ResourceNotFoundException("RequestPerson", request_person_id)

    if not reason:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Rejection reason is required.",
        )

    # Check main request status (similar to approve)
    db_request = (
        db.query(models.Request)
        .filter(models.Request.id == db_person.request_id)
        .first()
    )
    if not db_request:
        raise ResourceNotFoundException("Request", db_person.request_id)

    allowed_request_statuses_for_usb = [
        schemas.RequestStatusEnum.PENDING_USB.value,
        schemas.RequestStatusEnum.APPROVED_USB.value,
        schemas.RequestStatusEnum.DECLINED_USB.value,
    ]

    if (
        rbac.is_usb(approver)
        and db_request.status not in allowed_request_statuses_for_usb
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Вы не являетесь сотрудником УСБ или статус заявки не совпадает с нужным!",
        )

    allowed_request_statuses_for_as = [
        schemas.RequestStatusEnum.APPROVED_USB.value,
        schemas.RequestStatusEnum.PENDING_AS.value,
        schemas.RequestStatusEnum.APPROVED_AS.value,
        schemas.RequestStatusEnum.DECLINED_AS.value,
    ]

    if (
        rbac.is_as(approver)
        and db_request.status not in allowed_request_statuses_for_as
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Вы не являетесь сотрудником АС или статус заявки не совпадает с нужным!",
        )

    # Запретить АС изменять статус посетителей, которых УСБ отклонил
    if (
        rbac.is_as(approver)
        and db_person.status == models.RequestPersonStatus.DECLINED_USB
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Невозможно изменить статус посетителя, отклоненного УСБ!",
        )

    # Запретить АС работать с заявками, полностью отклоненными УСБ
    if (
        rbac.is_as(approver)
        and db_request.status == schemas.RequestStatusEnum.DECLINED_USB.value
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Невозможно изменить заявку, отклоненную УСБ!",
        )

    allowed_usb_statuses = {
        schemas.RequestPersonStatusEnum.PENDING_USB.value,
        schemas.RequestPersonStatusEnum.APPROVED_USB.value,
        schemas.RequestPersonStatusEnum.DECLINED_USB.value,
    }

    allowed_as_statuses = {
        schemas.RequestPersonStatusEnum.APPROVED_USB.value,
        schemas.RequestPersonStatusEnum.PENDING_AS.value,
        schemas.RequestPersonStatusEnum.APPROVED_AS.value,
        schemas.RequestPersonStatusEnum.DECLINED_AS.value,
    }

    # Reject based on role and allowed statuses
    if rbac.is_usb(approver) and db_person.status.value in allowed_usb_statuses:
        db_person.status = models.RequestPersonStatus.DECLINED_USB
        print(f"Updated status to: {db_person.status!r}")
    elif rbac.is_as(approver) and db_person.status.value in allowed_as_statuses:
        db_person.status = models.RequestPersonStatus.DECLINED_AS
        print(f"Updated status to: {db_person.status!r}")
    else:
        # Handle unauthorized or invalid transitions
        raise PermissionError(
            "You are not allowed to reject this request or the current status is invalid for your role."
        )
    db_person.rejection_reason = reason
    db.add(db_person)
    db.commit()
    db.refresh(db_person)
    _finalize_request_if_all_persons_processed(db, db_person.request_id, approver)
    create_audit_log(
        db,
        actor_id=approver.id,
        entity="request_person",
        entity_id=db_person.id,
        action="REJECT",
        data={
            "request_id": db_person.request_id,
            "new_status": "REJECTED",
            "reason": reason,
        },
    )
    return db_person


def _finalize_request_if_all_persons_processed(
    db: Session, request_id: int, approver: models.User
):
    """
    Автоматически переводит статус Request, когда все связанные RequestPerson обработаны для данной роли.
    """
    print(f"\n[DEBUG] === _finalize_request_if_all_persons_processed called ===")
    print(f"[DEBUG] Request ID: {request_id}")
    print(
        f"[DEBUG] Approver: {approver.username} (Role: {approver.role.code if approver.role else 'NO_ROLE'})"
    )

    if rbac.is_usb(approver):
        print(f"[DEBUG] === USB PROCESSING ===")
        # УСБ обрабатывает всех посетителей
        total_persons = (
            db.query(func.count(models.RequestPerson.id))
            .filter(models.RequestPerson.request_id == request_id)
            .scalar()
            or 0
        )

        # Количество обработанных УСБ (одобренных или отклоненных)
        usb_processed = (
            db.query(func.count(models.RequestPerson.id))
            .filter(
                models.RequestPerson.request_id == request_id,
                models.RequestPerson.status.in_(
                    [
                        models.RequestPersonStatus.APPROVED_USB,
                        models.RequestPersonStatus.DECLINED_USB,
                    ]
                ),
            )
            .scalar()
            or 0
        )

        print(f"[DEBUG] Total persons: {total_persons}, USB processed: {usb_processed}")

        # Если УСБ обработал всех посетителей
        if usb_processed == total_persons:
            print(f"[DEBUG] All persons processed by USB")
            # Количество одобренных УСБ
            usb_approved = (
                db.query(func.count(models.RequestPerson.id))
                .filter(
                    models.RequestPerson.request_id == request_id,
                    models.RequestPerson.status
                    == models.RequestPersonStatus.APPROVED_USB,
                )
                .scalar()
                or 0
            )

            print(f"[DEBUG] USB approved count: {usb_approved}")

            # Определяем новый статус заявки
            if usb_approved == 0:
                # Все отклонены УСБ
                new_status = schemas.RequestStatusEnum.DECLINED_USB.value
                print(f"[DEBUG] All declined by USB -> {new_status}")
            else:
                # Есть одобренные УСБ (частично или полностью)
                new_status = schemas.RequestStatusEnum.APPROVED_USB.value
                print(f"[DEBUG] Some approved by USB -> {new_status}")

            # Обновляем статус заявки
            request_obj = db.get(models.Request, request_id)
            old_status = request_obj.status
            request_obj.status = new_status
            db.commit()
            db.refresh(request_obj)

            print(
                f"[DEBUG] USB: Request status updated from {old_status} to {request_obj.status}"
            )

            create_audit_log(
                db,
                actor_id=approver.id,
                entity="request",
                entity_id=request_id,
                action="AUTO_STATUS_UPDATE_USB",
                data={
                    "new_status": new_status,
                    "approved_count": usb_approved,
                    "total_count": total_persons,
                },
            )
        else:
            print(
                f"[DEBUG] USB: Not all persons processed yet: {usb_processed}/{total_persons}"
            )

    elif rbac.is_as(approver):
        print(f"[DEBUG] === AS PROCESSING ===")
        # Получаем текущую заявку для проверки её статуса
        request_obj = db.get(models.Request, request_id)
        if not request_obj:
            print(f"[DEBUG] Request {request_id} not found!")
            return

        print(
            f"[DEBUG] AS Processing - Request ID: {request_id}, Current Status: {request_obj.status}"
        )

        # Общее количество посетителей в заявке
        total_persons = (
            db.query(func.count(models.RequestPerson.id))
            .filter(models.RequestPerson.request_id == request_id)
            .scalar()
            or 0
        )

        print(f"[DEBUG] Total persons in request: {total_persons}")

        # Получаем детальную информацию о статусах всех посетителей
        all_persons = (
            db.query(models.RequestPerson)
            .filter(models.RequestPerson.request_id == request_id)
            .all()
        )
        print(f"[DEBUG] === ALL PERSONS STATUS ===")
        for person in all_persons:
            print(
                f"[DEBUG] Person {person.id}: {person.firstname} {person.lastname} - Status: {person.status.value}"
            )

        if request_obj.status == schemas.RequestStatusEnum.PENDING_AS.value:
            print(f"[DEBUG] Processing PENDING_AS flow (direct to AS)")
            # Заявка пришла напрямую к АС (краткосрочная, <= 3 граждан КЗ)
            # АС должен обработать всех посетителей
            as_processed = (
                db.query(func.count(models.RequestPerson.id))
                .filter(
                    models.RequestPerson.request_id == request_id,
                    models.RequestPerson.status.in_(
                        [
                            models.RequestPersonStatus.APPROVED_AS,
                            models.RequestPersonStatus.DECLINED_AS,
                        ]
                    ),
                )
                .scalar()
                or 0
            )

            print(f"[DEBUG] AS processed: {as_processed}, Total: {total_persons}")

            # Если АС обработал всех посетителей
            if as_processed == total_persons:
                print(f"[DEBUG] All persons processed by AS - updating request status")
                # Количество одобренных АС
                as_approved = (
                    db.query(func.count(models.RequestPerson.id))
                    .filter(
                        models.RequestPerson.request_id == request_id,
                        models.RequestPerson.status
                        == models.RequestPersonStatus.APPROVED_AS,
                    )
                    .scalar()
                    or 0
                )

                print(f"[DEBUG] AS approved count: {as_approved}")

                # Определяем новый статус заявки
                if as_approved == 0:
                    # АС отклонил всех посетителей
                    new_status = schemas.RequestStatusEnum.DECLINED_AS.value
                    print(f"[DEBUG] All declined by AS -> {new_status}")
                else:
                    # АС одобрил хотя бы одного посетителя
                    new_status = schemas.RequestStatusEnum.APPROVED_AS.value
                    print(f"[DEBUG] Some approved by AS -> {new_status}")

                # Обновляем статус заявки
                old_status = request_obj.status
                request_obj.status = new_status
                db.add(request_obj)
                db.commit()
                db.refresh(request_obj)

                print(
                    f"[DEBUG] AS DIRECT: Request status updated from {old_status} to {request_obj.status}"
                )

                create_audit_log(
                    db,
                    actor_id=approver.id,
                    entity="request",
                    entity_id=request_id,
                    action="AUTO_STATUS_UPDATE_AS_DIRECT",
                    data={
                        "new_status": new_status,
                        "as_approved_count": as_approved,
                        "total_count": total_persons,
                        "flow": "direct_to_as",
                    },
                )
            else:
                print(
                    f"[DEBUG] Not all persons processed yet: {as_processed}/{total_persons}"
                )

        elif request_obj.status == schemas.RequestStatusEnum.APPROVED_USB.value:
            print(f"[DEBUG] Processing APPROVED_USB flow (via USB)")
            # Заявка пришла через УСБ

            # ПРАВИЛЬНЫЙ подсчет: УСБ одобрил тех, кто сейчас APPROVED_USB или уже обработан АС
            # Получаем количество посетителей, которых УСБ изначально одобрил
            usb_originally_approved = (
                db.query(func.count(models.RequestPerson.id))
                .filter(
                    models.RequestPerson.request_id == request_id,
                    models.RequestPerson.status.in_(
                        [
                            models.RequestPersonStatus.APPROVED_USB,  # Еще не обработаны АС
                            models.RequestPersonStatus.APPROVED_AS,  # Одобрены АС
                            models.RequestPersonStatus.DECLINED_AS,  # Отклонены АС
                        ]
                    ),
                )
                .scalar()
                or 0
            )

            # Получаем количество посетителей, отклоненных УСБ (они не должны обрабатываться АС)
            usb_declined_persons = (
                db.query(func.count(models.RequestPerson.id))
                .filter(
                    models.RequestPerson.request_id == request_id,
                    models.RequestPerson.status
                    == models.RequestPersonStatus.DECLINED_USB,
                )
                .scalar()
                or 0
            )

            # Получаем количество посетителей, обработанных АС
            as_processed = (
                db.query(func.count(models.RequestPerson.id))
                .filter(
                    models.RequestPerson.request_id == request_id,
                    models.RequestPerson.status.in_(
                        [
                            models.RequestPersonStatus.APPROVED_AS,
                            models.RequestPersonStatus.DECLINED_AS,
                        ]
                    ),
                )
                .scalar()
                or 0
            )

            print(
                f"[DEBUG] USB originally approved: {usb_originally_approved}, USB declined: {usb_declined_persons}"
            )
            print(f"[DEBUG] AS processed: {as_processed}")
            print(
                f"[DEBUG] Expected: AS should process {usb_originally_approved} persons"
            )

            # АС должен обработать всех изначально одобренных УСБ посетителей
            # Но статус заявки обновляется, когда АС принял окончательное решение

            # Проверяем, есть ли решения АС
            if as_processed > 0:
                print(f"[DEBUG] AS has processed some persons - checking final status")

                # Количество одобренных АС
                as_approved = (
                    db.query(func.count(models.RequestPerson.id))
                    .filter(
                        models.RequestPerson.request_id == request_id,
                        models.RequestPerson.status
                        == models.RequestPersonStatus.APPROVED_AS,
                    )
                    .scalar()
                    or 0
                )

                # Количество отклоненных АС
                as_declined = (
                    db.query(func.count(models.RequestPerson.id))
                    .filter(
                        models.RequestPerson.request_id == request_id,
                        models.RequestPerson.status
                        == models.RequestPersonStatus.DECLINED_AS,
                    )
                    .scalar()
                    or 0
                )

                print(f"[DEBUG] AS approved: {as_approved}, AS declined: {as_declined}")

                # Если АС обработал всех изначально одобренных УСБ посетителей
                if as_processed == usb_originally_approved:
                    print(
                        f"[DEBUG] All USB-originally-approved persons processed by AS - updating request status"
                    )

                    # Определяем новый статус заявки
                    if as_approved == 0:
                        # АС отклонил всех одобренных УСБ посетителей
                        new_status = schemas.RequestStatusEnum.DECLINED_AS.value
                        print(
                            f"[DEBUG] All USB-approved declined by AS -> {new_status}"
                        )
                    else:
                        # АС одобрил хотя бы одного посетителя
                        new_status = schemas.RequestStatusEnum.APPROVED_AS.value
                        print(
                            f"[DEBUG] Some USB-approved approved by AS -> {new_status}"
                        )

                    # Обновляем статус заявки
                    old_status = request_obj.status
                    request_obj.status = new_status
                    db.add(request_obj)
                    db.commit()
                    db.refresh(request_obj)

                    print(
                        f"[DEBUG] AS VIA USB: Request status updated from {old_status} to {request_obj.status}"
                    )

                    create_audit_log(
                        db,
                        actor_id=approver.id,
                        entity="request",
                        entity_id=request_id,
                        action="AUTO_STATUS_UPDATE_AS_AFTER_USB",
                        data={
                            "new_status": new_status,
                            "as_approved_count": as_approved,
                            "as_declined_count": as_declined,
                            "usb_originally_approved_count": usb_originally_approved,
                            "usb_declined_count": usb_declined_persons,
                            "flow": "via_usb",
                        },
                    )
                else:
                    print(
                        f"[DEBUG] AS still processing: {as_processed}/{usb_originally_approved} completed"
                    )
            else:
                print(f"[DEBUG] AS hasn't processed any USB-approved persons yet")
        else:
            print(
                f"[DEBUG] Request status {request_obj.status} not handled for AS processing"
            )
    else:
        print(
            f"[DEBUG] Approver role {approver.role.code if approver.role else 'NO_ROLE'} not handled"
        )

    print(f"[DEBUG] === _finalize_request_if_all_persons_processed finished ===\n")


# ------------- Request CRUD (Modified) -------------
# Role constants are now in constants.py and imported.
def create_request(
    db: Session, request_in: schemas.RequestCreate, creator: models.User
) -> models.Request:
    """
    Создание заявки с автоматической маршрутизацией на одобрение.

    Логика маршрутизации:
    - Долгосрочные заявки -> УСБ
    - Краткосрочные заявки с > 3 человек -> УСБ
    - Заявки с иностранными гражданами -> УСБ
    - Краткосрочные заявки с <= 3 человек (только граждане КЗ) -> АС
    """
    # 1. Проверка чёрного списка
    for person_schema in request_in.request_persons:
        if is_person_blacklisted(
            db,
            firstname=person_schema.firstname,
            lastname=person_schema.lastname,
            iin=person_schema.iin,
            doc_number=person_schema.doc_number,
            birth_date=person_schema.birth_date,
        ):
            full_name_for_log = f"{person_schema.firstname} {person_schema.lastname}"
            create_audit_log(
                db,
                actor_id=creator.id,
                entity="request_creation_attempt",
                entity_id=0,
                action="CREATE_FAIL_BLACKLISTED",
                data={
                    "message": f"Попытка создать заявку с человеком из чёрного списка: {full_name_for_log}"
                },
            )
            raise BlacklistedPersonException(
                f"{person_schema.firstname} {person_schema.lastname}"
            )

    # 2. Проверка прав на создание заявок
    if not creator.role or not creator.department:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Роль или подразделение пользователя не определены.",
        )

    is_admin = rbac.is_admin(creator)
    is_nach_departamenta = rbac.is_nach_departamenta(creator)
    is_nach_upravleniya = rbac.is_nach_upravleniya(creator)

    # Проверка типа заявки и прав
    if request_in.duration == RequestDuration.LONG_TERM:
        if not (is_nach_departamenta or is_admin):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Только начальники департаментов или администраторы могут создавать долгосрочные заявки.",
            )
    elif request_in.duration == RequestDuration.SHORT_TERM:
        if not (is_nach_upravleniya or is_nach_departamenta or is_admin):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Только начальники управлений, департаментов или администраторы могут создавать краткосрочные заявки.",
            )

        # Проверка продолжительности заявки
        if request_in.end_date < request_in.start_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Конечная дата не может быть раньше начальной даты.",
            )

        if request_in.end_date - request_in.start_date > timedelta(days=1):
            if request_in.duration != RequestDuration.LONG_TERM:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Если период заявки больше одного дня, необходимо выбрать тип 'Долгосрочная'.",
                )

        thirty_days_ago = datetime.utcnow() - timedelta(days=30)

        # Проверка по всем лицам, указанным в заявке
        for person_in in request_in.request_persons:
            if not person_in.iin:
                continue  # Пропустить, если ИИН не указан

            recent_requests_count = (
                db.query(func.count(models.Request.id))
                .join(models.RequestPerson)
                .filter(
                    models.RequestPerson.iin == person_in.iin,
                    models.Request.duration == RequestDuration.SHORT_TERM,
                    models.Request.created_at >= thirty_days_ago,
                )
                .scalar()
            )
            print(recent_requests_count, "количество заходов")

            if recent_requests_count >= 3:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Для ИИН {person_in.iin} превышен лимит разовых заявок за последние 30 дней. Подайте долгосрочную.",
                )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Неверный тип заявки."
        )

    # 3. Проверка наличия КПП
    if not request_in.checkpoint_ids:
        raise HTTPException(400, "Необходимо указать хотя бы один КПП")

    checkpoints = (
        db.query(models.Checkpoint)
        .filter(models.Checkpoint.id.in_(request_in.checkpoint_ids))
        .all()
    )
    if len(checkpoints) != len(request_in.checkpoint_ids):
        raise HTTPException(404, "Некоторые КПП не найдены")

    # 4. Определение начального статуса заявки на основе бизнес-логики
    # Проверка наличия иностранных граждан
    contains_foreign_citizen = any(
        p.nationality == models.NationalityType.FOREIGN
        for p in request_in.request_persons
    )

    # Определение маршрута согласно новым правилам
    if (
        request_in.duration == RequestDuration.LONG_TERM
        or len(request_in.request_persons) > 3
        or contains_foreign_citizen
    ):
        # Долгосрочные, больше 3 человек или есть иностранцы -> УСБ
        initial_status = schemas.RequestStatusEnum.PENDING_USB.value
    else:
        # Краткосрочные, <= 3 человек, все граждане КЗ -> АС
        initial_status = schemas.RequestStatusEnum.PENDING_AS.value

    # 5. Создание заявки с определенным статусом
    db_request = models.Request(
        creator_id=creator.id,
        status=initial_status,  # Используем вычисленный статус вместо DRAFT
        start_date=request_in.start_date,
        end_date=request_in.end_date,
        arrival_purpose=request_in.arrival_purpose,
        accompanying=request_in.accompanying,
        contacts_of_accompanying=request_in.contacts_of_accompanying,
        duration=request_in.duration.value,
    )
    db_request.checkpoints = checkpoints
    db.add(db_request)
    db.commit()

    # 6. Создание персон в заявке
    for person_schema in request_in.request_persons:
        # Определение маршрута согласно новым правилам
        if (
            request_in.duration == RequestDuration.LONG_TERM
            or len(request_in.request_persons) > 3
            or contains_foreign_citizen
        ):
            # Долгосрочные, больше 3 человек или есть иностранцы -> УСБ
            person_schema.status = schemas.RequestPersonStatusEnum.PENDING_USB.value
        else:
            # Краткосрочные, <= 3 человек, все граждане КЗ -> АС
            person_schema.status = schemas.RequestPersonStatusEnum.PENDING_AS.value

        person_model = models.RequestPerson(
            **person_schema.model_dump(), request_id=db_request.id
        )
        db.add(person_model)
    db.commit()
    db.flush()
    db.refresh(db_request)

    # 7. Журнал действий
    create_audit_log(
        db,
        actor_id=creator.id,
        entity="request",
        entity_id=db_request.id,
        action="CREATE_AND_SUBMIT",
        data={
            "status": db_request.status,
            "num_persons": len(db_request.request_persons),
            "route_reason": "auto_routed_on_creation",
        },
    )

    # 8. Создание уведомлений для соответствующих ролей
    if db_request.status == schemas.RequestStatusEnum.PENDING_USB.value:
        usb_users = (
            db.query(models.User)
            .join(models.Role)
            .filter(models.Role.code == constants.USB_ROLE_CODE)
            .all()
        )
        for usb_user in usb_users:
            create_notification(
                db,
                user_id=usb_user.id,
                message=f"Новая заявка {db_request.id} ожидает вашего рассмотрения (УСБ).",
                request_id=db_request.id,
            )
    elif db_request.status == schemas.RequestStatusEnum.PENDING_AS.value:
        as_users = (
            db.query(models.User)
            .join(models.Role)
            .filter(models.Role.code == constants.AS_ROLE_CODE)
            .all()
        )
        for as_user in as_users:
            create_notification(
                db,
                user_id=as_user.id,
                message=f"Новая заявка {db_request.id} ожидает вашего рассмотрения (АС).",
                request_id=db_request.id,
            )

    return db_request


def get_request(
    db: Session, request_id: int, user: models.User  # Добавили пользователя для RBAC
) -> Optional[models.Request]:
    # Сразу подгружаем все нужные связи
    request_obj = (
        db.query(models.Request)
        .options(
            selectinload(models.Request.creator).options(
                selectinload(models.User.role),
                selectinload(models.User.department),
            ),
            selectinload(models.Request.checkpoints),  # many-to-many
            selectinload(models.Request.request_persons),
            selectinload(models.Request.approvals).selectinload(
                models.Approval.approver
            ),
        )
        .filter(models.Request.id == request_id)
        .first()
    )

    # RBAC: проверяем право просмотра
    if request_obj and not rbac.can_user_view_request(db, user, request_obj):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this request",
        )

    # Если request_obj is None, он уходит дальше как None (404 обрабатывается в роутере)
    return request_obj


def get_department_descendant_ids(db: Session, department_id: int) -> List[int]:
    """
    Helper function to get a list of IDs for a department and all its descendants.
    Uses a recursive CTE for full hierarchy traversal (PostgreSQL syntax).
    """
    from sqlalchemy import text
    from fastapi import (
        status,
    )  # For HTTPException, though it might be better to raise custom errors here

    if not isinstance(department_id, int):
        # Log this or raise a more specific internal error type
        print(
            f"Warning: get_department_descendant_ids called with non-integer department_id: {department_id}"
        )
        return []

    # This CTE is for PostgreSQL.
    cte_query = text(
        """
        WITH RECURSIVE sub_departments AS (
            SELECT id FROM departments WHERE id = :dept_id
            UNION ALL
            SELECT d.id FROM departments d JOIN sub_departments sd ON d.parent_id = sd.id
        )
        SELECT id FROM sub_departments
    """
    )
    try:
        result = db.execute(cte_query, {"dept_id": department_id}).fetchall()
        return [row[0] for row in result]
    except Exception as e:
        print(
            f"Error executing CTE for department descendants (dept_id: {department_id}): {e}"
        )
        # Depending on application design, either raise the raw DB error, a custom app error,
        # or an HTTPException if this function is very close to the API layer.
        # For a CRUD function, raising a custom DataAccessError or similar might be best.
        # For now, re-raising as a generic server error if it happens.
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error retrieving department hierarchy.",
        )


def get_requests(
    db: Session,
    user: models.User,
    skip: int = 0,
    limit: int = 100,
    statuses: Optional[List[str]] = None,
    checkpoints: Optional[List[int]] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    visitor_name: Optional[str] = None,
) -> Union[list[Any], list[type[models.Request]]]:
    query = db.query(models.Request).options(
        selectinload(models.Request.creator).selectinload(models.User.role),
        selectinload(models.Request.creator).selectinload(models.User.department),
        selectinload(models.Request.checkpoints),
        selectinload(models.Request.request_persons),
    )

    # 1) Базовые фильтры видимости
    vf = rbac.get_request_filters_for_user(db, user)
    if not vf.get("is_unrestricted", False):
        conds = []

        # 1) Always let a creator see their own requests
        if "creator_id" in vf:
            conds.append(models.Request.creator_id == vf["creator_id"])

        # 2) Department/Division Heads: requests whose creator's department is in department_ids
        if "department_ids" in vf and vf["department_ids"]:
            conds.append(
                models.Request.creator.has(
                    models.User.department_id.in_(vf["department_ids"])
                )
            )

        # 3) Checkpoint Operators: requests at their checkpoint with allowed statuses
        if "checkpoint_id" in vf:
            conds.append(
                models.Request.checkpoints.any(
                    models.Checkpoint.id == vf["checkpoint_id"]
                )
                & models.Request.status.in_(vf.get("allowed_statuses", []))
            )

        if conds:
            query = query.filter(or_(*conds))
        else:
            # Если нет условий доступа, возвращаем пустой результат
            return []

    # 2) Явные фильтры из запроса
    if statuses:
        query = query.filter(models.Request.status.in_(statuses))

    if checkpoints:
        query = query.filter(
            models.Request.checkpoints.any(models.Checkpoint.id.in_(checkpoints))
        )

    if date_from:
        query = query.filter(models.Request.start_date >= date_from)

    if date_to:
        query = query.filter(models.Request.end_date <= date_to)

    if visitor_name:
        query = query.join(models.RequestPerson).filter(
            models.RequestPerson.firstname.ilike(f"%{visitor_name}%")
        )

    return (
        query.order_by(models.Request.created_at.desc()).offset(skip).limit(limit).all()
    )


def update_request_draft(
    db: Session,
    request_id: int,
    request_update: schemas.RequestUpdate,
    user: models.User,
) -> models.Request:
    from fastapi import (
        status as fastapi_status,
    )  # Local import for HTTPException status

    # Use the existing get_request which includes RBAC check
    db_request = get_request(db, request_id=request_id, user=user)
    if not db_request:
        # get_request would have raised 403 if not allowed, or this means 404
        raise ResourceNotFoundException("Request", request_id)

    if db_request.status != schemas.RequestStatusEnum.PENDING_USB.value:
        raise InvalidRequestStateException(db_request.status, "PENDING_USB")

    from . import rbac  # Import rbac module for creator check

    if not rbac.is_creator(user, db_request) and not rbac.is_admin(
        user
    ):  # Allow admin to edit drafts too
        raise HTTPException(
            status_code=fastapi_status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this request.",
        )

    update_data = request_update.model_dump(
        exclude_unset=True, exclude={"request_persons"}
    )
    changed_fields_log = {}

    for key, value in update_data.items():
        if getattr(db_request, key) != value:  # Check if value actually changed
            changed_fields_log[key] = {"old": getattr(db_request, key), "new": value}
            setattr(db_request, key, value)

    # Handle RequestPersons update (simple replacement: delete old, create new)
    if request_update.request_persons is not None:
        changed_fields_log["request_persons"] = (
            "updated"  # Simple log message for persons update
        )
        # Delete existing persons for this request
        db.query(models.RequestPerson).filter(
            models.RequestPerson.request_id == db_request.id
        ).delete(synchronize_session=False)
        # Add new persons
        for person_data in request_update.request_persons:
            db_person = models.RequestPerson(
                **person_data.model_dump(), request_id=db_request.id
            )
            db.add(db_person)

    if (
        changed_fields_log
    ):  # Only commit if actual changes occurred to request or persons
        db.add(db_request)  # Add db_request again in case it was modified
        db.commit()
        db.refresh(db_request)
        create_audit_log(
            db,
            actor_id=user.id,
            entity="request",
            entity_id=db_request.id,
            action="UPDATE_DRAFT",
            data=changed_fields_log,
        )
    return db_request


# --- USB Workflow Functions ---
def approve_request_usb(
    db: Session, request_id: int, approver: models.User
) -> models.Request:
    """
    Одобрение заявки пользователем с ролью УСБ.
    После одобрения УСБ заявка переходит к АС.
    """
    db_request = get_request(db, request_id, approver)
    if not db_request:
        raise ResourceNotFoundException("Request", request_id)

    allowed_request_statuses_for_usb = [
        schemas.RequestStatusEnum.PENDING_USB.value,
        schemas.RequestStatusEnum.APPROVED_USB.value,
        schemas.RequestStatusEnum.DECLINED_USB.value,
    ]

    if (
        rbac.is_usb(approver)
        and db_request.status not in allowed_request_statuses_for_usb
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Вы не являетесь сотрудником УСБ и статус заявки не совпадает с нужным!",
        )

    # Обновление статуса заявки
    db_request.status = schemas.RequestStatusEnum.APPROVED_USB.value

    # Сразу переводим на следующий этап - к АС
    db_request.status = schemas.RequestStatusEnum.PENDING_AS.value

    # Каскадное одобрение всех персон в заявке
    for person in db_request.request_persons:
        person.status = models.RequestPersonStatus.APPROVED_USB.value
        person.rejection_reason = None
        db.add(person)

    db.add(db_request)
    db.commit()
    db.refresh(db_request)

    create_audit_log(
        db,
        actor_id=approver.id,
        entity="request",
        entity_id=db_request.id,
        action="USB_APPROVE_ALL",
        data={"new_status": db_request.status},
    )

    # TODO: Уведомить пользователей с ролью АС
    as_users = (
        db.query(models.User)
        .join(models.Role)
        .filter(models.Role.code == constants.AS_ROLE_CODE)
        .all()
    )
    for as_user in as_users:
        create_notification(
            db,
            as_user.id,
            message=f"Заявка {db_request.id} одобрена УСБ и ожидает вашего рассмотрения.",
            request_id=db_request.id,
        )

    return db_request


def decline_request_usb(
    db: Session, request_id: int, approver: models.User, reason: str
) -> models.Request:
    db_request = get_request(db, request_id, approver)
    if not db_request:
        raise ResourceNotFoundException("Request", request_id)

    allowed_request_statuses_for_usb = [
        schemas.RequestStatusEnum.PENDING_USB.value,
        schemas.RequestStatusEnum.APPROVED_USB.value,
        schemas.RequestStatusEnum.DECLINED_USB.value,
    ]

    if (
        rbac.is_usb(approver)
        and db_request.status not in allowed_request_statuses_for_usb
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Вы не являетесь сотрудником УСБ и статус заявки не совпадает с нужным!",
        )

    if not reason or len(reason.strip()) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Rejection reason is required for declining the request.",
        )

    db_request.status = schemas.RequestStatusEnum.DECLINED_USB.value

    # Cascade rejection to all persons
    cascade_rejection_reason = f"Main request declined by USB: {reason}"
    for person in db_request.request_persons:
        person.status = models.RequestPersonStatus.DECLINED_USB.value
        person.rejection_reason = cascade_rejection_reason
        db.add(person)

    db.add(db_request)
    db.commit()
    db.refresh(db_request)
    create_audit_log(
        db,
        actor_id=approver.id,
        entity="request",
        entity_id=db_request.id,
        action="USB_DECLINE_ALL",
        data={"new_status": db_request.status, "reason": reason},
    )
    # TODO: Notify creator about rejection.
    return db_request


# --- AS Workflow Functions ---
def approve_request_as(
    db: Session, request_id: int, approver: models.User
) -> models.Request:
    """
    Одобрение заявки пользователем с ролью АС.
    Это финальное одобрение, после которого заявка становится доступна для КПП.
    """
    db_request = get_request(db, request_id, approver)
    if not db_request:
        raise ResourceNotFoundException("Request", request_id)

    # АС может одобрять заявки в статусе PENDING_AS (прямые или после УСБ)
    allowed_request_statuses_for_as = [
        schemas.RequestStatusEnum.PENDING_AS.value,
        schemas.RequestStatusEnum.APPROVED_AS.value,
        schemas.RequestStatusEnum.DECLINED_AS.value,
    ]

    if (
        rbac.is_as(approver)
        and db_request.status not in allowed_request_statuses_for_as
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Вы не являетесь сотрудником АС и статус заявки не совпадает с нужным!",
        )

    # Запретить АС работать с заявками, полностью отклоненными УСБ
    if db_request.status == schemas.RequestStatusEnum.DECLINED_USB.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Невозможно одобрить заявку, отклоненную УСБ!",
        )

    # Финальное одобрение
    db_request.status = schemas.RequestStatusEnum.APPROVED_AS.value

    # Каскадное одобрение только тех посетителей, которые не были отклонены УСБ или АС
    for person in db_request.request_persons:
        # АС может одобрить только тех, кого не отклонили УСБ и не отклонил сам АС
        if (
            person.status != models.RequestPersonStatus.DECLINED_USB
            and person.status != models.RequestPersonStatus.DECLINED_AS
        ):
            person.status = models.RequestPersonStatus.APPROVED_AS
            person.rejection_reason = None
            db.add(person)

    db.add(db_request)
    db.commit()
    db.refresh(db_request)

    create_audit_log(
        db,
        actor_id=approver.id,
        entity="request",
        entity_id=db_request.id,
        action="AS_APPROVE_ALL",
        data={"new_status": db_request.status},
    )

    # Уведомить создателя заявки
    create_notification(
        db,
        user_id=db_request.creator_id,
        message=f"Ваша заявка {db_request.id} полностью одобрена и готова к использованию.",
        request_id=db_request.id,
    )

    # Уведомить КПП
    for checkpoint in db_request.checkpoints:
        kpp_role_code = f"{constants.KPP_ROLE_PREFIX}{checkpoint.id}"
        kpp_users = (
            db.query(models.User)
            .join(models.Role)
            .filter(models.Role.code == kpp_role_code)
            .all()
        )
        for kpp_user in kpp_users:
            create_notification(
                db,
                user_id=kpp_user.id,
                message=f"Новая одобренная заявка {db_request.id} для КПП {checkpoint.name}.",
                request_id=db_request.id,
            )

    return db_request


def decline_request_as(
    db: Session, request_id: int, approver: models.User, reason: str
) -> models.Request:
    db_request = get_request(db, request_id, approver)
    if not db_request:
        raise ResourceNotFoundException("Request", request_id)

    allowed_request_statuses_for_as = [
        schemas.RequestStatusEnum.PENDING_AS.value,
        schemas.RequestStatusEnum.APPROVED_AS.value,
        schemas.RequestStatusEnum.DECLINED_AS.value,
    ]

    if (
        rbac.is_as(approver)
        and db_request.status not in allowed_request_statuses_for_as
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Вы не являетесь сотрудником АС и статус заявки не совпадает с нужным!",
        )

    if not reason or len(reason.strip()) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Rejection reason is required for declining the request.",
        )

    db_request.status = schemas.RequestStatusEnum.DECLINED_AS.value

    cascade_rejection_reason = f"Main request declined by AS: {reason}"
    for person in db_request.request_persons:
        # Only reject persons who are not already rejected to avoid overwriting specific previous rejection reasons by USB.
        # Or, always overwrite if AS decline is final. For now, let's assume AS decline is final for all non-approved.
        if person.status != models.RequestPersonStatus.DECLINED_AS.value:
            person.status = models.RequestPersonStatus.DECLINED_AS.value
            person.rejection_reason = (
                cascade_rejection_reason  # Overwrites individual USB reasons if any
            )
        # If a person was individually approved by USB, and AS rejects the whole request, that person becomes rejected.
        db.add(person)

    db.add(db_request)
    db.commit()
    db.refresh(db_request)
    create_audit_log(
        db,
        actor_id=approver.id,
        entity="request",
        entity_id=db_request.id,
        action="AS_DECLINE_ALL",
        data={"new_status": db_request.status, "reason": reason},
    )
    # TODO: Notify creator about rejection.
    return db_request


def get_requests_for_checkpoint(
    db: Session, checkpoint_id: int, user: models.User
) -> list[type[models.Request]]:
    if not (user.role and user.role.code.startswith(constants.KPP_ROLE_PREFIX)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User not a checkpoint operator.",
        )

    # the statuses we care about
    approved_request_statuses = [
        schemas.RequestStatusEnum.APPROVED_AS.value,
        schemas.RequestStatusEnum.ISSUED.value,
    ]
    approved_person_status = schemas.RequestPersonStatusEnum.APPROVED_AS.value

    query = (
        db.query(models.Request)
        # join only through approved persons
        .join(models.Request.request_persons)
        .filter(
            # request must be for this checkpoint
            models.Request.checkpoints.any(models.Checkpoint.id == checkpoint_id),
            # request must be APPROVED_AS or ISSUED
            models.Request.status.in_(approved_request_statuses),
            # person must be APPROVED
            models.RequestPerson.status == approved_person_status,
        )
        # load that joined RequestPerson into the .request_persons collection
        .options(
            contains_eager(models.Request.request_persons),
            # still eager-load creator→role and checkpoints
            selectinload(models.Request.creator).selectinload(models.User.role),
            selectinload(models.Request.checkpoints),
        )
        # avoid duplicate Request rows if there are multiple approved persons
        .distinct()
        .order_by(models.Request.created_at.desc())
    )

    return query.all()


def delete_request(db: Session, db_request: models.Request) -> models.Request:
    db.query(models.Approval).filter(
        models.Approval.request_id == db_request.id
    ).delete(synchronize_session=False)
    db.query(models.RequestPerson).filter(
        models.RequestPerson.request_id == db_request.id
    ).delete(synchronize_session=False)
    # Need to delete visit logs associated with request_persons of this request, or handle via DB cascade.
    # For now, assuming cascade delete handles VisitLog or they are kept for history even if request is deleted.
    # If VisitLog needs manual deletion here, it'd be more complex:
    # for rp in db_request.request_persons:
    #     db.query(models.VisitLog).filter(models.VisitLog.request_person_id == rp.id).delete(synchronize_session=False)
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
    return (
        db.query(models.Approval)
        .options(
            selectinload(models.Approval.approver),
            selectinload(models.Approval.request),  # Careful with depth here
        )
        .filter(models.Approval.id == approval_id)
        .first()
    )


def get_approvals_for_request(
    db: Session, request_id: int, skip: int = 0, limit: int = 100
) -> list[type[models.Approval]]:
    return (
        db.query(models.Approval)
        .options(selectinload(models.Approval.approver))
        .filter(models.Approval.request_id == request_id)
        .order_by(models.Approval.timestamp.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def update_approval(
    db: Session, db_approval: models.Approval, approval_in: schemas.ApprovalUpdate
) -> models.Approval:
    update_data = approval_in.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_approval, key, value)
    db.add(db_approval)
    db.commit()
    db.refresh(db_approval)
    return db_approval


# ------------- AuditLog CRUD -------------
def create_audit_log(
    db: Session,
    actor_id: Optional[int],
    entity: str,
    entity_id: int,
    action: str,
    data: Optional[dict] = None,
) -> models.AuditLog:
    safe_data = jsonable_encoder(data)
    db_audit_log = models.AuditLog(
        actor_id=actor_id,
        entity=entity,
        entity_id=entity_id,
        action=action,
        data=safe_data,
        # timestamp is server_default in model
    )
    db.add(db_audit_log)
    db.commit()
    db.refresh(db_audit_log)
    return db_audit_log


def get_audit_logs(
    db: Session, skip: int = 0, limit: int = 100
) -> list[type[models.AuditLog]]:  # Basic getter
    return (
        db.query(models.AuditLog)
        .options(
            selectinload(models.AuditLog.actor).selectinload(
                models.User.department
            ),  # Load actor's department
            selectinload(models.AuditLog.actor).selectinload(models.User.role),
        )
        .order_by(models.AuditLog.timestamp.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_audit_logs_filtered(
    db: Session,
    current_user: models.User,  # For RBAC
    skip: int = 0,
    limit: int = 100,
    actor_department_id: Optional[
        int
    ] = None,  # Optional filter by specific department ID
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> list[type[models.AuditLog]]:

    query = (
        db.query(models.AuditLog)
        .join(models.AuditLog.actor, isouter=True)
        .join(models.User.department, isouter=True)
    )

    if not rbac.can_view_all_logs(current_user):
        allowed_actor_dept_ids = rbac.get_request_filters_for_user(db, current_user)
        if not allowed_actor_dept_ids:  # Empty list means cannot see any by this rule
            return []

        # If manager is trying to filter by a specific department, it must be within their scope
        if actor_department_id and actor_department_id not in allowed_actor_dept_ids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to view audit logs for the specified department.",
            )

        # Apply manager's scope
        query = query.filter(models.User.department_id.in_(allowed_actor_dept_ids))

    # If admin/usb/as provided a specific department_id to filter by
    if actor_department_id and rbac.can_view_all_logs(current_user):
        query = query.filter(models.User.department_id == actor_department_id)

    # Date filters
    if start_date:
        query = query.filter(models.AuditLog.timestamp >= start_date)
    if end_date:
        from datetime import timedelta

        query = query.filter(models.AuditLog.timestamp < (end_date + timedelta(days=1)))

    query = query.options(
        selectinload(models.AuditLog.actor).selectinload(models.User.department),
        selectinload(models.AuditLog.actor).selectinload(models.User.role),
    ).order_by(models.AuditLog.timestamp.desc())

    return query.offset(skip).limit(limit).all()


# ------------- Blacklist CRUD (Refactored) -------------
def create_blacklist_entry(
    db: Session, entry_in: schemas.BlackListCreate, adder_id: int
) -> models.BlackList:
    db_entry = models.BlackList(
        **entry_in.model_dump(
            exclude={"added_by"}
        ),  # Exclude added_by if present, as we're setting it from adder_id
        added_by=adder_id,
        # added_at is server_default
    )
    db.add(db_entry)
    db.commit()
    db.refresh(db_entry)
    create_audit_log(
        db,
        actor_id=adder_id,
        entity="blacklist",
        entity_id=db_entry.id,
        action="CREATE",
        data={"full_name": db_entry.firstname},
    )
    return db_entry


def get_blacklist_entry(db: Session, entry_id: int) -> Optional[models.BlackList]:
    return (
        db.query(models.BlackList)
        .options(
            selectinload(models.BlackList.added_by_user),
            selectinload(models.BlackList.removed_by_user),
        )
        .filter(models.BlackList.id == entry_id)
        .first()
    )


def get_blacklist_entries(
    db: Session, skip: int = 0, limit: int = 100, active_only: bool = False
) -> list[type[models.BlackList]]:
    query = db.query(models.BlackList).options(
        selectinload(models.BlackList.added_by_user),
        selectinload(models.BlackList.removed_by_user),
    )
    if active_only:
        query = query.filter(models.BlackList.status == "ACTIVE")
    return (
        query.order_by(models.BlackList.added_at.desc()).offset(skip).limit(limit).all()
    )


def update_blacklist_entry(
    db: Session,
    db_entry: models.BlackList,
    entry_in: schemas.BlackListUpdate,
    actor_id: Optional[int],
) -> models.BlackList:
    update_data = entry_in.model_dump(
        exclude_unset=True
    )  # For BlackListUpdate which is BaseModel
    changed_fields = {}
    for key, value in update_data.items():
        if hasattr(db_entry, key) and getattr(db_entry, key) != value:
            changed_fields[key] = {"old": getattr(db_entry, key), "new": value}
            setattr(db_entry, key, value)

    if changed_fields:
        db.add(db_entry)
        db.commit()
        db.refresh(db_entry)
        create_audit_log(
            db,
            actor_id=actor_id,
            entity="blacklist",
            entity_id=db_entry.id,
            action="UPDATE",
            data=changed_fields,
        )
    return db_entry


def is_person_blacklisted(
    db: Session,
    firstname: str,
    lastname: str,
    iin: Optional[str] = None,
    doc_number: Optional[str] = None,
    birth_date: Optional[date] = None,  # Added birth_date for more precise matching
) -> bool:
    query = db.query(models.BlackList).filter(
        models.BlackList.status == "ACTIVE",
        # Case-insensitive matching for names might be good (e.g., using .ilike() or func.lower())
        models.BlackList.firstname.ilike(firstname),
        models.BlackList.lastname.ilike(lastname),
    )
    if birth_date:  # Matching by birth_date significantly reduces false positives
        query = query.filter(models.BlackList.birth_date == birth_date)

    # Check IIN or doc_number
    conditions = []
    if iin:
        conditions.append(models.BlackList.iin == iin)
    if (
        doc_number
    ):  # This doc_number is for foreign nationals as per new model structure
        conditions.append(models.BlackList.doc_number == doc_number)

    if (
        not conditions
    ):  # If neither IIN nor doc_number is provided for check, rely on name+birthdate only.
        # This might be too broad depending on policy.
        # For now, if no identifier, we assume it's not a strong enough check to block.
        # Or, one of them MUST be present for a meaningful check.
        # Based on "Сверка по ФИО, номеру документа, ИИН", at least one ID should be there.
        return False  # Or raise an error if identifier is mandatory for blacklist check call.

    query = query.filter(or_(*conditions))

    return query.first() is not None


def remove_blacklist_entry(
    db: Session, entry_id: int, remover_id: int
) -> Optional[models.BlackList]:
    """Soft deletes a blacklist entry by marking it as INACTIVE."""
    db_entry = get_blacklist_entry(db, entry_id=entry_id)
    if not db_entry:
        return None  # Or raise HTTPException(404) if preferred by calling router

    if db_entry.status == "INACTIVE":  # Already processed
        return db_entry

    db_entry.status = "INACTIVE"
    db_entry.removed_by = remover_id
    from sqlalchemy.sql import func

    db_entry.removed_at = func.now()
    db.add(db_entry)
    db.commit()
    db.refresh(db_entry)
    create_audit_log(
        db,
        actor_id=remover_id,
        entity="blacklist",
        entity_id=db_entry.id,
        action="REMOVE",
        data={"full_name": db_entry.firstname, "status": "INACTIVE"},
    )
    return db_entry


def delete_blacklist_entry(
    db: Session, db_entry: models.BlackList, actor_id: Optional[int]
) -> models.BlackList:  # This is a hard delete
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
def create_notification(
    db: Session, user_id: int, message: str, request_id: Optional[int] = None
) -> models.Notification:
    db_notification = models.Notification(
        user_id=user_id,
        message=message,
        related_request_id=request_id,
        # timestamp and is_read have defaults in model
    )
    db.add(db_notification)
    db.commit()
    db.refresh(db_notification)
    return db_notification


def get_user_notifications(
    db: Session,
    user_id: int,
    read: Optional[bool] = None,
    skip: int = 0,
    limit: int = 20,
) -> list[type[models.Notification]]:
    query = db.query(models.Notification).filter(models.Notification.user_id == user_id)
    if read is not None:
        query = query.filter(models.Notification.is_read == read)
    return (
        query.order_by(models.Notification.timestamp.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def mark_notification_as_read(
    db: Session, notification_id: int, user_id: int
) -> Optional[type[models.Notification]]:
    db_notification = (
        db.query(models.Notification)
        .filter(
            models.Notification.id == notification_id,
            models.Notification.user_id
            == user_id,  # Ensure user can only mark their own
        )
        .first()
    )

    if db_notification:
        if not db_notification.is_read:
            db_notification.is_read = True
            db.commit()
            db.refresh(db_notification)
        return db_notification
    return None


# ------------- VisitLog CRUD -------------
def create_visit_log(db: Session, visit_log: schemas.VisitLogCreate) -> models.VisitLog:
    """
    Creates a new visit log entry.
    check_in_time is set automatically by the database (server_default=func.now()).
    """
    db_visit_log = models.VisitLog(
        request_id=visit_log.request_id,
        request_person_id=visit_log.request_person_id,
        checkpoint_id=visit_log.checkpoint_id,  # Added checkpoint_id
        check_in_time=visit_log.check_in_time,
    )
    db.add(db_visit_log)
    db.commit()
    db.refresh(db_visit_log)
    return db_visit_log


def get_visit_log(db: Session, visit_log_id: int) -> Optional[models.VisitLog]:
    """
    Retrieves a specific visit log entry by its ID.
    """
    return (
        db.query(models.VisitLog)
        .options(
            selectinload(
                models.VisitLog.request_person
            ),  # Eager load related request_person (visitor)
            selectinload(models.VisitLog.request)
            .selectinload(models.Request.creator)
            .selectinload(models.User.department),
        )
        .filter(models.VisitLog.id == visit_log_id)
        .first()
    )


def get_visit_logs_by_request_id(
    db: Session, request_id: int, skip: int = 0, limit: int = 100
) -> list[type[models.VisitLog]]:
    """
    Retrieves all visit log entries for a given request ID.
    """
    return (
        db.query(models.VisitLog)
        .options(
            selectinload(
                models.VisitLog.request_person
            ),  # Eager load related request_person (visitor)
            selectinload(models.VisitLog.request)
            .selectinload(models.Request.creator)
            .selectinload(models.User.department),
        )
        .filter(models.VisitLog.request_id == request_id)
        .order_by(models.VisitLog.check_in_time.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_visit_logs_by_request_person_id(
    db: Session, request_person_id: int, skip: int = 0, limit: int = 100
) -> list[type[models.VisitLog]]:
    """
    Retrieves all visit log entries for a given request_person_id.
    """
    return (
        db.query(models.VisitLog)
        .options(
            selectinload(models.VisitLog.request_person),
            selectinload(models.VisitLog.request),
        )
        .filter(models.VisitLog.request_person_id == request_person_id)
        .order_by(models.VisitLog.check_in_time.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_visit_logs_with_rbac(
    db: Session,
    current_user: models.User,
    skip: int = 0,
    limit: int = 100,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> Union[list[Any], list[type[models.VisitLog]]]:
    """
    Retrieves visit logs based on user's RBAC permissions, with optional date filtering and pagination.
    """
    # Базовый запрос с нужными JOIN для фильтрации
    query = (
        db.query(models.VisitLog)
        .join(models.VisitLog.request)
        .join(models.Request.creator)
    )

    # 1) Полный доступ
    if rbac.can_view_all_logs(current_user):
        pass

    # 2) KPP-роль — фильтрация по checkpoint_id и статусу Request
    elif current_user.role and current_user.role.code.startswith(
        constants.KPP_ROLE_PREFIX
    ):
        filters: Union[dict, None] = rbac.get_request_filters_for_user(db, current_user)
        # Ожидаем {'checkpoint_id': int, 'allowed_statuses': List[str]}
        if not filters or not isinstance(filters, dict):
            return []
        checkpoint_id = filters.get("checkpoint_id")
        allowed_statuses = filters.get("allowed_statuses", [])
        if checkpoint_id is None:
            return []
        query = query.filter(
            models.VisitLog.checkpoint_id == checkpoint_id,
            models.Request.status.in_(allowed_statuses),
        )

    # 3) Менеджер — по отделам создателей
    else:
        dept_filters = rbac.get_request_filters_for_user(db, current_user)
        # Ожидаем список ID или dict с ключом 'department_ids'
        if not dept_filters:
            return []
        if isinstance(dept_filters, dict):
            dept_ids = dept_filters.get("department_ids") or []
        else:
            dept_ids = dept_filters
        if not isinstance(dept_ids, list):
            dept_ids = [dept_ids]
        if not dept_ids:
            return []
        query = query.filter(models.User.department_id.in_(dept_ids))

    # Применяем фильтры по дате
    if start_date:
        start_dt = datetime.combine(start_date, time.min)
        query = query.filter(models.VisitLog.check_in_time >= start_dt)
    if end_date:
        end_dt = datetime.combine(end_date + timedelta(days=1), time.min)
        query = query.filter(models.VisitLog.check_in_time < end_dt)

    # Жадная загрузка для сериализации
    query = query.options(
        selectinload(models.VisitLog.request_person),
        selectinload(models.VisitLog.request)
        .selectinload(models.Request.creator)
        .selectinload(models.User.department),
        selectinload(models.VisitLog.request)
        .selectinload(models.Request.creator)
        .selectinload(models.User.role),
    )

    # Сортировка и пагинация
    return (
        query.order_by(models.VisitLog.check_in_time.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def update_visit_log(
    db: Session, visit_log_id: int, visit_log_update: schemas.VisitLogUpdate
) -> Optional[models.VisitLog]:
    """
    Updates a visit log entry, primarily for setting check_out_time.
    """
    db_visit_log = (
        db.query(models.VisitLog).filter(models.VisitLog.id == visit_log_id).first()
    )
    if db_visit_log:
        # Only update check_out_time if it's provided in the update schema
        if visit_log_update.check_out_time is not None:
            db_visit_log.check_out_time = visit_log_update.check_out_time
            db.add(db_visit_log)
            db.commit()
            db.refresh(db_visit_log)
    return db_visit_log


def cleanup_old_visit_logs(db: Session, retention_months: int = 18) -> int:
    """
    Удаляет старые записи журнала посещений.

    Args:
        db: Сессия базы данных
        retention_months: Количество месяцев для хранения (по умолчанию 18)

    Returns:
        Количество удалённых записей
    """
    cutoff_date = datetime.utcnow() - timedelta(days=retention_months * 30)

    # Подсчёт записей для удаления
    count = (
        db.query(models.VisitLog)
        .filter(models.VisitLog.check_in_time < cutoff_date)
        .count()
    )

    # Удаление старых записей
    db.query(models.VisitLog).filter(
        models.VisitLog.check_in_time < cutoff_date
    ).delete(synchronize_session=False)

    db.commit()

    # Создание записи в журнале действий
    create_audit_log(
        db,
        actor_id=None,  # Системное действие
        entity="visit_logs",
        entity_id=0,
        action="CLEANUP",
        data={
            "deleted_count": count,
            "cutoff_date": cutoff_date.isoformat(),
            "retention_months": retention_months,
        },
    )

    return count


def cleanup_old_audit_logs(db: Session, retention_months: int = 18) -> int:
    """
    Удаляет старые записи журнала действий.

    Args:
        db: Сессия базы данных
        retention_months: Количество месяцев для хранения (по умолчанию 18)

    Returns:
        Количество удалённых записей
    """
    cutoff_date = datetime.utcnow() - timedelta(days=retention_months * 30)

    # Подсчёт записей для
