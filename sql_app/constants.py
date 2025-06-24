# Role Codes
# TODO: Ensure these codes match exactly with the 'code' field in the 'roles' table in the database.

# Administrative & High-Level Roles
ADMIN_ROLE_CODE = "admin"
# KPP_ROLE_CODE = "KPP_" # Old, replaced by KPP_ROLE_PREFIX

# Approval & Security Roles (New based on requirements)
USB_ROLE_CODE = "usb_officer"
AS_ROLE_CODE = "as_officer"

# Deprecated/Replaced Approval Roles (if USB/AS replace them)
DCS_OFFICER_ROLE_CODE = "dcs_officer"  # Potentially replaced by USB_ROLE_CODE
ZD_DEPUTY_HEAD_ROLE_CODE = "zd_deputy_head" # Potentially replaced by AS_ROLE_CODE

SECURITY_OFFICER_ROLE_CODE = "security_officer" # General security officer, may still be used or combined with USB/AS functions

# Management Roles
# "Начальник департамента"
NACH_DEPARTAMENTA_ROLE_CODE = "head_of_department" # This can replace/be the same as DEPARTMENT_HEAD_ROLE_CODE
# "Начальник управления" - 'управление' can be a 'DIVISION' or 'UNIT' type in Department model
NACH_UPRAVLENIYA_ROLE_CODE = "head_of_management_unit" # Generic term, specific type (Division/Unit) checked in logic

# Existing granular management roles (can be used by NACH_DEPARTAMENTA_ROLE_CODE or NACH_UPRAVLENIYA_ROLE_CODE if they are assigned to a dept of this type)
DEPARTMENT_HEAD_ROLE_CODE = "department_head" # Kept for now, might consolidate with NACH_DEPARTAMENTA
DEPUTY_DEPARTMENT_HEAD_ROLE_CODE = "deputy_department_head"
DIVISION_MANAGER_ROLE_CODE = "division_manager" # Manager of a 'DIVISION' type department
DEPUTY_DIVISION_MANAGER_ROLE_CODE = "deputy_division_manager"
UNIT_HEAD_ROLE_CODE = "unit_head" # Manager of a 'UNIT' type department
DEPUTY_UNIT_HEAD_ROLE_CODE = "deputy_unit_head"

# Operational Roles
CHECKPOINT_OPERATOR_ROLE_PREFIX = "checkpoint_operator_cp" # e.g., checkpoint_operator_cp1. This is for specific checkpoint hardware/software.
                                                            # KPP_ROLE_CODE is for the human personnel at these checkpoints.
                                                            # The problem states "КПП-*" sees requests. This implies KPP_ROLE_CODE might be like "KPP-1", "KPP-2".
                                                            # Let's adjust KPP_ROLE_CODE to be a prefix.
KPP_ROLE_PREFIX = "KPP-" # e.g. KPP-1, KPP-2. (Replaces single KPP_ROLE_CODE)

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
