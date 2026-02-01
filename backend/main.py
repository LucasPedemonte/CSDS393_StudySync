from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from database import engine, Base, get_db
import models

# Create tables in PostgreSQL automatically 
Base.metadata.create_all(bind=engine)

app = FastAPI()

# Allow front end connection from React 
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class LoginRequest(BaseModel):
    email: str
    password: str

@app.post("/login")
def login(request: LoginRequest, db: Session = Depends(get_db)):
    # 3. Look for the user in the database Ohta will manage 
    user = db.query(models.User).filter(models.User.email == request.email).first()
    
    if not user or user.password_hash != request.password:
        raise HTTPException(status_code=400, detail="Invalid email or password")
    
    return {"status": "success", "user": user.full_name, "role": user.role}