from fastapi import FastAPI, Depends, HTTPException, Query
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
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Updated for local development flexibility
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============ PYDANTIC MODELS ============

class UserSimple(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    user_id: int
    firebase_uid: str
    full_name: str
    email: str
    role: str

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

class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    sender_uid: str
    receiver_uid: str
    content: str
    created_at: datetime

class ConversationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    conversation_id: int
    is_group: bool
    group_name: Optional[str]
    created_at: datetime
    participants: List[UserResponse]

class PostCreate(BaseModel):
    title: str
    description: Optional[str] = None
    resource_link: Optional[str] = None

class PostOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    author_uid: str
    author_name: str
    author_role: str
    title: str
    description: Optional[str]
    resource_link: Optional[str]
    score: int
    user_vote: int
    created_at: datetime

# ============ USER ENDPOINTS ============

@app.post("/sync-user")
def sync_user(user_data: UserCreate, db: Session = Depends(get_db)):
    """Synchronizes Firebase Auth user with PostgreSQL database."""
    db_user = db.query(models.User).filter(models.User.firebase_uid == user_data.firebase_uid).first()
    
    if db_user:
        # Robust Sync: If verified email in Firebase differs from DB, update DB
        if db_user.email != user_data.email:
            db_user.email = user_data.email
            db.commit()
            db.refresh(db_user)
        
        return {
            "status": "exists",
            "user": {"user_id": db_user.user_id, "full_name": db_user.full_name, "role": db_user.role}
        }
    
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
    """Updates profile while preventing login issues during pending email verification."""
    db_user = db.query(models.User).filter(models.User.firebase_uid == firebase_uid).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    db_user.full_name = update_data.full_name
    db_user.role = update_data.role
    db_user.email = update_data.email 
    
    db.commit()
    return {"status": "success"}

@app.get("/users", response_model=List[UserSimple])
def list_users(db: Session = Depends(get_db)):
    """Return all users for chat roster."""
    users = db.query(models.User).all()
    return [
        UserSimple(
            user_id=u.user_id,
            firebase_uid=u.firebase_uid,
            full_name=u.full_name,
            email=u.email,
            role=u.role or "Student"
        )
        for u in users
    ]

# ============ MESSAGING ENDPOINTS ============

@app.post("/conversations/one-on-one/{user_id_1}/{user_id_2}")
def create_or_get_one_on_one_conversation(user_id_1: int, user_id_2: int, db: Session = Depends(get_db)):
    if user_id_1 == user_id_2:
        raise HTTPException(status_code=400, detail="Cannot create conversation with yourself")
    
    existing_conv = db.query(models.Conversation).filter(
        models.Conversation.is_group == False
    ).join(models.ConversationParticipant).filter(
        models.ConversationParticipant.user_id.in_([user_id_1, user_id_2])
    ).group_by(models.Conversation.conversation_id).having(
        func.count(models.ConversationParticipant.participant_id) == 2
    ).first()
    
    if existing_conv:
        return {"conversation_id": existing_conv.conversation_id, "is_new": False}
    
    try:
        conv = models.Conversation(is_group=False)
        db.add(conv)
        db.flush()
        
        p1 = models.ConversationParticipant(conversation_id=conv.conversation_id, user_id=user_id_1)
        p2 = models.ConversationParticipant(conversation_id=conv.conversation_id, user_id=user_id_2)
        db.add(p1)
        db.add(p2)
        db.commit()
        
        return {"conversation_id": conv.conversation_id, "is_new": True}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@app.post("/conversations/group")
def create_group_conversation(group_name: str, user_ids: List[int], db: Session = Depends(get_db)):
    try:
        conv = models.Conversation(is_group=True, group_name=group_name)
        db.add(conv)
        db.flush()
        for u_id in user_ids:
            p = models.ConversationParticipant(conversation_id=conv.conversation_id, user_id=u_id)
            db.add(p)
        db.commit()
        return {"conversation_id": conv.conversation_id, "is_new": True}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@app.get("/conversations/{user_id}")
def get_user_conversations(user_id: int, db: Session = Depends(get_db)):
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

# ============ DIRECT MESSAGE ENDPOINTS (by Firebase UID) ============

class DirectMessageCreate(BaseModel):
    sender_uid: str
    receiver_uid: str
    content: str

@app.get("/messages")
def get_messages_by_uid(user1: str, user2: str, db: Session = Depends(get_db)):
    from sqlalchemy import text
    rows = db.execute(
        text("""
            SELECT id, sender_uid, receiver_uid, content, created_at
            FROM messages
            WHERE (sender_uid = :u1 AND receiver_uid = :u2)
               OR (sender_uid = :u2 AND receiver_uid = :u1)
            ORDER BY created_at ASC
        """),
        {"u1": user1, "u2": user2}
    ).fetchall()
    return [
        {
            "id": r[0],
            "sender_uid": r[1],
            "receiver_uid": r[2],
            "content": r[3],
            "created_at": r[4]
        }
        for r in rows
    ]

@app.post("/messages")
def send_message_by_uid(msg: DirectMessageCreate, db: Session = Depends(get_db)):
    from sqlalchemy import text
    result = db.execute(
        text("""
            INSERT INTO messages (sender_uid, receiver_uid, content)
            VALUES (:sender_uid, :receiver_uid, :content)
            RETURNING id, sender_uid, receiver_uid, content, created_at
        """),
        {"sender_uid": msg.sender_uid, "receiver_uid": msg.receiver_uid, "content": msg.content}
    ).fetchone()
    db.commit()
    return {
        "id": result[0],
        "sender_uid": result[1],
        "receiver_uid": result[2],
        "content": result[3],
        "created_at": result[4]
    }


@app.post("/messages/{conversation_id}")
def send_message(conversation_id: int, sender_id: int, message: MessageCreate, db: Session = Depends(get_db)):
    participant = db.query(models.ConversationParticipant).filter(
        models.ConversationParticipant.conversation_id == conversation_id,
        models.ConversationParticipant.user_id == sender_id
    ).first()
    
    if not participant:
        raise HTTPException(status_code=403, detail="User not in conversation")
    
    try:
        msg = models.Message(conversation_id=conversation_id, sender_id=sender_id, content=message.content)
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
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@app.get("/messages/{conversation_id}")
def get_conversation_messages(conversation_id: int, db: Session = Depends(get_db)):
    messages = db.query(models.Message).filter(
        models.Message.conversation_id == conversation_id
    ).order_by(models.Message.created_at.asc()).all()
    
    return [
        {
            "message_id": m.message_id,
            "conversation_id": m.conversation_id,
            "sender_id": m.sender_id,
            "sender_name": db.query(models.User).filter(models.User.user_id == m.sender_id).first().full_name,
            "content": m.content,
            "created_at": m.created_at
        }
        for m in messages
    ]

# ============ RESOURCE SHARING ENDPOINTS ============

@app.get("/posts", response_model=List[PostOut])
def get_posts(current_user_uid: str = None, db: Session = Depends(get_db)):
    posts = db.query(models.Post).order_by(models.Post.created_at.desc()).all()
    result = []
    for post in posts:
        author = db.query(models.User).filter(models.User.firebase_uid == post.author_uid).first()
        user_vote = 0
        if current_user_uid:
            vote = db.query(models.PostVote).filter(
                (models.PostVote.post_id == post.id) & (models.PostVote.user_uid == current_user_uid)
            ).first()
            if vote: user_vote = vote.vote
        result.append(PostOut(
            id=post.id, author_uid=post.author_uid,
            author_name=author.full_name if author else "Unknown",
            author_role=author.role if author else "Student",
            title=post.title, description=post.description,
            resource_link=post.resource_link, score=post.score,
            user_vote=user_vote, created_at=post.created_at
        ))
    return result

@app.post("/posts", response_model=PostOut)
def create_post(post_data: PostCreate, author_uid: str, db: Session = Depends(get_db)):
    author = db.query(models.User).filter(models.User.firebase_uid == author_uid).first()
    if not author: raise HTTPException(status_code=404, detail="User not found")
    new_post = models.Post(
        author_uid=author_uid, title=post_data.title.strip(),
        description=post_data.description.strip() if post_data.description else None,
        resource_link=post_data.resource_link, score=0,
    )
    db.add(new_post)
    db.commit()
    db.refresh(new_post)
    return PostOut(
        id=new_post.id, author_uid=new_post.author_uid,
        author_name=author.full_name, author_role=author.role,
        title=new_post.title, description=new_post.description,
        resource_link=new_post.resource_link, score=new_post.score,
        user_vote=0, created_at=new_post.created_at
    )

@app.post("/posts/{post_id}/vote")
def vote_post(post_id: int, user_uid: str = Query(...), vote: int = Query(...), db: Session = Depends(get_db)):
    if vote not in [-1, 0, 1]: raise HTTPException(status_code=400, detail="Invalid vote")
    post = db.query(models.Post).filter(models.Post.id == post_id).first()
    if not post: raise HTTPException(status_code=404, detail="Post not found")
    
    post_vote = db.query(models.PostVote).filter(
        (models.PostVote.post_id == post_id) & (models.PostVote.user_uid == user_uid)
    ).first()
    prev_vote = post_vote.vote if post_vote else 0
    
    if post_vote:
        if vote == 0: db.delete(post_vote)
        else: post_vote.vote = vote
    elif vote != 0:
        db.add(models.PostVote(post_id=post_id, user_uid=user_uid, vote=vote))
    
    post.score = post.score - prev_vote + vote
    db.commit()
    return {"status": "success"}


# ============ STUDY GROUP ENDPOINTS ============

class StudyGroupCreate(BaseModel):
    name: str
    user_email: str

class JoinGroupRequest(BaseModel):
    user_email: str

@app.get("/study-groups")
def get_study_groups(user_email: str, db: Session = Depends(get_db)):
    members = db.query(models.StudyGroupMember).filter(
        models.StudyGroupMember.user_email == user_email
    ).all()
    group_ids = [m.group_id for m in members]
    groups = db.query(models.StudyGroup).filter(
        models.StudyGroup.id.in_(group_ids)
    ).all()
    return [
        {"id": g.id, "name": g.name, "created_at": g.created_at,
         "member_count": len(g.members)}
        for g in groups
    ]

@app.post("/study-groups")
def create_study_group(body: StudyGroupCreate, db: Session = Depends(get_db)):
    group = models.StudyGroup(name=body.name)
    db.add(group)
    db.flush()
    db.add(models.StudyGroupMember(group_id=group.id, user_email=body.user_email))
    db.commit()
    db.refresh(group)
    return {"id": group.id, "name": group.name, "created_at": group.created_at}

@app.post("/study-groups/{group_id}/join")
def join_study_group(group_id: int, body: JoinGroupRequest, db: Session = Depends(get_db)):
    group = db.query(models.StudyGroup).filter(models.StudyGroup.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    existing = db.query(models.StudyGroupMember).filter(
        models.StudyGroupMember.group_id == group_id,
        models.StudyGroupMember.user_email == body.user_email
    ).first()
    if not existing:
        db.add(models.StudyGroupMember(group_id=group_id, user_email=body.user_email))
        db.commit()
    return {"id": group.id, "name": group.name}

@app.get("/study-groups/{group_id}/suggestions")
def get_group_suggestions(
    group_id: int,
    range_start: str,
    range_end: str,
    duration_minutes: int = 60,
    slot_minutes: int = 30,
    day_start_hour: int = 8,
    day_end_hour: int = 22,
    min_available_members: int = 1,
    user_timezone: str = "UTC",
    db: Session = Depends(get_db)
):
    from datetime import timedelta
    group = db.query(models.StudyGroup).filter(models.StudyGroup.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    members = db.query(models.StudyGroupMember).filter(
        models.StudyGroupMember.group_id == group_id
    ).all()
    member_emails = {m.user_email for m in members}
    total_members = len(member_emails)

    start = datetime.fromisoformat(range_start.replace("Z", "+00:00")).replace(tzinfo=None)
    end = datetime.fromisoformat(range_end.replace("Z", "+00:00")).replace(tzinfo=None)

    busy_slots = db.query(models.UserAvailability).filter(
        models.UserAvailability.user_email.in_(member_emails),
        models.UserAvailability.starts_at < end,
        models.UserAvailability.ends_at > start
    ).all()

    suggestions = []
    slot_start = start
    while slot_start + timedelta(minutes=duration_minutes) <= end:
        slot_end = slot_start + timedelta(minutes=duration_minutes)
        if day_start_hour <= slot_start.hour < day_end_hour:
            busy_count = sum(
                1 for b in busy_slots
                if b.starts_at < slot_end and b.ends_at > slot_start
            )
            available = total_members - busy_count
            if available >= min_available_members:
                suggestions.append({
                    "starts_at": slot_start.isoformat(),
                    "ends_at": slot_end.isoformat(),
                    "available_members": available,
                    "total_members": total_members
                })
        slot_start += timedelta(minutes=slot_minutes)

    return {"suggestions": suggestions[:50]}


# ============ STUDY SESSION ENDPOINTS ============

class StudySessionCreate(BaseModel):
    creator_email: str
    session_type: str = "solo"
    title: str
    starts_at: str
    ends_at: str
    group_id: Optional[int] = None

@app.get("/study-sessions")
def get_study_sessions(user_email: str, range_start: str, range_end: str, db: Session = Depends(get_db)):
    start = datetime.fromisoformat(range_start.replace("Z", "+00:00")).replace(tzinfo=None)
    end = datetime.fromisoformat(range_end.replace("Z", "+00:00")).replace(tzinfo=None)
    sessions = db.query(models.StudySession).filter(
        models.StudySession.creator_email == user_email,
        models.StudySession.starts_at >= start,
        models.StudySession.starts_at < end
    ).order_by(models.StudySession.starts_at.asc()).all()
    return [
        {
            "id": s.id,
            "title": s.title,
            "session_type": s.session_type,
            "starts_at": s.starts_at.isoformat(),
            "ends_at": s.ends_at.isoformat(),
            "group_id": s.group_id,
            "creator_email": s.creator_email
        }
        for s in sessions
    ]

@app.post("/study-sessions")
def create_study_session(body: StudySessionCreate, db: Session = Depends(get_db)):
    session = models.StudySession(
        creator_email=body.creator_email,
        session_type=body.session_type,
        title=body.title,
        starts_at=datetime.fromisoformat(body.starts_at.replace("Z", "+00:00")).replace(tzinfo=None),
        ends_at=datetime.fromisoformat(body.ends_at.replace("Z", "+00:00")).replace(tzinfo=None),
        group_id=body.group_id
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return {
        "id": session.id,
        "title": session.title,
        "session_type": session.session_type,
        "starts_at": session.starts_at.isoformat(),
        "ends_at": session.ends_at.isoformat(),
        "group_id": session.group_id
    }


# ============ AVAILABILITY SYNC ENDPOINT ============

class BusySlot(BaseModel):
    starts_at: str
    ends_at: str

class AvailabilitySync(BaseModel):
    user_email: str
    starts_at: str
    ends_at: str
    timezone: str = "UTC"
    source: str = "google_calendar"
    busy_slots: List[BusySlot]

@app.post("/availability/sync")
def sync_availability(body: AvailabilitySync, db: Session = Depends(get_db)):
    range_start = datetime.fromisoformat(body.starts_at.replace("Z", "+00:00")).replace(tzinfo=None)
    range_end = datetime.fromisoformat(body.ends_at.replace("Z", "+00:00")).replace(tzinfo=None)
    # Delete old blocks in range
    db.query(models.UserAvailability).filter(
        models.UserAvailability.user_email == body.user_email,
        models.UserAvailability.starts_at >= range_start,
        models.UserAvailability.ends_at <= range_end
    ).delete(synchronize_session=False)
    count = 0
    for slot in body.busy_slots:
        db.add(models.UserAvailability(
            user_email=body.user_email,
            starts_at=datetime.fromisoformat(slot.starts_at.replace("Z", "+00:00")).replace(tzinfo=None),
            ends_at=datetime.fromisoformat(slot.ends_at.replace("Z", "+00:00")).replace(tzinfo=None),
            source=body.source
        ))
        count += 1
    db.commit()
    return {"inserted_busy_blocks": count}
