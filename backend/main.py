from fastapi import FastAPI, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict
from database import engine, Base, get_db
import models
from typing import List, Optional
from datetime import datetime, timedelta

# WARNING: This deletes all data! 
# Uncomment once to reset the schema for your new multi-class structure.
# Base.metadata.drop_all(bind=engine)

# Create tables in PostgreSQL automatically 
Base.metadata.create_all(bind=engine)

app = FastAPI()

origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============ PYDANTIC MODELS ============

class UserSimple(BaseModel):
    model_config = ConfigDict(from_attributes=True)
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
    firebase_uid: str
    email: str
    full_name: str
    role: str


class MessageSend(BaseModel):
    sender_uid: str
    receiver_uid: str
    content: str
    course_id: int
    is_group: bool = False
    
class MessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    message_id: int
    conversation_id: int
    sender_id: str
    sender_name: str
    content: str
    created_at: datetime


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
    course_id: int


class CourseCreate(BaseModel):
    name: str
    course_code: str
    owner_id: str  # Changed to Firebase UID


class CourseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    course_code: str
    name: str
    description: Optional[str]


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
            "user": {
                "firebase_uid": db_user.firebase_uid,
                "full_name": db_user.full_name,
                "role": db_user.role
            }
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
        return {
            "status": "success",
            "firebase_uid": new_user.firebase_uid,
            "full_name": new_user.full_name,
            "role": new_user.role
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@app.get("/user/{firebase_uid}")
def get_user_profile(firebase_uid: str, db: Session = Depends(get_db)):
    """Fetch user profile by Firebase UID."""
    user = db.query(models.User).filter(models.User.firebase_uid == firebase_uid).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {
        "firebase_uid": user.firebase_uid,
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
            firebase_uid=u.firebase_uid,
            full_name=u.full_name,
            email=u.email,
            role=u.role or "Student"
        )
        for u in users
    ]


@app.get("/users/{firebase_uid}/courses", response_model=List[CourseResponse])
def get_user_courses(firebase_uid: str, db: Session = Depends(get_db)):
    """Returns all courses a user is enrolled in for the home page grid."""
    enrollments = db.query(models.Enrollment).filter(models.Enrollment.user_id == firebase_uid).all()
    return [e.course for e in enrollments]


# ============ MESSAGING ENDPOINTS ============

@app.post("/conversations/one-on-one")
def get_or_create_one_on_one(
    user_uid_1: str,
    user_uid_2: str,
    course_id: int,
    db: Session = Depends(get_db)
):
    """Creates or retrieves a 1-on-1 DM scoped to a specific course."""
    if user_uid_1 == user_uid_2:
        raise HTTPException(status_code=400, detail="Cannot chat with yourself.")

    # Look for existing 1-on-1 in this specific course context
    existing = db.query(models.Conversation).filter(
        models.Conversation.is_group == False,
        models.Conversation.course_id == course_id
    ).join(models.ConversationParticipant).filter(
        models.ConversationParticipant.user_id.in_([user_uid_1, user_uid_2])
    ).group_by(models.Conversation.conversation_id).having(
        func.count(models.ConversationParticipant.participant_id) == 2
    ).first()

    if existing:
        return {"conversation_id": existing.conversation_id, "is_new": False}

    new_conv = models.Conversation(is_group=False, course_id=course_id)
    db.add(new_conv)
    db.flush()
    
    db.add(models.ConversationParticipant(conversation_id=new_conv.conversation_id, user_id=user_uid_1))
    db.add(models.ConversationParticipant(conversation_id=new_conv.conversation_id, user_id=user_uid_2))
    db.commit()
    
    return {"conversation_id": new_conv.conversation_id, "is_new": True}

