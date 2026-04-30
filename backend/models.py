"""SQLAlchemy ORM models that define the StudySync data schema."""

from database import Base
from sqlalchemy import Column, Integer, String, DateTime, Enum, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
import datetime
import enum


class UserRole(str, enum.Enum):
    """Supported application roles used for authorization decisions."""

    STUDENT = "Student"
    TA = "TA"
    ADMIN = "Admin"


class User(Base):
    """Application user synchronized from Firebase authentication."""

    __tablename__ = "users"

    # Firebase UID is now the primary key (string)
    firebase_uid = Column(String, primary_key=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String)
    role = Column(String, default="Student")
    google_calendar_token = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.UTC))
    
    # Relationships
    messages = relationship("Message", back_populates="sender")
    conversation_participants = relationship("ConversationParticipant", back_populates="user")
    courses_created = relationship("Course", back_populates="owner")
    posts = relationship("Post", back_populates="author")
    enrollments = relationship("Enrollment", back_populates="user")


class Course(Base):
    """Course workspace that groups users, posts, chat, and scheduling."""

    __tablename__ = "courses"

    id = Column(Integer, primary_key=True, index=True)
    course_code = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    owner_id = Column(String, ForeignKey("users.firebase_uid"), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.UTC))

    # Relationships
    owner = relationship("User", back_populates="courses_created")
    members = relationship("Enrollment", back_populates="course", cascade="all, delete-orphan")
    posts = relationship("Post", back_populates="course")
    study_groups = relationship("StudyGroup", back_populates="course")
    conversations = relationship("Conversation", back_populates="course")


class Enrollment(Base):
    """Membership record connecting one user to one course."""

    __tablename__ = "enrollments"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.firebase_uid"), nullable=False)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    enrolled_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.UTC))

    user = relationship("User", back_populates="enrollments")
    course = relationship("Course", back_populates="members")


class Conversation(Base):
    """Direct-message or course-wide chat thread."""

    __tablename__ = "conversations"
    
    conversation_id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=True)
    is_group = Column(Boolean, default=False)
    group_name = Column(String, nullable=True) 
    created_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.UTC))
    
    course = relationship("Course", back_populates="conversations")
    participants = relationship("ConversationParticipant", back_populates="conversation", cascade="all, delete-orphan")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")


class ConversationParticipant(Base):
    """Participant mapping for a conversation."""

    __tablename__ = "conversation_participants"
    
    participant_id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.conversation_id"), nullable=False)
    user_id = Column("user_uid", String, ForeignKey("users.firebase_uid"), nullable=False)
    joined_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.UTC))
    
    # Relationships
    conversation = relationship("Conversation", back_populates="participants")
    user = relationship("User", back_populates="conversation_participants")


class Message(Base):
    """Single chat message stored within a conversation."""

    __tablename__ = "messages"
    
    message_id = Column("id", Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.conversation_id"), nullable=False)
    sender_id = Column("sender_uid", String, ForeignKey("users.firebase_uid"), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.UTC))
    
    # Relationships
    conversation = relationship("Conversation", back_populates="messages")
    sender = relationship("User", back_populates="messages")


class Post(Base):
    """Shared course resource post with optional moderation state."""

    __tablename__ = "posts"

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    author_uid = Column(String, ForeignKey("users.firebase_uid"), nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    resource_link = Column(String, nullable=True)
    score = Column(Integer, default=0)
    is_flagged = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.UTC))

    author = relationship("User", back_populates="posts")
    course = relationship("Course", back_populates="posts")
    votes = relationship("PostVote", back_populates="post", cascade="all, delete-orphan")


class PostVote(Base):
    """Per-user vote attached to a resource post."""

    __tablename__ = "post_votes"

    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(Integer, ForeignKey("posts.id"), nullable=False)
    user_uid = Column(String, nullable=False)
    vote = Column(Integer, nullable=False)

    post = relationship("Post", back_populates="votes")


class StudyGroup(Base):
    """Small study team created inside a course."""

    __tablename__ = "study_groups"

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    name = Column(String, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.UTC))

    course = relationship("Course", back_populates="study_groups")
    members = relationship("StudyGroupMember", back_populates="group", cascade="all, delete-orphan")
    sessions = relationship("StudySession", back_populates="group", cascade="all, delete-orphan")


class StudySession(Base):
    """Scheduled study meeting for an individual or a group."""

    __tablename__ = "study_sessions"

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    creator_email = Column(String, nullable=False)
    session_type = Column(String, default="solo")
    title = Column(String, nullable=False)
    starts_at = Column(DateTime, nullable=False)
    ends_at = Column(DateTime, nullable=False)
    group_id = Column(Integer, ForeignKey("study_groups.id"), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.UTC))

    group = relationship("StudyGroup", back_populates="sessions")
    invitees = relationship("StudySessionInvitee", back_populates="session", cascade="all, delete-orphan")


class StudyGroupMember(Base):
    """Membership record connecting a user email to a study group."""

    __tablename__ = "study_group_members"

    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(Integer, ForeignKey("study_groups.id"), nullable=False)
    user_email = Column(String, nullable=False)
    joined_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.UTC))

    group = relationship("StudyGroup", back_populates="members")


class UserAvailability(Base):
    """Busy-time block imported from Google Calendar or local scheduling data."""

    __tablename__ = "user_availability"

    id = Column(Integer, primary_key=True, index=True)
    user_email = Column(String, nullable=False)
    starts_at = Column(DateTime, nullable=False)
    ends_at = Column(DateTime, nullable=False)
    source = Column(String, default="google_calendar")
    study_session_id = Column(Integer, ForeignKey("study_sessions.id"), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.UTC))


class StudySessionInvitee(Base):
    """Email invitee attached to a scheduled study session."""

    __tablename__ = "study_session_invitees"

    id = Column(Integer, primary_key=True, index=True)
    study_session_id = Column(Integer, ForeignKey("study_sessions.id"), nullable=False)
    user_email = Column(String, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.UTC))

    session = relationship("StudySession", back_populates="invitees")
