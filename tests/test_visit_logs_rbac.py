import pytest
from unittest.mock import MagicMock, patch

from sqlalchemy.orm import Session

from sql_app import (
    rbac,
    models,
    crud,
)  # Assuming crud is needed for get_department_descendant_ids
from sql_app.models import DepartmentType  # For setting department type

# --- Mock Objects & Fixtures ---


@pytest.fixture
def db_session_mock():
    return MagicMock(spec=Session)


@pytest.fixture
def mock_user_builder():
    """Factory fixture to create mock user objects."""

    def _builder(user_id, role_code, department_id=None, department_type=None):
        user = MagicMock(spec=models.User)
        user.id = user_id
        user.role = MagicMock(spec=models.Role)
        user.role.code = role_code

        user.department_id = department_id
        user.department = None
        if department_id:
            user.department = MagicMock(spec=models.Department)
            user.department.id = department_id
            user.department.type = department_type
        return user

    return _builder


# --- RBAC Role Codes (ensure they match those in rbac.py) ---
ADMIN_ROLE_CODE = "admin"
DCS_OFFICER_ROLE_CODE = "dcs_officer"
ZD_DEPUTY_HEAD_ROLE_CODE = "zd_deputy_head"
DEPARTMENT_HEAD_ROLE_CODE = "department_head"
DEPUTY_DEPARTMENT_HEAD_ROLE_CODE = "deputy_department_head"
DIVISION_MANAGER_ROLE_CODE = "division_manager"
DEPUTY_DIVISION_MANAGER_ROLE_CODE = "deputy_division_manager"
EMPLOYEE_ROLE_CODE = "employee"  # A generic role for no specific access

# --- Tests for can_user_access_visit_log_full_history ---


@pytest.mark.parametrize(
    "role_code, expected",
    [
        (ADMIN_ROLE_CODE, True),
        (DCS_OFFICER_ROLE_CODE, True),
        (ZD_DEPUTY_HEAD_ROLE_CODE, True),
        (DEPARTMENT_HEAD_ROLE_CODE, False),
        (EMPLOYEE_ROLE_CODE, False),
        (None, False),  # Test case for user with no role
    ],
)
def test_can_user_access_visit_log_full_history(mock_user_builder, role_code, expected):
    user = mock_user_builder(1, role_code)
    if role_code is None:  # Special handling for user with no role object
        user.role = None
    assert rbac.can_user_access_visit_log_full_history(user) == expected


# --- Tests for can_user_access_visit_log_department_history ---


def test_can_access_dept_history_is_dept_head_own_dept(
    db_session_mock, mock_user_builder
):
    user = mock_user_builder(1, DEPARTMENT_HEAD_ROLE_CODE, department_id=10)
    request_creator_dept_id = 10
    # No need to mock get_department_descendant_ids if it's direct match
    assert (
        rbac.can_user_access_visit_log_department_history(
            db_session_mock, user, request_creator_dept_id
        )
        == True
    )


@patch("sql_app.crud.get_department_descendant_ids")
def test_can_access_dept_history_is_dept_head_descendant_dept(
    mock_get_descendants, db_session_mock, mock_user_builder
):
    user = mock_user_builder(1, DEPARTMENT_HEAD_ROLE_CODE, department_id=10)
    request_creator_dept_id = 15
    mock_get_descendants.return_value = [10, 12, 15]  # Dept 15 is a descendant of 10

    assert (
        rbac.can_user_access_visit_log_department_history(
            db_session_mock, user, request_creator_dept_id
        )
        == True
    )
    mock_get_descendants.assert_called_once_with(db_session_mock, 10)


@patch("sql_app.crud.get_department_descendant_ids")
def test_can_access_dept_history_is_dept_head_unrelated_dept(
    mock_get_descendants, db_session_mock, mock_user_builder
):
    user = mock_user_builder(1, DEPUTY_DEPARTMENT_HEAD_ROLE_CODE, department_id=10)
    request_creator_dept_id = 20  # Unrelated department
    mock_get_descendants.return_value = [10, 12, 15]

    assert (
        rbac.can_user_access_visit_log_department_history(
            db_session_mock, user, request_creator_dept_id
        )
        == False
    )
    mock_get_descendants.assert_called_once_with(db_session_mock, 10)


