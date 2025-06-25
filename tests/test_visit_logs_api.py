import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from sql_app import main, schemas, models # main for app, schemas for payloads, models for DB objects
from sql_app.constants import KPP_ROLE_PREFIX
from sql_app.dependencies import get_db # To override
# Assuming auth dependency is like requests.py:
from sql_app.routers.requests import get_current_active_user_for_req_router

# --- Test Client Setup ---
# Override get_db dependency for all API tests
@pytest.fixture
def db_session_mock_api(): # Renamed to avoid conflict if used in same file as other db mocks
    return MagicMock(spec=Session)

# This fixture will be used by app dependency overrides
def override_get_db():
    mock_db = MagicMock(spec=Session)
    # Configure mock methods for db as needed by tests, e.g. query, add, commit, refresh
    return mock_db

# Fixture for the TestClient
@pytest.fixture
def client(db_session_mock_api): # This client will use the overridden get_db
    main.app.dependency_overrides[get_db] = lambda: db_session_mock_api
    # If get_current_active_user is defined globally (e.g. in main or dependencies)
    # and needs to be mocked for all tests, do it here.
    # For per-test user mocking, it's done within the test function or a more specific fixture.
    yield TestClient(main.app)
    main.app.dependency_overrides.clear() # Clear overrides after tests


# --- Mock User and Auth ---
def mock_user_with_role(user_id, role_code, department_id=None, department_type=None, is_active=True):
    user = MagicMock(spec=models.User)
    user.id = user_id
    user.is_active = is_active
    user.role = MagicMock(spec=models.Role)
    user.role.code = role_code
    user.department_id = department_id
    user.department = None
    if department_id:
        user.department = MagicMock(spec=models.Department)
        user.department.id = department_id
        user.department.type = department_type
    return user

# --- API Tests ---

# == POST /requests/{request_id}/visits ==
def test_create_visit_log_success_admin(client, db_session_mock_api):
    request_id = 1
    visitor_user_id = 2
    admin_user = mock_user_with_role(100, ADMIN_ROLE_CODE)

    main.app.dependency_overrides[get_current_active_user_for_req_router] = lambda: admin_user

    # Mock crud.get_request to return a valid request
    mock_request_obj = MagicMock(spec=models.Request)
    mock_request_obj.id = request_id
    # ... other request attributes if needed by the endpoint logic before crud.create_visit_log
    db_session_mock_api.query(models.Request).options().filter().first.return_value = mock_request_obj # Simplistic mock for get_request

    # Mock crud.get_user for visitor validation
    mock_visitor_user = mock_user_with_role(visitor_user_id, "some_role") # Visitor's role doesn't matter here
    # This patching needs to be more specific if crud.get_user is called with different args for current_user vs visitor
    with patch('sql_app.crud.get_user', return_value=mock_visitor_user) as mock_get_user_crud:
        # Mock crud.create_visit_log
        created_log_schema = schemas.VisitLog(
            id=1, request_id=request_id, user_id=visitor_user_id,
            check_in_time=datetime.utcnow(), check_out_time=None,
            user=schemas.UserForVisitLog(id=visitor_user_id, username="visitor"), # Simplified
            request=schemas.RequestForVisitLog(id=request_id, status=schemas.RequestStatusEnum.DRAFT, start_date=datetime.today().date(), end_date=datetime.today().date()) # Simplified
        )
        with patch('sql_app.crud.create_visit_log', return_value=created_log_schema) as mock_create_log:
            response = client.post(
                f"/requests/{request_id}/visits",
                json={"request_id": request_id, "user_id": visitor_user_id, "check_out_time": None}
            )
            assert response.status_code == 201
            assert response.json()["request_id"] == request_id
            assert response.json()["user_id"] == visitor_user_id
            mock_create_log.assert_called_once()

    main.app.dependency_overrides.clear()


