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
    allow_origins=["*"],  # Allow all origins for local development
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
                "role": db_user.role,
            },
        }

    # 2. Create new user in PostgreSQL if they don't exist
    try:
        new_user = models.User(
            firebase_uid=user_data.firebase_uid,
            email=user_data.email,
            full_name=user_data.full_name,
            role=user_data.role,
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
        "gcal_connected": True if user.google_calendar_token else False,
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


@app.get("/users", response_model=List[UserSimple])
def list_users(db: Session = Depends(get_db)):
    """
    Return all users (for chat roster).
    Frontend is responsible for excluding the current user.
    """
    users = db.query(models.User).all()
    return [
        UserSimple(firebase_uid=u.firebase_uid, full_name=u.full_name, role=u.role or "Student")
        for u in users
    ]


@app.get("/messages", response_model=List[MessageOut])
def get_messages(user1: str, user2: str, db: Session = Depends(get_db)):
    """
    Get all messages between user1 and user2 ordered by time ascending.
    """
    messages = (
        db.query(models.Message)
        .filter(
            ((models.Message.sender_uid == user1) & (models.Message.receiver_uid == user2))
            | ((models.Message.sender_uid == user2) & (models.Message.receiver_uid == user1))
        )
        .order_by(models.Message.created_at.asc())
        .all()
    )

    return [
        MessageOut(
            id=m.id,
            sender_uid=m.sender_uid,
            receiver_uid=m.receiver_uid,
            content=m.content,
            created_at=m.created_at.isoformat(),
        )
        for m in messages
    ]


@app.post("/messages", response_model=MessageOut)
def send_message(message: MessageCreate, db: Session = Depends(get_db)):
    """
    Store a new direct message between two users.
    """
    if not message.content.strip():
        raise HTTPException(status_code=400, detail="Message content cannot be empty")

    new_msg = models.Message(
        sender_uid=message.sender_uid,
        receiver_uid=message.receiver_uid,
        content=message.content.strip(),
    )
    db.add(new_msg)
    db.commit()
    db.refresh(new_msg)

    return MessageOut(
        id=new_msg.id,
        sender_uid=new_msg.sender_uid,
        receiver_uid=new_msg.receiver_uid,
        content=new_msg.content,
        created_at=new_msg.created_at.isoformat(),
    )


# --- Post/Resource endpoints ---

@app.get("/posts", response_model=List[PostOut])
def get_posts(current_user_uid: str = None, db: Session = Depends(get_db)):
    """
    Get all posts ordered by newest first.
    If current_user_uid is provided, include user's vote for each post.
    """
    posts = db.query(models.Post).order_by(models.Post.created_at.desc()).all()
    result = []
    for post in posts:
        author = db.query(models.User).filter(models.User.firebase_uid == post.author_uid).first()
        user_vote = 0
        if current_user_uid:
            vote = db.query(models.PostVote).filter(
                (models.PostVote.post_id == post.id) &
                (models.PostVote.user_uid == current_user_uid)
            ).first()
            if vote:
                user_vote = vote.vote
        result.append(PostOut(
            id=post.id,
            author_uid=post.author_uid,
            author_name=author.full_name if author else "Unknown",
            author_role=author.role if author else "Student",
            title=post.title,
            description=post.description,
            resource_link=post.resource_link,
            score=post.score,
            user_vote=user_vote,
            created_at=post.created_at.isoformat(),
        ))
    return result


@app.post("/posts", response_model=PostOut)
def create_post(post_data: PostCreate, author_uid: str, db: Session = Depends(get_db)):
    """
    Create a new post/resource.
    Author UID is passed as a query parameter.
    """
    if not post_data.title.strip():
        raise HTTPException(status_code=400, detail="Post title cannot be empty")
    # Verify user exists
    author = db.query(models.User).filter(models.User.firebase_uid == author_uid).first()
    if not author:
        raise HTTPException(status_code=404, detail="User not found")
    new_post = models.Post(
        author_uid=author_uid,
        title=post_data.title.strip(),
        description=post_data.description.strip() if post_data.description else None,
        resource_link=post_data.resource_link,
        score=0,
    )
    db.add(new_post)
    db.commit()
    db.refresh(new_post)
    return PostOut(
        id=new_post.id,
        author_uid=new_post.author_uid,
        author_name=author.full_name,
        author_role=author.role,
        title=new_post.title,
        description=new_post.description,
        resource_link=new_post.resource_link,
        score=new_post.score,
        user_vote=0,
        created_at=new_post.created_at.isoformat(),
    )


from fastapi import Query

# Vote endpoint: vote can be +1 (upvote), -1 (downvote), or 0 (neutral/remove)
@app.post("/posts/{post_id}/vote")
def vote_post(post_id: int, user_uid: str = Query(...), vote: int = Query(...), db: Session = Depends(get_db)):
    """
    Set the user's vote for a post. vote: +1 (upvote), -1 (downvote), 0 (neutral/remove)
    """
    if vote not in [-1, 0, 1]:
        raise HTTPException(status_code=400, detail="Vote must be -1, 0, or 1")
    post = db.query(models.Post).filter(models.Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    post_vote = db.query(models.PostVote).filter(
        (models.PostVote.post_id == post_id) & (models.PostVote.user_uid == user_uid)
    ).first()
    prev_vote = post_vote.vote if post_vote else 0
    # Update or create vote
    if post_vote:
        if vote == 0:
            db.delete(post_vote)
        else:
            post_vote.vote = vote
    elif vote != 0:
        new_vote = models.PostVote(post_id=post_id, user_uid=user_uid, vote=vote)
        db.add(new_vote)
    # Update post score
    post.score = post.score - prev_vote + vote
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
