import os
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Response
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from dotenv import load_dotenv

from .. import crud, models, schemas
from ..dependencies import get_db
from ..auth import decode_token as auth_decode_token
from ..rbac import ADMIN_ROLE_CODE # Import admin role code

load_dotenv()

SECRET_KEY = os.getenv('SECRET_KEY')
ALGORITHM = os.getenv('ALGORITHM')

if not SECRET_KEY or not ALGORITHM:
    print("CRITICAL WARNING in role.py: SECRET_KEY or ALGORITHM not found.")

router = APIRouter(
    prefix="/roles",
    tags=["Roles"],
    responses={
        404: {"description": "Not found"},
        403: {"description": "Operation not permitted"} # Added for RBAC
    }
)

# --- Real Authentication Logic (Locally Defined) ---
oauth2_scheme_role = OAuth2PasswordBearer(tokenUrl="/auth/token")

async def get_current_user_for_role_router(token: str = Depends(oauth2_scheme_role), db: Session = Depends(get_db)) -> models.User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials (role router)",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not SECRET_KEY or not ALGORITHM:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Server auth configuration error (role router)")
    try:
        payload = auth_decode_token(token)
        user_id_from_token = payload.get("sub")
        if user_id_from_token is None: user_id_from_token = payload.get("user_id") # Fallback
        if user_id_from_token is None: raise credentials_exception
        user_id = int(user_id_from_token)
    except (JWTError, ValueError):
        raise credentials_exception

    user = crud.get_user(db, user_id=user_id)
    if user is None: raise credentials_exception
    return user

async def get_current_active_user_for_role_router(current_user: models.User = Depends(get_current_user_for_role_router)) -> models.User:
    if not current_user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user (role router)")
    return current_user

async def get_admin_user_local(current_user: models.User = Depends(get_current_active_user_for_role_router)) -> models.User:
    if not current_user.role or current_user.role.code != ADMIN_ROLE_CODE:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User does not have admin privileges for role management")
    return current_user
# --- End Real Authentication Logic ---


@router.get("/", response_model=List[schemas.Role]) # Changed response_model to full Role
async def read_roles_endpoint( # Renamed, async
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_admin_user_local) # Admin protected
):
    roles = crud.get_roles(db, skip=skip, limit=limit)
    return roles

@router.get("/{role_id}", response_model=schemas.Role) # Changed response_model
async def read_role_by_id_endpoint( # Renamed, async
    role_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_admin_user_local) # Admin protected
):
    db_role = crud.get_role(db, role_id=role_id) # crud.get_role instead of get_role_by_id for consistency
    if db_role is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
    return db_role

@router.post("/", response_model=schemas.Role, status_code=status.HTTP_201_CREATED) # Changed response_model
async def create_role_endpoint( # Renamed, async
    role: schemas.RoleCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_admin_user_local) # Admin protected
):
    existing_role_by_name = crud.get_role_by_name(db, role_name=role.name)
    if existing_role_by_name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Role name '{role.name}' already exists.")
    if role.code: # Ensure code is unique if provided
        existing_role_by_code = db.query(models.Role).filter(models.Role.code == role.code).first()
        if existing_role_by_code:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Role code '{role.code}' already exists.")

    new_role = crud.create_role(db=db, role=role)
    crud.create_audit_log(db, actor_id=current_user.id, entity="role", entity_id=new_role.id, action="CREATE", data=role.model_dump())
    return new_role


@router.delete("/{role_id}", status_code=status.HTTP_204_NO_CONTENT) # Changed method, path, and status
async def delete_role_endpoint( # Renamed, async
    role_id: int, # Changed to int
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_admin_user_local) # Admin protected
):
    db_role = crud.get_role(db, role_id=role_id)
    if db_role is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")

    # Check if role is in use by any user
    users_with_role = db.query(models.User).filter(models.User.role_id == role_id).first()
    if users_with_role:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Role '{db_role.name}' is currently assigned to users and cannot be deleted.")

    crud.delete_role(db, db_role=db_role) # crud.delete_role expects the model instance
    crud.create_audit_log(db, actor_id=current_user.id, entity="role", entity_id=role_id, action="DELETE", data={"name": db_role.name})
    return Response(status_code=status.HTTP_204_NO_CONTENT)

# TODO: Add PUT endpoint for updating a role if needed.
# @router.put("/{role_id}", response_model=schemas.Role)
# async def update_role_endpoint(
#     role_id: int,
#     role_in: schemas.RoleUpdate,
#     db: Session = Depends(get_db),
#     current_user: models.User = Depends(get_admin_user_local)
# ):
#     db_role = crud.get_role(db, role_id=role_id)
#     if not db_role:
#         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
#     updated_role = crud.update_role(db=db, db_role=db_role, role_in=role_in)
#     crud.create_audit_log(db, actor_id=current_user.id, entity="role", entity_id=updated_role.id, action="UPDATE", data=role_in.model_dump(exclude_unset=True))
#     return updated_role
