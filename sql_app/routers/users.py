from fastapi import Depends, FastAPI, HTTPException, APIRouter, Header
from sqlalchemy.orm import Session
from ..dependencies import get_db
from .. import crud, models, schemas

router = APIRouter(    
    prefix="/users",
    tags=["Users"],
    responses={418: {"description": "I'm a teapot"}}
)

#-------------User-Related-APIs------------------->
# Create User 
@router.post("/users/", response_model=schemas.User)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    existing_user = crud.get_user_by_username(db, user.full_name)
    if existing_user:
        raise HTTPException(status_code=400, detail="User already exists")
    return crud.create_user(db=db, user=user)

# Get All Users
@router.get("/users/", response_model=list[schemas.User])
def read_users(skip: int=0, limit: int=100, db: Session = Depends(get_db)):
    users = crud.get_users(db, skip=skip, limit=limit)
    return users

@router.get("/delete_user/", response_model = bool)
def delete_user(user_id: str, db: Session = Depends(get_db)):
    return crud.delete_user(db, user_id)

# Get User By User_id
@router.get("/users_id/{user_id}", response_model=schemas.User)
def read_user(user_id: str, db: Session = Depends(get_db)):
    db_user = crud.get_user_by_id(db, user_id=user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user

# Get user ID by username
@router.get("/username/{username}", response_model=int)
def get_user_id_by_username(username: str, db: Session = Depends(get_db)):
    db_user = crud.get_user_by_username(db, username=username)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user.id

# Get User By Username
@router.get("/users_username/{username}", response_model=schemas.User)
def read_user_by_username(username: str, db: Session = Depends(get_db)):
    db_user = crud.get_user_by_username(db, username=username)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user
