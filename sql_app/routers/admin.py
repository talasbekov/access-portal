from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Dict

from .. import crud, models, schemas
from ..dependencies import get_db
from ..auth_dependencies import get_admin_user
from ..constants import AUDIT_LOG_RETENTION_MONTHS

router = APIRouter(
    prefix="/admin",
    tags=["Admin"],
    responses={404: {"description": "Not found"}}
)


@router.post("/cleanup-logs", response_model=Dict[str, int])
async def cleanup_old_logs(
        retention_months: int = AUDIT_LOG_RETENTION_MONTHS,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_admin_user)
):
    """
    Очистка старых логов посещений и действий.
    Требует права администратора.

    Args:
        retention_months: Количество месяцев для хранения логов (по умолчанию 18)
    """
    if retention_months < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Период хранения должен быть не менее 1 месяца"
        )

    # Очистка логов посещений
    deleted_visit_logs = crud.cleanup_old_visit_logs(db, retention_months)

    # Очистка логов действий
    deleted_audit_logs = crud.cleanup_old_audit_logs(db, retention_months)

    return {
        "deleted_visit_logs": deleted_visit_logs,
        "deleted_audit_logs": deleted_audit_logs,
        "retention_months": retention_months
    }


@router.get("/system-stats", response_model=Dict[str, int])
async def get_system_statistics(
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_admin_user)
):
    """
    Получение статистики системы.
    Требует права администратора.
    """
    total_users = db.query(models.User).count()
    active_users = db.query(models.User).filter(models.User.is_active == True).count()
    total_requests = db.query(models.Request).count()
    pending_requests = db.query(models.Request).filter(
        models.Request.status.in_([
            schemas.RequestStatusEnum.PENDING_USB.value,
            schemas.RequestStatusEnum.PENDING_AS.value
        ])
    ).count()
    blacklist_entries = db.query(models.BlackList).filter(models.BlackList.status == 'ACTIVE').count()
    total_visits = db.query(models.VisitLog).count()

    return {
        "total_users": total_users,
        "active_users": active_users,
        "total_requests": total_requests,
        "pending_requests": pending_requests,
        "blacklist_entries": blacklist_entries,
        "total_visits": total_visits
    }
