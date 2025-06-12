from fastapi import Depends, FastAPI, HTTPException, APIRouter
from sqlalchemy.orm import Session
from ..dependencies import get_db
from .. import crud, models, schemas

router = APIRouter(
    prefix="/roles",
    tags=["Roles"],
    responses={418: {"description": "I'm a teapot"}}
)

# Get All roles
@router.get("", response_model=list[schemas.RoleBase])
def get_roles(skip: int=0, limit: int=100, db: Session = Depends(get_db)):
    roles = crud.get_roles(db, skip=skip, limit=limit)
    return roles

#Get roles created by specific user
@router.get("/{role_id}", response_model=schemas.RoleBase)
def get_role_by_id(role_id: int, db: Session = Depends(get_db)):
    db_role = crud.get_role_by_id(db, role_id=role_id)
    if db_role is None:
        raise HTTPException(status_code=404, detail="Role not found")
    return db_role

@router.post("", response_model=schemas.RoleCreate)
def create_role(role: schemas.RoleCreate, db: Session = Depends(get_db)):
    existing_role = crud.get_role_by_name(db, role.name)
    if existing_role:
        raise HTTPException(status_code=400, detail="Role already exists")
    return crud.create_role(db=db, role=role)


@router.get("/delete_role/", response_model = bool)
def delete_role(role_id: str, db: Session = Depends(get_db)):
    return crud.delete_role(db, role_id)
