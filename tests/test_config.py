#!/usr/bin/env python3
"""
Тест для проверки работы конфигурации
"""

try:
    from sql_app.config import settings

    print("✅ Config imported successfully")
    print(f"Database URL: {settings.database_url}")
    print(f"Environment: {settings.env}")
    print(f"API Title: {settings.api_title}")
except Exception as e:
    print(f"❌ Error importing config: {e}")

try:
    from sql_app.database import engine

    print("✅ Database imported successfully")
except Exception as e:
    print(f"❌ Error importing database: {e}")

try:
    from main import app

    print("✅ Main app imported successfully")
except Exception as e:
    print(f"❌ Error importing main app: {e}")