@app.get("/conversations/group")
def get_or_create_group_chat(
    course_id: int, 
    group_id: Optional[int] = None, 
    db: Session = Depends(get_db)
):
    """Retrieves or creates a group chat for a class or study group."""
    # If group_id is provided, it's a study group chat. Otherwise, it's the main Class Chat.
    query = db.query(models.Conversation).filter(
        models.Conversation.course_id == course_id,
        models.Conversation.is_group == True
    )
    
    if group_id:
        # You might need to add group_id to your Conversation model if not there
        query = query.filter(models.Conversation.group_id == group_id)
        name = f"Study Group {group_id}" 
    else:
        course = db.query(models.Course).filter(models.Course.id == course_id).first()
        name = f"{course.course_code} Class Chat"

    conversation = query.first()

    if not conversation:
        conversation = models.Conversation(
            course_id=course_id, 
            is_group=True, 
            group_name=name
        )
        db.add(conversation)
        db.commit()
        db.refresh(conversation)

    return {"conversation_id": conversation.conversation_id, "name": conversation.group_name}


@app.get("/messages")
def get_messages(
    user1: str,
    user2: str,
    course_id: Optional[int] = None,
    is_group: bool = Query(False), # New parameter to distinguish chat types
    db: Session = Depends(get_db)
):
    """Fetch messages for either a private DM or a Class Group chat."""
    
    if is_group:
        # 1. Look for the shared group conversation for this course
        conversation = db.query(models.Conversation).filter(
            models.Conversation.course_id == course_id,
            models.Conversation.is_group == True
        ).first()
    else:
        # 2. Look for the private 1-on-1 conversation
        conversation = db.query(models.Conversation).filter(
            models.Conversation.course_id == course_id,
            models.Conversation.is_group == False
        ).join(models.ConversationParticipant).filter(
            models.ConversationParticipant.user_id.in_([user1, user2])
        ).group_by(models.Conversation.conversation_id).having(
            func.count(models.ConversationParticipant.participant_id) == 2
        ).first()

    # If no conversation exists yet, return an empty list instead of crashing
    if not conversation:
        return []

    # 3. Fetch all messages belonging to that conversation ID
    messages = db.query(models.Message).filter(
        models.Message.conversation_id == conversation.conversation_id
    ).order_by(models.Message.created_at.asc()).all()

    return [
        {
            "id": m.message_id,
            "sender_uid": m.sender_id,
            "sender_name": m.sender.full_name,
            "content": m.content,
            "created_at": m.created_at.isoformat()
        }
        for m in messages
    ]

@app.get("/conversations/class/{course_id}")
def get_class_conversation(course_id: int, db: Session = Depends(get_db)):
    """Find or create the public group conversation for a specific course."""
    # Look for a group conversation tagged to this course
    conv = db.query(models.Conversation).filter(
        models.Conversation.course_id == course_id,
        models.Conversation.is_group == True
    ).first()

    if not conv:
        # If it doesn't exist, create the 'Class Chat'
        course = db.query(models.Course).filter(models.Course.id == course_id).first()
        conv = models.Conversation(
            course_id=course_id,
            is_group=True,
            group_name=f"{course.course_code} General Chat"
        )
        db.add(conv)
        db.commit()
        db.refresh(conv)
    
    return conv

