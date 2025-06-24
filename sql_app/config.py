"""
Централизованное управление конфигурацией с использованием Pydantic settings.
"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator
from typing import List, Union


class Settings(BaseSettings):
    """Настройки приложения"""

    # База данных
    database_url: str

    # JWT настройки
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7

    # Окружение
    env: str = "dev"

    # API настройки
    api_title: str = "Система управления посетителями"
    api_version: str = "1.0.0"
    api_description: str = "Комплексная система управления посетителями с RBAC"

    # CORS настройки - изменено для правильного парсинга
    cors_origins: Union[str, List[str]] = "http://localhost,http://localhost:5173,http://localhost:3000"

    # Настройки пагинации
    default_page_size: int = 100
    max_page_size: int = 1000

    # Безопасность
    password_min_length: int = 8
    max_login_attempts: int = 5
    lockout_duration_minutes: int = 30

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore"
    )

    @field_validator('cors_origins', mode='before')
    @classmethod
    def parse_cors_origins(cls, v):
        """Парсинг CORS origins из строки или списка"""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(',')]
        return v

    @field_validator('secret_key')
    @classmethod
    def secret_key_must_be_strong(cls, v):
        if len(v) < 32:
            raise ValueError('Секретный ключ должен содержать минимум 32 символа')
        return v

    @field_validator('database_url')
    @classmethod
    def database_url_must_be_valid(cls, v):
        if not v.startswith(('postgresql://', 'postgresql+psycopg2://', 'sqlite:///')):
            raise ValueError('URL базы данных должен быть валидным PostgreSQL или SQLite URL')
        return v


@lru_cache()
def get_settings() -> Settings:
    """Получить кэшированный экземпляр настроек"""
    return Settings()


# Глобальный экземпляр настроек
settings = get_settings()