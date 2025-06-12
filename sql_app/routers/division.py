from fastapi import Depends, FastAPI, HTTPException, APIRouter
from sqlalchemy.orm import Session
from ..dependencies import get_db
from .. import crud, models, schemas

router = APIRouter(
    prefix="/divisions",
    tags=["Divisions"],
    responses={418: {"description": "I'm a teapot"}}
)


# Get All divisions
@router.get("", response_model=list[schemas.DivisionBase])
def get_divisions(skip: int=0, limit: int=100, db: Session = Depends(get_db)):
    divisions = crud.get_divisions(db, skip=skip, limit=limit)
    return divisions


#Get divisions created by specific user
@router.get("/{division_id}", response_model=schemas.RoleBase)
def get_division_by_id(division_id: int, db: Session = Depends(get_db)):
    db_division = crud.get_division_by_id(db, division_id=division_id)
    if db_division is None:
        raise HTTPException(status_code=404, detail="Division not found")
    return db_division


@router.post("", response_model=schemas.DivisionCreate)
def create_division(division: schemas.DivisionCreate, db: Session = Depends(get_db)):
    existing_division = crud.get_division_by_name(db, division.name)
    if existing_division:
        raise HTTPException(status_code=400, detail="Division already exists")
    return crud.create_division(db=db, division=division)


@router.get("/delete_division/", response_model = bool)
def delete_division(division_id: str, db: Session = Depends(get_db)):
    return crud.delete_division(db, division_id)
