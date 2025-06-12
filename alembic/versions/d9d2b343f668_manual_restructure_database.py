"""manual_restructure_database

Revision ID: d9d2b343f668
Revises: 3da7417286b3
Create Date: 2025-06-12 07:11:35.018903

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'd9d2b343f668'
down_revision: Union[str, None] = '3da7417286b3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### Drop Old Tables (in reverse order of creation dependency where possible) ###
    op.drop_table('blackList') # Depends on visitors
    op.drop_table('visitors')  # Depends on requests, citizenships
    op.drop_table('requests')  # Depends on users
    op.drop_table('users')     # Depends on roles, divisions
    op.drop_table('divisions') # No dependencies from this list
    op.drop_table('citizenships') # No dependencies from this list
    op.drop_table('roles')     # No dependencies from this list

    # ### Create New Tables ###
    # Department table
    op.create_table('departments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=True),
        sa.Column('parent_id', sa.Integer(), nullable=True),
        sa.Column('type', sa.Enum('COMPANY', 'DEPARTMENT', 'DIVISION', 'UNIT', name='departmenttype'), nullable=True),
        sa.ForeignKeyConstraint(['parent_id'], ['departments.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_departments_id'), 'departments', ['id'], unique=False)
    op.create_index(op.f('ix_departments_name'), 'departments', ['name'], unique=False) # Name may not be unique across different parent_id

    # Checkpoint table
    op.create_table('checkpoints',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('code', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_checkpoints_id'), 'checkpoints', ['id'], unique=False)
    op.create_index(op.f('ix_checkpoints_code'), 'checkpoints', ['code'], unique=True)

    # Role table (recreate)
    op.create_table('roles',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('code', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_roles_id'), 'roles', ['id'], unique=False)
    op.create_index(op.f('ix_roles_name'), 'roles', ['name'], unique=True)
    op.create_index(op.f('ix_roles_code'), 'roles', ['code'], unique=True)

    # User table (recreate)
    op.create_table('users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('username', sa.String(), nullable=False),
        sa.Column('full_name', sa.String(), nullable=True),
        sa.Column('hashed_password', sa.String(), nullable=True),
        sa.Column('role_id', sa.Integer(), nullable=True),
        sa.Column('department_id', sa.Integer(), nullable=True),
        sa.Column('email', sa.String(), nullable=True),
        sa.Column('phone', sa.String(), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.ForeignKeyConstraint(['department_id'], ['departments.id'], ),
        sa.ForeignKeyConstraint(['role_id'], ['roles.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_username'), 'users', ['username'], unique=True)
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True) # Assuming email should be unique

    # Request table (recreate)
    op.create_table('requests',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('creator_id', sa.Integer(), nullable=True),
        sa.Column('checkpoint_id', sa.Integer(), nullable=True),
        # start_date and end_date were from old model, not in new one per instructions.
        # If they are needed, they should be added back. For now, omitting.
        # sa.Column('start_date', sa.String(), nullable=True),
        # sa.Column('end_date', sa.String(), nullable=True),
        sa.Column('status', sa.String(), server_default='DRAFT', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['creator_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['checkpoint_id'], ['checkpoints.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # RequestPerson table
    op.create_table('request_persons',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('request_id', sa.Integer(), nullable=False),
        sa.Column('full_name', sa.String(), nullable=False),
        sa.Column('doc_type', sa.String(), nullable=True),
        sa.Column('doc_number', sa.String(), nullable=True),
        sa.Column('citizenship', sa.String(), nullable=True),
        sa.Column('company', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['request_id'], ['requests.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_request_persons_id'), 'request_persons', ['id'], unique=False)

    # Approval table
    op.create_table('approvals',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('request_id', sa.Integer(), nullable=False),
        sa.Column('approver_id', sa.Integer(), nullable=False),
        sa.Column('step', sa.Enum('DCS', 'ZD', name='approvalstep'), nullable=True),
        sa.Column('status', sa.Enum('PENDING', 'APPROVED', 'DECLINED', name='approvalstatus'), nullable=True),
        sa.Column('comment', sa.Text(), nullable=True),
        sa.Column('timestamp', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['approver_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['request_id'], ['requests.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_approvals_id'), 'approvals', ['id'], unique=False)

    # AuditLog table
    op.create_table('audit_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('entity', sa.String(), nullable=True),
        sa.Column('entity_id', sa.Integer(), nullable=True),
        sa.Column('action', sa.String(), nullable=True),
        sa.Column('actor_id', sa.Integer(), nullable=True),
        sa.Column('timestamp', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('data', sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(['actor_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_audit_logs_id'), 'audit_logs', ['id'], unique=False)

    # Blacklist table (new structure)
    op.create_table('blacklist',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('full_name', sa.String(), nullable=False),
        sa.Column('doc_type', sa.String(), nullable=True),
        sa.Column('doc_number', sa.String(), nullable=True),
        sa.Column('citizenship', sa.String(), nullable=True),
        sa.Column('reason', sa.String(), nullable=True), # Kept as String, model has Text. Can be changed to sa.Text()
        sa.Column('added_by', sa.Integer(), nullable=False),
        sa.Column('added_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('removed_by', sa.Integer(), nullable=True),
        sa.Column('removed_at', sa.DateTime(), nullable=True),
        sa.Column('status', sa.String(), server_default='ACTIVE', nullable=False),
        sa.ForeignKeyConstraint(['added_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['removed_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_blacklist_id'), 'blacklist', ['id'], unique=False)
    op.create_index(op.f('ix_blacklist_full_name'), 'blacklist', ['full_name'], unique=False)
    op.create_index(op.f('ix_blacklist_doc_number'), 'blacklist', ['doc_number'], unique=False)
    op.create_index(op.f('ix_blacklist_status'), 'blacklist', ['status'], unique=False)
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### Drop New Tables (in reverse order of creation) ###
    op.drop_index(op.f('ix_blacklist_status'), table_name='blacklist')
    op.drop_index(op.f('ix_blacklist_doc_number'), table_name='blacklist')
    op.drop_index(op.f('ix_blacklist_full_name'), table_name='blacklist')
    op.drop_index(op.f('ix_blacklist_id'), table_name='blacklist')
    op.drop_table('blacklist')

    op.drop_index(op.f('ix_audit_logs_id'), table_name='audit_logs')
    op.drop_table('audit_logs')

    op.drop_index(op.f('ix_approvals_id'), table_name='approvals')
    op.drop_table('approvals')

    op.drop_index(op.f('ix_request_persons_id'), table_name='request_persons')
    op.drop_table('request_persons')

    op.drop_table('requests') # Recreated below with old structure

    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_index(op.f('ix_users_username'), table_name='users')
    op.drop_table('users') # Recreated below with old structure

    op.drop_index(op.f('ix_roles_code'), table_name='roles')
    op.drop_index(op.f('ix_roles_name'), table_name='roles')
    op.drop_index(op.f('ix_roles_id'), table_name='roles')
    op.drop_table('roles') # Recreated below with old structure

    op.drop_index(op.f('ix_checkpoints_code'), table_name='checkpoints')
    op.drop_index(op.f('ix_checkpoints_id'), table_name='checkpoints')
    op.drop_table('checkpoints')

    op.drop_index(op.f('ix_departments_name'), table_name='departments')
    op.drop_index(op.f('ix_departments_id'), table_name='departments')
    op.drop_table('departments')

    # ### Recreate Old Tables (matching 3da7417286b3_initial_schema.py) ###
    op.create_table('roles',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=True),
        sa.Column('description', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_roles_id'), 'roles', ['id'], unique=False)
    op.create_index(op.f('ix_roles_name'), 'roles', ['name'], unique=True)

    op.create_table('citizenships',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_citizenships_id'), 'citizenships', ['id'], unique=False)
    op.create_index(op.f('ix_citizenships_name'), 'citizenships', ['name'], unique=False)

    op.create_table('divisions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=True),
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('parent_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['parent_id'], ['divisions.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_divisions_id'), 'divisions', ['id'], unique=False)
    op.create_index(op.f('ix_divisions_name'), 'divisions', ['name'], unique=True)

    op.create_table('users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('username', sa.String(), nullable=True),
        sa.Column('full_name', sa.String(), nullable=True),
        sa.Column('position', sa.String(), nullable=True),
        sa.Column('hashed_password', sa.String(), nullable=True),
        sa.Column('role_id', sa.Integer(), nullable=True),
        sa.Column('division_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['division_id'], ['divisions.id'], ),
        sa.ForeignKeyConstraint(['role_id'], ['roles.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_username'), 'users', ['username'], unique=True)

    op.create_table('requests',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('purpose', sa.String(), nullable=True),
        sa.Column('checkpoint', sa.Integer(), nullable=True),
        sa.Column('visit_type', sa.String(), nullable=True),
        sa.Column('start_date', sa.String(), nullable=True),
        sa.Column('end_date', sa.String(), nullable=True),
        sa.Column('visit_date', sa.String(), nullable=True),
        sa.Column('req_author', sa.String(), nullable=True),
        sa.Column('req_date', sa.String(), nullable=True),
        sa.Column('req_sysdata', sa.String(), nullable=True),
        sa.Column('convoy', sa.String(), nullable=True),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_table('visitors',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('iin_number', sa.Integer(), nullable=True),
        sa.Column('pass_number', sa.String(), nullable=True),
        sa.Column('first_name', sa.String(), nullable=True),
        sa.Column('second_name', sa.String(), nullable=True),
        sa.Column('third_name', sa.String(), nullable=True),
        sa.Column('gender', sa.String(), nullable=True),
        sa.Column('dob', sa.String(), nullable=True),
        sa.Column('id_exp', sa.String(), nullable=True),
        sa.Column('sb_check', sa.Boolean(), nullable=True),
        sa.Column('sb_approval', sa.Boolean(), nullable=True),
        sa.Column('sb_disapp_reason', sa.String(), nullable=True),
        sa.Column('sb_notes', sa.String(), nullable=True),
        sa.Column('ap_check', sa.Boolean(), nullable=True),
        sa.Column('ap_approval', sa.Boolean(), nullable=True),
        sa.Column('ap_disapp_reason', sa.String(), nullable=True),
        sa.Column('ap_notes', sa.String(), nullable=True),
        sa.Column('entered', sa.PickleType(), nullable=True),
        sa.Column('citizenship_id', sa.Integer(), nullable=True),
        sa.Column('request_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['citizenship_id'], ['citizenships.id'], ),
        sa.ForeignKeyConstraint(['request_id'], ['requests.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_table('blackList', # Old name was blackList (camelCase)
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('reason', sa.String(), nullable=True),
        sa.Column('visitor_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['visitor_id'], ['visitors.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###
