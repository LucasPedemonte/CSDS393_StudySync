from database import Base
from sqlalchemy import Column, Integer, String, DateTime, Enum, ForeignKey
import datetime
import enum


class UserRole(str, enum.Enum):
    STUDENT = "Student"
    TA = "TA"
    ADMIN = "Admin"


class User(Base):
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True, index=True)
    firebase_uid = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String)
    role = Column(String, default="Student")  # Or use Enum(UserRole)
    google_calendar_token = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class Message(Base):
    """
    Stores direct messages between two users, identified by their Firebase UIDs.
    """

    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    sender_uid = Column(String, ForeignKey("users.firebase_uid"), nullable=False, index=True)
    receiver_uid = Column(String, ForeignKey("users.firebase_uid"), nullable=False, index=True)
    content = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, index=True)


class Post(Base):
    """
    Stores resource posts shared by users in the resources library.
    """

    __tablename__ = "posts"

    id = Column(Integer, primary_key=True, index=True)
    author_uid = Column(String, ForeignKey("users.firebase_uid"), nullable=False, index=True)
    title = Column(String, nullable=False)
    description = Column(String, nullable=True)
    resource_link = Column(String, nullable=True)
    score = Column(Integer, default=0)  # can be negative
    created_at = Column(DateTime, default=datetime.datetime.utcnow, index=True)


class PostVote(Base):
    """
    Tracks upvotes and downvotes per user per post. vote: +1 (upvote), -1 (downvote), 0 (neutral)
    """

    __tablename__ = "post_votes"

    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(Integer, ForeignKey("posts.id"), nullable=False, index=True)
    user_uid = Column(String, ForeignKey("users.firebase_uid"), nullable=False, index=True)
    vote = Column(Integer, nullable=False)  # +1, -1, or 0
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
