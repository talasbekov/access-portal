from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy.orm import Session
from fastapi.middleware.cors import CORSMiddleware

from sql_app import crud, models, schemas
from sql_app.database import SessionLocal, engine
from sql_app.routers import users, requests, visitors, restricted_users, role, division
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
app.include_router(users.router)
app.include_router(division.router)
app.include_router(requests.router)
app.include_router(visitors.router)
app.include_router(restricted_users.router)
app.include_router(role.router)

