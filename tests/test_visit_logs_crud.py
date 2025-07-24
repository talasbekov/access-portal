import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime

from sqlalchemy.orm import Session

from sql_app import crud, models, schemas


@pytest.fixture
def db_session_mock():
    return MagicMock(spec=Session)


@pytest.fixture
def mock_visit_log_create_schema():
    return schemas.VisitLogCreate(
        request_id=1, user_id=1, check_out_time=None  # Visitor's user ID
    )


@pytest.fixture
def mock_db_visit_log():
    return models.VisitLog(
        id=1,
        request_id=1,
        user_id=1,
        check_in_time=datetime.utcnow(),
        check_out_time=None,
    )


def test_create_visit_log(db_session_mock, mock_visit_log_create_schema):
    db_visit_log_instance = models.VisitLog(
        request_id=mock_visit_log_create_schema.request_id,
        user_id=mock_visit_log_create_schema.user_id,
        check_out_time=mock_visit_log_create_schema.check_out_time,
        # check_in_time is expected to be set by server_default in model
    )
    # Ensure db.add, commit, refresh are called
    # The actual check_in_time is set by DB, so we can't easily assert its value here without DB interaction
    # We mainly test that the object is created with payload data and DB methods are called.

    created_log = crud.create_visit_log(
        db_session_mock, visit_log=mock_visit_log_create_schema
    )

    db_session_mock.add.assert_called_once()  # Check if add was called
    db_session_mock.commit.assert_called_once()
    db_session_mock.refresh.assert_called_once()

    assert created_log is not None
    assert created_log.request_id == mock_visit_log_create_schema.request_id
    assert created_log.user_id == mock_visit_log_create_schema.user_id
    # Cannot assert check_in_time here as it's a server_default value (func.now())
    # We'd need to inspect the object passed to db_session_mock.add if we want to be very specific about what's added before commit.


def test_get_visit_log(db_session_mock, mock_db_visit_log):
    visit_log_id = 1

    # Configure the query mock
    mock_query = db_session_mock.query.return_value
    mock_options = mock_query.options.return_value
    mock_filter = mock_options.filter.return_value
    mock_filter.first.return_value = mock_db_visit_log

    retrieved_log = crud.get_visit_log(db_session_mock, visit_log_id=visit_log_id)

    db_session_mock.query.assert_called_once_with(models.VisitLog)
    # options().filter().first() chain
    assert mock_filter.first.call_count == 1
    assert retrieved_log == mock_db_visit_log
    assert retrieved_log.id == visit_log_id


def test_get_visit_log_not_found(db_session_mock):
    visit_log_id = 99
    mock_query = db_session_mock.query.return_value
    mock_options = mock_query.options.return_value
    mock_filter = mock_options.filter.return_value
    mock_filter.first.return_value = None

    retrieved_log = crud.get_visit_log(db_session_mock, visit_log_id=visit_log_id)
    assert retrieved_log is None


def test_get_visit_logs_by_request_id(db_session_mock, mock_db_visit_log):
    request_id = 1
    expected_logs = [mock_db_visit_log]

    mock_query = db_session_mock.query.return_value
    mock_options = mock_query.options.return_value
    mock_filter = mock_options.filter.return_value
    mock_orderby = mock_filter.order_by.return_value
    mock_offset = mock_orderby.offset.return_value
    mock_offset.limit.return_value = expected_logs

    logs = crud.get_visit_logs_by_request_id(
        db_session_mock, request_id=request_id, skip=0, limit=10
    )

    db_session_mock.query.assert_called_once_with(models.VisitLog)
    assert logs == expected_logs
    assert logs[0].request_id == request_id


def test_update_visit_log_set_checkout(db_session_mock, mock_db_visit_log):
    visit_log_id = 1
    checkout_time = datetime.utcnow()
    update_schema = schemas.VisitLogUpdate(check_out_time=checkout_time)

    # Ensure the log to be updated is found
    mock_query = db_session_mock.query.return_value
    mock_filter = mock_query.filter.return_value
    mock_filter.first.return_value = mock_db_visit_log

    updated_log = crud.update_visit_log(
        db_session_mock, visit_log_id=visit_log_id, visit_log_update=update_schema
    )

    db_session_mock.add.assert_called_once_with(mock_db_visit_log)
    db_session_mock.commit.assert_called_once()
    db_session_mock.refresh.assert_called_once_with(mock_db_visit_log)

    assert updated_log is not None
    assert updated_log.check_out_time == checkout_time


def test_update_visit_log_not_found(db_session_mock):
    visit_log_id = 99
    update_schema = schemas.VisitLogUpdate(check_out_time=datetime.utcnow())

    mock_query = db_session_mock.query.return_value
    mock_filter = mock_query.filter.return_value
    mock_filter.first.return_value = None  # Simulate not found

    updated_log = crud.update_visit_log(
        db_session_mock, visit_log_id=visit_log_id, visit_log_update=update_schema
    )

    assert updated_log is None
    db_session_mock.add.assert_not_called()
    db_session_mock.commit.assert_not_called()
    db_session_mock.refresh.assert_not_called()


# More tests can be added for edge cases, e.g. update with check_out_time = None (if allowed by logic)
# or specific checks on the filter conditions.
# For create_visit_log, one might want to inspect the object passed to db_session_mock.add()
# to ensure its attributes are correctly set from the schema before the commit.
# For now, this covers the basic CRUD operations.
