from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Enum, Text, JSON, DateTime, Date, Table
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import relationship
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


class RequestDuration(enum.Enum):
    SHORT_TERM = "SHORT_TERM"
    LONG_TERM  = "LONG_TERM"


class DepartmentType(enum.Enum):
    COMPANY = "COMPANY"
    DEPARTMENT = "DEPARTMENT"
    DIVISION = "DIVISION"
    UNIT = "UNIT"


class Department(Base):
    __tablename__ = "departments"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    parent_id = Column(Integer, ForeignKey("departments.id"), nullable=True)
    type = Column(Enum(DepartmentType))

    parent = relationship("Department", remote_side=[id], back_populates="children")
    children = relationship("Department", back_populates="parent")
    users = relationship("User", back_populates="department")


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


class ApprovalStep(enum.Enum):
    DCS = "DCS"
    ZD = "ZD"


class ApprovalStatus(enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    DECLINED = "DECLINED"


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
    data = Column(MutableDict.as_mutable(JSONB), nullable=True) # Renamed from metadata to data

    actor = relationship("User", back_populates="audit_logs")


class Role(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    description = Column(String, nullable=True)
    code = Column(String, unique=True, nullable=True, index=True)

    users = relationship("User", back_populates="role", lazy="dynamic")


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
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=True) # Added, nullable for now
    department = relationship("Department", back_populates="users")
    approvals = relationship("Approval", back_populates="approver")
    audit_logs = relationship("AuditLog", back_populates="actor")
    created_blacklist_entries = relationship("BlackList", foreign_keys="[BlackList.added_by]", back_populates="added_by_user")
    removed_blacklist_entries = relationship("BlackList", foreign_keys="[BlackList.removed_by]", back_populates="removed_by_user")
    notifications = relationship("Notification", back_populates="recipient", foreign_keys="[Notification.user_id]")


    requests = relationship("Request", back_populates="creator") # Renamed from user


class Request(Base):
    __tablename__ = "requests"

    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    start_date = Column(Date, nullable=False) # Added as per detailed instructions
    end_date = Column(Date, nullable=False) # Added as per detailed instructions
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

    request_persons = relationship("RequestPerson", back_populates="request")
    approvals = relationship("Approval", back_populates="request")
    notifications = relationship("Notification", back_populates="request", foreign_keys="[Notification.related_request_id]")
    checkpoints = relationship(
        "Checkpoint",
        secondary=request_checkpoint,
        back_populates="requests"
    )


class RequestPerson(Base):
    __tablename__ = "request_persons"

    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(Integer, ForeignKey("requests.id"))
    firstname = Column(String)
    lastname = Column(String)
    surname = Column(String, nullable=True)
    birth_date = Column(Date, nullable=False)
    doc_type = Column(String, nullable=False)
    doc_number = Column(String, nullable=False)
    doc_start_date = Column(Date, nullable=False)
    doc_end_date = Column(Date, nullable=False)
    gender = Column(Enum(GenderEnum), nullable=False)
    citizenship = Column(String, nullable=False) # Storing as string, not FK to Citizenship
    company = Column(String, nullable=False)
    is_entered = Column(Boolean, nullable=False, default=False)

    request = relationship("Request", back_populates="request_persons")


class BlackList(Base):
    __tablename__ = "blacklist"

    id = Column(Integer, primary_key=True, index=True)
    firstname = Column(String)
    lastname = Column(String)
    surname = Column(String, nullable=True)
    birth_date = Column(Date, nullable=False)
    doc_type = Column(String, nullable=False)
    doc_number = Column(String, nullable=False)
    doc_start_date = Column(Date, nullable=False)
    doc_end_date = Column(Date, nullable=False)
    citizenship = Column(String, nullable=False)  # Storing as string, not FK to Citizenship
    company = Column(String, nullable=False)
    reason = Column(Text, nullable=True) # Changed from String to Text for potentially longer reasons

    added_by = Column(Integer, ForeignKey("users.id"))
    added_at = Column(DateTime(timezone=True), server_default=func.now())
    removed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    removed_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(String, default='ACTIVE', index=True) # e.g. ACTIVE, INACTIVE

    added_by_user = relationship("User", foreign_keys=[added_by], back_populates="created_blacklist_entries")
    removed_by_user = relationship("User", foreign_keys=[removed_by], back_populates="removed_blacklist_entries")


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False) # Recipient
    message = Column(String, nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    is_read = Column(Boolean, default=False, nullable=False)
    related_request_id = Column(Integer, ForeignKey("requests.id"), nullable=True)

    recipient = relationship("User", back_populates="notifications", foreign_keys=[user_id])
    request = relationship("Request", back_populates="notifications", foreign_keys=[related_request_id])
