from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from sql_app import models
from sql_app.database import engine
from sql_app.config import settings
from sql_app.routers import (
    auth,
    users,
    role,
    departments,
    requests,
    blacklist,
    checkpoints,
    visits
)

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Безопасное создание таблиц
try:
    models.Base.metadata.create_all(bind=engine)
    logger.info("Таблицы базы данных созданы/проверены успешно")
except Exception as e:
    logger.error(f"Ошибка при создании таблиц базы данных: {e}")
    logger.warning("Приложение запускается без подключения к базе данных")

app = FastAPI(
    title=settings.api_title,
    version=settings.api_version,
    description=settings.api_description
)

app.add_middleware(
    CORSMiddleware,
    # allow_origins=settings.cors_origins,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Проверка здоровья
@app.get("/health")
async def health_check():
    try:
        from sql_app.database import check_database_health
        db_healthy = check_database_health()
    except Exception:
        db_healthy = False

    return {
        "status": "healthy" if db_healthy else "healthy_no_db",
        "database": "connected" if db_healthy else "disconnected",
        "version": settings.api_version,
        "environment": settings.env
    }


# Подключение роутеров
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(role.router)
app.include_router(departments.router)
app.include_router(requests.router)
app.include_router(blacklist.router)
app.include_router(checkpoints.router)
app.include_router(visits.router)


@app.get("/")
async def root():
    return {
        "message": "Добро пожаловать в API системы управления посетителями",
        "version": settings.api_version,
        "environment": settings.env,
        "docs": "/docs",
        "health": "/health"
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.env == "dev",
        log_level="info"
    )