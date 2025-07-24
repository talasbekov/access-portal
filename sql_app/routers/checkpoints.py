import os
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer  # Added
from jose import JWTError, jwt  # Added
from sqlalchemy.orm import Session
from dotenv import load_dotenv

from .. import crud, models, schemas
from ..dependencies import get_db  # Only get_db
from ..auth import decode_token as auth_decode_token  # For JWT decoding
from ..constants import KPP_ROLE_PREFIX
from ..auth_dependencies import (
    get_current_user,
    get_current_active_user,
    get_admin_user,
    get_security_officer_user,
    get_checkpoint_operator_user,
)

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")

if not SECRET_KEY or not ALGORITHM:
    print("CRITICAL WARNING in checkpoints.py: SECRET_KEY or ALGORITHM not found.")

router = APIRouter(
    prefix="/checkpoints",
    tags=["Checkpoints"],
    responses={404: {"description": "Not found"}},
)

# --- Real Authentication Logic (Locally Defined) ---
oauth2_scheme_cp = OAuth2PasswordBearer(tokenUrl="/auth/token")  # Local scheme


async def get_current_user_for_cp_router(
    token: str = Depends(oauth2_scheme_cp), db: Session = Depends(get_db)
) -> models.User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials (cp router)",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not SECRET_KEY or not ALGORITHM:
        print("ERROR in checkpoints.py: JWT Secret Key or Algorithm is not configured.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server auth configuration error (cp router)",
        )
    try:
        payload = auth_decode_token(token)
        user_id: int = payload.get("user_id")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = crud.get_user(db, user_id=user_id)
    if user is None:
        raise credentials_exception
    return user


async def get_current_active_user_for_cp_router(
    current_user: models.User = Depends(get_current_user_for_cp_router),
) -> models.User:
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user (cp router)"
        )
    return current_user


# Specific role check for Checkpoint Operator
async def get_checkpoint_operator_user_local(
    current_user: models.User = Depends(get_current_active_user_for_cp_router),
) -> models.User:
    if not current_user.role or not current_user.role.code.startswith(KPP_ROLE_PREFIX):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="У пользователя нет привилегий оператора КПП",
        )
    return current_user


# --- End Real Authentication Logic ---


@router.get("/cp/requests", response_model=List[schemas.Request])
async def read_checkpoint_requests(
    skip: int = 0,
    limit: int = 100,
    status_filter: Optional[schemas.RequestStatusEnum] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_checkpoint_operator_user),
):
    """
    Retrieve requests for a specific checkpoint relevant for the operator.
    - Requires authentication (Checkpoint Operator).
    - RBAC for *specific* checkpoint access is partially handled by get_checkpoint_operator_user_local
      and further refined by crud.get_requests_for_checkpoint if needed.
    """
    prefix = KPP_ROLE_PREFIX  # "KPP_"
    suffix = current_user.role.code[len(prefix) :]
    try:
        cp_id = int(suffix)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Невалидный код роли оператора КПП",
        )

    # The get_checkpoint_operator_user_local dependency already performs a basic check
    # that the user has a checkpoint operator role.
    # More specific RBAC (e.g., this user for this specific cp_id) would be handled here
    # or ideally within a more specific dependency if the cp_id from path could be passed to it.
    # For now, crud.get_requests_for_checkpoint will fetch requests for the given cp_id.

    # Note: status_filter is not directly used here as crud.get_requests_for_checkpoint
    # has its own fixed status filtering logic (APPROVED_ZD, ISSUED).
    # If dynamic status filtering is needed for this endpoint, crud function needs adjustment.
    if status_filter:
        print(
            f"Note: status_filter ('{status_filter.value}') provided but this endpoint uses fixed statuses by default for checkpoint operators."
        )
        # Potentially, could pass status_filter to crud function if it's designed to override default statuses.

    print(
        f"User {current_user.username} (Role: {current_user.role.code if current_user.role else 'None'}) fetching requests for checkpoint ID: {cp_id}."
    )

    requests_list = crud.get_requests_for_checkpoint(
        db,
        checkpoint_id=cp_id,
        user=current_user,  # Pass current_user for any further RBAC within CRUD if needed
    )
    # crud.get_requests_for_checkpoint should ideally handle skip/limit if they are needed.
    # For now, assuming it returns all relevant requests and client-side pagination or a more complex
    # CRUD function would handle more advanced pagination.
    # If skip/limit are essential here, the CRUD function needs to accept them.
    # Applying basic slicing if crud function doesn't support skip/limit:
    # total_requests = len(requests_list)
    # return requests_list[skip : skip + limit]
    return requests_list
