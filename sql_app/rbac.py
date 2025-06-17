from sqlalchemy.orm import Session
from . import models, schemas, crud
from .schemas import RequestStatusEnum

# Role Codes - define them centrally here or import from a constants file/schemas if they exist there
# For now, define here for clarity within rbac.py
ADMIN_ROLE_CODE = "admin"
SECURITY_OFFICER_ROLE_CODE = "security_officer"
DCS_OFFICER_ROLE_CODE = "dcs_officer"
ZD_DEPUTY_HEAD_ROLE_CODE = "zd_deputy_head"
DEPARTMENT_HEAD_ROLE_CODE = "department_head" # Assuming a generic code for all dept heads
DEPUTY_DEPARTMENT_HEAD_ROLE_CODE = "deputy_department_head"
DIVISION_MANAGER_ROLE_CODE = "division_manager" # Assuming a generic code
DEPUTY_DIVISION_MANAGER_ROLE_CODE = "deputy_division_manager"
CHECKPOINT_OPERATOR_ROLE_PREFIX = "KPP_"
EMPLOYEE_ROLE_CODE = "employee"

def is_admin(user: models.User) -> bool:
    return user.role and user.role.code == ADMIN_ROLE_CODE

def is_security_officer(user: models.User) -> bool:
    return user.role and user.role.code == SECURITY_OFFICER_ROLE_CODE

def is_dcs_officer(user: models.User) -> bool:
    return user.role and user.role.code == DCS_OFFICER_ROLE_CODE

def is_zd_deputy_head(user: models.User) -> bool:
    return user.role and user.role.code == ZD_DEPUTY_HEAD_ROLE_CODE


# --- RBAC Functions for Visit Log History ---

def can_user_access_visit_log_full_history(user: models.User) -> bool:
    """
    Checks if the user has a role that grants access to the full visit log history.
    (DCS Officer, Admin, ZD Deputy Head)
    """
    if not user.role:
        return False
    return user.role.code in [DCS_OFFICER_ROLE_CODE, ADMIN_ROLE_CODE, ZD_DEPUTY_HEAD_ROLE_CODE]

def can_user_access_visit_log_department_history(db: Session, user: models.User, request_creator_department_id: int) -> bool:
    """
    Checks if a Department Head or Deputy can access visit logs for requests
    created by users in their department or its sub-departments.
    """
    if not user.role or not user.department_id:
        return False

    if user.role.code not in [DEPARTMENT_HEAD_ROLE_CODE, DEPUTY_DEPARTMENT_HEAD_ROLE_CODE]:
        return False

    # User is a Department Head or Deputy. Check if request_creator_department_id is their own or a descendant.
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

    if user.role.code not in [DIVISION_MANAGER_ROLE_CODE, DEPUTY_DIVISION_MANAGER_ROLE_CODE]:
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

    # Department Head or Deputy: Can see requests from their own department and its children.
    if user.role.code in [DEPARTMENT_HEAD_ROLE_CODE, DEPUTY_DEPARTMENT_HEAD_ROLE_CODE]:
        # Check if request_creator.department_id is user.department_id or one of its children
        return is_user_in_department_or_children(db, request_creator, user.department_id)

    # Division Manager or Deputy: Can see requests from their own division.
    # Assumes their user.department_id points to a 'DIVISION' type department.
    if user.role.code in [DIVISION_MANAGER_ROLE_CODE, DEPUTY_DIVISION_MANAGER_ROLE_CODE]:
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
    if role and role.code.startswith(CHECKPOINT_OPERATOR_ROLE_PREFIX):
        # Из кода роли вычленяем ID КПП
        # Например, код "CP_OP_5" → префикс "CP_OP_" → цифра "5"
        cp_id_str = role.code[len(CHECKPOINT_OPERATOR_ROLE_PREFIX):]
        try:
            cp_id = int(cp_id_str)
        except ValueError:
            return False

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

    if role_code in [ADMIN_ROLE_CODE, DCS_OFFICER_ROLE_CODE, ZD_DEPUTY_HEAD_ROLE_CODE]:
        filters["is_unrestricted"] = True
    elif role_code in [DEPARTMENT_HEAD_ROLE_CODE, DEPUTY_DEPARTMENT_HEAD_ROLE_CODE]:
        if user.department_id:
            filters["department_ids"] = crud.get_department_descendant_ids(db, user.department_id)
        else: # Head of no department, can't see any based on this role
            filters["department_ids"] = [] # Empty list means no results based on this
    elif role_code in [DIVISION_MANAGER_ROLE_CODE, DEPUTY_DIVISION_MANAGER_ROLE_CODE]:
        if user.department_id and user.department and user.department.type == models.DepartmentType.DIVISION:
            filters["exact_department_id"] = user.department_id
        else: # Not a manager of a division
            filters["exact_department_id"] = -1 # Impossible ID to ensure no results
    # Операторы КПП
    elif role_code.startswith(CHECKPOINT_OPERATOR_ROLE_PREFIX):
        suffix = role_code[len(CHECKPOINT_OPERATOR_ROLE_PREFIX):]
        print(suffix)
        try:
            cp_id = int(suffix)
            filters["checkpoint_id"] = cp_id
            filters["target_statuses"] = [
                schemas.RequestStatusEnum.APPROVED_ZD.value,
                schemas.RequestStatusEnum.ISSUED.value,
            ]
        except ValueError:
            # невалидный код роли — никаких заявок
            filters["checkpoint_id"] = -1

    # остальные роли — свои заявки
    else:
        filters["creator_id"] = user.id

    return filters
