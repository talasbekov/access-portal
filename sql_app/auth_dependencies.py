"""
Централизованные зависимости аутентификации для избежания дублирования кода в роутерах.
"""
import os
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.orm import Session
from dotenv import load_dotenv

from . import crud, models, constants
from .auth import decode_token as auth_decode_token
from .dependencies import get_db

load_dotenv()

SECRET_KEY = os.getenv('SECRET_KEY')
ALGORITHM = os.getenv('ALGORITHM')

if not SECRET_KEY or not ALGORITHM:
    raise RuntimeError("SECRET_KEY or ALGORITHM not found in environment variables")

# Глобальная OAuth2 схема
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")

class AuthDependencies:
    """Централизованные зависимости аутентификации"""

    @staticmethod
    def get_current_user(  # Убрали async здесь
        token: str = Depends(oauth2_scheme),
        db: Session = Depends(get_db)
    ) -> models.User:
        """Получить текущего аутентифицированного пользователя"""
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

        try:
            payload = auth_decode_token(token)
            # Пробуем 'sub' сначала (стандарт), затем 'user_id' для обратной совместимости
            user_id_str = payload.get("sub") or payload.get("user_id")
            if user_id_str is None:
                raise credentials_exception
            user_id = int(user_id_str)
        except (JWTError, ValueError):
            raise credentials_exception

        user = crud.get_user(db, user_id=user_id)
        if user is None:
            raise credentials_exception
        return user

    @staticmethod
    def get_current_active_user(  # Убрали async здесь
        current_user: models.User = Depends(get_current_user)  # Теперь правильная зависимость
    ) -> models.User:
        """Получить текущего активного пользователя"""
        if not current_user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Inactive user"
            )
        return current_user

    @staticmethod
    def get_admin_user(  # Убрали async здесь
        current_user: models.User = Depends(get_current_active_user)  # Правильная зависимость
    ) -> models.User:
        """Требовать роль администратора"""
        # from .rbac import is_admin # is_admin likely uses constants.ADMIN_ROLE_CODE
        if not current_user.role or current_user.role.code != constants.ADMIN_ROLE_CODE:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin privileges required"
            )
        return current_user

    @staticmethod
    def get_security_officer_user(  # Убрали async здесь
        current_user: models.User = Depends(get_current_active_user)  # Правильная зависимость
    ) -> models.User:
        """Требовать привилегии офицера безопасности или выше"""
        allowed_roles = [
            constants.SECURITY_OFFICER_ROLE_CODE,
            constants.DCS_OFFICER_ROLE_CODE,
            constants.ZD_DEPUTY_HEAD_ROLE_CODE,
            constants.ADMIN_ROLE_CODE
        ]
        if not current_user.role or current_user.role.code not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Security officer privileges required"
            )
        return current_user

    @staticmethod
    def get_checkpoint_operator_user(  # Убрали async здесь
        current_user: models.User = Depends(get_current_active_user)  # Правильная зависимость
    ) -> models.User:
        """Требовать роль оператора КПП"""
        if not current_user.role or not current_user.role.code.startswith(constants.CHECKPOINT_OPERATOR_ROLE_PREFIX):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Checkpoint operator privileges required"
            )
        return current_user

    @staticmethod
    def get_kpp_user(current_user: models.User = Depends(get_current_active_user)) -> models.User:
        """Требовать роль КПП"""
        if not current_user.role or current_user.role.code != constants.KPP_ROLE_CODE:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="KPP privileges required"
            )
        return current_user

# Создаем экземпляры для легкого импорта
get_current_user = AuthDependencies.get_current_user
get_current_active_user = AuthDependencies.get_current_active_user
get_admin_user = AuthDependencies.get_admin_user
get_security_officer_user = AuthDependencies.get_security_officer_user
get_checkpoint_operator_user = AuthDependencies.get_checkpoint_operator_user
get_kpp_user = AuthDependencies.get_kpp_user # Exporting the new dependency