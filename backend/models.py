from database import Base
from sqlalchemy import Column, Integer, String, DateTime, Enum, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
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
    
    # Relationships
    messages = relationship("Message", back_populates="sender")
    conversation_participants = relationship("ConversationParticipant", back_populates="user")


class Conversation(Base):
    __tablename__ = "conversations"
    
    conversation_id = Column(Integer, primary_key=True, index=True)
    is_group = Column(Boolean, default=False)
    group_name = Column(String, nullable=True)  # Only for group conversations
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    # Relationships
    participants = relationship("ConversationParticipant", back_populates="conversation", cascade="all, delete-orphan")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")


class ConversationParticipant(Base):
    __tablename__ = "conversation_participants"
    
    participant_id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.conversation_id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    joined_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    # Relationships
    conversation = relationship("Conversation", back_populates="participants")
    user = relationship("User", back_populates="conversation_participants")


class Message(Base):
    __tablename__ = "messages"
    
    message_id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.conversation_id"), nullable=False)
    sender_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    # Relationships
    conversation = relationship("Conversation", back_populates="messages")
    sender = relationship("User", back_populates="messages")


class Post(Base):
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True, index=True)
    author_uid = Column(String, ForeignKey("users.firebase_uid"), nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    resource_link = Column(String, nullable=True)
    score = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    votes = relationship("PostVote", back_populates="post", cascade="all, delete-orphan")


class PostVote(Base):
    __tablename__ = "post_votes"

    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(Integer, ForeignKey("posts.id"), nullable=False)
    user_uid = Column(String, nullable=False)
    vote = Column(Integer, nullable=False)  # 1 or -1

    post = relationship("Post", back_populates="votes")


class StudyGroup(Base):
    __tablename__ = "study_groups"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    members = relationship("StudyGroupMember", back_populates="group", cascade="all, delete-orphan")
    sessions = relationship("StudySession", back_populates="group", cascade="all, delete-orphan")


class StudyGroupMember(Base):
    __tablename__ = "study_group_members"

    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(Integer, ForeignKey("study_groups.id"), nullable=False)
    user_email = Column(String, nullable=False)
    joined_at = Column(DateTime, default=datetime.datetime.utcnow)

    group = relationship("StudyGroup", back_populates="members")


class StudySession(Base):
    __tablename__ = "study_sessions"

    id = Column(Integer, primary_key=True, index=True)
    creator_email = Column(String, nullable=False)
    session_type = Column(String, default="solo")  # 'solo' or 'group'
    title = Column(String, nullable=False)
    starts_at = Column(DateTime, nullable=False)
    ends_at = Column(DateTime, nullable=False)
    group_id = Column(Integer, ForeignKey("study_groups.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    group = relationship("StudyGroup", back_populates="sessions")


class UserAvailability(Base):
    __tablename__ = "user_availability"

    id = Column(Integer, primary_key=True, index=True)
    user_email = Column(String, nullable=False)
    starts_at = Column(DateTime, nullable=False)
    ends_at = Column(DateTime, nullable=False)
    source = Column(String, default="google_calendar")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
