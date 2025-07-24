# Заменить содержимое sql_app/dependencies.py на:

from sqlalchemy.orm import Session
from .database import SessionLocal

# Этот файл содержит только get_db.
# Все зависимости аутентификации перенесены в auth_dependencies.py


def get_db():
    """Получение сессии базы данных"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Можно добавить другие общие зависимости здесь, например:
# - Зависимости для пагинации
# - Зависимости для валидации параметров
# - Общие фильтры

from fastapi import Query
from typing import Optional


def get_pagination(
    skip: int = Query(0, ge=0, description="Количество записей для пропуска"),
    limit: int = Query(
        100, ge=1, le=1000, description="Максимальное количество записей"
    ),
):
    """Зависимость для пагинации"""
    return {"skip": skip, "limit": limit}


def get_search_params(
    search: Optional[str] = Query(None, description="Строка поиска"),
    sort_by: Optional[str] = Query(None, description="Поле для сортировки"),
    sort_order: Optional[str] = Query(
        "asc", regex="^(asc|desc)$", description="Порядок сортировки"
    ),
):
    """Зависимость для параметров поиска и сортировки"""
    return {"search": search, "sort_by": sort_by, "sort_order": sort_order}
