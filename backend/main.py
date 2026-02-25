from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from database import engine, Base, get_db
import models
from typing import List

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


class UserSimple(BaseModel):
    firebase_uid: str
    full_name: str
    role: str


class MessageCreate(BaseModel):
    sender_uid: str
    receiver_uid: str
    content: str


class MessageOut(BaseModel):
    id: int
    sender_uid: str
    receiver_uid: str
    content: str
    created_at: str


class PostCreate(BaseModel):
    title: str
    description: str = None
    resource_link: str = None


class PostOut(BaseModel):
    id: int
    author_uid: str
    author_name: str
    author_role: str
    title: str
    description: str = None
    resource_link: str = None
    score: int
    user_vote: int  # +1, -1, or 0
    created_at: str


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
    return {"status": "success", "score": post.score, "user_vote": vote}
