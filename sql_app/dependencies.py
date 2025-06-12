from sqlalchemy.orm import Session
from .database import SessionLocal

# This file will only contain get_db.
# All authentication-related dependencies will be temporarily defined locally in routers
# due to tool limitations.

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()