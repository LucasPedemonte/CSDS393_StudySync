from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from database import engine, Base, get_db
import models

# Create tables in PostgreSQL automatically 
Base.metadata.create_all(bind=engine)

app = FastAPI()

origins = [
    "http://localhost:3000",  # Default React port
    "http://127.0.0.1:3000",
]

# Allow front end connection from React 
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

class UserCreate(BaseModel):
    firebase_uid: str
    email: str
    full_name: str
    role: str

@app.post("/sync-user")
def sync_user(user_data: UserCreate, db: Session = Depends(get_db)):
    # 1. Check if user already exists in PostgreSQL by Firebase UID
    db_user = db.query(models.User).filter(models.User.firebase_uid == user_data.firebase_uid).first()
    
    if db_user:
        # User is already synced; return their existing data
        return {
            "status": "exists", 
            "message": "User already in database",
            "user": {
                "full_name": db_user.full_name,
                "role": db_user.role
            }
        }
    
    # 2. Create new user in PostgreSQL if they don't exist
    try:
        new_user = models.User(
            firebase_uid=user_data.firebase_uid,
            email=user_data.email,
            full_name=user_data.full_name,
            role=user_data.role
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        return {"status": "success", "user": new_user.full_name, "role": new_user.role}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    
@app.get("/user/{firebase_uid}")
def get_user_profile(firebase_uid: str, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.firebase_uid == firebase_uid).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {
        "full_name": user.full_name,
        "email": user.email,
        "role": user.role,
        "gcal_connected": True if user.google_calendar_token else False
    }

@app.put("/user/{firebase_uid}/update")
def update_user_profile(firebase_uid: str, update_data: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.firebase_uid == firebase_uid).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    db_user.full_name = update_data.full_name
    db_user.role = update_data.role
    # Email updates in DB should usually sync with Firebase updates
    db_user.email = update_data.email 
    
    db.commit()
    return {"status": "success"}