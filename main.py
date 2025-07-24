# main.py
import os
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.openapi.docs import get_swagger_ui_html

import swagger_ui_bundle
from sql_app import models
from sql_app.admin import create_admin
from sql_app.database import engine
from sql_app.config import settings

from sql_app.routers import (
    auth, users, role, departments, checkpoints,
    requests, blacklist, audit_logs, visits, admin as admin_router
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 1) Создаём/проверяем таблицы
try:
    models.Base.metadata.create_all(bind=engine)
    logger.info("Таблицы созданы или уже существуют")
except Exception as e:
    logger.error(f"Ошибка при создании таблиц: {e}")

# 2) Инициализируем FastAPI (отключаем встроенные /docs и /redoc)
app = FastAPI(
    title=settings.api_title,
    version=settings.api_version,
    description=settings.api_description,
    docs_url=None,
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 3) Роутеры
for router in (auth, users, role, departments, checkpoints,
               requests, blacklist, audit_logs, visits, admin_router):
    app.include_router(router.router)


swagger_dist = "static/dist"
app.mount(
    "/swagger-static",
    StaticFiles(directory=swagger_dist),
    name="swagger-static",
)

# 3) Сервируем UI, подставляя локальные файлы
@app.get("/docs", include_in_schema=False)
def custom_swagger_ui():
    return get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title=app.title + " – Swagger UI",
        swagger_js_url="/swagger-static/swagger-ui-bundle.js",
        swagger_css_url="/swagger-static/swagger-ui.css",
        swagger_favicon_url="/swagger-static/favicon-32x32.png",
    )

# 5) SQLAdmin
#
#   a) монтируем локальную статику из пакета sqladmin
import sqladmin
sqladmin_pkg_dir = os.path.dirname(sqladmin.__file__)
app.mount(
    "/admin/statics",
    StaticFiles(directory=os.path.join(sqladmin_pkg_dir, "statics")),
    name="sqladmin-static",
)

#   b) создаём админку (у себя в create_admin можно просто делать admin.add_view(...))
#      и указываем именно тот же static_url, куда мы выше примонтировали папку
admin = create_admin(app)

# 6) Хелсчек и корень
@app.get("/")
async def root():
    return {
        "message": "Добро пожаловать в API …",
        "docs": "/docs",
        "admin": "/admin",
        "health": "/health",
    }

@app.get("/health")
async def health_check():
    from sql_app.database import check_database_health
    ok = check_database_health()
    return {
        "status": "ok" if ok else "degraded",
        "db": "up" if ok else "down",
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000,
                reload=settings.env == "dev", log_level="info")
