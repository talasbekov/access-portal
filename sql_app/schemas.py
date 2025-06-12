from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, Field
from datetime import datetime


class CitizenshipBase(BaseModel):
    name: str


class CitizenshipCreate(CitizenshipBase):
    pass


#-------------Visitor Related Schemas--------->
class VisitorBase(BaseModel):
    iin_number: str = Field(default='000000000000')
    pass_number: str = Field(default='N000000')
    first_name: str
    second_name: str
    third_name: str = Field(default='')
    gender: str = Field(default='male')
    dob: str
    id_exp: str

    sb_check: bool = Field(default=False)
    sb_approval: bool = Field(default=False)
    sb_disapp_reason: str = Field(default='None')
    sb_notes: str = Field(default='None')

    ap_check: bool = Field(default=False)
    ap_approval: bool = Field(default=False)
    ap_disapp_reason: str = Field(default='None')
    ap_notes: str = Field(default='None')

    entered: str = Field(default='')

    citizenship_id: int
    citizenship: CitizenshipBase


class VisitorCreate(VisitorBase):
    pass


class Visitor(VisitorBase):
    request_id: int | None
    id: int

    class Config:
        orm_mode = True


#-------------Request-Related-Schemas----------->
class RequestBase(BaseModel):
    purpose: str
    checkpoint: int
    visit_type: str
    start_date: str = Field(default='None')  # Use date instead; if visit_type === PERIOD
    end_date: str = Field(default='None')  # Use date instead; if visit_type === PERIOD
    visit_date: str = Field(default='None')  # Use date instead; if visit_type === ONE_DAY
    req_author: str
    req_date: str = Field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    req_sysdata: str = Field(default='None')
    convoy: str


class RequestCreate(RequestBase):
    pass


class Request(RequestBase):
    visitors: list[Visitor] = []
    user_id: int
    id: int

    class Config:
        orm_mode = True


#-------------User Related Schemas------------>
class UserBase(BaseModel):
    username: str
    full_name: str
    position: str
    role_id: int
    division_id: int


class UserCreate(UserBase):
    hashed_password: str


class User(UserBase):
    id: int
    role: RoleBase
    requests: list[Request] = []

    class Config:
        orm_mode = True


# class UserInDivision(BaseModel):
#     id: int
#     username: str
#     full_name: str
#     position: str
#
#     class Config:
#         orm_mode = True

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class TokenData(BaseModel):
    user_id: int

class UserLogin(BaseModel):
    username: str
    password: str

#-------------Black List Related Schemas -------------->
class RestrictedUserBase(BaseModel):
    visitor_id: int
    reason: str
    visitor: VisitorBase


class RestrictedUserCreate(RestrictedUserBase):
    pass


class RestrictedUser(RestrictedUserBase):
    id: int

    class Config:
        orm_mode = True





class RoleBase(BaseModel):
    name: str
    description: Optional[str]


class RoleCreate(RoleBase):
    pass


class DivisionBase(BaseModel):
    name: str
    description: Optional[str]
    parent_id: Optional[int]

    class Config:
        orm_mode = True


class DivisionCreate(DivisionBase):
    pass

# class DivisionTree(BaseModel):
#     id: int
#     name: str
#     description: Optional[str]
#     parent_id: Optional[int] = None
#     children: List["DivisionTree"] = []  # рекурсивная ссылка
#     users: List[UserInDivision] = []     # пользователи, если есть
#
#     class Config:
#         orm_mode = True
#
# DivisionTree.update_forward_refs()
