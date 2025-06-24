#!/usr/bin/env python3
"""
Тест после исправления проблемы с JSONB
"""
import os

# Устанавливаем переменную окружения для использования SQLite
os.environ['DATABASE_URL'] = 'sqlite:///./test_fixed.db'

print("🔧 Тестирование после исправления JSONB...")

try:
    print("\n1️⃣ Импорт config...")
    from sql_app.config import settings

    print(f"✅ Config: {settings.database_url}")
except Exception as e:
    print(f"❌ Ошибка config: {e}")
    exit(1)

try:
    print("\n2️⃣ Импорт models...")
    from sql_app import models

    print("✅ Models импортированы")
except Exception as e:
    print(f"❌ Ошибка models: {e}")
    exit(1)

try:
    print("\n3️⃣ Импорт database...")
    from sql_app.database import engine, create_tables

    print("✅ Database импортирован")
except Exception as e:
    print(f"❌ Ошибка database: {e}")
    exit(1)

try:
    print("\n4️⃣ Создание таблиц...")
    create_tables()
    print("✅ Таблицы созданы успешно!")
except Exception as e:
    print(f"❌ Ошибка создания таблиц: {e}")
    import traceback

    traceback.print_exc()
    exit(1)

try:
    print("\n5️⃣ Проверка таблиц...")
    from sql_app.database import get_db_context
    from sqlalchemy import text

    with get_db_context() as db:
        # Проверяем, что таблица audit_logs создана
        result = db.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='audit_logs'")).fetchone()
        if result:
            print("✅ Таблица audit_logs создана")

            # Проверяем структуру таблицы
            columns = db.execute(text("PRAGMA table_info(audit_logs)")).fetchall()
            print(f"✅ Колонки audit_logs: {[col[1] for col in columns]}")
        else:
            print("❌ Таблица audit_logs не найдена")

except Exception as e:
    print(f"❌ Ошибка проверки таблиц: {e}")

try:
    print("\n6️⃣ Тест записи в audit_log...")
    from sql_app.database import get_db_context
    from sql_app.models import AuditLog

    with get_db_context() as db:
        # Создаем тестовую запись в audit_log
        test_log = AuditLog(
            entity="test",
            entity_id=1,
            action="TEST",
            data={"test_key": "test_value", "number": 123}
        )
        db.add(test_log)
        db.commit()

        # Читаем запись обратно
        saved_log = db.query(AuditLog).filter_by(entity="test").first()
        if saved_log and saved_log.data:
            print(f"✅ Тест JSON: {saved_log.data}")
        else:
            print("❌ Ошибка чтения JSON данных")

except Exception as e:
    print(f"❌ Ошибка теста JSON: {e}")
    import traceback

    traceback.print_exc()

try:
    print("\n7️⃣ Импорт main app...")
    import main

    print(f"✅ Main app: {main.app.title}")
except Exception as e:
    print(f"❌ Ошибка main app: {e}")

print("\n🎉 Тестирование завершено!")
print("\n🚀 Теперь можно запустить:")
print("   python switch_env.py local")
print("   uvicorn main:app --reload")