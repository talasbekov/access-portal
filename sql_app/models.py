from sqlalchemy import Column, Integer, String, Date, Boolean, ForeignKey, PickleType
from sqlalchemy.orm import relationship
import pickle

from .database import Base


class Citizenship(Base):
    __tablename__ = "citizenships"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)

    visitor = relationship("Visitor", back_populates="citizenship")


class Role(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    description = Column(String, nullable=True)

    users = relationship("User", back_populates="role", lazy="dynamic")


class Division(Base):
    __tablename__ = "divisions"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    description = Column(String, nullable=True)

    parent_id = Column(Integer, ForeignKey("divisions.id"))

    users = relationship("User", back_populates="division")


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, index=True)
    full_name = Column(String)
    position = Column(String)
    hashed_password = Column(String)

    role_id = Column(Integer, ForeignKey("roles.id"))
    role = relationship("Role", back_populates="users")
    division_id = Column(Integer, ForeignKey("divisions.id"))
    division = relationship("Division", back_populates="users")

    requests = relationship("Request", back_populates="user")


class Request(Base):
    __tablename__ = "requests"

    id = Column(Integer, primary_key=True)
    purpose = Column(String)
    checkpoint = Column(Integer)
    visit_type = Column(String)
    start_date = Column(String)
    end_date = Column(String)
    visit_date = Column(String)
    req_author = Column(String)
    req_date = Column(String)
    req_sysdata = Column(String)
    convoy = Column(String)

    user_id = Column(Integer, ForeignKey("users.id"))
    user = relationship("User", back_populates="requests")

    visitors = relationship("Visitor", back_populates="request")


class Visitor(Base):
    __tablename__ = "visitors"

    id = Column(Integer, primary_key=True)

    iin_number = Column(Integer)
    pass_number = Column(String)
    first_name = Column(String)
    second_name = Column(String)
    third_name = Column(String)
    gender = Column(String)
    dob = Column(String)
    id_exp = Column(String)
    sb_check = Column(Boolean)
    sb_approval = Column(Boolean)
    sb_disapp_reason = Column(String)
    sb_notes = Column(String)
    ap_check = Column(Boolean)
    ap_approval = Column(Boolean)
    ap_disapp_reason = Column(String)
    ap_notes = Column(String)
    entered = Column(PickleType)

    citizenship_id = Column(Integer, ForeignKey("citizenships.id"))
    citizenship = relationship("Citizenship", back_populates="visitor")
    request_id = Column(Integer, ForeignKey("requests.id"))
    request = relationship("Request", back_populates="visitors")

    blacklist = relationship("BlackList", back_populates="visitors")

    def set_entered(self, entered_list):
        self.entered = pickle.dumps(entered_list)

    def get_options(self):
        return pickle.loads(self.entered)


class BlackList(Base):
    __tablename__ = "blacklist"

    id = Column(Integer, primary_key=True)
    reason = Column(String)

    visitor_id = Column(Integer, ForeignKey("visitors.id"))
    visitors = relationship("Visitor", back_populates="blacklist")
