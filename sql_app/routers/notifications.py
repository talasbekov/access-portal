import os
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from dotenv import load_dotenv

from .. import crud, models, schemas
from ..dependencies import get_db # Only get_db from central dependencies
from ..auth import decode_token as auth_decode_token # For JWT decoding

load_dotenv()

SECRET_KEY = os.getenv('SECRET_KEY')
ALGORITHM = os.getenv('ALGORITHM')

if not SECRET_KEY or not ALGORITHM:
    print("CRITICAL WARNING in notifications.py: SECRET_KEY or ALGORITHM not found.")

router = APIRouter(
    prefix="/notifications",
    tags=["Notifications"],
    responses={404: {"description": "Not found"}}
)

# --- Real Authentication Logic (Locally Defined) ---
oauth2_scheme_notifications = OAuth2PasswordBearer(tokenUrl="/auth/token")

async def get_current_user_for_notifications_router(token: str = Depends(oauth2_scheme_notifications), db: Session = Depends(get_db)) -> models.User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials (notifications router)",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not SECRET_KEY or not ALGORITHM:
        print("ERROR in notifications.py: JWT Secret Key or Algorithm is not configured.")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Server auth configuration error (notifications router)")
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

async def get_current_active_user_for_notifications_router(current_user: models.User = Depends(get_current_user_for_notifications_router)) -> models.User:
    if not current_user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user (notifications router)")
    return current_user
# --- End Real Authentication Logic ---


@router.get("/", response_model=List[schemas.Notification])
async def read_user_notifications(
    read_status: Optional[bool] = None, # Query parameter to filter by read status
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user_for_notifications_router)
):
    """
    Retrieve notifications for the current user.
    Optionally filter by read status (true for read, false for unread, None for all).
    """
    notifications = crud.get_user_notifications(
        db, user_id=current_user.id, read=read_status, skip=skip, limit=limit
    )
    return notifications


@router.post("/{notification_id}/mark-as-read", response_model=schemas.Notification)
async def mark_notification_as_read_endpoint(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user_for_notifications_router)
):
    """
    Mark a specific notification as read for the current user.
    """
    db_notification = crud.mark_notification_as_read(
        db, notification_id=notification_id, user_id=current_user.id
    )
    if db_notification is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found or not owned by user")
    return db_notification