def test_create_visit_log_forbidden_employee(client, db_session_mock_api):
    request_id = 1
    employee_user = mock_user_with_role(101, EMPLOYEE_ROLE_CODE)
    main.app.dependency_overrides[get_current_active_user_for_req_router] = lambda: employee_user

    response = client.post(
        f"/requests/{request_id}/visits",
        json={"request_id": request_id, "user_id": 2, "check_out_time": None}
    )
    assert response.status_code == 403 # Forbidden
    main.app.dependency_overrides.clear()

# TODO: Add more tests for POST: request not found, visitor user not found, payload request_id mismatch

# == GET /requests/{request_id}/visits ==
@patch('sql_app.crud.get_request') # To control the returned request object
@patch('sql_app.rbac.can_user_access_visit_log_full_history', return_value=True) # Example: Admin access
@patch('sql_app.crud.get_visit_logs_by_request_id')
def test_get_visit_logs_full_history_access(
    mock_get_logs, mock_rbac_full, mock_crud_get_request, client, db_session_mock_api
):
    request_id = 1
    admin_user = mock_user_with_role(100, ADMIN_ROLE_CODE) # User that mock_rbac_full would allow
    main.app.dependency_overrides[get_current_active_user_for_req_router] = lambda: admin_user

    # Mock the request object returned by crud.get_request
    mock_db_request = MagicMock(spec=models.Request)
    mock_db_request.id = request_id
    mock_db_request.creator = mock_user_with_role(200, "some_role", department_id=10) # Creator info
    mock_crud_get_request.return_value = mock_db_request

    # Mock the logs returned by crud
    mock_log_list = [
        schemas.VisitLog(id=1, request_id=request_id, user_id=1, check_in_time=datetime.utcnow(), user=None, request=None),
        schemas.VisitLog(id=2, request_id=request_id, user_id=2, check_in_time=datetime.utcnow(), user=None, request=None)
    ]
    mock_get_logs.return_value = mock_log_list

    response = client.get(f"/requests/{request_id}/visits")

    assert response.status_code == 200
    assert len(response.json()) == 2
    mock_crud_get_request.assert_called_once_with(db_session_mock_api, request_id=request_id, user=admin_user)
    mock_rbac_full.assert_called_once_with(admin_user)
    mock_get_logs.assert_called_once_with(db=db_session_mock_api, request_id=request_id, skip=0, limit=100)

    # Detailed content check for the new fields
    response_data = response.json()
    assert len(response_data) > 0
    first_log_response = response_data[0]

    # Assuming the mock_log_list was constructed with models.VisitLog that would lead to this data
    # This part of the test needs the mock_get_logs to return data that, after serialization,
    # contains these fields. The current mock_log_list in the test is too simple.
    # Let's refine this test after defining a proper mock for get_visit_logs_by_request_id.
    # For now, this structure shows the intent.
    # assert first_log_response['request']['creator_full_name'] == "Test Creator Name"
    # assert first_log_response['request']['creator_department_name'] == "Test Department"
    # assert first_log_response['user']['full_name'] == "Test Visitor Name"

    main.app.dependency_overrides.clear()


