from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy.orm import Session
from fastapi.middleware.cors import CORSMiddleware

from sql_app import crud, models, schemas
from sql_app.database import SessionLocal, engine
# Updated imports for all active routers
from sql_app.routers import (
    auth,
    users,
    role,
    departments,
    requests,
    blacklist,
    checkpoints,
    notifications # Added notifications router
)
from sql_app.dependencies import get_db

models.Base.metadata.create_all(bind=engine)


app = FastAPI()

origins = [
    "http://localhost",
    "http://localhost:5173",  # Your frontend's URL (if different)
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,   # Only if you use cookies/authentication
    allow_methods=["*"],      # Allow all methods (or specify)
    allow_headers=["*"],      # Allow all headers (or specify)
)


#------------Separate File APIs------------------>
app.include_router(auth.router) # Added/Ensured
app.include_router(users.router)
app.include_router(role.router)
app.include_router(departments.router) # Added
app.include_router(requests.router)
app.include_router(blacklist.router)
app.include_router(checkpoints.router)
app.include_router(notifications.router) # Added notifications router

# app.include_router(division.router) # Confirmed Removed
# app.include_router(visitors.router) # Confirmed Removed
# app.include_router(restricted_users.router) # Confirmed Removed

