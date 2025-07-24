import logging
from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import StaticPool
from contextlib import contextmanager

try:
    from .config import settings
except ImportError:
    # Fallback для случаев, когда config недоступен
    import os
    from dotenv import load_dotenv

    load_dotenv()

    class FallbackSettings:
        database_url = os.getenv("DATABASE_URL", "sqlite:///./test.db")
        env = os.getenv("ENV", "dev")

    settings = FallbackSettings()

logger = logging.getLogger(__name__)

# Определяем тип базы данных
is_sqlite = settings.database_url.startswith("sqlite")
is_test = getattr(settings, "env", "dev") == "test"

# Конфигурация движка базы данных
if is_sqlite or is_test:
    # SQLite конфигурация
    engine = create_engine(
        settings.database_url,
        connect_args={"check_same_thread": False} if is_sqlite else {},
        poolclass=StaticPool if is_sqlite else None,
        echo=getattr(settings, "env", "dev") == "dev",
    )
else:
    # PostgreSQL конфигурация
    engine = create_engine(
        settings.database_url,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
        pool_recycle=3600,
        echo=getattr(settings, "env", "dev") == "dev",
    )


# Обработчики событий подключения
@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """Настройка SQLite pragma для поддержки внешних ключей"""
    if "sqlite" in str(dbapi_connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


@event.listens_for(Engine, "connect")
def set_postgresql_search_path(dbapi_connection, connection_record):
    """Настройка PostgreSQL search path и timezone"""
    if "postgresql" in str(dbapi_connection):
        try:
            with dbapi_connection.cursor() as cursor:
                cursor.execute("SET timezone='UTC'")
        except Exception as e:
            logger.warning(f"Не удалось установить timezone для PostgreSQL: {e}")


# Конфигурация сессий
SessionLocal = sessionmaker(
    autocommit=False, autoflush=False, bind=engine, expire_on_commit=False
)

Base = declarative_base()


def get_db():
    """Зависимость для получения сессии базы данных"""
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error(f"Ошибка сессии базы данных: {e}")
        db.rollback()
        raise
    finally:
        db.close()


@contextmanager
def get_db_context():
    """Контекстный менеджер для сессий базы данных"""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception as e:
        logger.error(f"Ошибка контекста базы данных: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def check_database_health():
    """Проверка состояния базы данных"""
    try:
        with get_db_context() as db:
            result = db.execute(text("SELECT 1")).scalar()
            return result == 1
    except Exception as e:
        logger.error(f"Проверка состояния базы данных не удалась: {e}")
        return False


def create_tables():
    """Создать все таблицы базы данных"""
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Таблицы базы данных созданы успешно")
    except Exception as e:
        logger.error(f"Не удалось создать таблицы базы данных: {e}")
        raise