def test_get_visit_logs_response_data_population(client, db_session_mock_api):
    request_id_val = 1
    admin_user = mock_user_with_role(user_id=100, role_code=ADMIN_ROLE_CODE)
    main.app.dependency_overrides[get_current_active_user_for_req_router] = lambda: admin_user

    # 1. Mock for db_request (used in RBAC and to get creator info)
    mock_creator_department = models.Department(id=30, name="Creator Test Department", type="DEPARTMENT")
    mock_creator_user = models.User(
        id=200, full_name="Test Creator Name",
        department_id=30, department=mock_creator_department,
        role=models.Role(id=5, code="some_creator_role", name="Creator Role") # Role needed for User model
    )
    mock_db_request_for_rbac = models.Request(
        id=request_id_val, creator_id=200, creator=mock_creator_user,
        status=schemas.RequestStatusEnum.DRAFT.value, # Add other required fields for Request model
        start_date=date.today(), end_date=date.today(),
        arrival_purpose="Test", accompanying="Test", contacts_of_accompanying="Test"
    )

    # 2. Mock for visitor user (part of VisitLog.user)
    mock_visitor = models.User(id=300, username="visitor1", full_name="Test Visitor Name", is_active=True, role_id=1) # role_id for User model

    # 3. Mock for the request associated with the visit_log (VisitLog.request)
    # This can be the same as mock_db_request_for_rbac or a simplified version if appropriate
    # For this test, we assume it's the same detailed request object.
    mock_request_in_visit_log = mock_db_request_for_rbac

    # 4. Mock for the VisitLog database object itself
    mock_db_visit_log_item = models.VisitLog(
        id=1,
        request_id=request_id_val,
        user_id=mock_visitor.id,
        check_in_time=datetime.utcnow(),
        check_out_time=None,
        request=mock_request_in_visit_log, # Nested model
        user=mock_visitor                 # Nested model
    )

    with patch('sql_app.crud.get_request', return_value=mock_db_request_for_rbac) as mock_get_req_call, \
         patch('sql_app.crud.get_visit_logs_by_request_id', return_value=[mock_db_visit_log_item]) as mock_get_visit_logs_call, \
         patch('sql_app.rbac.can_user_access_visit_log_full_history', return_value=True): # Grant access

        response = client.get(f"/requests/{request_id_val}/visits")

        assert response.status_code == 200
        response_json = response.json()
        assert len(response_json) == 1

        log_item = response_json[0]
        assert log_item["id"] == mock_db_visit_log_item.id

        # Verify nested request details
        assert log_item["request"] is not None
        assert log_item["request"]["id"] == mock_request_in_visit_log.id
        assert log_item["request"]["creator_full_name"] == "Test Creator Name"
        assert log_item["request"]["creator_department_name"] == "Creator Test Department"

        # Verify nested user (visitor) details
        assert log_item["user"] is not None
        assert log_item["user"]["id"] == mock_visitor.id
        assert log_item["user"]["username"] == "visitor1"
        assert log_item["user"]["full_name"] == "Test Visitor Name"

    main.app.dependency_overrides.clear()


# TODO: Add many more tests for GET /requests/{request_id}/visits covering:
# - Department history access (mock rbac.can_user_access_visit_log_department_history)
# - Division history access (mock rbac.can_user_access_visit_log_division_history)
# - Creator access
# - Checkpoint operator access (and specific CP operator if logic is refined)
# - No access for other roles / insufficient hierarchy
# - Request not found (mock crud.get_request to return None)
# - Request creator or department info being None

def test_get_visit_logs_forbidden(client, db_session_mock_api):
    request_id = 1
    unauthorized_user = mock_user_with_role(102, EMPLOYEE_ROLE_CODE, department_id=1) # Employee
    main.app.dependency_overrides[get_current_active_user_for_req_router] = lambda: unauthorized_user

    # Mock crud.get_request to return a request (user can see request but not logs)
    mock_db_request = MagicMock(spec=models.Request)
    mock_db_request.id = request_id
    mock_db_request.creator = mock_user_with_role(200, "some_creator_role", department_id=10) # Different department
    mock_db_request.creator_id = 200

    with patch('sql_app.crud.get_request', return_value=mock_db_request):
        # Mock all RBAC functions to return False for this user
        with patch('sql_app.rbac.can_user_access_visit_log_full_history', return_value=False), \
             patch('sql_app.rbac.can_user_access_visit_log_department_history', return_value=False), \
             patch('sql_app.rbac.can_user_access_visit_log_division_history', return_value=False):
            response = client.get(f"/requests/{request_id}/visits")
            assert response.status_code == 403
    main.app.dependency_overrides.clear()


