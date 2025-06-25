from sqlalchemy.orm import Session
from typing import List, Optional
from . import models, schemas, crud, constants

# Role codes are now imported from constants

def is_admin(user: models.User) -> bool:
    return user.role and user.role.code == constants.ADMIN_ROLE_CODE

def is_security_officer(user: models.User) -> bool: # Not used directly in this file, but good for consistency
    return user.role and user.role.code == constants.SECURITY_OFFICER_ROLE_CODE

def is_dcs_officer(user: models.User) -> bool:
    return user.role and user.role.code == constants.DCS_OFFICER_ROLE_CODE

def is_zd_deputy_head(user: models.User) -> bool:
    return user.role and user.role.code == constants.ZD_DEPUTY_HEAD_ROLE_CODE

def is_usb_officer(user: models.User) -> bool: # Renamed from is_usb for consistency
    return user.role and user.role.code == constants.USB_ROLE_CODE

def is_as_officer(user: models.User) -> bool: # Renamed from is_as for consistency
    return user.role and user.role.code == constants.AS_ROLE_CODE

def get_kpp_checkpoint_id_from_user(user: models.User) -> Optional[int]:
    """Extracts checkpoint ID from KPP user's role code (e.g., KPP-1 -> 1)."""
    if user.role and user.role.code and user.role.code.startswith(constants.KPP_ROLE_PREFIX):
        try:
            return int(user.role.code[len(constants.KPP_ROLE_PREFIX):])
        except ValueError:
            return None # Role code suffix is not a valid integer
    return None # Not a KPP role or role code is malformed


def get_allowed_creator_department_ids_for_visit_logs(db: Session, user: models.User) -> Optional[List[int]]:
    """
    Returns a list of department IDs whose requests' visit logs the user is allowed to see.
    Returns None if user can see all logs (handled by can_view_all_visit_logs).
    Returns an empty list if user is a manager but has no applicable departments or sub-departments.
    """
    if not user.role or not user.department_id:
        return [] # No role or department, cannot see any logs based on department hierarchy

    role_code = user.role.code
    user_dept_id = user.department_id

    # Department Heads, Deputy Dept Heads, Unit Heads, Deputy Unit Heads
    manager_roles = [
        constants.DEPARTMENT_HEAD_ROLE_CODE,
        constants.DEPUTY_DEPARTMENT_HEAD_ROLE_CODE,
        constants.UNIT_HEAD_ROLE_CODE,
        constants.DEPUTY_UNIT_HEAD_ROLE_CODE
    ]
    if role_code in manager_roles:
        # They see their own department and all its children.
        # For a Unit Head, if their unit (department) has no children, this will just be their unit's ID.
        return crud.get_department_descendant_ids(db, user_dept_id)

    # Division Managers and Deputies
    division_manager_roles = [
        constants.DIVISION_MANAGER_ROLE_CODE,
        constants.DEPUTY_DIVISION_MANAGER_ROLE_CODE
    ]
    if role_code in division_manager_roles:
        # They see their own division (which is a department) and all its children departments.
        if user.department and user.department.type == models.DepartmentType.DIVISION:
            return crud.get_department_descendant_ids(db, user_dept_id)
        return [] # Is a division manager but not linked to a department of type DIVISION - restricted

    return [] # Default for other roles not covered above (e.g., employee, KPP) - they don't see logs via this mechanism


