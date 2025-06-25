# Создайте файл init_checkpoints.py в корне проекта:

# !/usr/bin/env python3
"""
Скрипт для инициализации контрольно-пропускных пунктов в базе данных
"""
import os
from dotenv import load_dotenv

load_dotenv()

from sql_app.database import SessionLocal, engine
from sql_app.models import Base, Checkpoint


def init_checkpoints():
    """Инициализация КПП в базе данных"""

    # Создаём таблицы, если их нет
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()

    checkpoints_data = [
        {
            "code": "KPP-1",
            "name": "КПП-1 (Главный вход)"
        },
        {
            "code": "KPP-2",
            "name": "КПП-2 (Служебный вход)"
        },
        {
            "code": "KPP-3",
            "name": "КПП-3 (Грузовой вход)"
        },
        {
            "code": "KPP-4",
            "name": "КПП-4 (Запасной вход)"
        }
    ]

    try:
        for checkpoint_data in checkpoints_data:
            # Проверяем, существует ли КПП
            existing_checkpoint = db.query(Checkpoint).filter(
                Checkpoint.code == checkpoint_data["code"]
            ).first()

            if not existing_checkpoint:
                # Создаём новый КПП
                new_checkpoint = Checkpoint(**checkpoint_data)
                db.add(new_checkpoint)
                print(f"✅ Создан КПП: {checkpoint_data['name']} ({checkpoint_data['code']})")
            else:
                # Обновляем существующий КПП
                existing_checkpoint.name = checkpoint_data["name"]
                print(f"📝 Обновлен КПП: {checkpoint_data['name']} ({checkpoint_data['code']})")

        db.commit()
        print("\n🎉 Инициализация КПП завершена успешно!")

    except Exception as e:
        print(f"❌ Ошибка при инициализации КПП: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    init_checkpoints()