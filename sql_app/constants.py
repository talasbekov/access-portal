# sql_app/constants.py
"""Константы системы управления посетителями"""

# Роли системы
ADMIN_ROLE_CODE = "admin"
NACH_DEPARTAMENTA_ROLE_CODE = "nach_departamenta"  # Начальник департамента
NACH_UPRAVLENIYA_ROLE_CODE = "nach_upravleniya"    # Начальник управления
USB_ROLE_CODE = "usb"                               # УСБ
AS_ROLE_CODE = "as"                                 # АС
KPP_ROLE_PREFIX = "KPP-"                           # Префикс для ролей КПП
EMPLOYEE_ROLE_CODE = "employee"                     # Обычный сотрудник

# Типы подразделений
COMPANY = "COMPANY"        # Организация
DEPARTMENT = "DEPARTMENT"  # Департамент
DIVISION = "DIVISION"      # Управление
UNIT = "UNIT"             # Отдел

# Статусы заявок
PENDING_USB = "PENDING_USB"      # Ожидает одобрения УСБ
APPROVED_USB = "APPROVED_USB"    # Одобрено УСБ
DECLINED_USB = "DECLINED_USB"    # Отклонено УСБ
PENDING_AS = "PENDING_AS"        # Ожидает одобрения АС
APPROVED_AS = "APPROVED_AS"      # Одобрено АС (финальное)
DECLINED_AS = "DECLINED_AS"      # Отклонено АС
ISSUED = "ISSUED"                # Пропуск выдан
CLOSED = "CLOSED"                # Заявка закрыта

# КПП
CHECKPOINTS = ["KPP-1", "KPP-2", "KPP-3", "KPP-4"]

# Настройки системы
AUDIT_LOG_RETENTION_MONTHS = 18  # Срок хранения логов
MIN_PASSWORD_LENGTH = 8          # Минимальная длина пароля
MAX_LOGIN_ATTEMPTS = 5           # Максимум попыток входа
LOCKOUT_DURATION_MINUTES = 30    # Время блокировки

# Пороги для маршрутизации заявок
MAX_SHORT_TERM_PERSONS = 3       # Максимум человек для прямой подачи в АС