# Kept for potential direct use, but get_allowed_creator_department_ids_for_visit_logs is preferred for the list view
def can_user_access_visit_log_department_history(db: Session, user: models.User, request_creator_department_id: int) -> bool:
    """
    Checks if a Department Head or Deputy can access visit logs for requests
    created by users in their department or its sub-departments.
    Also includes Unit Heads/Deputies for their specific unit (department).
    """
    if not user.role or not user.department_id:
        return False

    allowed_manager_roles = [
        constants.DEPARTMENT_HEAD_ROLE_CODE,
        constants.DEPUTY_DEPARTMENT_HEAD_ROLE_CODE,
        constants.UNIT_HEAD_ROLE_CODE,
        constants.DEPUTY_UNIT_HEAD_ROLE_CODE
    ]
    if user.role.code not in allowed_manager_roles:
        return False

    # User is a Department/Unit Head or Deputy. Check if request_creator_department_id is their own or a descendant.
    # For Unit heads, this usually means their own department_id only unless units can have sub-units.
    if user.department_id == request_creator_department_id:
        return True

    descendant_ids = crud.get_department_descendant_ids(db, user.department_id)
    return request_creator_department_id in descendant_ids

def can_user_access_visit_log_division_history(db: Session, user: models.User, request_creator_department_id: int) -> bool:
    """
    Checks if a Division Manager or Deputy can access visit logs for requests
    created by users in their division.
    """
    if not user.role or not user.department or not user.department.type or not user.department_id:
        return False

    allowed_division_roles = [
        constants.DIVISION_MANAGER_ROLE_CODE,
        constants.DEPUTY_DIVISION_MANAGER_ROLE_CODE
    ]
    if user.role.code not in allowed_division_roles:
        return False

    # User is a Division Manager or Deputy. Check if their department is a DIVISION.
    if user.department.type != models.DepartmentType.DIVISION:
        return False # Role implies they should be in a Division, but data says otherwise.

    # Check if the request_creator_department_id is the same as the Division Manager's department_id.
    # This assumes a Division Manager manages requests from their own specific department ID,
    # and that this department ID represents the entire division for this check.
    # If a division spans multiple "department" entries that roll up to it, this logic might need adjustment
    # or rely on get_department_descendant_ids if the division itself has sub-departments listed under it.
    # For now, direct match or descendants if the division itself is a parent department.
    if user.department_id == request_creator_department_id:
        return True

    # Additionally, if the division can have sub-departments and the manager oversees them for logs:
    # descendant_ids = crud.get_department_descendant_ids(db, user.department_id)
    # return request_creator_department_id in descendant_ids
    # Based on the prompt, simpler check: "request_creator_department_id is the same as the user's department_id"
    # The current implementation is direct match only. If broader (descendants) is needed, uncomment above.

    return False # Default to false if direct match fails.


def is_creator(user: models.User, resource: models.Request) -> bool: # Example with Request model
    """Checks if the user is the creator of the given resource."""
    return resource.creator_id == user.id

def is_user_in_department_or_children(db: Session, user: models.User, target_department_id: int) -> bool:
    """
    Checks if the user's department is the target_department_id or one of its children.
    Assumes user.department_id is their direct assignment.
    """
    if not user.department_id:
        return False
    if user.department_id == target_department_id:
        return True

    # Check if user's department is a child of target_department_id
    # This requires traversing up from user.department_id to its parent(s)
    # or traversing down from target_department_id to its children.
    # Using crud.get_department_descendant_ids is more efficient for the latter.
    descendant_ids = crud.get_department_descendant_ids(db, target_department_id)
    return user.department_id in descendant_ids

def can_view_request_based_on_role_and_department(db: Session, user: models.User, request_creator: models.User) -> bool:
    """
    Checks if a user can view a request based on their role and department relative to the request's creator.
    """
    if not user.role or not user.department_id or not request_creator.department_id:
        return False # User or creator not properly configured

    # Department Head or Deputy or Unit Head/Deputy: Can see requests from their own department and its children.
    department_manager_roles = [
        constants.DEPARTMENT_HEAD_ROLE_CODE,
        constants.DEPUTY_DEPARTMENT_HEAD_ROLE_CODE,
        constants.UNIT_HEAD_ROLE_CODE,
        constants.DEPUTY_UNIT_HEAD_ROLE_CODE
    ]
    if user.role.code in department_manager_roles:
        # Check if request_creator.department_id is user.department_id or one of its children
        return is_user_in_department_or_children(db, request_creator, user.department_id)

    # Division Manager or Deputy: Can see requests from their own division.
    # Assumes their user.department_id points to a 'DIVISION' type department.
    division_manager_roles = [
        constants.DIVISION_MANAGER_ROLE_CODE,
        constants.DEPUTY_DIVISION_MANAGER_ROLE_CODE
    ]
    if user.role.code in division_manager_roles:
        if user.department and user.department.type == models.DepartmentType.DIVISION: # Direct check on enum member
            # Check if request_creator.department_id is within this division (same department or child if division has sub-depts)
             return is_user_in_department_or_children(db, request_creator, user.department_id)
    return False


