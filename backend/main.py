"""
- Wires up the FastAPI app and CORS for the React frontend.
- Defines Pydantic request/response schemas alongside their routes.
- Implements all REST endpoints, grouped by feature: users & profile,
  courses & enrollment, posts & moderation, conversations & messages,
  study groups, study sessions, and Google Calendar availability sync.
- Runs lightweight additive schema migrations at startup via
  ``ensure_schema_updates`` so local dev databases stay compatible.
"""
from fastapi import FastAPI, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, text, or_
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict
from database import engine, Base, get_db
import models
from typing import List, Optional
from datetime import datetime, timedelta, timezone


def ensure_schema_updates():
    """Apply minimal additive schema updates for local development."""
    # Skip schema updates for SQLite (used in testing)
    from database import SQLALCHEMY_DATABASE_URL
    if "sqlite" in SQLALCHEMY_DATABASE_URL.lower():
        return
        
    statements = [
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS google_calendar_refresh_token VARCHAR",
        "ALTER TABLE conversations ADD COLUMN IF NOT EXISTS course_id INTEGER",
        "ALTER TABLE study_sessions ADD COLUMN IF NOT EXISTS course_id INTEGER",
        "ALTER TABLE posts ADD COLUMN IF NOT EXISTS course_id INTEGER",
        "ALTER TABLE posts ADD COLUMN IF NOT EXISTS is_flagged BOOLEAN DEFAULT FALSE",
        "ALTER TABLE user_availability ADD COLUMN IF NOT EXISTS study_session_id INTEGER",
        "ALTER TABLE messages ADD COLUMN IF NOT EXISTS conversation_id INTEGER",
        "ALTER TABLE messages ADD COLUMN IF NOT EXISTS sender_id VARCHAR",
        "ALTER TABLE conversation_participants ADD COLUMN IF NOT EXISTS user_uid VARCHAR",
        """
        CREATE TABLE IF NOT EXISTS study_session_invitees (
            id SERIAL PRIMARY KEY,
            study_session_id INTEGER NOT NULL REFERENCES study_sessions(id),
            user_email VARCHAR NOT NULL,
            created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
        )
        """,
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_name = 'messages' AND column_name = 'sender_uid'
            ) THEN
                UPDATE messages
                SET sender_id = sender_uid
                WHERE sender_id IS NULL;
            END IF;
        END $$;
        """,
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_name = 'messages' AND column_name = 'sender_uid'
            ) THEN
                ALTER TABLE messages ALTER COLUMN sender_uid DROP NOT NULL;
            END IF;
        END $$;
        """,
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_name = 'messages' AND column_name = 'receiver_uid'
            ) THEN
                ALTER TABLE messages ALTER COLUMN receiver_uid DROP NOT NULL;
            END IF;
        END $$;
        """,
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_name = 'conversation_participants' AND column_name = 'user_id'
            ) AND EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_name = 'users' AND column_name = 'user_id'
            ) THEN
                UPDATE conversation_participants cp
                SET user_uid = u.firebase_uid
                FROM users u
                WHERE cp.user_uid IS NULL
                  AND cp.user_id::text = u.user_id::text;
            END IF;
        END $$;
        """,
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_name = 'conversation_participants' AND column_name = 'user_id'
            ) THEN
                ALTER TABLE conversation_participants ALTER COLUMN user_id DROP NOT NULL;
            END IF;
        END $$;
        """,
    ]

    with engine.begin() as connection:
        for statement in statements:
            connection.execute(text(statement))


# Create tables in PostgreSQL automatically 
Base.metadata.create_all(bind=engine)
ensure_schema_updates()

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


def find_direct_conversation(db: Session, course_id: int, user_uid_1: str, user_uid_2: str):
    """Find a 1-on-1 conversation using either legacy or current participant columns."""
    row = db.execute(
        text(
            """
            SELECT c.conversation_id
            FROM conversations c
            JOIN conversation_participants cp
              ON c.conversation_id = cp.conversation_id
            WHERE c.course_id = :course_id
              AND c.is_group = FALSE
              AND COALESCE(cp.user_uid, cp.user_id::text) IN (:user1, :user2)
            GROUP BY c.conversation_id
            HAVING COUNT(DISTINCT COALESCE(cp.user_uid, cp.user_id::text)) = 2
            LIMIT 1
            """
        ),
        {"course_id": course_id, "user1": user_uid_1, "user2": user_uid_2},
    ).first()

    if not row:
        return None

    return db.query(models.Conversation).filter(
        models.Conversation.conversation_id == row[0]
    ).first()


def conversation_has_participant(db: Session, conversation_id: int, user_uid: str) -> bool:
    row = db.execute(
        text(
            """
            SELECT 1
            FROM conversation_participants cp
            WHERE cp.conversation_id = :conversation_id
              AND COALESCE(cp.user_uid, cp.user_id::text) = :user_uid
            LIMIT 1
            """
        ),
        {"conversation_id": conversation_id, "user_uid": user_uid},
    ).first()
    return row is not None


def get_other_participant_uid(db: Session, conversation_id: int, user_uid: str) -> Optional[str]:
    row = db.execute(
        text(
            """
            SELECT COALESCE(cp.user_uid, cp.user_id::text) AS participant_uid
            FROM conversation_participants cp
            WHERE cp.conversation_id = :conversation_id
              AND COALESCE(cp.user_uid, cp.user_id::text) != :user_uid
            LIMIT 1
            """
        ),
        {"conversation_id": conversation_id, "user_uid": user_uid},
    ).first()
    if not row:
        return None
    return row[0]


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


@app.get("/courses/{course_id}/members", response_model=List[UserSimple])
def get_course_members(course_id: int, db: Session = Depends(get_db)):
    """Returns all enrolled users for a course."""
    enrollments = db.query(models.Enrollment).filter(models.Enrollment.course_id == course_id).all()
    member_ids = [enrollment.user_id for enrollment in enrollments]
    if not member_ids:
        return []

    users = db.query(models.User).filter(models.User.firebase_uid.in_(member_ids)).all()
    return [
        UserSimple(
            firebase_uid=u.firebase_uid,
            full_name=u.full_name,
            email=u.email,
            role=u.role or "Student"
        )
        for u in users
    ]


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

    existing = find_direct_conversation(db, course_id, user_uid_1, user_uid_2)

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
        conversation = find_direct_conversation(db, course_id, user1, user2)

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
            "sender_name": m.sender.full_name if m.sender else "Unknown User",
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
        conversation = find_direct_conversation(
            db, data.course_id, data.sender_uid, data.receiver_uid
        )

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

@app.get("/conversations/inbox/global")
def get_global_inbox(user_uid: str = Query(...), db: Session = Depends(get_db)):
    """
    Fetches ALL active conversations for a user across ALL enrolled courses.
    Appends course codes to group chat names.
    """
    # 1. Get all courses the user is enrolled in
    enrollments = db.query(models.Enrollment).filter(models.Enrollment.user_id == user_uid).all()
    course_ids = [e.course_id for e in enrollments]

    # 2. Get all conversations (Group and Private) for those courses
    # We join with Course to get the course_code for the label
    conversations = db.query(models.Conversation).join(models.Course).filter(
        models.Conversation.course_id.in_(course_ids)
    ).all()

    inbox = []
    for conv in conversations:
        # Check if user is a participant (for DMs) or if it's a group chat
        is_participant = conversation_has_participant(db, conv.conversation_id, user_uid)

        if conv.is_group:
            # Append Course Code to Group Name: e.g., "General Chat (CSDS393)"
            inbox.append({
                "conversation_id": conv.conversation_id,
                "firebase_uid": f"GROUP_{conv.conversation_id}",
                "full_name": conv.group_name or "Class Discussion",
                "role": "Public Channel",
                "is_group": True,
                "course_code": conv.course.course_code, 
                "course_id": conv.course_id
            })
        elif is_participant:
            # For DMs, find the other person
            other_part_uid = get_other_participant_uid(db, conv.conversation_id, user_uid)
            other_user = None
            if other_part_uid:
                other_user = db.query(models.User).filter(
                    models.User.firebase_uid == other_part_uid
                ).first()

            if other_user:
                inbox.append({
                    "conversation_id": conv.conversation_id,
                    "firebase_uid": other_user.firebase_uid,
                    "full_name": other_user.full_name,
                    "role": other_user.role,
                    "is_group": False,
                    "course_code": conv.course.course_code,
                    "course_id": conv.course_id
                })

    return inbox


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

    normalized_code = course_data.course_code.strip().upper()
    normalized_name = course_data.name.strip()
    if not normalized_code or not normalized_name:
        raise HTTPException(status_code=400, detail="Course name and code are required.")

    existing_course = db.query(models.Course).filter(models.Course.course_code == normalized_code).first()
    if existing_course:
        raise HTTPException(status_code=400, detail="A course with that code already exists.")
    
    new_course = models.Course(
        name=normalized_name,
        course_code=normalized_code,
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
    normalized_code = course_code.strip().upper()
    if not normalized_code:
        raise HTTPException(status_code=400, detail="Course code is required.")

    user = db.query(models.User).filter(models.User.firebase_uid == firebase_uid).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    course = db.query(models.Course).filter(models.Course.course_code == normalized_code).first()
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
    invitees: List[str] = []


@app.get("/study-sessions")
def get_study_sessions(
    user_email: str,
    range_start: str,
    range_end: str,
    course_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Fetches study sessions for a user, optionally filtered by course."""
    normalized_user_email = normalize_email(user_email)
    start = datetime.fromisoformat(range_start.replace("Z", "+00:00")).replace(tzinfo=None)
    end = datetime.fromisoformat(range_end.replace("Z", "+00:00")).replace(tzinfo=None)
    
    query = db.query(models.StudySession).filter(
        models.StudySession.creator_email == normalized_user_email,
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


@app.get("/study-sessions/course/{course_id}")
def get_course_sessions(
    course_id: int,
    range_start: str,
    range_end: str,
    requester_email: str = Query(...),
    db: Session = Depends(get_db)
):
    """Fetch study sessions in a course visible to the requester."""
    normalized_requester_email = normalize_email(requester_email)
    start = parse_iso_to_naive(range_start)
    end = parse_iso_to_naive(range_end)

    invited_session_ids = db.query(models.StudySessionInvitee.study_session_id).filter(
        models.StudySessionInvitee.user_email == normalized_requester_email
    )

    sessions = db.query(models.StudySession).filter(
        models.StudySession.course_id == course_id,
        models.StudySession.starts_at >= start,
        models.StudySession.starts_at < end,
        or_(
            models.StudySession.creator_email == normalized_requester_email,
            models.StudySession.id.in_(invited_session_ids),
        )
    ).order_by(models.StudySession.starts_at.asc()).all()

    return [
        {
            "id": s.id,
            "title": s.title,
            "session_type": s.session_type,
            "starts_at": s.starts_at.isoformat(),
            "ends_at": s.ends_at.isoformat(),
            "group_id": s.group_id,
            "course_id": s.course_id,
            "creator_email": s.creator_email,
            "invitees": [invitee.user_email for invitee in s.invitees],
        }
        for s in sessions
    ]


@app.get("/study-sessions/course/{course_id}/summary")
def get_course_session_summary(
    course_id: int,
    requester_email: str = Query(...),
    db: Session = Depends(get_db)
):
    """Fetch upcoming visible study sessions and completed study hours for a course."""
    normalized_requester_email = normalize_email(requester_email)
    now = datetime.utcnow()

    invited_session_ids = db.query(models.StudySessionInvitee.study_session_id).filter(
        models.StudySessionInvitee.user_email == normalized_requester_email
    )

    visible_sessions = db.query(models.StudySession).filter(
        models.StudySession.course_id == course_id,
        or_(
            models.StudySession.creator_email == normalized_requester_email,
            models.StudySession.id.in_(invited_session_ids),
        )
    )

    upcoming_sessions = visible_sessions.filter(
        models.StudySession.starts_at >= now
    ).order_by(models.StudySession.starts_at.asc()).all()

    completed_sessions = visible_sessions.filter(
        models.StudySession.ends_at <= now
    ).all()

    completed_minutes = 0
    for session in completed_sessions:
        completed_minutes += max(
            0,
            int((session.ends_at - session.starts_at).total_seconds() // 60)
        )

    return {
        "upcoming_sessions": [
            {
                "id": s.id,
                "title": s.title,
                "session_type": s.session_type,
                "starts_at": s.starts_at.isoformat(),
                "ends_at": s.ends_at.isoformat(),
                "group_id": s.group_id,
                "course_id": s.course_id,
                "creator_email": s.creator_email,
                "invitees": [invitee.user_email for invitee in s.invitees],
            }
            for s in upcoming_sessions
        ],
        "completed_hours": round(completed_minutes / 60, 1),
        "completed_sessions": len(completed_sessions),
    }


@app.post("/study-sessions")
def create_study_session(body: StudySessionCreate, db: Session = Depends(get_db)):
    """Creates a study session."""
    normalized_creator_email = normalize_email(body.creator_email)
    normalized_invitees = sorted({
        normalize_email(email)
        for email in body.invitees
        if email and normalize_email(email) != normalized_creator_email
    })

    if body.session_type == "TA_review":
        user = db.query(models.User).filter(models.User.email == normalized_creator_email).first()
        if not user or user.role not in ["TA", "Admin"]:
            raise HTTPException(status_code=403, detail="Only TAs or Admins can create Review Sessions.")

    session_start = parse_iso_to_naive(body.starts_at)
    session_end = parse_iso_to_naive(body.ends_at)

    session = models.StudySession(
        creator_email=normalized_creator_email,
        course_id=body.course_id,
        session_type=body.session_type,
        title=body.title,
        starts_at=session_start,
        ends_at=session_end,
        group_id=body.group_id
    )
    db.add(session)
    db.flush()

    session_participants = {normalized_creator_email}
    for email in normalized_invitees:
        if email != normalized_creator_email:
            db.add(models.StudySessionInvitee(
                study_session_id=session.id,
                user_email=email
            ))
            session_participants.add(email)

    apply_study_session_availability(
        db=db,
        session_id=session.id,
        session_start=session_start,
        session_end=session_end,
        participants=session_participants,
    )

    db.commit()
    db.refresh(session)
    return {
        "id": session.id,
        "title": session.title,
        "session_type": session.session_type,
        "starts_at": session.starts_at.isoformat(),
        "ends_at": session.ends_at.isoformat(),
        "group_id": session.group_id,
        "course_id": session.course_id,
        "invitees": [invitee.user_email for invitee in session.invitees]
    }


@app.put("/study-sessions/{session_id}")
def update_study_session(
    session_id: int,
    body: StudySessionCreate,
    db: Session = Depends(get_db)
):
    """Updates an existing study session and refreshes invitees/busy blocks."""
    normalized_creator_email = normalize_email(body.creator_email)
    normalized_invitees = sorted({
        normalize_email(email)
        for email in body.invitees
        if email and normalize_email(email) != normalized_creator_email
    })

    session = db.query(models.StudySession).filter(models.StudySession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Study session not found.")

    if session.creator_email != normalized_creator_email:
        raise HTTPException(status_code=403, detail="Only the meeting creator can edit this session.")

    session_start = parse_iso_to_naive(body.starts_at)
    session_end = parse_iso_to_naive(body.ends_at)

    session.title = body.title.strip()
    session.course_id = body.course_id
    session.session_type = body.session_type
    session.starts_at = session_start
    session.ends_at = session_end
    session.group_id = body.group_id

    db.query(models.StudySessionInvitee).filter(
        models.StudySessionInvitee.study_session_id == session_id
    ).delete(synchronize_session=False)

    session_participants = {normalized_creator_email}
    for email in normalized_invitees:
        db.add(models.StudySessionInvitee(
            study_session_id=session_id,
            user_email=email
        ))
        session_participants.add(email)

    apply_study_session_availability(
        db=db,
        session_id=session_id,
        session_start=session_start,
        session_end=session_end,
        participants=session_participants,
    )

    db.commit()
    db.refresh(session)
    return {
        "id": session.id,
        "title": session.title,
        "session_type": session.session_type,
        "starts_at": session.starts_at.isoformat(),
        "ends_at": session.ends_at.isoformat(),
        "group_id": session.group_id,
        "course_id": session.course_id,
        "creator_email": session.creator_email,
        "invitees": [invitee.user_email for invitee in session.invitees],
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


def parse_iso_to_naive(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
    return parsed


def normalize_email(value: str) -> str:
    return value.strip().lower()


def apply_study_session_availability(
    db: Session,
    session_id: int,
    session_start: datetime,
    session_end: datetime,
    participants: set[str],
):
    db.query(models.UserAvailability).filter(
        models.UserAvailability.study_session_id == session_id
    ).delete(synchronize_session=False)

    for email in participants:
        db.add(models.UserAvailability(
            user_email=email,
            starts_at=session_start,
            ends_at=session_end,
            source="study_session",
            study_session_id=session_id,
        ))


@app.post("/availability/sync")
def sync_availability(body: AvailabilitySync, db: Session = Depends(get_db)):
    """Syncs busy blocks from Google Calendar."""
    normalized_user_email = normalize_email(body.user_email)
    range_start = parse_iso_to_naive(body.starts_at)
    range_end = parse_iso_to_naive(body.ends_at)
    
    # Delete old blocks in range to avoid duplicates
    db.query(models.UserAvailability).filter(
        models.UserAvailability.user_email == normalized_user_email,
        models.UserAvailability.starts_at >= range_start,
        models.UserAvailability.ends_at <= range_end
    ).delete(synchronize_session=False)
    
    count = 0
    for slot in body.busy_slots:
        db.add(models.UserAvailability(
            user_email=normalized_user_email,
            starts_at=parse_iso_to_naive(slot.starts_at),
            ends_at=parse_iso_to_naive(slot.ends_at),
            source=body.source
        ))
        count += 1
    db.commit()
    return {"inserted_busy_blocks": count}


@app.get("/availability/connected")
def check_availability_connected(user_email: str = Query(...), db: Session = Depends(get_db)):
    """Returns whether a user has synced Google Calendar availability."""
    normalized_user_email = normalize_email(user_email)
    has_synced_availability = db.query(models.UserAvailability.id).filter(
        models.UserAvailability.user_email == normalized_user_email,
        models.UserAvailability.source == "google_calendar"
    ).first() is not None
    return {"connected": has_synced_availability, "email": normalized_user_email}


@app.get("/availability")
def get_availability(
    user_emails: List[str] = Query(...),
    time_min: str = Query(...),
    time_max: str = Query(...),
    db: Session = Depends(get_db)
):
    """Fetch busy blocks for one or more users in a time range."""
    normalized_user_emails = [normalize_email(email) for email in user_emails]
    range_start = parse_iso_to_naive(time_min)
    range_end = parse_iso_to_naive(time_max)

    busy_blocks = db.query(models.UserAvailability).filter(
        models.UserAvailability.user_email.in_(normalized_user_emails),
        models.UserAvailability.starts_at < range_end,
        models.UserAvailability.ends_at > range_start
    ).order_by(
        models.UserAvailability.user_email.asc(),
        models.UserAvailability.starts_at.asc()
    ).all()

    grouped = {email: [] for email in normalized_user_emails}
    for block in busy_blocks:
        grouped.setdefault(block.user_email, []).append({
            "starts_at": block.starts_at.replace(tzinfo=timezone.utc).isoformat(),
            "ends_at": block.ends_at.replace(tzinfo=timezone.utc).isoformat(),
            "source": block.source,
        })

    return {"availability": grouped}
