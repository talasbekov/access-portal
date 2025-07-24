from datetime import datetime, date, timedelta

from sqladmin import Admin, ModelView

from sqladmin.filters import (
    BooleanFilter,
    AllUniqueStringValuesFilter,
    ForeignKeyFilter, get_column_obj
)
from typing import Any, Callable, List, Optional, Tuple

from sqlalchemy.sql.elements import and_
from sqlalchemy.sql.expression import Select

from sqladmin._types import MODEL_ATTR

from ..database import engine, SessionLocal
from ..models import (
    User, Role, Department, Request, RequestPerson,
    Checkpoint, AuditLog, BlackList, Notification, VisitLog
)


class UserAdmin(ModelView, model=User):
    """Админка для пользователей"""

    column_default_sort = 'id'
    column_list = [User.id, User.username, User.full_name, User.email, User.role_id, User.is_active]
    column_searchable_list = [User.username, User.full_name, User.email]
    column_sortable_list = [User.id, User.username, User.full_name, User.email]
    column_filters = [
        BooleanFilter(User.is_active),
        ForeignKeyFilter(User.role_id, Role.name, foreign_model=Role),
        ForeignKeyFilter(User.department_id, Department.name, foreign_model=Department)
    ]

    form_excluded_columns = [
        User.hashed_password, User.audit_logs, User.approvals,
        User.created_blacklist_entries, User.removed_blacklist_entries,
        User.notifications, User.requests
    ]


class RoleAdmin(ModelView, model=Role):
    """Админка для ролей"""

    column_default_sort = 'id'
    column_list = [Role.id, Role.name, Role.code, Role.description]
    column_searchable_list = [Role.name, Role.code]
    form_columns = [Role.name, Role.code, Role.description]


class DepartmentAdmin(ModelView, model=Department):
    """Админка для подразделений"""

    column_list = [Department.id, Department.name, Department.type]
    column_searchable_list = [Department.name]
    column_filters = [AllUniqueStringValuesFilter(Department.type)]
    form_columns = [Department.name, Department.type, Department.parent_id]


class RequestAdmin(ModelView, model=Request):
    """Админка для заявок"""

    column_list = [
        Request.id, Request.status, Request.start_date,
        Request.end_date, Request.created_at
    ]
    column_searchable_list = [Request.status]
    column_filters = [
        AllUniqueStringValuesFilter(Request.status),
        AllUniqueStringValuesFilter(Request.duration),
        AllUniqueStringValuesFilter(Request.accompanying)
    ]
    column_sortable_list = [Request.id, Request.created_at, Request.start_date]
    can_edit = False
    can_create = False


class RequestPersonAdmin(ModelView, model=RequestPerson):
    """Админка для посетителей в заявках"""

    column_list = [
        RequestPerson.id, RequestPerson.firstname, RequestPerson.lastname,
        RequestPerson.company, RequestPerson.status, RequestPerson.nationality
    ]
    column_searchable_list = [
        RequestPerson.firstname, RequestPerson.lastname,
        RequestPerson.iin, RequestPerson.doc_number
    ]
    column_filters = [
        AllUniqueStringValuesFilter(RequestPerson.status),
        AllUniqueStringValuesFilter(RequestPerson.nationality),
        AllUniqueStringValuesFilter(RequestPerson.gender)
    ]
    can_edit = False
    can_create = False


class CheckpointAdmin(ModelView, model=Checkpoint):
    """Админка для КПП"""

    column_list = [Checkpoint.id, Checkpoint.code, Checkpoint.name]
    column_searchable_list = [Checkpoint.code, Checkpoint.name]


class BlackListAdmin(ModelView, model=BlackList):
    """Админка для черного списка"""

    column_list = [
        BlackList.id, BlackList.firstname, BlackList.lastname,
        BlackList.iin, BlackList.status, BlackList.added_at
    ]
    column_searchable_list = [
        BlackList.firstname, BlackList.lastname, BlackList.iin, BlackList.doc_number
    ]
    column_filters = [
        AllUniqueStringValuesFilter(BlackList.status),
        AllUniqueStringValuesFilter(BlackList.nationality)
    ]


