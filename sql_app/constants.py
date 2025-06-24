# Role Codes
# TODO: Ensure these codes match exactly with the 'code' field in the 'roles' table in the database.

# Administrative & High-Level Roles
ADMIN_ROLE_CODE = "admin"
KPP_ROLE_CODE = "KPP_" # Checkpoint/Entry point personnel

# Approval & Security Roles
DCS_OFFICER_ROLE_CODE = "dcs_officer"
ZD_DEPUTY_HEAD_ROLE_CODE = "zd_deputy_head"
SECURITY_OFFICER_ROLE_CODE = "security_officer" # General security officer

# Management Roles
DEPARTMENT_HEAD_ROLE_CODE = "department_head"
DEPUTY_DEPARTMENT_HEAD_ROLE_CODE = "deputy_department_head"
DIVISION_MANAGER_ROLE_CODE = "division_manager" # Assuming Division is a higher/parallel structure
DEPUTY_DIVISION_MANAGER_ROLE_CODE = "deputy_division_manager"
UNIT_HEAD_ROLE_CODE = "unit_head" # Assuming Unit is a type of department/subunit
DEPUTY_UNIT_HEAD_ROLE_CODE = "deputy_unit_head" # Example, if exists

# Operational Roles
CHECKPOINT_OPERATOR_ROLE_PREFIX = "checkpoint_operator_cp" # e.g., checkpoint_operator_cp1

# General User Roles
EMPLOYEE_ROLE_CODE = "employee" # Generic employee

# Add other role codes as they are defined and used.

# Request Statuses (already in schemas.RequestStatusEnum, but if needed as constants elsewhere)
# PENDING_DCS = "PENDING_DCS"
# ... etc.

# Department Types (from models.DepartmentType)
# COMPANY = "COMPANY"
# DEPARTMENT = "DEPARTMENT"
# DIVISION = "DIVISION"
# UNIT = "UNIT"
