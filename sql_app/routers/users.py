import os
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from dotenv import load_dotenv

from .. import crud, models, schemas
from ..dependencies import get_db
from ..auth import decode_token as auth_decode_token
from ..auth_dependencies import (
    get_current_user,
    get_current_active_user,
    get_admin_user,
    get_security_officer_user,
    get_checkpoint_operator_user
)

load_dotenv()

SECRET_KEY = os.getenv('SECRET_KEY')
ALGORITHM = os.getenv('ALGORITHM')

if not SECRET_KEY or not ALGORITHM:
    print("CRITICAL WARNING in users.py: SECRET_KEY or ALGORITHM not found.")

router = APIRouter(    
    prefix="/users",
    tags=["Users"],
    responses={404: {"description": "Not found"}} # Changed from 418
)

# --- Real Authentication Logic (Locally Defined) ---
oauth2_scheme_users = OAuth2PasswordBearer(tokenUrl="/auth/token")

async def get_current_user_for_users_router(token: str = Depends(oauth2_scheme_users), db: Session = Depends(get_db)) -> models.User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials (users router)",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not SECRET_KEY or not ALGORITHM:
        print("ERROR in users.py: JWT Secret Key or Algorithm is not configured.")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Server auth configuration error (users router)")
    try:
        payload = auth_decode_token(token)
        user_id_from_token = payload.get("sub") # Expect 'sub' from token as per plan
        if user_id_from_token is None:
            user_id_from_token = payload.get("user_id") # Fallback for older tokens
            if user_id_from_token is None:
                raise credentials_exception
        user_id = int(user_id_from_token)
    except (JWTError, ValueError): # ValueError for int conversion
        raise credentials_exception

    user = crud.get_user(db, user_id=user_id)
    if user is None:
        raise credentials_exception
    return user

async def get_current_active_user_for_users_router(current_user: models.User = Depends(get_current_user_for_users_router)) -> models.User:
    if not current_user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user (users router)")
    return current_user
# --- End Real Authentication Logic ---

@router.get("/me", response_model=schemas.User)
async def read_users_me(current_user: models.User = Depends(get_current_active_user)):
    """
    Get current logged-in user.
    """
    return current_user

# Create User - Typically an admin task or open during initial setup.
# For now, leaving without auth as per original, but this usually needs protection.
@router.post("/", response_model=schemas.User, status_code=status.HTTP_201_CREATED) # Changed path from /users/
def create_user_endpoint(user: schemas.UserCreate, db: Session = Depends(get_db)): # Renamed, user param was schemas.UserCreate
    # Consider adding from ..auth import get_password_hash
    # hashed_password = get_password_hash(user.password) # Assuming UserCreate has plain password
    # db_user_data = schemas.UserCreateInternal(**user.model_dump(), hashed_password=hashed_password)
    # The current crud.create_user expects UserCreate which has hashed_password.
    # This implies hashing is done client-side or in a previous step if this is direct.
    # For robust API, server should hash.

    existing_user = crud.get_user_by_username(db, username=user.username) # Check by username
    if existing_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already registered")
    if user.email: # Check email if provided
        existing_email_user = crud.get_user_by_email(db, email=user.email)
        if existing_email_user:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    # Assuming user.hashed_password is provided in UserCreate schema as per current crud.create_user
    return crud.create_user(db, user)


@router.get("/", response_model=List[schemas.User]) # Changed path from /users/
async def read_users_endpoint( # Renamed
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user) # Added Auth
):
    # TODO: Add RBAC - e.g., only admins can list all users.
    # from .. import rbac
    # if not rbac.is_admin(current_user):
    #     raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to list users")
    users = crud.get_users(db, skip=skip, limit=limit)
    return users


@router.get("/{user_id}", response_model=schemas.User) # Changed path from /users_id/{user_id}
async def read_user_endpoint( # Renamed
    user_id: int,  # Changed to int
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user) # Added Auth
):
    # TODO: Add RBAC - admin or self can view.
    # from .. import rbac
    # if not (rbac.is_admin(current_user) or current_user.id == user_id):
    #    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to view this user")
    db_user = crud.get_user(db, user_id=user_id) # crud.get_user now used
    if db_user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return db_user

# The following endpoints are somewhat redundant or non-standard, will comment out for now
# but can be reinstated or refactored if specific use cases exist.

# @router.get("/delete_user/", response_model = bool) # Non-standard: GET for delete
# async def delete_user_endpoint(user_id: str, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
#     # TODO: RBAC, and use HTTP DELETE method
#     # db_user_to_delete = crud.get_user(db, user_id=int(user_id))
#     # if not db_user_to_delete: ...
#     # return crud.delete_user(db, db_user_to_delete)
#     raise HTTPException(status_code=501, detail="Deletion via GET not recommended; use HTTP DELETE /users/{user_id}")


# @router.get("/username/{username}/id", response_model=int) # Changed path for clarity
# async def get_user_id_by_username_endpoint(username: str, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
#     # TODO: RBAC - who needs this?
#     db_user = crud.get_user_by_username(db, username=username)
#     if db_user is None:
#         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
#     return db_user.id

# @router.get("/username/{username}", response_model=schemas.User) # Changed path from /users_username/
# async def read_user_by_username_endpoint(username: str, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
#     # TODO: RBAC
#     db_user = crud.get_user_by_username(db, username=username)
#     if db_user is None:
#         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
#     return db_user
