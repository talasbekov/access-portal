from __future__ import annotations
from typing import Optional, List, Any
from pydantic import BaseModel, Field
from datetime import datetime
import enum

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
    DRAFT = "DRAFT"
    PENDING_DCS = "PENDING_DCS"
    APPROVED_DCS = "APPROVED_DCS"
    DECLINED_DCS = "DECLINED_DCS"
    PENDING_ZD = "PENDING_ZD"
    APPROVED_ZD = "APPROVED_ZD"
    DECLINED_ZD = "DECLINED_ZD"
    ISSUED = "ISSUED" # Pass issued
    CLOSED = "CLOSED" # Request completed or expired

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
        orm_mode = True

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
        orm_mode = True

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
        orm_mode = True

class Role(RoleInDBBase):
    pass


# ------------- User Schemas (Modified) -------------
# Forward declaration for nested schemas if User is defined before them
class DepartmentSmall(BaseModel): # A smaller version for nesting if needed, or use Department
    id: int
    name: str
    type: DepartmentTypeEnum
    class Config:
        orm_mode = True

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
        orm_mode = True

class User(UserInDBBase):
    pass

class UserForAudit(BaseModel): # Simplified User for Audit Log actor
    id: int
    username: str
    full_name: Optional[str] = None
    class Config:
        orm_mode = True

class UserForApproval(BaseModel): # Simplified User for Approval approver
    id: int
    username: str
    full_name: Optional[str] = None
    class Config:
        orm_mode = True

class UserForBlackList(BaseModel): # Simplified User for BlackList user fields
    id: int
    username: str
    full_name: Optional[str] = None
    class Config:
        orm_mode = True

class UserForRecipient(BaseModel): # Simplified User for Notification recipient
    id: int
    username: str
    full_name: Optional[str] = None
    class Config:
        orm_mode = True

# ------------- RequestPerson Schemas -------------

class RequestPersonBase(BaseModel):
    full_name: str
    doc_type: Optional[str] = None
    doc_number: Optional[str] = None
    citizenship: Optional[str] = None
    company: Optional[str] = None

class RequestPersonCreate(RequestPersonBase):
    pass # request_id removed as per plan, will be set by path/system

class RequestPersonUpdate(RequestPersonBase):
    full_name: Optional[str] = None


class RequestPersonInDBBase(RequestPersonBase):
    id: int
    request_id: int

    class Config:
        orm_mode = True

class RequestPerson(RequestPersonInDBBase):
    pass


# ------------- Request Schemas (Modified) -------------

class RequestBase(BaseModel):
    checkpoint_id: int
    # status: str = 'DRAFT' # Will be RequestStatusEnum
    # Removed: purpose, visit_type, visit_date, req_author, req_sysdata, convoy
    # req_date is replaced by created_at (handled by DB)
    start_date: datetime # For determining single/multi-day pass
    end_date: datetime   # For determining single/multi-day pass
    # Pass_type can be derived or explicitly set. For now, deriving.

class RequestCreate(RequestBase):
    # creator_id will typically be set by the current authenticated user
    # request_persons can be provided on creation
    request_persons: List[RequestPersonBase] = [] # Changed from RequestPersonCreate
    status: RequestStatusEnum = RequestStatusEnum.DRAFT # Set default status here

class RequestUpdate(RequestBase):
    checkpoint_id: Optional[int] = None
    status: Optional[RequestStatusEnum] = None # Use Enum for updates too
    request_persons: Optional[List[RequestPersonUpdate]] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
# Removed duplicated RequestUpdate here

class RequestInDBBase(RequestBase): # Inherits start_date, end_date from RequestBase
    id: int
    creator_id: int
    created_at: datetime
    status: RequestStatusEnum # Ensure status in DB is also using the enum or compatible string
    creator: Optional[User] = None # Nested User schema
    checkpoint: Optional[Checkpoint] = None # Nested Checkpoint schema
    request_persons: List[RequestPerson] = []

    class Config:
        orm_mode = True

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
        orm_mode = True

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
        orm_mode = True

class AuditLog(AuditLogInDBBase):
    pass


# ------------- BlackList Schemas (Modified) -------------

class BlackListBase(BaseModel):
    full_name: str
    doc_type: Optional[str] = None
    doc_number: Optional[str] = None
    citizenship: Optional[str] = None
    reason: Optional[str] = None
    status: str = 'ACTIVE'

class BlackListCreate(BlackListBase):
    added_by: int # Usually current user

class BlackListUpdate(BlackListBase):
    full_name: Optional[str] = None
    status: Optional[str] = None
    # removed_by and removed_at are usually set by specific actions/endpoints

class BlackListInDBBase(BlackListBase):
    id: int
    added_by: int
    added_at: datetime
    removed_by: Optional[int] = None
    removed_at: Optional[datetime] = None
    added_by_user: Optional[UserForBlackList] = None # Simplified User
    removed_by_user: Optional[UserForBlackList] = None # Simplified User


    class Config:
        orm_mode = True

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
        orm_mode = True

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
        orm_mode = True

class Notification(NotificationInDBBase):
    recipient: Optional[UserForRecipient] = None
    request: Optional[RequestSmall] = None # Simplified Request