@app.post("/messages")
def send_message(data: MessageSend, db: Session = Depends(get_db)):
    """Send a message in either a 1-on-1 or Class Group context."""
    if not data.content.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    if data.is_group:
        # 1. GROUP CHAT LOGIC
        conversation = db.query(models.Conversation).filter(
            models.Conversation.is_group == True,
            models.Conversation.course_id == data.course_id
        ).first()

        if not conversation:
            # Fallback: Create the class chat if it doesn't exist yet
            course = db.query(models.Course).filter(models.Course.id == data.course_id).first()
            conversation = models.Conversation(
                is_group=True, 
                course_id=data.course_id,
                group_name=f"{course.course_code} General Chat"
            )
            db.add(conversation)
            db.flush()
    else:
        # 2. 1-on-1 DM LOGIC (Existing logic)
        conversation = db.query(models.Conversation).filter(
            models.Conversation.is_group == False,
            models.Conversation.course_id == data.course_id
        ).join(models.ConversationParticipant).filter(
            models.ConversationParticipant.user_id.in_([data.sender_uid, data.receiver_uid])
        ).group_by(models.Conversation.conversation_id).having(
            func.count(models.ConversationParticipant.participant_id) == 2
        ).first()

        if not conversation:
            conversation = models.Conversation(is_group=False, course_id=data.course_id)
            db.add(conversation)
            db.flush()
            db.add(models.ConversationParticipant(conversation_id=conversation.conversation_id, user_id=data.sender_uid))
            db.add(models.ConversationParticipant(conversation_id=conversation.conversation_id, user_id=data.receiver_uid))

    # 3. Create and save the message
    new_message = models.Message(
        conversation_id=conversation.conversation_id,
        sender_id=data.sender_uid,
        content=data.content.strip()
    )
    db.add(new_message)
    db.commit()
    db.refresh(new_message)

    return {
        "id": new_message.message_id,
        "sender_uid": new_message.sender_id,
        "sender_name": new_message.sender.full_name,
        "content": new_message.content,
        "created_at": new_message.created_at.isoformat()
    }

# ============ RESOURCE/POST ENDPOINTS ============

@app.post("/posts")
def create_post(
    post_data: PostCreate,
    course_id: int = Query(...),
    author_uid: str = Query(...),
    db: Session = Depends(get_db)
):
    """Create a resource post in a course."""
    author = db.query(models.User).filter(models.User.firebase_uid == author_uid).first()
    if not author:
        raise HTTPException(status_code=404, detail="Author not found")

    new_post = models.Post(
        course_id=course_id,
        author_uid=author_uid,
        title=post_data.title,
        description=post_data.description,
        resource_link=post_data.resource_link
    )
    db.add(new_post)
    db.commit()
    db.refresh(new_post)
    return new_post