# == PATCH /visits/{visit_log_id} ==
def test_update_visit_log_checkout_success_cp_operator(client, db_session_mock_api):
    visit_log_id = 1
    cp_op_user = mock_user_with_role(103, f"{KPP_ROLE_PREFIX}1")
    main.app.dependency_overrides[get_current_active_user_for_req_router] = lambda: cp_op_user # This auth is for /visits router

    # Mock crud.get_visit_log
    mock_existing_log = MagicMock(spec=models.VisitLog) # Simulate loaded SQLAlchemy model
    mock_existing_log.id = visit_log_id
    mock_existing_log.request_id = 10
    mock_existing_log.user_id = 20
    mock_existing_log.check_in_time = datetime.utcnow() - timedelta(hours=1)
    mock_existing_log.check_out_time = None # Ensure it's None before update

    # Mock crud.update_visit_log
    # It should return the updated SQLAlchemy model object
    updated_db_log = MagicMock(spec=models.VisitLog)
    updated_db_log.id = visit_log_id
    updated_db_log.request_id = 10
    updated_db_log.user_id = 20
    updated_db_log.check_in_time = mock_existing_log.check_in_time
    checkout_payload_dt = datetime.utcnow()
    # The crud.update_visit_log returns the model, which is then mapped by Pydantic in the response model
    # So, the return value of crud.update_visit_log should be a models.VisitLog instance

    with patch('sql_app.crud.get_visit_log', return_value=mock_existing_log) as mock_get_log, \
         patch('sql_app.crud.update_visit_log', return_value=updated_db_log) as mock_update_log:

        # Simulate that the updated_db_log has the new checkout time
        # This is what the response model will build from
        updated_db_log.check_out_time = checkout_payload_dt

        response = client.patch(
            f"/visits/{visit_log_id}", # Using the /visits prefix for this router
            json={"check_out_time": checkout_payload_dt.isoformat()}
        )
        assert response.status_code == 200
        # The response model (schemas.VisitLog) will serialize this.
        # Ensure it contains the updated check_out_time.
        # The exact format of datetime string in JSON response depends on FastAPI's JSON encoder.
        assert response.json()["check_out_time"] is not None
        assert response.json()["id"] == visit_log_id

        mock_get_log.assert_called_once_with(db_session_mock_api, visit_log_id=visit_log_id)
        # Check that update_visit_log was called with a schema object
        mock_update_log.assert_called_once()
        call_args = mock_update_log.call_args[1] # Get kwargs
        assert isinstance(call_args['visit_log_update'], schemas.VisitLogUpdate)
        assert call_args['visit_log_update'].check_out_time == checkout_payload_dt

    main.app.dependency_overrides.clear()


def test_update_visit_log_checkout_forbidden_employee(client, db_session_mock_api):
    visit_log_id = 1
    employee_user = mock_user_with_role(104, EMPLOYEE_ROLE_CODE)
    main.app.dependency_overrides[get_current_active_user_for_req_router] = lambda: employee_user

    response = client.patch(
        f"/visits/{visit_log_id}",
        json={"check_out_time": datetime.utcnow().isoformat()}
    )
    assert response.status_code == 403
    main.app.dependency_overrides.clear()

# TODO: Add more tests for PATCH: visit log not found, invalid payload (e.g. non-datetime string)
# Test that if check_out_time is not in payload, it's not updated (if that's the desired behavior).

# Remember to clear app.dependency_overrides[get_current_active_user_for_req_router]
# in each test or a fixture if it's set per test.
# The client fixture clears get_db override.
# The auth override for /visits router might need a different key if it uses a different auth function instance.
# For now, assuming get_current_active_user_for_req_router is reused or a similar one is mocked for /visits tests.
# If sql_app.routers.visits.get_current_active_user is distinct, that's what needs overriding for PATCH tests.
# The current code in visits.py imports:
# from .requests import get_current_active_user_for_req_router as get_current_active_user
# So, overriding get_current_active_user_for_req_router in main.app should affect both.
# This is fine for now.

# Final check for the test structure:
# - test_visit_logs_api.py uses TestClient
# - Mocks auth (get_current_active_user_for_req_router)
# - Mocks DB session (get_db)
# - Mocks CRUD functions called by API endpoints to isolate testing of API layer logic (auth, request/response handling, parameter passing)
# - Verifies status codes and response content (partially).
# - RBAC scenarios for GET /requests/{request_id}/visits are sketched out.
# - Basic success/failure for POST and PATCH are sketched out.
# More detailed assertions on response body and mock call arguments would be needed for full coverage.
