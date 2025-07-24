# Создайте файл init_roles.py в корне проекта:

# !/usr/bin/env python3
"""
Скрипт для инициализации ролей в базе данных
"""
import os
from dotenv import load_dotenv

load_dotenv()

from sql_app.database import SessionLocal, engine
from sql_app.models import Base, Role
from sql_app import constants


def init_roles():
    """Инициализация ролей в базе данных"""

    # Создаём таблицы, если их нет
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()

    roles_data = [
        {
            "code": constants.ADMIN_ROLE_CODE,
            "name": "Администратор",
            "description": "Полный доступ к системе",
        },
        {
            "code": constants.NACH_DEPARTAMENTA_ROLE_CODE,
            "name": "Начальник департамента",
            "description": "Может создавать долгосрочные заявки, видит журналы своего департамента",
        },
        {
            "code": constants.NACH_UPRAVLENIYA_ROLE_CODE,
            "name": "Начальник управления",
            "description": "Может создавать краткосрочные заявки, видит журналы своего управления",
        },
        {
            "code": constants.USB_ROLE_CODE,
            "name": "УСБ",
            "description": "Проверяет и одобряет долгосрочные заявки и заявки с более чем 3 посетителями или иностранцами",
        },
        {
            "code": constants.AS_ROLE_CODE,
            "name": "АС",
            "description": "Проверяет и одобряет заявки после УСБ и краткосрочные заявки с менее чем 4 посетителями",
        },
        {
            "code": "KPP-1",
            "name": "Оператор КПП-1",
            "description": "Фиксирует вход и выход посетителей на КПП-1",
        },
        {
            "code": "KPP-2",
            "name": "Оператор КПП-2",
            "description": "Фиксирует вход и выход посетителей на КПП-2",
        },
        {
            "code": "KPP-3",
            "name": "Оператор КПП-3",
            "description": "Фиксирует вход и выход посетителей на КПП-3",
        },
        {
            "code": "KPP-4",
            "name": "Оператор КПП-4",
            "description": "Фиксирует вход и выход посетителей на КПП-4",
        },
        {
            "code": constants.EMPLOYEE_ROLE_CODE,
            "name": "Сотрудник",
            "description": "Обычный сотрудник без специальных прав",
        },
    ]

    try:
        for role_data in roles_data:
            # Проверяем, существует ли роль
            existing_role = (
                db.query(Role).filter(Role.code == role_data["code"]).first()
            )

            if not existing_role:
                # Создаём новую роль
                new_role = Role(**role_data)
                db.add(new_role)
                print(f"✅ Создана роль: {role_data['name']} ({role_data['code']})")
            else:
                # Обновляем существующую роль
                existing_role.name = role_data["name"]
                existing_role.description = role_data["description"]
                print(f"📝 Обновлена роль: {role_data['name']} ({role_data['code']})")

        db.commit()
        print("\n🎉 Инициализация ролей завершена успешно!")

    except Exception as e:
        print(f"❌ Ошибка при инициализации ролей: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    init_roles()
