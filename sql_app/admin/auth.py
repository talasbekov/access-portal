from typing import Optional
from fastapi import Request, HTTPException, status
from sqlalchemy.orm import Session
from sqladmin.authentication import AuthenticationBackend

from ..database import get_db
from ..auth import decode_token
from ..auth_dependencies import get_current_user
from .. import crud, rbac


class AdminAuthBackend(AuthenticationBackend):
    """Бэкенд аутентификации для админки"""

    async def login(self, request: Request) -> bool:
        """Логин через форму админки"""
        form = await request.form()
        username = form.get("username")
        password = form.get("password")

        if not username or not password:
            return False

        # Получаем сессию БД
        db = next(get_db())
        try:
            # Аутентифицируем пользователя
            user = crud.authenticate_user(db, username=username, password=password)
            if not user:
                return False

            # Проверяем права администратора
            if not rbac.is_admin(user):
                return False

            # Сохраняем ID пользователя в сессии
            request.session.update({"user_id": user.id})
            return True

        finally:
            db.close()

    async def logout(self, request: Request) -> bool:
        """Выход из админки"""
        request.session.clear()
        return True

    async def authenticate(self, request: Request) -> Optional[str]:
        """Проверка аутентификации для каждого запроса"""
        user_id = request.session.get("user_id")
        if not user_id:
            return None

        # Получаем сессию БД
        db = next(get_db())
        try:
            user = crud.get_user(db, user_id=user_id)
            if not user or not user.is_active:
                return None

            # Проверяем права администратора
            if not rbac.is_admin(user):
                return None

            return user.username

        finally:
            db.close()