class RelativeDateFilter:
    """
    Фильтр по column, с опциями:
      * today     — Сегодня
      * yesterday — Вчера
      * week      — За неделю
      * month     — За месяц
    """
    OPTIONS: List[Tuple[str, str]] = [
        ("",          "Все"),
        ("today",     "Сегодня"),
        ("yesterday", "Вчера"),
        ("week",      "За 7 дней"),
        ("month",     "За 30 дней"),
    ]

    def __init__(
        self,
        column: MODEL_ATTR,
        title: Optional[str] = None,
        parameter_name: Optional[str] = None,
    ):
        self.column = column
        # здесь можно использовать ваш get_title/get_parameter_name
        self.title = title or title or str(column).split(".")[-1].title()
        self.parameter_name = parameter_name or self.title.lower()

    async def lookups(
        self,
        request: Request,
        model: Any,
        run_query: Callable[[Select], Any],
    ) -> List[Tuple[str, str]]:
        # возвращаем готовые опции
        return self.OPTIONS

    async def get_filtered_query(
        self,
        query: Select,
        value: Any,
        model: Any,
    ) -> Select:
        # если “Все” — ничего не делаем
        if not value:
            return query

        # приводим к datetime
        now = datetime.utcnow()
        today = date.today()
        if value == "today":
            start = datetime.combine(today, datetime.min.time())
            end   = start + timedelta(days=1)
        elif value == "yesterday":
            start = datetime.combine(today - timedelta(days=1), datetime.min.time())
            end   = start + timedelta(days=1)
        elif value == "week":
            start = now - timedelta(days=7)
            end   = now
        elif value == "month":
            start = now - timedelta(days=30)
            end   = now
        else:
            return query

        column_obj = get_column_obj(self.column, model)
        return query.filter(
            and_(
                column_obj >= start,
                column_obj <  end
            )
        )


class AuditLogAdmin(ModelView, model=AuditLog):
    """Админка для журнала действий"""

    column_list = [
        AuditLog.id, AuditLog.entity, AuditLog.action,
        AuditLog.timestamp
    ]
    column_searchable_list = [AuditLog.entity, AuditLog.action]
    column_filters = [
        AllUniqueStringValuesFilter(AuditLog.entity),
        AllUniqueStringValuesFilter(AuditLog.action),
        RelativeDateFilter(AuditLog.timestamp, title="Время логирование")
    ]
    column_sortable_list = [AuditLog.id, AuditLog.timestamp]
    can_edit = False
    can_create = False
    can_delete = False


class VisitLogAdmin(ModelView, model=VisitLog):
    """Админка для журнала посещений"""

    column_list = [
        VisitLog.id, VisitLog.request_person_id, VisitLog.checkpoint_id,
        VisitLog.check_in_time, VisitLog.check_out_time
    ]
    column_filters = [
        ForeignKeyFilter(VisitLog.checkpoint_id, Checkpoint.name, foreign_model=Checkpoint),
        RelativeDateFilter(VisitLog.check_in_time, title="Время заезда")
    ]
    column_sortable_list = [VisitLog.id, VisitLog.check_in_time, VisitLog.check_out_time]
    can_edit = False
    can_create = False


class NotificationAdmin(ModelView, model=Notification):
    """Админка для уведомлений"""

    column_list = [
        Notification.id, Notification.user_id, Notification.message,
        Notification.is_read, Notification.timestamp
    ]
    column_searchable_list = [Notification.message]
    column_filters = [
        BooleanFilter(Notification.is_read),
        RelativeDateFilter(Notification.timestamp, title="Время уведомления")
    ]
    column_sortable_list = [Notification.id, Notification.timestamp]


def create_admin(app) -> Admin:
    """Создание и настройка админки"""

    admin = Admin(app, engine)

    admin.add_view(UserAdmin)
    admin.add_view(RoleAdmin)
    admin.add_view(DepartmentAdmin)
    admin.add_view(RequestAdmin)
    admin.add_view(RequestPersonAdmin)
    admin.add_view(CheckpointAdmin)
    admin.add_view(BlackListAdmin)
    admin.add_view(AuditLogAdmin)
    admin.add_view(VisitLogAdmin)
    admin.add_view(NotificationAdmin)

    return admin