def test_can_access_dept_history_not_dept_head(db_session_mock, mock_user_builder):
    user = mock_user_builder(
        1, ADMIN_ROLE_CODE, department_id=10
    )  # Admin, not dept head
    request_creator_dept_id = 10
    assert (
        rbac.can_user_access_visit_log_department_history(
            db_session_mock, user, request_creator_dept_id
        )
        == False
    )


def test_can_access_dept_history_no_user_dept(db_session_mock, mock_user_builder):
    user = mock_user_builder(
        1, DEPARTMENT_HEAD_ROLE_CODE, department_id=None
    )  # Dept head with no dept
    request_creator_dept_id = 10
    assert (
        rbac.can_user_access_visit_log_department_history(
            db_session_mock, user, request_creator_dept_id
        )
        == False
    )


# --- Tests for can_user_access_visit_log_division_history ---


def test_can_access_div_history_is_div_manager_own_div_dept(
    db_session_mock, mock_user_builder
):
    # User is Div Manager, their dept is type DIVISION, request from same dept
    user = mock_user_builder(
        1,
        DIVISION_MANAGER_ROLE_CODE,
        department_id=5,
        department_type=DepartmentType.DIVISION,
    )
    request_creator_dept_id = 5
    assert (
        rbac.can_user_access_visit_log_division_history(
            db_session_mock, user, request_creator_dept_id
        )
        == True
    )


def test_can_access_div_history_is_div_manager_dept_not_division(
    db_session_mock, mock_user_builder
):
    # User is Div Manager, but their dept is NOT type DIVISION
    user = mock_user_builder(
        1,
        DIVISION_MANAGER_ROLE_CODE,
        department_id=5,
        department_type=DepartmentType.DEPARTMENT,
    )
    request_creator_dept_id = 5
    assert (
        rbac.can_user_access_visit_log_division_history(
            db_session_mock, user, request_creator_dept_id
        )
        == False
    )


def test_can_access_div_history_is_div_manager_unrelated_dept(
    db_session_mock, mock_user_builder
):
    # User is Div Manager, their dept is DIVISION, but request from different dept
    user = mock_user_builder(
        1,
        DEPUTY_DIVISION_MANAGER_ROLE_CODE,
        department_id=5,
        department_type=DepartmentType.DIVISION,
    )
    request_creator_dept_id = 7
    # Assuming Division check does not use get_department_descendant_ids as per current rbac impl.
    assert (
        rbac.can_user_access_visit_log_division_history(
            db_session_mock, user, request_creator_dept_id
        )
        == False
    )


def test_can_access_div_history_not_div_manager(db_session_mock, mock_user_builder):
    user = mock_user_builder(
        1,
        DEPARTMENT_HEAD_ROLE_CODE,
        department_id=5,
        department_type=DepartmentType.DIVISION,
    )
    request_creator_dept_id = 5
    assert (
        rbac.can_user_access_visit_log_division_history(
            db_session_mock, user, request_creator_dept_id
        )
        == False
    )


def test_can_access_div_history_user_no_dept_details(
    db_session_mock, mock_user_builder
):
    user_no_dept = mock_user_builder(1, DIVISION_MANAGER_ROLE_CODE, department_id=None)
    user_no_dept.department = None  # Ensure department object is None
    request_creator_dept_id = 5
    assert (
        rbac.can_user_access_visit_log_division_history(
            db_session_mock, user_no_dept, request_creator_dept_id
        )
        == False
    )

    user_no_dept_type = mock_user_builder(
        1, DIVISION_MANAGER_ROLE_CODE, department_id=5, department_type=None
    )
    user_no_dept_type.department.type = None  # Ensure department type is None
    assert (
        rbac.can_user_access_visit_log_division_history(
            db_session_mock, user_no_dept_type, request_creator_dept_id
        )
        == False
    )


# Add more tests for edge cases, like when user.role is None for the latter two functions.
# Test with the commented out descendant check for division history if that logic gets activated.
# Ensure all paths in the RBAC functions are tested.
# For example, user.role being None should always result in False.
@pytest.mark.parametrize(
    "rbac_function_to_test",
    [
        rbac.can_user_access_visit_log_department_history,
        rbac.can_user_access_visit_log_division_history,
    ],
)
def test_rbac_functions_user_no_role(
    db_session_mock, mock_user_builder, rbac_function_to_test
):
    user_no_role = mock_user_builder(1, None, department_id=1)  # Role code is None
    user_no_role.role = None  # Ensure role object itself is None
    request_creator_dept_id = 1
    assert (
        rbac_function_to_test(db_session_mock, user_no_role, request_creator_dept_id)
        == False
    )
