from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Enum, Text, JSON, DateTime, Date, Table
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import relationship
from sqlalchemy.orm.exc import DetachedInstanceError
from sqlalchemy.sql import func
import enum


from .database import Base


# 1. Ассоциационная таблица
request_checkpoint = Table(
    "request_checkpoint",
    Base.metadata,
    Column("request_id", ForeignKey("requests.id"), primary_key=True),
    Column("checkpoint_id", ForeignKey("checkpoints.id"), primary_key=True)
)


class GenderEnum(enum.Enum):
    MALE = "MALE"
    FEMALE = "FEMALE"

    def __str__(self) -> str:
        return self.value


class RequestDuration(enum.Enum):
    SHORT_TERM = "SHORT_TERM"
    LONG_TERM  = "LONG_TERM"

    def __str__(self) -> str:
        return self.value


class DepartmentType(enum.Enum):
    COMPANY = "COMPANY"
    DEPARTMENT = "DEPARTMENT"
    DIVISION = "DIVISION"
    UNIT = "UNIT"

    def __str__(self) -> str:
        return self.value


class RequestPersonStatus(enum.Enum):
    PENDING_USB = "PENDING_USB"  # Ожидает одобрения УСБ
    APPROVED_USB = "APPROVED_USB"  # Одобрено УСБ
    DECLINED_USB = "DECLINED_USB"  # Отклонено УСБ

    PENDING_AS = "PENDING_AS"  # Ожидает одобрения АС
    APPROVED_AS = "APPROVED_AS"  # Одобрено АС (финальное одобрение)
    DECLINED_AS = "DECLINED_AS"

    def __str__(self) -> str:
        return self.value


class NationalityType(enum.Enum):
    KZ = "KZ"       # Kazakhstan Citizen
    FOREIGN = "FOREIGN" # Foreign Citizen

    def __str__(self) -> str:
        return self.value


class Department(Base):
    __tablename__ = "departments"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    parent_id = Column(Integer, ForeignKey("departments.id"), nullable=True)
    type = Column(Enum(DepartmentType))

    parent = relationship("Department", remote_side=[id], back_populates="children")
    children = relationship("Department", back_populates="parent")
    users = relationship("User", back_populates="department")

    def __str__(self):
        return self.get_full_name()

    def get_full_name(self):
        try:
            name_chain = [self.name]
            parent = self.parent
            while parent:
                name_chain.insert(0, parent.name)
                parent = parent.parent
            return "->".join(name_chain)
        except DetachedInstanceError:
            return self.name  # fallback


class Checkpoint(Base):
    __tablename__ = "checkpoints"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, unique=True, index=True)
    name = Column(String)

    requests = relationship(
        "Request",
        secondary=request_checkpoint,
        back_populates="checkpoints"
    )

    def __str__(self):
        return f"{self.id}) {self.name}"


class ApprovalStep(enum.Enum):
    DCS = "DCS"
    ZD = "ZD"

    def __str__(self) -> str:
        return self.value


