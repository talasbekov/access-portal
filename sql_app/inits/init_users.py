# Создайте файл init_test_users.py в корне проекта:

# !/usr/bin/env python3
"""
Скрипт для создания тестовых пользователей
"""
import os
from dotenv import load_dotenv

load_dotenv()

from sql_app.database import SessionLocal, engine
from sql_app.models import Base, User, Role, Department
from sql_app.auth import get_password_hash
from sql_app import constants


def init_test_users():
    """Создание тестовых пользователей для демонстрации"""

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        # Создаём тестовую структуру организации
        # Организация
        org = db.query(Department).filter(Department.name == "ТОО Тестовая Организация").first()
        if not org:
            org = Department(
                name="ТОО Тестовая Организация",
                type="COMPANY",
                parent_id=None
            )
            db.add(org)
            db.commit()
            print("✅ Создана организация")

        # Департамент
        dept = db.query(Department).filter(Department.name == "Департамент ИТ").first()
        if not dept:
            dept = Department(
                name="Департамент ИТ",
                type="DEPARTMENT",
                parent_id=org.id
            )
            db.add(dept)
            db.commit()
            print("✅ Создан департамент")

        # Управление
        division = db.query(Department).filter(Department.name == "Управление разработки").first()
        if not division:
            division = Department(
                name="Управление разработки",
                type="DIVISION",
                parent_id=dept.id
            )
            db.add(division)
            db.commit()
            print("✅ Создано управление")

        # Отдел
        unit = db.query(Department).filter(Department.name == "Отдел веб-разработки").first()
        if not unit:
            unit = Department(
                name="Отдел веб-разработки",
                type="UNIT",
                parent_id=division.id
            )
            db.add(unit)
            db.commit()
            print("✅ Создан отдел")

        # Создаём тестовых пользователей
        test_users = [
            {
                "username": "admin",
                "full_name": "Администратор Системы",
                "email": "admin@test.kz",
                "phone": "+77001234567",
                "role_code": constants.ADMIN_ROLE_CODE,
                "department_id": org.id,
                "password": "admin123"
            },
            {
                "username": "nach_dept",
                "full_name": "Иванов Иван Иванович",
                "email": "ivanov@test.kz",
                "phone": "+77001234568",
                "role_code": constants.NACH_DEPARTAMENTA_ROLE_CODE,
                "department_id": dept.id,
                "password": "dept123"
            },
            {
                "username": "nach_upr",
                "full_name": "Петров Петр Петрович",
                "email": "petrov@test.kz",
                "phone": "+77001234569",
                "role_code": constants.NACH_UPRAVLENIYA_ROLE_CODE,
                "department_id": division.id,
                "password": "upr123"
            },
            {
                "username": "usb_user",
                "full_name": "Сидоров Сидор Сидорович",
                "email": "sidorov@test.kz",
                "phone": "+77001234570",
                "role_code": constants.USB_ROLE_CODE,
                "department_id": org.id,
                "password": "usb123"
            },
            {
                "username": "as_user",
                "full_name": "Асанов Асан Асанович",
                "email": "asanov@test.kz",
                "phone": "+77001234571",
                "role_code": constants.AS_ROLE_CODE,
                "department_id": org.id,
                "password": "as123"
            },
            {
                "username": "kpp1_user",
                "full_name": "Охранник КПП-1",
                "email": "kpp1@test.kz",
                "phone": "+77001234572",
                "role_code": "KPP-1",
                "department_id": org.id,
                "password": "kpp123"
            },
            {
                "username": "employee",
                "full_name": "Работник Обычный",
                "email": "employee@test.kz",
                "phone": "+77001234573",
                "role_code": constants.EMPLOYEE_ROLE_CODE,
                "department_id": unit.id,
                "password": "emp123"
            }
        ]

        for user_data in test_users:
            # Проверяем, существует ли пользователь
            existing_user = db.query(User).filter(User.username == user_data["username"]).first()

            if not existing_user:
                # Получаем роль
                role = db.query(Role).filter(Role.code == user_data["role_code"]).first()
                if not role:
                    print(f"❌ Роль {user_data['role_code']} не найдена. Запустите init_roles.py")
                    continue

                # Создаём пользователя
                new_user = User(
                    username=user_data["username"],
                    full_name=user_data["full_name"],
                    email=user_data["email"],
                    phone=user_data["phone"],
                    hashed_password=get_password_hash(user_data["password"]),
                    role_id=role.id,
                    department_id=user_data["department_id"],
                    is_active=True
                )
                db.add(new_user)
                print(f"✅ Создан пользователь: {user_data['username']} (пароль: {user_data['password']})")
            else:
                print(f"📝 Пользователь {user_data['username']} уже существует")

        db.commit()
        print("\n🎉 Создание тестовых пользователей завершено!")
        print("\n📋 Данные для входа:")
        print("=" * 50)
        for user in test_users:
            print(f"Логин: {user['username']:<15} Пароль: {user['password']:<10} Роль: {user['role_code']}")

    except Exception as e:
        print(f"❌ Ошибка: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    init_test_users()