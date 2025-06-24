"""
Custom exception handlers and error responses for better API consistency.
"""
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from pydantic import ValidationError
import logging
from typing import Union

logger = logging.getLogger(__name__)


class VisitorManagementException(Exception):
    """Base exception for visitor management system"""

    def __init__(self, message: str, status_code: int = 500, detail: dict = None):
        self.message = message
        self.status_code = status_code
        self.detail = detail or {}
        super().__init__(self.message)


class BlacklistedPersonException(VisitorManagementException):
    """Raised when trying to create request for blacklisted person"""

    def __init__(self, person_name: str, detail: dict = None):
        message = f"Person '{person_name}' is blacklisted and cannot be added to requests"
        super().__init__(message, status.HTTP_400_BAD_REQUEST, detail)


class InsufficientPermissionsException(VisitorManagementException):
    """Raised when user lacks required permissions"""

    def __init__(self, required_role: str = None, detail: dict = None):
        message = f"Insufficient permissions. Required role: {required_role}" if required_role else "Insufficient permissions"
        super().__init__(message, status.HTTP_403_FORBIDDEN, detail)


class InvalidRequestStateException(VisitorManagementException):
    """Raised when request is in invalid state for operation"""

    def __init__(self, current_state: str, required_state: str, detail: dict = None):
        message = f"Request in invalid state '{current_state}'. Required state: '{required_state}'"
        super().__init__(message, status.HTTP_400_BAD_REQUEST, detail)


class ResourceNotFoundException(VisitorManagementException):
    """Raised when requested resource is not found"""

    def __init__(self, resource_type: str, resource_id: Union[int, str], detail: dict = None):
        message = f"{resource_type} with ID '{resource_id}' not found"
        super().__init__(message, status.HTTP_404_NOT_FOUND, detail)


async def visitor_management_exception_handler(request: Request, exc: VisitorManagementException):
    """Handle custom visitor management exceptions"""
    logger.error(f"VisitorManagementException: {exc.message} - Detail: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": True,
            "message": exc.message,
            "detail": exc.detail,
            "type": exc.__class__.__name__
        }
    )


async def http_exception_handler(request: Request, exc: HTTPException):
    """Enhanced HTTP exception handler"""
    logger.warning(f"HTTPException: {exc.status_code} - {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": True,
            "message": exc.detail,
            "status_code": exc.status_code
        }
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors with detailed information"""
    logger.warning(f"Validation error: {exc.errors()}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": True,
            "message": "Validation error",
            "detail": exc.errors(),
            "type": "ValidationError"
        }
    )


async def integrity_error_handler(request: Request, exc: IntegrityError):
    """Handle database integrity errors"""
    logger.error(f"Database integrity error: {str(exc)}")

    # Common integrity error patterns
    error_message = "Database constraint violation"
    if "unique" in str(exc).lower():
        error_message = "A record with this information already exists"
    elif "foreign key" in str(exc).lower():
        error_message = "Referenced record does not exist"
    elif "not null" in str(exc).lower():
        error_message = "Required field is missing"

    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "error": True,
            "message": error_message,
            "type": "IntegrityError"
        }
    )


async def sqlalchemy_error_handler(request: Request, exc: SQLAlchemyError):
    """Handle general SQLAlchemy errors"""
    logger.error(f"Database error: {str(exc)}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": True,
            "message": "Database operation failed",
            "type": "DatabaseError"
        }
    )


async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected errors"""
    logger.error(f"Unexpected error: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": True,
            "message": "An unexpected error occurred",
            "type": "InternalError"
        }
    )


def setup_exception_handlers(app):
    """Setup all exception handlers for the FastAPI app"""
    app.add_exception_handler(VisitorManagementException, visitor_management_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(IntegrityError, integrity_error_handler)
    app.add_exception_handler(SQLAlchemyError, sqlalchemy_error_handler)
    app.add_exception_handler(Exception, general_exception_handler)