class ApprovalStatus(enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    DECLINED = "DECLINED"

    def __str__(self) -> str:
        return self.value


class Approval(Base):
    __tablename__ = "approvals"

    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(Integer, ForeignKey("requests.id"))
    approver_id = Column(Integer, ForeignKey("users.id"))
    step = Column(Enum(ApprovalStep))
    status = Column(Enum(ApprovalStatus))
    comment = Column(Text, nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    request = relationship("Request", back_populates="approvals")
    approver = relationship("User", back_populates="approvals")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    entity = Column(String)
    entity_id = Column(Integer)
    action = Column(String)
    actor_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    # Исправлено: используем JSON вместо JSONB для совместимости с SQLite
    data = Column(MutableDict.as_mutable(JSON), nullable=True)

    actor = relationship("User", back_populates="audit_logs")

    def __str__(self):
        return f"{self.id}) {self.data}"


class Role(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    description = Column(String, nullable=True)
    code = Column(String, unique=True, nullable=True, index=True)

    users = relationship("User", back_populates="role", lazy="selectin")

    def __str__(self):
        return f"{self.name} - {self.description}"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, index=True)
    full_name = Column(String)
    email = Column(String, nullable=True, index=True)
    phone = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    hashed_password = Column(String)

    role_id = Column(Integer, ForeignKey("roles.id"))
    role = relationship("Role", back_populates="users")
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=True)
    department = relationship("Department", back_populates="users")
    approvals = relationship("Approval", back_populates="approver")
    audit_logs = relationship("AuditLog", back_populates="actor")
    created_blacklist_entries = relationship("BlackList", foreign_keys="[BlackList.added_by]", back_populates="added_by_user")
    removed_blacklist_entries = relationship("BlackList", foreign_keys="[BlackList.removed_by]", back_populates="removed_by_user")
    notifications = relationship("Notification", back_populates="recipient", foreign_keys="[Notification.user_id]")

    requests = relationship("Request", back_populates="creator")
    # visit_logs relationship removed from User, as VisitLog will now link to RequestPerson

    def __str__(self):
        return f"{self.id}) логин ({self.username}), ФИО ({self.full_name}), тел ({self.phone})"


class Request(Base):
    __tablename__ = "requests"

    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    status = Column(String, default='DRAFT')
    arrival_purpose = Column(String, nullable=False)
    accompanying = Column(String, nullable=False)
    contacts_of_accompanying = Column(String, nullable=False)
    duration = Column(
        Enum(RequestDuration),
        nullable=False,
        server_default=RequestDuration.SHORT_TERM.value
    )

    creator_id = Column(Integer, ForeignKey("users.id"))
    creator = relationship("User", back_populates="requests")

    request_persons = relationship("RequestPerson", back_populates="request", passive_deletes=True)
    approvals = relationship("Approval", back_populates="request")
    notifications = relationship("Notification", back_populates="request", foreign_keys="[Notification.related_request_id]")
    checkpoints = relationship(
        "Checkpoint",
        secondary=request_checkpoint,
        back_populates="requests"
    )
    visit_logs = relationship("VisitLog", back_populates="request", passive_deletes=True)

    def __str__(self):
        return f"{self.id}) {self.status} {self.start_date}-{self.end_date} {self.arrival_purpose} {self.accompanying} {self.contacts_of_accompanying} {self.creator_id}"


class RequestPerson(Base):
    __tablename__ = "request_persons"

    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(Integer, ForeignKey("requests.id", ondelete="CASCADE"))
    firstname = Column(String)
    lastname = Column(String)
    surname = Column(String, nullable=True)
    birth_date = Column(Date, nullable=False)

    nationality = Column(Enum(NationalityType), nullable=False, server_default=NationalityType.KZ.value)
    iin = Column(String(12), nullable=True, index=True) # Indexed for potential lookups

    doc_type = Column(String, nullable=True) # Nullable if KZ and IIN is provided
    doc_number = Column(String, nullable=True, index=True) # Nullable if KZ and IIN is provided, indexed
    doc_start_date = Column(Date, nullable=True) # Nullable if KZ
    doc_end_date = Column(Date, nullable=True)   # Nullable if KZ

    gender = Column(Enum(GenderEnum), nullable=False)
    citizenship = Column(String, nullable=False) # For foreign: country name. For KZ: "Kazakhstan"
    company = Column(String, nullable=False)
    is_entered = Column(Boolean, nullable=False, default=False)
    status = Column(Enum(RequestPersonStatus), nullable=False, server_default=RequestPersonStatus.PENDING_USB.value, default=RequestPersonStatus.PENDING_USB)
    rejection_reason = Column(Text, nullable=True)

    request = relationship("Request", back_populates="request_persons")
    visit_logs = relationship("VisitLog", back_populates="request_person", passive_deletes=True) # Added back_populates

    def __str__(self):
        if self.iin and self.doc_number is None:
            return f"{self.lastname} {self.firstname} {self.company}"
        elif self.iin is not None:
            return f"{self.lastname} {self.firstname} {self.iin} {self.company}"
        else:
            return f"{self.lastname} {self.firstname} {self.doc_number} {self.company}"


class VisitLog(Base):
    __tablename__ = "visit_logs"

    id = Column(Integer, primary_key=True, index=True)
    # request_id is still relevant to know which overall request this visit belongs to.
    request_id = Column(Integer, ForeignKey("requests.id", ondelete="CASCADE"), nullable=False)
    request_person_id = Column(Integer, ForeignKey("request_persons.id", ondelete="CASCADE"), nullable=False)
    check_in_time = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    check_out_time = Column(DateTime(timezone=True), nullable=True)
    checkpoint_id = Column(Integer, ForeignKey("checkpoints.id"), nullable=False)

    request = relationship("Request", back_populates="visit_logs")
    request_person = relationship("RequestPerson", back_populates="visit_logs")
    checkpoint = relationship("Checkpoint") # Added relationship to Checkpoint

    # NOTE: Data Retention Policy: VisitLog records should be managed (e.g., archived or purged)
    # after 18 months as per operational requirements. This is typically handled by
    # database maintenance scripts or scheduled jobs, not directly in application API logic
    # unless specific admin endpoints for data management are implemented.

    def __str__(self):
        # Форматируем время входа
        check_in = self.check_in_time.strftime("%Y-%m-%d %H:%M")
        # Если нужно форматировать время выхода — аналогично, с защитой на None
        if self.check_out_time:
            check_out = self.check_out_time.strftime("%Y-%m-%d %H:%M")
        else:
            check_out = "/*/"

        return f"request_id={self.request_id}, person_id={self.request_person_id}, {check_in}-{check_out}, KPP-{self.checkpoint_id}"

class BlackList(Base):
    __tablename__ = "blacklist"

    id = Column(Integer, primary_key=True, index=True)
    firstname = Column(String)
    lastname = Column(String)
    surname = Column(String, nullable=True)
    birth_date = Column(Date, nullable=False) # Keep for matching

    nationality = Column(Enum(NationalityType), nullable=True) # To distinguish IIN from foreign docs
    iin = Column(String(12), nullable=True, index=True)

    # doc_type, doc_number, etc. for foreign documents or if IIN is not the primary blacklist key
    doc_type = Column(String, nullable=True)
    doc_number = Column(String, nullable=True, index=True)
    # doc_start_date and doc_end_date might be less relevant for blacklist matching than the number itself
    # citizenship can be used to store the country for foreign nationals
    citizenship = Column(String, nullable=True)

    company = Column(String, nullable=True) # Company might not always be known for blacklist
    reason = Column(Text, nullable=True)

    added_by = Column(Integer, ForeignKey("users.id"))
    added_at = Column(DateTime(timezone=True), server_default=func.now())
    removed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    removed_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(String, default='ACTIVE', index=True)

    added_by_user = relationship("User", foreign_keys=[added_by], back_populates="created_blacklist_entries")
    removed_by_user = relationship("User", foreign_keys=[removed_by], back_populates="removed_blacklist_entries")

    def __str__(self):
        return f"{self.lastname} {self.firstname} {self.iin} {self.company} {self.citizenship} {self.reason} {self.added_by}"


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    message = Column(String, nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    is_read = Column(Boolean, default=False, nullable=False)
    related_request_id = Column(Integer, ForeignKey("requests.id"), nullable=True)

    recipient = relationship("User", back_populates="notifications", foreign_keys=[user_id])
    request = relationship("Request", back_populates="notifications", foreign_keys=[related_request_id])

    def __str__(self):
        return f"{self.id} {self.user_id} {self.message} {self.is_read}"