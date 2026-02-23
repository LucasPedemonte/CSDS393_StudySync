from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from database import engine, Base, get_db
import models

Base.metadata.create_all(bind=engine)

app = FastAPI()

origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Existing login ---
class LoginRequest(BaseModel):
    email: str
    password: str

@app.post("/login")
def login(request: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == request.email).first()
    if not user or user.password_hash != request.password:
        raise HTTPException(status_code=400, detail="Invalid email or password")
    return {"status": "success", "user": user.full_name, "role": user.role}

# --- Resource endpoints ---
class ResourceCreate(BaseModel):
    title: str
    url: str
    description: Optional[str] = None
    submitted_by: Optional[int] = None

@app.get("/resources")
def get_resources(db: Session = Depends(get_db)):
    resources = db.query(models.Resource).order_by(models.Resource.vote_score.desc()).all()
    return resources

@app.post("/resources")
def create_resource(resource: ResourceCreate, db: Session = Depends(get_db)):
    db_resource = models.Resource(
        title=resource.title,
        url=resource.url,
        description=resource.description,
        submitted_by=resource.submitted_by,
    )
    db.add(db_resource)
    db.commit()
    db.refresh(db_resource)
    return db_resource

@app.post("/resources/{resource_id}/vote")
def vote_resource(resource_id: int, user_id: int, vote: int, db: Session = Depends(get_db)):
    if vote not in (1, -1):
        raise HTTPException(status_code=400, detail="Vote must be 1 or -1")

    existing = db.query(models.ResourceVote).filter_by(
        user_id=user_id, resource_id=resource_id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Already voted on this resource")

    new_vote = models.ResourceVote(user_id=user_id, resource_id=resource_id, vote=vote)
    db.add(new_vote)

    resource = db.query(models.Resource).filter(models.Resource.id == resource_id).first()
    if not resource:
        raise HTTPException(status_code=404, detail="Resource not found")

    resource.vote_score += vote
    db.commit()
    return {"status": "ok", "new_score": resource.vote_score}