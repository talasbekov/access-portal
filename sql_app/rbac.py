# sql_app/rbac.py
"""Централизованная система контроля доступа на основе ролей"""

from typing import List, Optional, Dict
from sqlalchemy.orm import Session
from . import models, schemas, constants


def is_admin(user: models.User) -> bool:
    """Проверка, является ли пользователь администратором"""
    return user.role and user.role.code == constants.ADMIN_ROLE_CODE


def is_usb(user: models.User) -> bool:
    """Проверка, является ли пользователь УСБ"""
    return user.role and user.role.code == constants.USB_ROLE_CODE


def is_as(user: models.User) -> bool:
    """Проверка, является ли пользователь АС"""
    return user.role and user.role.code == constants.AS_ROLE_CODE


def is_nach_departamenta(user: models.User) -> bool:
    """Проверка, является ли пользователь начальником департамента"""
    return user.role and user.role.code == constants.NACH_DEPARTAMENTA_ROLE_CODE


def is_nach_upravleniya(user: models.User) -> bool:
    """Проверка, является ли пользователь начальником управления"""
    return user.role and user.role.code == constants.NACH_UPRAVLENIYA_ROLE_CODE


def is_kpp(user: models.User) -> bool:
    """Проверка, является ли пользователь оператором КПП"""
    return user.role and user.role.code and user.role.code.startswith(constants.KPP_ROLE_PREFIX)


def get_kpp_number(user: models.User) -> Optional[int]:
    """Получить номер КПП из роли пользователя"""
    if is_kpp(user):
        try:
            return int(user.role.code[len(constants.KPP_ROLE_PREFIX):])
        except ValueError:
            return None
    return None


def can_create_request(user: models.User, duration: str) -> bool:
    """Проверка права создания заявки определенного типа"""
    if is_admin(user):
        return True

    if duration == "LONG_TERM":
        return is_nach_departamenta(user)
    elif duration == "SHORT_TERM":
        return is_nach_upravleniya(user) or is_nach_departamenta(user)

    return False


def can_approve_usb(user: models.User) -> bool:
    """Проверка права одобрения заявок на уровне УСБ"""
    return is_admin(user) or is_usb(user)


def can_approve_as(user: models.User) -> bool:
    """Проверка права одобрения заявок на уровне АС"""
    return is_admin(user) or is_as(user)


def can_manage_blacklist(user: models.User) -> bool:
    """Проверка права управления черным списком"""
    return user.role and user.role.code in [
        constants.ADMIN_ROLE_CODE,
        constants.USB_ROLE_CODE,
        constants.AS_ROLE_CODE
    ]


def can_view_all_requests(user: models.User) -> bool:
    """Проверка права просмотра всех заявок"""
    return user.role and user.role.code in [
        constants.ADMIN_ROLE_CODE,
        constants.USB_ROLE_CODE,
        constants.AS_ROLE_CODE
    ]


def can_view_all_logs(user: models.User) -> bool:
    """Проверка права просмотра всех логов"""
    return user.role and user.role.code in [
        constants.ADMIN_ROLE_CODE,
        constants.USB_ROLE_CODE,
        constants.AS_ROLE_CODE
    ]


def get_user_department_scope(db: Session, user: models.User) -> List[int]:
    """Получить список ID подразделений в зоне ответственности пользователя"""
    if not user.department_id:
        return []

    if is_nach_departamenta(user) or is_nach_upravleniya(user):
        from . import crud
        return crud.get_department_descendant_ids(db, user.department_id)

    return [user.department_id]


def get_request_filters_for_user(db: Session, user: models.User) -> Dict:
    """Получить фильтры для запросов заявок на основе роли пользователя"""
    filters = {}

    if can_view_all_requests(user):
        filters["unrestricted"] = True
        return filters

    # Начальники видят заявки своих подразделений
    if is_nach_departamenta(user) or is_nach_upravleniya(user):
        dept_ids = get_user_department_scope(db, user)
        if dept_ids:
            filters["creator_department_ids"] = dept_ids

    # КПП видят только одобренные заявки для своего КПП
    elif is_kpp(user):
        kpp_number = get_kpp_number(user)
        if kpp_number:
            filters["checkpoint_id"] = kpp_number
            filters["allowed_statuses"] = [
                constants.APPROVED_AS,
                constants.ISSUED
            ]

    # По умолчанию - только свои заявки
    else:
        filters["creator_id"] = user.id

    return filters


def can_user_check_in_visitor(user: models.User, request: models.Request) -> bool:
    """Проверка права регистрации входа посетителя"""
    if is_admin(user):
        return True

    if is_kpp(user):
        kpp_number = get_kpp_number(user)
        if kpp_number:
            # Проверяем, что заявка разрешает вход через КПП пользователя
            return any(cp.id == kpp_number for cp in request.checkpoints)

    return False


def can_user_view_request(db: Session, user: models.User, request: models.Request) -> bool:
    """Проверка права просмотра конкретной заявки"""
    # Админ, УСБ, АС видят все
    if can_view_all_requests(user):
        return True

    # Создатель видит свою заявку
    if request.creator_id == user.id:
        return True

    # Начальники видят заявки своих подразделений
    if user.department_id and request.creator and request.creator.department_id:
        from . import crud
        dept_ids = get_user_department_scope(db, user)
        if request.creator.department_id in dept_ids:
            return True

    # КПП видят одобренные заявки для своего КПП
    if is_kpp(user) and request.status in [constants.APPROVED_AS, constants.ISSUED]:
        kpp_number = get_kpp_number(user)
        if kpp_number:
            return any(cp.id == kpp_number for cp in request.checkpoints)

    return False