from sqlalchemy.orm import Session
from typing import List, Optional
from . import models, schemas, crud, constants  # Import constants
from .schemas import RequestStatusEnum

# Role codes are now imported from constants

def is_admin(user: models.User) -> bool:
    return user.role and user.role.code == constants.ADMIN_ROLE_CODE

def is_security_officer(user: models.User) -> bool: # Not used directly in this file, but good for consistency
    return user.role and user.role.code == constants.SECURITY_OFFICER_ROLE_CODE

def is_dcs_officer(user: models.User) -> bool:
    return user.role and user.role.code == constants.DCS_OFFICER_ROLE_CODE

def is_zd_deputy_head(user: models.User) -> bool:
    return user.role and user.role.code == constants.ZD_DEPUTY_HEAD_ROLE_CODE


# --- RBAC Functions for Visit Log Viewing ---

def can_view_all_visit_logs(user: models.User) -> bool:
    """
    Checks if the user has a role that grants access to all visit logs.
    (DCS Officer, Admin, ZD Deputy Head)
    """
    if not user.role:
        return False
    return user.role.code in [
        constants.DCS_OFFICER_ROLE_CODE,
        constants.ADMIN_ROLE_CODE,
        constants.ZD_DEPUTY_HEAD_ROLE_CODE
    ]

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

    # 1. Админы, ДКС и зам.нач. ЗД видят всё
    if is_admin(user) or is_dcs_officer(user) or is_zd_deputy_head(user):
        return True

    # 2. Создатель видит свой запрос
    if is_creator(user, request):
        return True

    # 3. Руководители по департаменту/подразделению
    if request.creator and can_view_request_based_on_role_and_department(db, user, request.creator):
        return True

    # 4. Операторы КПП видят «свои» заявки со статусами APPROVED_ZD и ISSUED
    role = user.role
    if role and role.code.startswith(constants.CHECKPOINT_OPERATOR_ROLE_PREFIX):
        # Из кода роли вычленяем ID КПП
        # Например, код "checkpoint_operator_cp5" -> "5"
        cp_id_str = role.code[len(constants.CHECKPOINT_OPERATOR_ROLE_PREFIX):]
        try:
            cp_id = int(cp_id_str)
        except ValueError:
            return False # Invalid role code format

        # Проверяем, что в списке request.checkpoints есть нужный КПП
        has_checkpoint = any(cp.id == cp_id for cp in request.checkpoints)

        # И что статус запроса — либо APPROVED_ZD, либо ISSUED
        allowed_statuses = {
            RequestStatusEnum.APPROVED_ZD.value,
            RequestStatusEnum.ISSUED.value,
        }
        if has_checkpoint and request.status in allowed_statuses:
            return True

    # Во всех остальных случаях — отказ
    return False

# Visibility for listing requests (to be used in crud.get_requests query building)
# These functions help determine query filters rather than a boolean for a single item.
# So, this might be structured differently, e.g. returning a filter object or modifying the query directly.

def get_request_visibility_filters_for_user(db: Session, user: models.User) -> dict:
    """
    Determines the base filters for listing requests based on user role.
    Returns a dict of filters to be applied by CRUD:
    {
        "creator_id": user.id (optional),
        "department_ids": [id1, id2,...] (user's dept and its children - for dept heads),
        "exact_department_id": user.department_id (for division managers),
        "target_statuses": [status1, status2,...] (e.g. for CPs)
        "is_unrestricted": True (for admin, DCS, ZD - see all)
    }
    """
    filters = {"is_unrestricted": False}
    if not user.role: # No role, most restricted view (e.g., only own if that's a fallback)
        filters["creator_id"] = user.id
        return filters

    role_code = user.role.code

    if role_code in [constants.ADMIN_ROLE_CODE, constants.DCS_OFFICER_ROLE_CODE, constants.ZD_DEPUTY_HEAD_ROLE_CODE]:
        filters["is_unrestricted"] = True
    elif role_code in [constants.DEPARTMENT_HEAD_ROLE_CODE, constants.DEPUTY_DEPARTMENT_HEAD_ROLE_CODE, constants.UNIT_HEAD_ROLE_CODE, constants.DEPUTY_UNIT_HEAD_ROLE_CODE]:
        if user.department_id:
            # For unit heads, this will correctly give their specific unit's ID if units don't have children.
            # If units can have children and unit heads should see them, get_department_descendant_ids will handle it.
            filters["department_ids"] = crud.get_department_descendant_ids(db, user.department_id)
        else:
            filters["department_ids"] = []
    elif role_code in [constants.DIVISION_MANAGER_ROLE_CODE, constants.DEPUTY_DIVISION_MANAGER_ROLE_CODE]:
        if user.department_id and user.department and user.department.type == models.DepartmentType.DIVISION:
            # Division managers see requests from creators within their entire division,
            # so we need all department IDs under this division.
            filters["department_ids"] = crud.get_department_descendant_ids(db, user.department_id)
            # filters["exact_department_id"] = user.department_id # Old logic, changed to department_ids
        else:
            filters["department_ids"] = []
    elif role_code.startswith(constants.CHECKPOINT_OPERATOR_ROLE_PREFIX):
        suffix = role_code[len(constants.CHECKPOINT_OPERATOR_ROLE_PREFIX):]
        try:
            cp_id = int(suffix)
            filters["checkpoint_id"] = cp_id
            filters["target_statuses"] = [
                schemas.RequestStatusEnum.APPROVED_ZD.value,
                schemas.RequestStatusEnum.ISSUED.value,
            ]
        except ValueError:
            filters["checkpoint_id"] = -1 # Invalid role code

    # Fallback for other roles (e.g. EMPLOYEE_ROLE_CODE or any unhandled manager role)
    else:
        filters["creator_id"] = user.id

    return filters
