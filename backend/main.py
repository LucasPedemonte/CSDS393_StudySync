from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict
from database import engine, Base, get_db
import models
from typing import List, Optional
from datetime import datetime

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

class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    user_id: int
    firebase_uid: str
    email: str
    full_name: str
    role: str

class MessageCreate(BaseModel):
    content: str

class MessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    message_id: int
    conversation_id: int
    sender_id: int
    sender_name: str
    content: str
    created_at: datetime

class ConversationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    conversation_id: int
    is_group: bool
    group_name: Optional[str]
    created_at: datetime
    participants: List[UserResponse]

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
                "user_id": db_user.user_id,
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
        return {"status": "success", "user_id": new_user.user_id, "user": new_user.full_name, "role": new_user.role}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    
@app.get("/user/{firebase_uid}")
def get_user_profile(firebase_uid: str, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.firebase_uid == firebase_uid).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {
        "user_id": user.user_id,
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

# ============ MESSAGING ENDPOINTS ============

@app.get("/users")
def get_all_users(db: Session = Depends(get_db)):
    """Get all users for the messaging feature"""
    users = db.query(models.User).all()
    return [
        {
            "user_id": user.user_id,
            "full_name": user.full_name,
            "email": user.email,
            "role": user.role
        }
        for user in users
    ]

@app.post("/conversations/one-on-one/{user_id_1}/{user_id_2}")
def create_or_get_one_on_one_conversation(user_id_1: int, user_id_2: int, db: Session = Depends(get_db)):
    """Create or get existing one-on-one conversation between two users"""
    if user_id_1 == user_id_2:
        raise HTTPException(status_code=400, detail="Cannot create conversation with yourself")
    
    # Check if conversation already exists
    existing_conv = db.query(models.Conversation).filter(
        models.Conversation.is_group == False
    ).join(models.ConversationParticipant).filter(
        models.ConversationParticipant.user_id.in_([user_id_1, user_id_2])
    ).group_by(models.Conversation.conversation_id).having(
        func.count(models.ConversationParticipant.participant_id) == 2
    ).first()
    
    if existing_conv:
        return {"conversation_id": existing_conv.conversation_id, "is_new": False}
    
    # Create new conversation
    try:
        conv = models.Conversation(is_group=False)
        db.add(conv)
        db.flush()
        
        # Add participants
        participant1 = models.ConversationParticipant(conversation_id=conv.conversation_id, user_id=user_id_1)
        participant2 = models.ConversationParticipant(conversation_id=conv.conversation_id, user_id=user_id_2)
        db.add(participant1)
        db.add(participant2)
        db.commit()
        
        return {"conversation_id": conv.conversation_id, "is_new": True}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error creating conversation: {str(e)}")

@app.post("/conversations/group")
def create_group_conversation(group_name: str, user_ids: List[int], db: Session = Depends(get_db)):
    """Create a group conversation"""
    try:
        conv = models.Conversation(is_group=True, group_name=group_name)
        db.add(conv)
        db.flush()
        
        # Add participants
        for user_id in user_ids:
            participant = models.ConversationParticipant(conversation_id=conv.conversation_id, user_id=user_id)
            db.add(participant)
        
        db.commit()
        return {"conversation_id": conv.conversation_id, "is_new": True}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error creating group: {str(e)}")

@app.get("/conversations/{user_id}")
def get_user_conversations(user_id: int, db: Session = Depends(get_db)):
    """Get all conversations for a user"""
    conversations = db.query(models.Conversation).join(
        models.ConversationParticipant
    ).filter(models.ConversationParticipant.user_id == user_id).all()
    
    result = []
    for conv in conversations:
        participants = db.query(models.User).join(
            models.ConversationParticipant
        ).filter(models.ConversationParticipant.conversation_id == conv.conversation_id).all()
        
        result.append({
            "conversation_id": conv.conversation_id,
            "is_group": conv.is_group,
            "group_name": conv.group_name,
            "created_at": conv.created_at,
            "participants": [
                {"user_id": p.user_id, "full_name": p.full_name, "email": p.email, "role": p.role}
                for p in participants
            ]
        })
    
    return result

@app.post("/messages/{conversation_id}")
def send_message(conversation_id: int, sender_id: int, message: MessageCreate, db: Session = Depends(get_db)):
    """Send a message to a conversation"""
    # Verify user is in conversation
    participant = db.query(models.ConversationParticipant).filter(
        models.ConversationParticipant.conversation_id == conversation_id,
        models.ConversationParticipant.user_id == sender_id
    ).first()
    
    if not participant:
        raise HTTPException(status_code=403, detail="User not in this conversation")
    
    try:
        msg = models.Message(
            conversation_id=conversation_id,
            sender_id=sender_id,
            content=message.content
        )
        db.add(msg)
        db.commit()
        db.refresh(msg)
        
        sender = db.query(models.User).filter(models.User.user_id == sender_id).first()
        
        return {
            "message_id": msg.message_id,
            "conversation_id": msg.conversation_id,
            "sender_id": msg.sender_id,
            "sender_name": sender.full_name,
            "content": msg.content,
            "created_at": msg.created_at
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error sending message: {str(e)}")

@app.get("/messages/{conversation_id}")
def get_conversation_messages(conversation_id: int, db: Session = Depends(get_db)):
    """Get all messages in a conversation"""
    messages = db.query(models.Message).filter(
        models.Message.conversation_id == conversation_id
    ).order_by(models.Message.created_at.asc()).all()
    
    result = []
    for msg in messages:
        sender = db.query(models.User).filter(models.User.user_id == msg.sender_id).first()
        result.append({
            "message_id": msg.message_id,
            "conversation_id": msg.conversation_id,
            "sender_id": msg.sender_id,
            "sender_name": sender.full_name,
            "content": msg.content,
            "created_at": msg.created_at
        })
    
    return result