@app.get("/posts")
def get_posts(
    course_id: Optional[int] = None,
    current_user_uid: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Fetch posts for a course with vote information."""
    query = db.query(models.Post)
    
    if course_id:
        query = query.filter(models.Post.course_id == course_id)
    
    posts = query.order_by(models.Post.created_at.desc()).all()

    result = []
    for post in posts:
        user_vote = 0
        if current_user_uid:
            vote = db.query(models.PostVote).filter(
                models.PostVote.post_id == post.id,
                models.PostVote.user_uid == current_user_uid
            ).first()
            user_vote = vote.vote if vote else 0

        result.append({
            "id": post.id,
            "course_id": post.course_id,
            "author_uid": post.author_uid,
            "author_name": post.author.full_name,
            "author_role": post.author.role,
            "title": post.title,
            "description": post.description,
            "resource_link": post.resource_link,
            "score": post.score,
            "user_vote": user_vote,
            "created_at": post.created_at.isoformat()
        })

    return result

@app.post("/posts/{post_id}/flag")
def flag_post(post_id: int, db: Session = Depends(get_db)):
    """Flags a post for TA/Admin review."""
    post = db.query(models.Post).filter(models.Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    post.is_flagged = True
    db.commit()
    return {"status": "success", "message": "Post flagged for review"}

@app.post("/posts/{post_id}/vote")
def vote_on_post(
    post_id: int,
    user_uid: str = Query(...),
    vote: int = Query(...),
    db: Session = Depends(get_db)
):
    """Vote on a post (+1 upvote, -1 downvote, 0 neutral)."""
    post = db.query(models.Post).filter(models.Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    existing_vote = db.query(models.PostVote).filter(
        models.PostVote.post_id == post_id,
        models.PostVote.user_uid == user_uid
    ).first()

    if existing_vote:
        # Remove old vote contribution
        post.score -= existing_vote.vote
        if vote == 0:
            db.delete(existing_vote)
        else:
            existing_vote.vote = vote
            post.score += vote
    else:
        if vote != 0:
            db.add(models.PostVote(post_id=post_id, user_uid=user_uid, vote=vote))
            post.score += vote

    db.commit()
    return {"status": "success", "new_score": post.score}

@app.delete("/posts/{post_id}")
def delete_post(post_id: int, user_uid: str = Query(...), db: Session = Depends(get_db)):
    """Allows TAs and Admins to delete any post."""
    # 1. Verify user role
    user = db.query(models.User).filter(models.User.firebase_uid == user_uid).first()
    if not user or user.role not in ["TA", "Admin"]:
        raise HTTPException(status_code=403, detail="Only TAs or Admins can delete posts.")

    # 2. Find and delete post
    post = db.query(models.Post).filter(models.Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    db.delete(post)
    db.commit()
    return {"status": "success", "message": "Post deleted"}

@app.get("/posts/flagged", response_model=List[PostOut])
def get_flagged_posts(db: Session = Depends(get_db)):
    """Fetch all posts that have been flagged by users."""
    posts = db.query(models.Post).filter(models.Post.is_flagged == True).all()
    # Return formatted posts for the dashboard
    return [
        {
            "id": p.id,
            "course_id": p.course_id,
            "author_uid": p.author_uid,
            "author_name": p.author.full_name,
            "author_role": p.author.role,
            "title": p.title,
            "description": p.description,
            "resource_link": p.resource_link,
            "score": p.score,
            "user_vote": 0, # Neutral for dashboard view
            "created_at": p.created_at.isoformat()
        }
        for p in posts
    ]

@app.post("/posts/{post_id}/dismiss-flag")
def dismiss_flag(post_id: int, db: Session = Depends(get_db)):
    """Unflags a post (TA determines content is safe)."""
    post = db.query(models.Post).filter(models.Post.id == post_id).first()
    post.is_flagged = False
    db.commit()
    return {"status": "success"}

# ============ COURSE & ENROLLMENT ENDPOINTS ============

@app.post("/courses", response_model=CourseResponse)
def create_course(course_data: CourseCreate, db: Session = Depends(get_db)):
    """Creates a new class workspace. Only for Admins/TAs."""
    user = db.query(models.User).filter(models.User.firebase_uid == course_data.owner_id).first()
    if not user or user.role not in ["Admin", "TA"]:
        raise HTTPException(status_code=403, detail="Only Admins/TAs can create courses.")
    
    new_course = models.Course(
        name=course_data.name,
        course_code=course_data.course_code.upper(),
        owner_id=course_data.owner_id
    )
    db.add(new_course)
    db.flush()
    
    # Auto-enroll the creator
    db.add(models.Enrollment(user_id=course_data.owner_id, course_id=new_course.id))
    db.commit()
    db.refresh(new_course)
    return new_course


@app.post("/courses/join")
def join_course(
    course_code: str = Query(...),
    firebase_uid: str = Query(...),
    db: Session = Depends(get_db)
):
    """Enrolls a student via a class code."""
    course = db.query(models.Course).filter(models.Course.course_code == course_code.upper()).first()
    if not course:
        raise HTTPException(status_code=404, detail="Invalid course code.")
    
    existing = db.query(models.Enrollment).filter(
        models.Enrollment.user_id == firebase_uid, 
        models.Enrollment.course_id == course.id
    ).first()
    
    if not existing:
        db.add(models.Enrollment(user_id=firebase_uid, course_id=course.id))
        db.commit()
    return {"status": "success", "course_id": course.id, "course_name": course.name}


# ============ STUDY GROUP ENDPOINTS ============

class StudyGroupCreate(BaseModel):
    name: str
    course_id: int


@app.post("/study-groups")
def create_study_group(group_data: StudyGroupCreate, db: Session = Depends(get_db)):
    """Create a study group in a course."""
    new_group = models.StudyGroup(
        course_id=group_data.course_id,
        name=group_data.name
    )
    db.add(new_group)
    db.commit()
    db.refresh(new_group)
    return {"id": new_group.id, "name": new_group.name, "course_id": new_group.course_id}


@app.post("/study-groups/{group_id}/members")
def add_group_member(
    group_id: int,
    user_email: str = Query(...),
    db: Session = Depends(get_db)
):
    """Add a member to a study group."""
    group = db.query(models.StudyGroup).filter(models.StudyGroup.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    existing = db.query(models.StudyGroupMember).filter(
        models.StudyGroupMember.group_id == group_id,
        models.StudyGroupMember.user_email == user_email
    ).first()

    if not existing:
        db.add(models.StudyGroupMember(group_id=group_id, user_email=user_email))
        db.commit()

    return {"status": "success"}


@app.get("/study-groups/{group_id}")
def get_study_group(group_id: int, db: Session = Depends(get_db)):
    """Fetch study group details."""
    group = db.query(models.StudyGroup).filter(models.StudyGroup.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    members = db.query(models.StudyGroupMember).filter(models.StudyGroupMember.group_id == group_id).all()
    
    return {
        "id": group.id,
        "name": group.name,
        "course_id": group.course_id,
        "members": [{"email": m.user_email, "joined_at": m.joined_at.isoformat()} for m in members]
    }


@app.get("/study-groups/course/{course_id}")
def get_course_study_groups(course_id: int, db: Session = Depends(get_db)):
    """Fetch all study groups for a course."""
    groups = db.query(models.StudyGroup).filter(models.StudyGroup.course_id == course_id).all()
    return [
        {
            "id": g.id,
            "name": g.name,
            "course_id": g.course_id,
            "member_count": len(db.query(models.StudyGroupMember).filter(models.StudyGroupMember.group_id == g.id).all())
        }
        for g in groups
    ]


# ============ STUDY SESSION ENDPOINTS ============

class StudySessionCreate(BaseModel):
    creator_email: str
    course_id: int
    session_type: str = "solo"
    title: str
    starts_at: str
    ends_at: str
    group_id: Optional[int] = None


@app.get("/study-sessions")
def get_study_sessions(
    user_email: str,
    range_start: str,
    range_end: str,
    course_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Fetches study sessions for a user, optionally filtered by course."""
    start = datetime.fromisoformat(range_start.replace("Z", "+00:00")).replace(tzinfo=None)
    end = datetime.fromisoformat(range_end.replace("Z", "+00:00")).replace(tzinfo=None)
    
    query = db.query(models.StudySession).filter(
        models.StudySession.creator_email == user_email,
        models.StudySession.starts_at >= start,
        models.StudySession.starts_at < end
    )
    
    if course_id:
        query = query.filter(models.StudySession.course_id == course_id)
        
    sessions = query.order_by(models.StudySession.starts_at.asc()).all()
    
    return [
        {
            "id": s.id,
            "title": s.title,
            "session_type": s.session_type,
            "starts_at": s.starts_at.isoformat(),
            "ends_at": s.ends_at.isoformat(),
            "group_id": s.group_id,
            "course_id": s.course_id,
            "creator_email": s.creator_email
        }
        for s in sessions
    ]


@app.post("/study-sessions")
def create_study_session(body: StudySessionCreate, db: Session = Depends(get_db)):
    """Creates a study session."""
    if body.session_type == "TA_review":
        user = db.query(models.User).filter(models.User.email == body.creator_email).first()
        if not user or user.role not in ["TA", "Admin"]:
            raise HTTPException(status_code=403, detail="Only TAs or Admins can create Review Sessions.")

    session = models.StudySession(
        creator_email=body.creator_email,
        course_id=body.course_id,
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
        "group_id": session.group_id,
        "course_id": session.course_id
    }


# ============ AVAILABILITY SYNC ENDPOINTS ============

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
    """Syncs busy blocks from Google Calendar."""
    range_start = datetime.fromisoformat(body.starts_at.replace("Z", "+00:00")).replace(tzinfo=None)
    range_end = datetime.fromisoformat(body.ends_at.replace("Z", "+00:00")).replace(tzinfo=None)
    
    # Delete old blocks in range to avoid duplicates
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