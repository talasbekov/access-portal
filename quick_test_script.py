#!/usr/bin/env python3
"""
Быстрый тест для проверки работы конфигурации
Поместите этот файл в корневую директорию проекта (рядом с main.py)
"""

print("🔍 Проверка структуры проекта...")
import os

print(f"Текущая директория: {os.getcwd()}")
print(f"Файлы в директории: {os.listdir('.')}")

if os.path.exists("sql_app"):
    print(f"✅ Найдена папка sql_app")
    print(f"Файлы в sql_app: {os.listdir('sql_app')}")
else:
    print("❌ Папка sql_app не найдена")

print("\n🔍 Проверка зависимостей...")
try:
    import pydantic_settings

    print("✅ pydantic-settings установлен")
except ImportError:
    print("❌ pydantic-settings не установлен")
    print("Установите: pip install pydantic-settings")

try:
    from dotenv import load_dotenv

    load_dotenv()
    print("✅ python-dotenv работает")
except ImportError:
    print("❌ python-dotenv не работает")

print("\n🔍 Проверка переменных окружения...")
import os

env_vars = ["DATABASE_URL", "SECRET_KEY", "ALGORITHM"]
for var in env_vars:
    value = os.getenv(var)
    if value:
        print(f"✅ {var}: {'*' * min(len(value), 10)}... (скрыто)")
    else:
        print(f"❌ {var}: не установлена")

print("\n🔍 Проверка импортов...")

try:
    print("Импорт config...")
    from sql_app.config import settings

    print("✅ Config imported successfully")
    print(f"Environment: {settings.env}")
    print(f"API Title: {settings.api_title}")
except Exception as e:
    print(f"❌ Error importing config: {e}")
    import traceback

    traceback.print_exc()

try:
    print("\nИмпорт database...")
    from sql_app.database import engine

    print("✅ Database imported successfully")
except Exception as e:
    print(f"❌ Error importing database: {e}")
    import traceback

    traceback.print_exc()

try:
    print("\nИмпорт main...")
    import main

    print("✅ Main app imported successfully")
except Exception as e:
    print(f"❌ Error importing main app: {e}")
    import traceback

    traceback.print_exc()

print("\n✅ Тест завершен!")
