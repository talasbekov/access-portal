from fastapi import Depends, FastAPI, HTTPException, APIRouter
from sqlalchemy.orm import Session
from ..dependencies import get_db
from .. import crud, models, schemas

router = APIRouter(    
    prefix="/requests",
    tags=["Requests"],
    responses={418: {"description": "I'm a teapot"}}
)

# Get All Requests
@router.get("/requests/", response_model=list[schemas.Request])
def read_requests(skip: int=0, limit: int=100, db: Session = Depends(get_db)):
    requests = crud.get_requests(db, skip=skip, limit=limit)
    return requests

#Get Requests created by specific user
@router.get("/requests/{user_id}", response_model=list[schemas.Request])
def read_user_requests(user_id: int, db: Session = Depends(get_db)):
    db_user = crud.get_user_by_id(db, user_id=user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user.requests

#Get Requests created by specific user
@router.get("/requests_username/{username}", response_model=list[schemas.Request])
def read_user_requests_username(username: str, db: Session = Depends(get_db)):
    db_user = crud.get_user_by_username(db, username=username)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user.requests

@router.get("/delete_request/", response_model = bool)
def delete_request(request_id: str, db: Session = Depends(get_db)):
    return crud.delete_request(db, request_id)

# Create Request Of Specific User
@router.post("/users/{user_id}/request", response_model=schemas.Request)
def create_request_for_user(user_id: int, request: schemas.RequestCreate, db: Session = Depends(get_db)):
    return crud.create_user_request(db=db, request=request, user_id=user_id)

@router.get("/request/{request_id}", response_model=schemas.Request)
def read_request_by_id(request_id: str, db: Session = Depends(get_db)):
    db_request = crud.get_request(db, request_id)
    if db_request is None:
        raise HTTPException(status_code=404, detail="Request not found")
    return db_request