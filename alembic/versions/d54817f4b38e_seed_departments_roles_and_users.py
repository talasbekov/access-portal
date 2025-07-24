"""seed departments, roles and users

Revision ID: d54817f4b38e
Revises: 7c649cf837a9
Create Date: 2025-06-13 17:02:23.319569

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import table, column


# revision identifiers, used by Alembic.
revision: str = "d54817f4b38e"
down_revision: Union[str, None] = "7c649cf837a9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # --- Seed departments ---
    departments = table(
        "departments",
        column("id", sa.Integer),
        column("name", sa.String),
        column("parent_id", sa.Integer),
        column("type", sa.String),
    )
    op.bulk_insert(
        departments,
        [
            {
                "id": 1,
                "name": "Служба государственной охраны РК",
                "parent_id": None,
                "type": "COMPANY",
            },
            {
                "id": 2,
                "name": "Седьмой департамент",
                "parent_id": 1,
                "type": "DEPARTMENT",
            },
            {"id": 3, "name": "6-управление", "parent_id": 2, "type": "DIVISION"},
            {
                "id": 4,
                "name": "Управление собственной безопасностью",
                "parent_id": 1,
                "type": "DEPARTMENT",
            },
            {"id": 5, "name": "Аппарат Службы", "parent_id": 1, "type": "DEPARTMENT"},
            {"id": 6, "name": "4-управление", "parent_id": 5, "type": "DIVISION"},
            {
                "id": 7,
                "name": "Второй департамент",
                "parent_id": 1,
                "type": "DEPARTMENT",
            },
        ],
    )
    # Reset departments sequence
    op.execute(
        "SELECT setval(pg_get_serial_sequence('departments','id'), COALESCE(MAX(id),0)) FROM departments;"
    )

    # --- Seed roles ---
    roles = table(
        "roles",
        column("id", sa.Integer),
        column("name", sa.String),
        column("description", sa.String),
        column("code", sa.String),
    )
    op.bulk_insert(
        roles,
        [
            {"id": 1, "name": "Администратор", "description": "admin", "code": "admin"},
            {"id": 2, "name": "УСБ", "description": "УСБ", "code": "dcs_officer"},
            {"id": 3, "name": "АС", "description": "АС", "code": "zd_deputy_head"},
            {"id": 4, "name": "НД", "description": "НД", "code": "department_head"},
            {
                "id": 5,
                "name": "ЗНД",
                "description": "ЗНД",
                "code": "deputy_department_head",
            },
            {"id": 6, "name": "НУ", "description": "НУ", "code": "division_manager"},
            {
                "id": 7,
                "name": "ЗНУ",
                "description": "ЗНУ",
                "code": "deputy_division_manager",
            },
            {
                "id": 8,
                "name": "КПП",
                "description": "КПП",
                "code": "checkpoint_operator",
            },
            {
                "id": 9,
                "name": "Сотрудник",
                "description": "Сотрудник",
                "code": "employee",
            },
        ],
    )
    # Reset roles sequence
    op.execute(
        "SELECT setval(pg_get_serial_sequence('roles','id'), COALESCE(MAX(id),0)) FROM roles;"
    )

    # --- Seed initial users ---
    users = table(
        "users",
        column("id", sa.Integer),
        column("username", sa.String),
        column("full_name", sa.String),
        column("hashed_password", sa.String),
        column("role_id", sa.Integer),
        column("department_id", sa.Integer),
        column("email", sa.String),
        column("phone", sa.String),
        column("is_active", sa.Boolean),
    )
    op.bulk_insert(
        users,
        [
            {
                "id": 1,
                "username": "admin",
                "full_name": "System Administrator",
                "hashed_password": "$2b$12$D4W0YpJSQAxs/d.sfdg98.nMV6SIG/s40iEVK7DcLRXbSYacujOLC",
                "role_id": 1,
                "department_id": 1,
                "email": "admin@@sgo.kz",
                "phone": "+70000000001",
                "is_active": True,
            },
            {
                "id": 2,
                "username": "a_saken",
                "full_name": "USB",
                "hashed_password": "$2b$12$D4W0YpJSQAxs/d.sfdg98.nMV6SIG/s40iEVK7DcLRXbSYacujOLC",
                "role_id": 2,
                "department_id": 4,
                "email": "a_saken@sgo.kz",
                "phone": "+70000000001",
                "is_active": True,
            },
            {
                "id": 3,
                "username": "d_dake",
                "full_name": "ND",
                "hashed_password": "$2b$12$D4W0YpJSQAxs/d.sfdg98.nMV6SIG/s40iEVK7DcLRXbSYacujOLC",
                "role_id": 4,
                "department_id": 2,
                "email": "d_dake@sgo.kz",
                "phone": "+70000000001",
                "is_active": True,
            },
            {
                "id": 4,
                "username": "a_aidos",
                "full_name": "KPP",
                "hashed_password": "$2b$12$D4W0YpJSQAxs/d.sfdg98.nMV6SIG/s40iEVK7DcLRXbSYacujOLC",
                "role_id": 8,
                "department_id": 3,
                "email": "a_aidos@sgo.kz",
                "phone": "+70000000001",
                "is_active": True,
            },
            {
                "id": 5,
                "username": "b_baha",
                "full_name": "AS",
                "hashed_password": "$2b$12$D4W0YpJSQAxs/d.sfdg98.nMV6SIG/s40iEVK7DcLRXbSYacujOLC",
                "role_id": 3,
                "department_id": 5,
                "email": "b_baha@sgo.kz",
                "phone": "+70000000001",
                "is_active": True,
            },
            {
                "id": 6,
                "username": "a_almaz",
                "full_name": "Almaz",
                "hashed_password": "$2b$12$D4W0YpJSQAxs/d.sfdg98.nMV6SIG/s40iEVK7DcLRXbSYacujOLC",
                "role_id": 9,
                "department_id": 3,
                "email": "a_almaz@sgo.kz",
                "phone": "+70000000001",
                "is_active": True,
            },
        ],
    )
    # Reset users sequence
    op.execute(
        "SELECT setval(pg_get_serial_sequence('users','id'), COALESCE(MAX(id),0)) FROM users;"
    )


def downgrade():
    # Remove seeded users
    op.execute("DELETE FROM users WHERE id IN (1,2);")
    # Remove seeded roles
    op.execute("DELETE FROM roles WHERE id BETWEEN 1 AND 9;")
    # Remove seeded departments
    op.execute("DELETE FROM departments WHERE id BETWEEN 1 AND 7;")
