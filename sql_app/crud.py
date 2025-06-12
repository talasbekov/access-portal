from sqlalchemy.orm import Session, joinedload
from fastapi import HTTPException, status
from sqlalchemy.sql.functions import user

from . import models, schemas
from datetime import datetime

def get_current_datetime(type="enter"):
    # Get the current date and time
    current_datetime = datetime.now()
    
    # Format the date and time as a string
    formatted_datetime = current_datetime.strftime('%H:%M:%S %d.%m.%Y')
    
    return f"{type}{formatted_datetime}"

#-------User-Related-CRUD------------------->
def get_user_by_id(db: Session, user_id: int):
    return db.query(models.User).filter(models.User.id == user_id).first()

def get_user_by_username(db: Session, username: str):
    return db.query(models.User).filter(models.User.username == username).first()

def delete_user(db: Session, user_id: str):
    db_user = db.query(models.User).filter(models.User.id == user_id).first()

    if not db_user:
        return False  # User not found

    db.delete(db_user)
    db.commit()
    return True  # Deletion successful

def get_users(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.User).offset(skip).limit(limit).all()

def create_user(db: Session, user: schemas.UserCreate):
    db_user = models.User(username=user.username, 
                          full_name=user.full_name,
                          division_id=user.division_id,
                          role_id=user.role_id,
                          position=user.position,
                          hashed_password=user.hashed_password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user 

#-------Request-Related-CRUD------------------->
def get_requests(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Request).offset(skip).limit(limit).all()
    # return db.query(models.Request).options(selectinload(models.Request.visitors)).offset(skip).limit(limit).all()

def get_request(db: Session, request_id: int):
    return db.query(models.Request).filter(models.Request.id == request_id).first()

def create_user_request(db: Session, request: schemas.RequestCreate, user_id: int):
    db_request = models.Request(**request.model_dump(), user_id=user_id)
    db.add(db_request)
    db.commit()
    db.refresh(db_request)
    return db_request

def delete_request(db: Session, request_id: str):
    db_request = db.query(models.Request).filter(models.Request.id == request_id).first()

    if not db_request:
        return False  # User not found

    db.delete(db_request)
    db.commit()
    return True  # Deletion successful

#--------Visitor-Related-CRUD-------------------->
def get_visitors(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Visitor).offset(skip).limit(limit).all()

def create_request_visitor(db: Session, visitor: schemas.VisitorCreate, request_id):
    db_visitor = models.Visitor(**visitor.model_dump(), request_id = request_id)
    db.add(db_visitor)
    db.commit()
    db.refresh(db_visitor)
    return db_visitor

def create_request_visitors(request_id: int, visitors: list[schemas.VisitorCreate], db: Session):
    db_visitors = []
    for visitor in visitors:
        db_visitor = models.Visitor(**visitor.model_dump(), request_id=request_id)
        db.add(db_visitor)
        db.commit()
        db.refresh(db_visitor)
        db_visitors.append(db_visitor)
    return db_visitors

def get_request_visitors(db: Session, request_id): 
    return db.query(models.Visitor).filter(models.Visitor.request_id == request_id)

def get_visitor_by_id(db: Session, visitor_id: int): 
    visitor = db.query(models.Visitor).options(joinedload(models.Visitor.request)).filter(models.Visitor.id == visitor_id).first()
    if not visitor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Visitor not found"
        )
    # print(visitor)
    return visitor

def edit_visitor(db: Session, visitor_id: int, role: str, approval_type: bool):
    visitor = db.query(models.Visitor).filter(models.Visitor.id == visitor_id).first()
    if not visitor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Visitor not found"
        )
    if role == 'sb':
        setattr(visitor, "sb_check", True)
        setattr(visitor, "sb_approval", approval_type)

    if role == 'ap':
        setattr(visitor, "ap_check", True)
        setattr(visitor, "ap_approval", approval_type)

    db.commit()

def edit_visitor_pass(db: Session, visitor_id: int, pass_type: str):
    visitor = db.query(models.Visitor).filter(models.Visitor.id == visitor_id).first()
    if not visitor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Visitor not found"
        )
    current_date_time = get_current_datetime(pass_type)
    setattr(visitor, "entered", current_date_time)
    db.commit()
    return current_date_time
    
# def record_visitor(db: Session, visitor_id: int, )
    
def get_black_list():
    # Get all visitors that are not approved 
    pass


#-------------Restricted User----------------------------------------------
# Create RestrictedUser
def create_restricted_user(db: Session, user: schemas.RestrictedUserCreate):
    db_user = models.BlackList(**user.model_dump())
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

# Get RestrictedUser by ID
def get_restricted_user(db: Session, user_id: int):
    return db.query(models.BlackList).filter(models.BlackList.id == user_id).first()

# Get all RestrictedUsers
def get_restricted_users(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.BlackList).offset(skip).limit(limit).all()

# Update RestrictedUser
def update_restricted_user(db: Session, user_id: int, user: schemas.RestrictedUserCreate):
    db_user = db.query(models.BlackList).filter(models.BlackList.id == user_id).first()
    if db_user:
        for var, value in vars(user).items():
            setattr(db_user, var, value)  # Update each field
        db.commit()
        db.refresh(db_user)
    return db_user

# Delete RestrictedUser
def delete_restricted_user(db: Session, user_id: int):
    db_user = db.query(models.BlackList).filter(models.BlackList.id == user_id).first()
    if db_user:
        db.delete(db_user)
        db.commit()
    return db_user


# def build_division_tree(all_divisions, parent_id=None):
#     tree = []
#     for division in filter(lambda d: d.parent_id == parent_id, all_divisions):
#         children = build_division_tree(all_divisions, division.id)
#         division_data = DivisionTree.from_orm(division)
#         division_data.children = children
#
#         # Добавляем пользователей только если нет потомков (лист)
#         if not children:
#             division_data.users = [UserInDivision.from_orm(user) for user in division.users]
#
#         tree.append(division_data)
#     return tree

#-------Role-Related-CRUD------------------->
def get_role_by_id(db: Session, role_id: int):
    return db.query(models.Role).filter(models.Role.id == role_id).first()

def get_roles(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Role).offset(skip).limit(limit).all()

def get_role_by_name(db: Session, role_name: str):
    return db.query(models.Role).filter(models.Role.name == role_name).first()

def create_role(db: Session, role: schemas.RoleCreate):
    db_role = models.Role(name=role.name,
                          description=role.description)
    db.add(db_role)
    db.commit()
    db.refresh(db_role)
    return db_role

def delete_role(db: Session, role_id: str):
    db_role = db.query(models.Role).filter(models.Role.id == role_id).first()

    if not db_role:
        return False  # User not found

    db.delete(db_role)
    db.commit()
    return True

#-------Division-Related-CRUD------------------->
def get_division_by_id(db: Session, division_id: int):
    return db.query(models.Division).filter(models.Division.id == division_id).first()

def get_divisions(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Division).offset(skip).limit(limit).all()

def get_division_by_name(db: Session, division_name: str):
    return db.query(models.Division).filter(models.Division.name == division_name).first()

def create_division(db: Session, division: schemas.DivisionCreate):
    db_division = models.Division(name=division.name,
                          description=division.description)
    db.add(db_division)
    db.commit()
    db.refresh(db_division)
    return db_division

def delete_division(db: Session, division_id: str):
    db_division = db.query(models.Division).filter(models.Division.id == division_id).first()

    if not db_division:
        return False  # User not found

    db.delete(db_division)
    db.commit()
    return True
