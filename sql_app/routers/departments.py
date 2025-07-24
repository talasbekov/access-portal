import os
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer  # Added
from jose import JWTError, jwt  # Added
from sqlalchemy.orm import Session
from dotenv import load_dotenv

from .. import crud, models, schemas
from ..dependencies import get_db  # get_db is the only import from dependencies

# Removed: from ..dependencies import oauth2_scheme
from ..auth import decode_token as auth_decode_token  # For JWT decoding

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")

if not SECRET_KEY or not ALGORITHM:
    print("CRITICAL WARNING in departments.py: SECRET_KEY or ALGORITHM not found.")
    # Consider raising an error to prevent app startup without proper auth config

router = APIRouter(
    prefix="/departments",
    tags=["Departments"],
    responses={404: {"description": "Not found"}},
)

# --- Real Authentication Logic (Locally Defined) ---
oauth2_scheme_dept = OAuth2PasswordBearer(tokenUrl="/auth/token")  # Local scheme


async def get_current_user_for_dept_router(
    token: str = Depends(oauth2_scheme_dept), db: Session = Depends(get_db)
) -> models.User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials (dept router)",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not SECRET_KEY or not ALGORITHM:
        print("ERROR in departments.py: JWT Secret Key or Algorithm is not configured.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server auth configuration error (dept router)",
        )
    try:
        payload = auth_decode_token(
            token
        )  # Using imported decode_token from sql_app.auth
        user_id: int = payload.get("user_id")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = crud.get_user(db, user_id=user_id)
    if user is None:
        raise credentials_exception
    return user


async def get_current_active_user_for_dept_router(
    current_user: models.User = Depends(get_current_user_for_dept_router),
) -> models.User:
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user (dept router)",
        )
    return current_user


# --- End Real Authentication Logic ---


@router.get("/", response_model=List[schemas.Department])
async def read_departments(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(
        get_current_active_user_for_dept_router
    ),  # Using REAL local auth
):
    """
    Retrieve all departments.
    - Requires authentication (any authenticated user).
    - RBAC for specific department visibility can be added later if needed.
    """
    # Basic check: user is authenticated. More granular RBAC can be added in Step 5 if needed.
    print(f"User {current_user.username} (ID: {current_user.id}) fetching departments.")
    departments = crud.get_departments(db, skip=skip, limit=limit)
    return departments


@router.get("/{department_id}", response_model=schemas.Department)
async def read_department(
    department_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(
        get_current_active_user_for_dept_router
    ),  # Using REAL local auth
):
    """
    Retrieve a single department by ID.
    - Requires authentication.
    """
    print(f"User {current_user.username} fetching department ID: {department_id}.")
    db_department = crud.get_department(db, department_id=department_id)
    if db_department is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Department not found"
        )
    return db_department


# Example for a protected POST endpoint (if needed later)
# @router.post("/", response_model=schemas.Department, status_code=status.HTTP_201_CREATED)
# async def create_department_endpoint(
#     department: schemas.DepartmentCreate,
#     db: Session = Depends(get_db),
#     current_user: models.User = Depends(get_current_active_user_for_dept_router) # Uses REAL local auth
# ):
#     # Add role check here, e.g., only admin can create
#     # if not current_user.role or current_user.role.code != "admin":
#     #     raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to create departments")
#
#     db_department = crud.get_department_by_name(db, name=department.name)
#     if db_department:
#         raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Department with this name already exists")
#
#     new_dept = crud.create_department(db=db, department=department)
#     crud.create_audit_log(db, actor_id=current_user.id, entity="department", entity_id=new_dept.id, action="CREATE", data=department.model_dump())
#     return new_dept
