from fastapi import Depends, APIRouter, HTTPException
from sqlalchemy.orm import Session
from ..dependencies import get_db
from .. import crud, schemas

router = APIRouter(
    prefix="/restricted-users",
    tags=["RestrictedUsers"],
    responses={404: {"description": "Not found"}}
)

# Create RestrictedUser
@router.post("/", response_model=schemas.RestrictedUser)
def create_restricted_user(user: schemas.RestrictedUserCreate, db: Session = Depends(get_db)):
    return crud.create_restricted_user(db=db, user=user)

# Get RestrictedUser by ID
@router.get("/{user_id}", response_model=schemas.RestrictedUser)
def get_restricted_user(user_id: int, db: Session = Depends(get_db)):
    db_user = crud.get_restricted_user(db=db, user_id=user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user

# Get all RestrictedUsers
@router.get("/", response_model=list[schemas.RestrictedUser])
def get_restricted_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return crud.get_restricted_users(db=db, skip=skip, limit=limit)

# Update RestrictedUser
@router.put("/{user_id}", response_model=schemas.RestrictedUser)
def update_restricted_user(user_id: int, user: schemas.RestrictedUserCreate, db: Session = Depends(get_db)):
    db_user = crud.get_restricted_user(db=db, user_id=user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return crud.update_restricted_user(db=db, user_id=user_id, user=user)

# Delete RestrictedUser
@router.delete("/{user_id}", response_model=schemas.RestrictedUser)
def delete_restricted_user(user_id: int, db: Session = Depends(get_db)):
    db_user = crud.get_restricted_user(db=db, user_id=user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return crud.delete_restricted_user(db=db, user_id=user_id)
