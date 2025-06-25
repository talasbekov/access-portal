# Role Codes
# Константы ролей в соответствии с требованиями

# Administrative & High-Level Roles
ADMIN_ROLE_CODE = "admin"

# Управленческие роли (создание заявок)
NACH_UPRAVLENIYA_ROLE_CODE = "nach_upravleniya"  # Начальник управления - краткосрочные заявки
NACH_DEPARTAMENTA_ROLE_CODE = "nach_departamenta"  # Начальник департамента - долгосрочные заявки

# Роли одобрения
USB_ROLE_CODE = "usb"  # УСБ - первичное одобрение
AS_ROLE_CODE = "as"    # АС - вторичное одобрение

# Роли КПП
KPP_ROLE_PREFIX = "KPP-"  # Префикс для ролей КПП (КПП-1, КПП-2, КПП-3, КПП-4)

# Вспомогательные роли (если нужны)
EMPLOYEE_ROLE_CODE = "employee"  # Обычный сотрудник

# Deprecated roles (для обратной совместимости, если есть старые данные)
SECURITY_OFFICER_ROLE_CODE = "security_officer"  # Старая роль, заменена на USB/AS
DCS_OFFICER_ROLE_CODE = "dcs_officer"  # Deprecated
ZD_DEPUTY_HEAD_ROLE_CODE = "zd_deputy_head"  # Deprecated

# Для обратной совместимости с существующим кодом
DEPARTMENT_HEAD_ROLE_CODE = NACH_DEPARTAMENTA_ROLE_CODE
DIVISION_MANAGER_ROLE_CODE = NACH_UPRAVLENIYA_ROLE_CODE
UNIT_HEAD_ROLE_CODE = "unit_head"  # Начальник отдела (если потребуется)
DEPUTY_DEPARTMENT_HEAD_ROLE_CODE = "deputy_department_head"
DEPUTY_DIVISION_MANAGER_ROLE_CODE = "deputy_division_manager"
DEPUTY_UNIT_HEAD_ROLE_CODE = "deputy_unit_head"
CHECKPOINT_OPERATOR_ROLE_PREFIX = "checkpoint_operator_cp"  # Старый префикс для операторов КПП

# Department Types (типы подразделений в структуре организации)
# Организация->Департамент->Управление->Отдел->Сотрудники
COMPANY = "COMPANY"  # Организация
DEPARTMENT = "DEPARTMENT"  # Департамент
DIVISION = "DIVISION"  # Управление (в терминологии кода это division)
UNIT = "UNIT"  # Отдел

# Request Statuses - статусы заявок
DRAFT = "DRAFT"  # Черновик
PENDING_USB = "PENDING_USB"  # Ожидает одобрения УСБ
APPROVED_USB = "APPROVED_USB"  # Одобрено УСБ
DECLINED_USB = "DECLINED_USB"  # Отклонено УСБ
PENDING_AS = "PENDING_AS"  # Ожидает одобрения АС
APPROVED_AS = "APPROVED_AS"  # Одобрено АС (финальное одобрение)
DECLINED_AS = "DECLINED_AS"  # Отклонено АС
ISSUED = "ISSUED"  # Пропуск выдан
CLOSED = "CLOSED"  # Заявка закрыта

# Checkpoint codes - коды КПП
CHECKPOINTS = ["KPP-1", "KPP-2", "KPP-3", "KPP-4"]

# Audit log retention period (months)
AUDIT_LOG_RETENTION_MONTHS = 18