import os
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Response
from fastapi.security import OAuth2PasswordBearer # Added
from jose import JWTError, jwt # Added
from sqlalchemy.orm import Session
from dotenv import load_dotenv

from .. import crud, models, schemas
from ..dependencies import get_db # Only get_db
from ..auth import decode_token as auth_decode_token # For JWT decoding

load_dotenv()

SECRET_KEY = os.getenv('SECRET_KEY')
ALGORITHM = os.getenv('ALGORITHM')

if not SECRET_KEY or not ALGORITHM:
    print("CRITICAL WARNING in blacklist.py: SECRET_KEY or ALGORITHM not found.")

router = APIRouter(
    prefix="/blacklist",
    tags=["Blacklist"],
    responses={404: {"description": "Not found"}},
)

# --- Real Authentication Logic (Locally Defined) ---
oauth2_scheme_bl = OAuth2PasswordBearer(tokenUrl="/auth/token") # Local scheme

async def get_current_user_for_bl_router(token: str = Depends(oauth2_scheme_bl), db: Session = Depends(get_db)) -> models.User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials (bl router)",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not SECRET_KEY or not ALGORITHM:
        print("ERROR in blacklist.py: JWT Secret Key or Algorithm is not configured.")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Server auth configuration error (bl router)")
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

async def get_current_active_user_for_bl_router(current_user: models.User = Depends(get_current_user_for_bl_router)) -> models.User:
    if not current_user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user (bl router)")
    return current_user

# Specific role check for Security Officer (can be expanded in Step 5 RBAC)
async def get_security_officer_user_local(current_user: models.User = Depends(get_current_active_user_for_bl_router)) -> models.User:
    allowed_roles = ["security_officer", "dcs_officer", "zd_deputy_head"]
    if not current_user.role or current_user.role.code not in allowed_roles: # Example role code
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User does not have Security Officer privileges")
    return current_user
# --- End Real Authentication Logic ---

# Specific role check for Security Officer (can be expanded in Step 5 RBAC)
async def get_security_officer_read_blacklist(current_user: models.User = Depends(get_current_active_user_for_bl_router)) -> models.User:
    allowed_roles = ["security_officer", "dcs_officer", "zd_deputy_head", "admin", "department_head", "deputy_department_head", "division_manager", "deputy_division_manager", "KPP_", "employee"]
    if not current_user.role or current_user.role.code not in allowed_roles: # Example role code
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User does not have Security Officer privileges")
    return current_user
# --- End Real Authentication Logic ---


@router.get("/", response_model=List[schemas.BlackList])
async def read_blacklist_entries(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_security_officer_read_blacklist)
):
    """
    Retrieve all blacklist entries.
    - Requires authentication (Security Officer).
    """
    # The crud.get_blacklist_entries can take active_only, skip, limit.
    # For now, returning all, as per original logic in this router.
    entries = crud.get_blacklist_entries(db, skip=skip, limit=limit, active_only=True)
    return entries


@router.get("/history", response_model=List[schemas.BlackList])
async def read_all_blacklist_entries(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_security_officer_read_blacklist)
):
    """
    Retrieve all blacklist entries.
    - Requires authentication (Security Officer).
    """
    # The crud.get_blacklist_entries can take active_only, skip, limit.
    # For now, returning all, as per original logic in this router.
    entries = crud.get_blacklist_entries(db, skip=skip, limit=limit, active_only=False)
    return entries


@router.post("/", response_model=schemas.BlackList, status_code=status.HTTP_201_CREATED)
async def create_blacklist_entry_endpoint(
    entry_in: schemas.BlackListCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_security_officer_user_local)
):
    """
    Create a new blacklist entry.
    - Requires authentication (Security Officer).
    - `added_by` in `entry_in` will be ignored; `current_user.id` is used by CRUD.
    """
    # crud.create_blacklist_entry now takes adder_id and handles audit.
    db_entry = crud.create_blacklist_entry(db=db, entry_in=entry_in, adder_id=current_user.id)
    return db_entry


@router.delete("/{blacklist_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_blacklist_entry_endpoint( # Renamed to match plan's intent (soft delete)
    blacklist_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_security_officer_user_local)
):
    """
    Deactivates a blacklist entry (soft delete by marking status=INACTIVE).
    - Requires authentication (Security Officer).
    """
    # crud.remove_blacklist_entry fetches the entry, checks if already inactive,
    # updates status, and audits. Returns the entry or None if not found.
    removed_entry = crud.remove_blacklist_entry(db=db, entry_id=blacklist_id, remover_id=current_user.id)
    if not removed_entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Blacklist entry not found to remove/deactivate.")
    # If already inactive, crud.remove_blacklist_entry returns it without error, which is fine.
    # Client gets 204, indicating the state is now "removed" or "inactive".
    return Response(status_code=status.HTTP_204_NO_CONTENT)