def can_user_view_request(
    db: Session,
    user: models.User,
    request: models.Request
) -> bool:
    if not user or not request:
        return False

    # 1. Admin, USB, AS see all requests
    if is_admin(user) or is_usb_officer(user) or is_as_officer(user):
        return True

    # 2. Creator sees their own request
    if is_creator(user, request):
        return True

    # 3. Managers (Nach. Departamenta, Nach. Upravleniya) see requests from their hierarchy
    if request.creator and can_view_request_based_on_role_and_department(db, user, request.creator):
        return True

    # 4. KPP users see requests for their checkpoint if status is APPROVED_AS
    role = user.role
    if role and role.code.startswith(constants.KPP_ROLE_PREFIX):
        kpp_checkpoint_id = get_kpp_checkpoint_id_from_user(user)
        if kpp_checkpoint_id is not None:
            # Check if the request is associated with the KPP user's checkpoint
            has_checkpoint_access = any(cp.id == kpp_checkpoint_id for cp in request.checkpoints)

            if has_checkpoint_access and request.status == schemas.RequestStatusEnum.APPROVED_AS.value:
                return True

    # Fallback: if none of the above, deny access
    return False


def get_allowed_actor_department_ids_for_audit_logs(db: Session, user: models.User) -> Optional[List[int]]:
    """
    Returns a list of department IDs for which the current user (e.g., a manager)
    can see audit logs created by actors from those departments.
    Returns None if no department-based restriction (e.g., for admin/usb/as who see all, handled by can_view_all_audit_logs).
    Returns an empty list if the user is a manager but has no applicable departments.
    """
    if not user.role or not user.department_id:
        return []

    # Using the same logic as for visit logs for managers seems appropriate initially.
    # This means managers see audit logs of actors from their department and sub-departments.
    # This assumes AuditLog.actor.department_id is the filter target.

    role_code = user.role.code
    user_dept_id = user.department_id

    manager_roles_for_dept_hierarchy = [
        constants.DEPARTMENT_HEAD_ROLE_CODE,
        constants.DEPUTY_DEPARTMENT_HEAD_ROLE_CODE,
        constants.UNIT_HEAD_ROLE_CODE,
        constants.DEPUTY_UNIT_HEAD_ROLE_CODE,
        constants.DIVISION_MANAGER_ROLE_CODE, # Division managers see their whole division
        constants.DEPUTY_DIVISION_MANAGER_ROLE_CODE
    ]
    if role_code in manager_roles_for_dept_hierarchy:
        # Ensure the department type matches for Division Managers if that's a strict rule
        if role_code in [constants.DIVISION_MANAGER_ROLE_CODE, constants.DEPUTY_DIVISION_MANAGER_ROLE_CODE]:
            if not (user.department and user.department.type == models.DepartmentType.DIVISION):
                return [] # Division manager not in a division type department
        return crud.get_department_descendant_ids(db, user_dept_id)

    return [] # Default for other roles: no department-specific view unless they can see all.


def is_nach_upravleniya(user: models.User) -> bool:
    """Проверка, является ли пользователь начальником управления"""
    return user.role and user.role.code == constants.NACH_UPRAVLENIYA_ROLE_CODE


