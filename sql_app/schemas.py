from __future__ import annotations
from typing import Optional, List, Any
from pydantic import BaseModel, Field
from datetime import datetime, date
import enum

from .models import GenderEnum, RequestDuration


# ------------- Enums (mirroring models.py) -------------
class DepartmentTypeEnum(str, enum.Enum):
    COMPANY = "COMPANY"
    DEPARTMENT = "DEPARTMENT"
    DIVISION = "DIVISION"
    UNIT = "UNIT"


class ApprovalStepEnum(str, enum.Enum):
    DCS = "DCS"
    ZD = "ZD"

class ApprovalStatusEnum(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    DECLINED = "DECLINED"


class RequestStatusEnum(str, enum.Enum):

    PENDING_USB = "PENDING_USB"      # Ожидает одобрения УСБ
    APPROVED_USB = "APPROVED_USB"    # Одобрено УСБ
    DECLINED_USB = "DECLINED_USB"    # Отклонено УСБ

    PENDING_AS = "PENDING_AS"        # Ожидает одобрения АС
    APPROVED_AS = "APPROVED_AS"      # Одобрено АС (финальное одобрение)
    DECLINED_AS = "DECLINED_AS"      # Отклонено АС

    ISSUED = "ISSUED"                # Пропуск выдан
    CLOSED = "CLOSED"                # Заявка закрыта/отменена

class RequestPersonStatusEnum(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"

class NationalityTypeEnum(str, enum.Enum):
    KZ = "KZ"
    FOREIGN = "FOREIGN"


# ------------- Department Schemas -------------
class DepartmentBase(BaseModel):
    name: str
    type: DepartmentTypeEnum
    parent_id: Optional[int] = None

class DepartmentCreate(DepartmentBase):
    pass

class DepartmentUpdate(DepartmentBase):
    name: Optional[str] = None
    type: Optional[DepartmentTypeEnum] = None
    parent_id: Optional[int] = None # Explicitly allow setting parent_id to null

class DepartmentInDBBase(DepartmentBase):
    id: int

    class Config:
        from_attributes = True

class Department(DepartmentInDBBase):
    children: List[Department] = [] # For hierarchical representation

# Self-referencing models need this
Department.update_forward_refs()


# ------------- Checkpoint Schemas -------------

class CheckpointBase(BaseModel):
    code: str
    name: str

class CheckpointCreate(CheckpointBase):
    pass

class CheckpointUpdate(CheckpointBase):
    code: Optional[str] = None
    name: Optional[str] = None

class CheckpointInDBBase(CheckpointBase):
    id: int

    class Config:
        from_attributes = True

class Checkpoint(CheckpointInDBBase):
    pass


# ------------- Role Schemas (Modified) -------------

class RoleBase(BaseModel):
    name: str
    description: Optional[str] = None
    code: Optional[str] = None

class RoleCreate(RoleBase):
    pass

class RoleUpdate(RoleBase):
    name: Optional[str] = None

class RoleInDBBase(RoleBase):
    id: int

    class Config:
        from_attributes = True

class Role(RoleInDBBase):
    pass


# ------------- User Schemas (Modified) -------------
# Forward declaration for nested schemas if User is defined before them
class DepartmentSmall(BaseModel): # A smaller version for nesting if needed, or use Department
    id: int
    name: str
    type: DepartmentTypeEnum
    class Config:
        from_attributes = True

class UserBase(BaseModel):
    username: str
    full_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    is_active: bool = True
    role_id: Optional[int] = None
    department_id: Optional[int] = None

class UserCreate(UserBase):
    hashed_password: str

class UserUpdate(BaseModel): # Changed from UserBase to BaseModel to list all fields explicitly
    username: Optional[str] = None
    full_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    is_active: Optional[bool] = None
    role_id: Optional[int] = None
    department_id: Optional[int] = None
    hashed_password: Optional[str] = None # Allow password update


class UserInDBBase(UserBase):
    id: int
    role: Optional[Role] = None
    department: Optional[DepartmentSmall] = None # Using smaller Department schema for nesting

    class Config:
        from_attributes = True

class User(UserInDBBase):
    pass

class UserForAudit(BaseModel): # Simplified User for Audit Log actor
    id: int
    username: str
    full_name: Optional[str] = None
    class Config:
        from_attributes = True

class UserForApproval(BaseModel): # Simplified User for Approval approver
    id: int
    username: str
    full_name: Optional[str] = None
    class Config:
        from_attributes = True

class UserForBlackList(BaseModel): # Simplified User for BlackList user fields
    id: int
    username: str
    full_name: Optional[str] = None
    class Config:
        from_attributes = True

class UserForRecipient(BaseModel): # Simplified User for Notification recipient
    id: int
    username: str
    full_name: Optional[str] = None
    class Config:
        from_attributes = True

# ------------- RequestPerson Schemas -------------

from pydantic import BaseModel, Field, validator, root_validator

class RequestPersonBase(BaseModel):
    firstname: str
    lastname: str
    surname: Optional[str] = None
    birth_date: date

    nationality: NationalityTypeEnum = NationalityTypeEnum.KZ
    iin: Optional[str] = None

    # Foreign document details
    doc_type: Optional[str] = None # E.g., "PASSPORT"
    doc_number: Optional[str] = None
    doc_start_date: Optional[date] = None
    doc_end_date: Optional[date] = None

    gender: GenderEnum # Made mandatory as per model
    citizenship: str # Country name for FOREIGN, "Kazakhstan" for KZ
    company: str
    is_entered: Optional[bool] = False
    status: RequestPersonStatusEnum = RequestPersonStatusEnum.PENDING
    rejection_reason: Optional[str] = None

    @root_validator(pre=True) # Changed to pre=True to ensure nationality is available
    @classmethod
    def check_iin_or_doc_number(cls, values):
        nationality = values.get('nationality')
        iin = values.get('iin')
        doc_number = values.get('doc_number')
        doc_type = values.get('doc_type') # Added doc_type to the check

        if nationality == NationalityTypeEnum.KZ:
            if not iin:
                raise ValueError("IIN is required for KZ nationals.")
            if len(iin) != 12 or not iin.isdigit():
                raise ValueError("IIN must be 12 digits.")
            # For KZ nationals, foreign doc fields can be optional or cleared
            values['doc_type'] = None
            values['doc_number'] = None
            values['doc_start_date'] = None
            values['doc_end_date'] = None
        elif nationality == NationalityTypeEnum.FOREIGN:
            if not doc_number:
                raise ValueError("Document number is required for foreign nationals.")
            if not doc_type:
                raise ValueError("Document type is required for foreign nationals.")
            # For foreign nationals, IIN can be optional or cleared
            values['iin'] = None
        else: # Should not happen if enum is used correctly
            raise ValueError("Invalid nationality type.")

        # Ensure citizenship matches nationality
        if nationality == NationalityTypeEnum.KZ and values.get('citizenship', '').lower() != "kazakhstan":
            # Overwrite or raise error. For now, let's try to overwrite for simplicity during creation.
            # Consider making this stricter if needed.
            values['citizenship'] = "Kazakhstan"
            # raise ValueError("Citizenship must be 'Kazakhstan' for KZ nationals.")
        elif nationality == NationalityTypeEnum.FOREIGN and values.get('citizenship', '').lower() == "kazakhstan":
            raise ValueError("Citizenship cannot be 'Kazakhstan' for FOREIGN nationals.")
        elif nationality == NationalityTypeEnum.FOREIGN and not values.get('citizenship'):
             raise ValueError("Citizenship is required for FOREIGN nationals.")


        return values

class RequestPersonCreate(RequestPersonBase):
    pass

class RequestPersonUpdate(BaseModel):
    firstname: Optional[str] = None
    lastname: Optional[str] = None
    surname: Optional[str] = None
    birth_date: Optional[date] = None

    nationality: Optional[NationalityTypeEnum] = None
    iin: Optional[str] = None

    doc_type: Optional[str] = None
    doc_number: Optional[str] = None
    doc_start_date: Optional[date] = None
    doc_end_date: Optional[date] = None

    gender: Optional[GenderEnum] = None
    citizenship: Optional[str] = None
    company: Optional[str] = None
    status: Optional[RequestPersonStatusEnum] = None
    rejection_reason: Optional[str] = None

    # TODO: Add root_validator for update if nationality changes, to ensure consistency
    # For example, if nationality changes from KZ to FOREIGN, IIN should be cleared and doc_number becomes required.
    # This can be complex. For now, assume PATCH updates individual fields and relies on full object validation elsewhere if needed.


class RequestPersonInDBBase(RequestPersonBase):
    id: int
    request_id: int
    # status and rejection_reason are inherited from RequestPersonBase

    class Config:
        from_attributes = True

class RequestPerson(RequestPersonInDBBase):
    # All fields from RequestPersonInDBBase are inherited
    pass


# ------------- Request Schemas (Modified) -------------

class RequestBase(BaseModel):
    start_date: date
    end_date: date
    arrival_purpose: str
    accompanying: str
    contacts_of_accompanying: str
    duration: Optional[RequestDuration]

class RequestCreate(RequestBase):
    checkpoint_ids: List[int]
    request_persons: List[RequestPersonCreate]


class RequestUpdate(RequestBase):
    checkpoint_ids: List[int] = None
    status: Optional[RequestStatusEnum] = None # Use Enum for updates too
    request_persons: Optional[List[RequestPersonUpdate]] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    arrival_purpose: Optional[str] = None
    accompanying: Optional[str] = None
    contacts_of_accompanying: Optional[str] = None
# Removed duplicated RequestUpdate here

class RequestInDBBase(RequestBase): # Inherits start_date, end_date from RequestBase
    id: int
    creator_id: int
    created_at: datetime
    status: RequestStatusEnum # Ensure status in DB is also using the enum or compatible string
    creator: Optional[User] = None # Nested User schema
    checkpoints:    List[CheckpointInDBBase] = [] # Nested Checkpoint schema
    request_persons: List[RequestPerson] = []

    class Config:
        from_attributes = True

class Request(RequestInDBBase):
    pass

# ------------- Approval Schemas -------------

class ApprovalBase(BaseModel):
    step: ApprovalStepEnum
    status: ApprovalStatusEnum = ApprovalStatusEnum.PENDING
    comment: Optional[str] = None

class ApprovalCreate(ApprovalBase):
    request_id: int
    approver_id: int # Usually current user or assigned

class ApprovalUpdate(ApprovalBase):
    step: Optional[ApprovalStepEnum] = None
    status: Optional[ApprovalStatusEnum] = None

class ApprovalInDBBase(ApprovalBase):
    id: int
    request_id: int
    approver_id: int
    timestamp: datetime
    approver: Optional[UserForApproval] = None # Simplified User

    class Config:
        from_attributes = True

class Approval(ApprovalInDBBase):
    request: Optional[Request] = None # Full Request, could be cyclical, use RequestInDBBase or smaller version if needed


# ------------- AuditLog Schemas -------------

class AuditLogBase(BaseModel):
    entity: str
    entity_id: int
    action: str
    data: Optional[dict | list] = None # Changed from 'metadata'

class AuditLogCreate(AuditLogBase):
    actor_id: Optional[int] = None # Can be null if system action

class AuditLogUpdate(AuditLogBase): # Audit logs are typically not updated
    pass

class AuditLogInDBBase(AuditLogBase):
    id: int
    timestamp: datetime
    actor_id: Optional[int] = None
    actor: Optional[UserForAudit] = None # Simplified User

    class Config:
        from_attributes = True

class AuditLog(AuditLogInDBBase):
    pass


# ------------- BlackList Schemas (Modified) -------------

class BlackListBase(BaseModel):
    firstname: str
    lastname: str
    surname: Optional[str] = None
    birth_date: date # Keep for matching

    nationality: Optional[NationalityTypeEnum] = None # Optional on creation, can be inferred or set
    iin: Optional[str] = None

    doc_type: Optional[str] = None
    doc_number: Optional[str] = None
    # doc_start_date, doc_end_date not primary for blacklist record, but could be added if needed
    citizenship: Optional[str] = None # Country if foreign

    company: Optional[str] = None # Company might not always be known
    reason: str # Reason for blacklisting should be mandatory
    status: str = 'ACTIVE'

    @root_validator(pre=True)
    @classmethod
    def check_blacklist_identifier(cls, values):
        iin = values.get('iin')
        doc_number = values.get('doc_number')
        nationality = values.get('nationality')

        if nationality == NationalityTypeEnum.KZ:
            if not iin:
                raise ValueError("IIN is required for blacklisting a KZ national if nationality is specified as KZ.")
            if len(iin) != 12 or not iin.isdigit():
                raise ValueError("IIN must be 12 digits.")
            values['doc_number'] = None # Clear foreign doc if KZ
        elif nationality == NationalityTypeEnum.FOREIGN:
            if not doc_number:
                raise ValueError("Document number is required for blacklisting a foreign national if nationality is specified as FOREIGN.")
            values['iin'] = None # Clear IIN if foreign
        elif not iin and not doc_number: # If nationality is not specified, at least one identifier must be present
             raise ValueError("Either IIN or Document Number must be provided for blacklisting.")

        # If IIN is provided, try to infer nationality as KZ if not given
        if iin and not nationality:
            values['nationality'] = NationalityTypeEnum.KZ
        # If doc_number is provided and not IIN, try to infer nationality as FOREIGN if not given
        elif doc_number and not iin and not nationality:
            values['nationality'] = NationalityTypeEnum.FOREIGN

        return values

class BlackListCreate(BlackListBase):
    pass

class BlackListUpdate(BaseModel): # Allow partial updates
    firstname: Optional[str] = None
    lastname: Optional[str] = None
    surname: Optional[str] = None
    birth_date: Optional[date] = None
    nationality: Optional[NationalityTypeEnum] = None
    iin: Optional[str] = None
    doc_type: Optional[str] = None
    doc_number: Optional[str] = None
    citizenship: Optional[str] = None
    company: Optional[str] = None
    reason: Optional[str] = None
    status: Optional[str] = None

class BlackListInDBBase(BlackListBase):
    id: int
    added_by: int
    added_at: datetime
    removed_by: Optional[int] = None
    removed_at: Optional[datetime] = None
    added_by_user: Optional[UserForBlackList] = None # Simplified User
    removed_by_user: Optional[UserForBlackList] = None # Simplified User


    class Config:
        from_attributes = True

class BlackList(BlackListInDBBase):
    pass


# ------------- Auth Schemas (Mostly Unchanged but ensure they exist) -------------

class Token(BaseModel):
    access_token: str
    refresh_token: str # Added refresh token for completeness
    token_type: str = "bearer"

class TokenData(BaseModel):
    user_id: Optional[int] = None # Changed from username to user_id to align with common practice

class UserLogin(BaseModel):
    username: str
    password: str

# ------------- Approval Comment Payload -------------

class ApprovalCommentPayload(BaseModel):
    comment: Optional[str] = None

# Ensure forward references are resolved for complex nested schemas
# Pydantic v1.x might need this for complex cases, especially with List[RecursiveType]
# For Pydantic V2, this is often handled automatically.
Department.update_forward_refs()
UserInDBBase.update_forward_refs()
RequestInDBBase.update_forward_refs()
Approval.update_forward_refs()
AuditLogInDBBase.update_forward_refs()
BlackListInDBBase.update_forward_refs()
# Notification.update_forward_refs() # If Notification responses include complex nested types that need it.
# For now, Notification response (Notification) uses UserForRecipient and RequestSmall which are defined before it.

# ------------- Notification Schemas -------------

class RequestSmall(BaseModel): # Simplified Request for Notification
    id: int
    status: RequestStatusEnum
    created_at: datetime
    # Potentially add creator_id or a very small creator summary if needed
    class Config:
        from_attributes = True

class NotificationBase(BaseModel):
    user_id: int # Recipient user ID
    message: str
    is_read: bool = False
    related_request_id: Optional[int] = None

class NotificationCreate(NotificationBase):
    pass

class NotificationInDBBase(NotificationBase):
    id: int
    timestamp: datetime

    class Config:
        from_attributes = True

class Notification(NotificationInDBBase):
    recipient: Optional[UserForRecipient] = None
    request: Optional[RequestSmall] = None # Simplified Request

# ------------- VisitLog Schemas -------------

# Simplified RequestPerson schema for VisitLog
class RequestPersonForVisitLog(BaseModel):
    id: int
    firstname: str
    lastname: str
    surname: Optional[str] = None
    company: Optional[str] = None
    status: Optional[RequestPersonStatusEnum] = None # To show status in logs
    rejection_reason: Optional[str] = None          # To show rejection reason in logs


    class Config:
        from_attributes = True

# Simplified Request schema for VisitLog
class RequestForVisitLog(BaseModel):
    id: int
    status: RequestStatusEnum # Assuming RequestStatusEnum is defined
    start_date: date
    end_date: date
    # creator_id: int # Optional: if needed to know who created the request
    creator_full_name: Optional[str] = None
    creator_department_name: Optional[str] = None

    class Config:
        from_attributes = True

class VisitLogBase(BaseModel):
    request_id: int
    request_person_id: int
    checkpoint_id: Optional[int] = None # Made optional here, but will be required in VisitLogCreate by KPP
    check_out_time: Optional[datetime] = None

class VisitLogCreate(VisitLogBase):
    checkpoint_id: int # KPP must provide this at entry
    # request_id and request_person_id are inherited and mandatory

class VisitLogUpdate(BaseModel):
    check_out_time: Optional[datetime] = None

class VisitLogInDBBase(VisitLogBase):
    id: int
    check_in_time: datetime
    checkpoint_id: int # Should be non-nullable in DB after KPP provides it

    class Config:
        from_attributes = True

class SimplifiedCheckpointForVisitLog(BaseModel):
    id: int
    name: str
    code: str
    class Config:
        from_attributes = True

class VisitLog(VisitLogInDBBase):
    request: Optional[RequestForVisitLog] = None
    request_person: Optional[RequestPersonForVisitLog] = None
    checkpoint: Optional[SimplifiedCheckpointForVisitLog] = None # To show checkpoint details
