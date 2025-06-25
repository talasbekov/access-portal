import os # For SECRET_KEY, ALGORITHM
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from jose.exceptions import JWTError # Corrected import name
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from dotenv import load_dotenv # For loading .env

from .. import crud, models, schemas
from ..auth import ( # JWT creation and password utils
    create_access_token, create_refresh_token,
    verify_password, get_password_hash # get_password_hash might be useful for user creation later
)
# JWT decoding utils will be used locally or from sql_app.auth if preferred
from ..auth import decode_token as auth_decode_token # Use directly from ..auth

from ..dependencies import get_db

load_dotenv() # Ensure env vars are loaded for SECRET_KEY/ALGORITHM

SECRET_KEY = os.getenv('SECRET_KEY')
ALGORITHM = os.getenv('ALGORITHM')

if not SECRET_KEY or not ALGORITHM:
    print("CRITICAL WARNING in auth.py: SECRET_KEY or ALGORITHM not found.")
    # This router won't work without these.

router = APIRouter(
    prefix="/auth", # Changed prefix
    tags=["Authentication"]
)

# Updated oauth2_scheme, local to this router
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token") # Updated tokenUrl

@router.post("/token", response_model=schemas.Token)
def login_for_access_token(  # Убрали async
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    user = crud.authenticate_user(db, username=form_data.username, password=form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Create tokens with user.id as the subject ('sub')
    access_token_expires_minutes = float(os.getenv('ACCESS_TOKEN_EXPIRE_MINUTES', 30)) # ensure it's float
    refresh_token_expire_days = float(os.getenv('REFRESH_TOKEN_EXPIRE_DAYS', 7)) # ensure it's float

    access_token = create_access_token(
        data={"sub": str(user.id), "user_id": user.id}, # Add user_id for compatibility if needed elsewhere
        expires_delta=timedelta(minutes=access_token_expires_minutes)
    )
    refresh_token = create_refresh_token(
        data={"sub": str(user.id)}, # Refresh token typically only has 'sub'
        expires_delta=timedelta(days=refresh_token_expire_days)
    )
    return schemas.Token(access_token=access_token, refresh_token=refresh_token, token_type="bearer")

# Local version of get_current_user for this router, using its own oauth2_scheme
def get_current_user_from_auth_router(  # Убрали async
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> models.User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Истек срок токена, перезайдите",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not SECRET_KEY or not ALGORITHM: # Runtime check
        print("ERROR in auth.py: JWT Secret Key or Algorithm is not configured for get_current_user_from_auth_router.")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Server auth configuration error")
    try:
        payload = auth_decode_token(token)
        # Try 'sub' first for user_id, then 'user_id' for backward compatibility with old tokens
        subject = payload.get("sub")
        if subject is None: # Fallback or if 'user_id' is still primary identifier in token
            user_id_from_token = payload.get("user_id")
            if user_id_from_token is None:
                raise credentials_exception
            user_id = int(user_id_from_token) # Ensure it's int
        else:
            try:
                user_id = int(subject)
            except ValueError:
                raise credentials_exception # 'sub' is not a valid int user_id

    except JWTError:
        raise credentials_exception

    user = crud.get_user(db, user_id=user_id)
    if user is None:
        raise credentials_exception
    return user

def get_current_active_user_from_auth_router(  # Убрали async
    current_user: models.User = Depends(get_current_user_from_auth_router)
) -> models.User:
    if not current_user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")
    return current_user

@router.get("/me", response_model=schemas.User)
def read_users_me(  # Убрали async
    current_user: models.User = Depends(get_current_active_user_from_auth_router)
):
    # The dependency already fetches and validates the user.
    # The schemas.User response model will handle converting the models.User object.
    return current_user