def is_nach_departamenta(user: models.User) -> bool:
    """Проверка, является ли пользователь начальником департамента"""
    return user.role and user.role.code == constants.NACH_DEPARTAMENTA_ROLE_CODE


def is_usb(user: models.User) -> bool:
    """Проверка, является ли пользователь УСБ"""
    return user.role and user.role.code == constants.USB_ROLE_CODE


def is_as(user: models.User) -> bool:
    """Проверка, является ли пользователь АС"""
    return user.role and user.role.code == constants.AS_ROLE_CODE


def is_kpp(user: models.User) -> bool:
    """Проверка, является ли пользователь оператором КПП"""
    return user.role and user.role.code and user.role.code.startswith(constants.KPP_ROLE_PREFIX)


def get_kpp_number(user: models.User) -> Optional[int]:
    """Получить номер КПП из роли пользователя (например, из КПП-1 вернёт 1)"""
    if user.role and user.role.code and user.role.code.startswith(constants.KPP_ROLE_PREFIX):
        try:
            return int(user.role.code[len(constants.KPP_ROLE_PREFIX):])
        except ValueError:
            return None
    return None


# Обновите функцию can_view_all_visit_logs:
def can_view_all_visit_logs(user: models.User) -> bool:
    """
    Проверяет, может ли пользователь видеть весь журнал посещений.
    УСБ, АС и Админ видят всё.
    """
    if not user.role:
        return False
    return user.role.code in [
        constants.USB_ROLE_CODE,
        constants.AS_ROLE_CODE,
        constants.ADMIN_ROLE_CODE
    ]


# Обновите функцию can_view_all_audit_logs:
def can_view_all_audit_logs(user: models.User) -> bool:
    """
    Проверяет, может ли пользователь видеть все журналы действий.
    УСБ, АС и Админ видят всё.
    """
    if not user.role:
        return False
    return user.role.code in [
        constants.ADMIN_ROLE_CODE,
        constants.USB_ROLE_CODE,
        constants.AS_ROLE_CODE
    ]


# Обновите функцию get_request_visibility_filters_for_user:
def get_request_visibility_filters_for_user(db: Session, user: models.User) -> dict:
    """
    Определяет фильтры видимости заявок для пользователя согласно новым требованиям.
    """
    filters = {"is_unrestricted": False}
    if not user.role:
        filters["creator_id"] = user.id
        return filters

    role_code = user.role.code

    # УСБ, АС и Админ видят все заявки
    if role_code in [constants.ADMIN_ROLE_CODE, constants.USB_ROLE_CODE, constants.AS_ROLE_CODE]:
        filters["is_unrestricted"] = True

    # Начальники департаментов видят заявки своего департамента и подчинённых подразделений
    elif role_code == constants.NACH_DEPARTAMENTA_ROLE_CODE:
        if user.department_id:
            filters["department_ids"] = crud.get_department_descendant_ids(db, user.department_id)
        else:
            filters["department_ids"] = []

    # Начальники управлений видят заявки своего управления и подчинённых подразделений
    elif role_code == constants.NACH_UPRAVLENIYA_ROLE_CODE:
        if user.department_id:
            filters["department_ids"] = crud.get_department_descendant_ids(db, user.department_id)
        else:
            filters["department_ids"] = []

    # КПП видят только одобренные заявки для своего КПП
    elif role_code.startswith(constants.KPP_ROLE_PREFIX):
        kpp_number = get_kpp_number(user)
        if kpp_number is not None:
            filters["checkpoint_id"] = kpp_number
            filters["target_statuses"] = [
                schemas.RequestStatusEnum.APPROVED_AS.value,
                schemas.RequestStatusEnum.ISSUED.value
            ]
        else:
            filters["checkpoint_id"] = -1  # Невалидный ID

    # Обычные сотрудники видят только свои заявки
    else:
        filters["creator_id"] = user.id

    return filters
