from fastapi import Depends, FastAPI, HTTPException, APIRouter
from sqlalchemy.orm import Session
from ..dependencies import get_db
from .. import crud, models, schemas

# Some 
router = APIRouter(    
    prefix="/visitors",
    tags=["Visitors"],
    responses={418: {"description": "I'm a teapot"}}
)

#-------------Visitor-Related-APIs------------------------>
# Get All Visitors
@router.get("/visitors/", response_model=list[schemas.Visitor])
def get_visitors(skip: int=0, limit: int=100, db: Session = Depends(get_db)):
    visitors = crud.get_visitors(db, skip=skip, limit=limit)
    return visitors

@router.get("/visitors/{visitor_id}", response_model=schemas.Visitor)
def get_visitor_by_id(visitor_id: int, db: Session = Depends(get_db)):
    return crud.get_visitor_by_id(db, visitor_id)

# Get Vistors Of Specific Request
@router.get("/requests/{request_id}/visitors", response_model=list[schemas.Visitor])
def get_visitors_by_request(request_id: int, db: Session = Depends(get_db)):
    visitors = crud.get_request_visitors(db, request_id)
    return visitors

# Create Visitor For Specific Request
@router.post("/request/{request_id}/visitors", response_model=list[schemas.Visitor])
def post_visitors_by_request(request_id: int , visitors: list[schemas.VisitorCreate], db: Session = Depends(get_db)):
    return crud.create_request_visitors(db=db, visitors=visitors, request_id=request_id)

# Approve or Disapprove Visitor 
@router.put("/visitors/{visitor_id}/{role}/{approval_type}")
def check_visitor(visitor_id: int, role: str, approval_type: str, db: Session = Depends(get_db)):
    if role not in ("sb", "ap"):
        raise HTTPException(status_code=404, detail="Wrong role")
    if approval_type not in ('true','false'):
        raise HTTPException(status_code=404, detail="Wrong approval type")
    approval = True if approval_type == 'true' else False
    return crud.edit_visitor(db=db, visitor_id=visitor_id, role=role, approval_type=approval)

# Note visitor passing
@router.post("/visitor/{visitor_id}/passing")
def note_visitor(visitor_id: int, pass_type: str, db: Session = Depends(get_db)):
    return crud.edit_visitor_pass(db=db, visitor_id=visitor_id, pass_type=pass_type)