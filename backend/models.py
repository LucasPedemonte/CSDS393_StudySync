"""
High-level entity map:

- ``User`` — a person (student, TA, or admin).
- ``Course`` + ``Enrollment`` — a class and its roster.
- ``Post`` + ``PostVote`` — discussion/resource posts and their votes.
- ``StudyGroup`` + ``StudyGroupMember`` — long-lived groups inside a course.
- ``StudySession`` + ``StudySessionInvitee`` — scheduled meetings (solo or group).
- ``UserAvailability`` — busy/free blocks, typically synced from Google Calendar.
- ``Conversation`` + ``ConversationParticipant`` + ``Message`` — chat.
"""
from database import Base
from sqlalchemy import Column, Integer, String, DateTime, Enum, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
import datetime
import enum


class UserRole(str, enum.Enum):
    """Allowed values for ``User.role``. Stored as a plain string column."""
    STUDENT = "Student"
    TA = "TA"
    ADMIN = "Admin"


class User(Base):
    """A StudySync user, keyed by their Firebase Auth UID.

    Holds profile basics plus an optional Google Calendar token used by
    the calendar-sync feature. All ownership/authorship foreign keys in
    other tables point at ``firebase_uid``.
    """
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
    """A class/course that students can enroll in and post to."""
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
    """Join table linking a ``User`` to a ``Course`` they are enrolled in."""
    __tablename__ = "enrollments"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.firebase_uid"), nullable=False)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    enrolled_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.UTC))

    user = relationship("User", back_populates="enrollments")
    course = relationship("Course", back_populates="members")


class Conversation(Base):
    """A chat thread, either 1:1 (``is_group`` False) or a named group chat.

    Optionally scoped to a course via ``course_id`` so course-specific
    chats can be filtered out of personal DMs.
    """
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
    """Membership of a user in a conversation; controls who can read/send."""
    __tablename__ = "conversation_participants"
    
    participant_id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.conversation_id"), nullable=False)
    user_id = Column("user_uid", String, ForeignKey("users.firebase_uid"), nullable=False)
    joined_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.UTC))
    
    # Relationships
    conversation = relationship("Conversation", back_populates="participants")
    user = relationship("User", back_populates="conversation_participants")


class Message(Base):
    """A single chat message inside a ``Conversation``."""
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
    """A discussion or resource post within a course.

    ``score`` is a denormalized vote tally maintained alongside
    ``PostVote`` rows. ``is_flagged`` lets moderators hide a post
    without deleting it.
    """
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
    """One user's upvote (+1) or downvote (-1) on a ``Post``."""
    __tablename__ = "post_votes"

    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(Integer, ForeignKey("posts.id"), nullable=False)
    user_uid = Column(String, nullable=False)
    vote = Column(Integer, nullable=False)

    post = relationship("Post", back_populates="votes")


class StudyGroup(Base):
    """A persistent study group inside a course.

    Holds the long-lived membership (``StudyGroupMember``) and any
    scheduled meetings (``StudySession``).
    """
    __tablename__ = "study_groups"

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    name = Column(String, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.UTC))

    course = relationship("Course", back_populates="study_groups")
    members = relationship("StudyGroupMember", back_populates="group", cascade="all, delete-orphan")
    sessions = relationship("StudySession", back_populates="group", cascade="all, delete-orphan")


class StudySession(Base):
    """A scheduled study meeting.

    ``session_type`` is ``"solo"`` for personal study blocks or
    ``"group"`` when tied to a ``StudyGroup`` via ``group_id``.
    Invitees (for group sessions) live in ``StudySessionInvitee``.
    """
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
    """A user's membership in a ``StudyGroup``, keyed by email."""
    __tablename__ = "study_group_members"

    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(Integer, ForeignKey("study_groups.id"), nullable=False)
    user_email = Column(String, nullable=False)
    joined_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.UTC))

    group = relationship("StudyGroup", back_populates="members")


class UserAvailability(Base):
    """A busy/free time block for a user.

    Most rows are imported from Google Calendar (``source =
    "google_calendar"``); rows tied to a StudySession reflect blocks
    StudySync itself created. Used by the scheduler to find overlap
    when proposing meeting times.
    """
    __tablename__ = "user_availability"

    id = Column(Integer, primary_key=True, index=True)
    user_email = Column(String, nullable=False)
    starts_at = Column(DateTime, nullable=False)
    ends_at = Column(DateTime, nullable=False)
    source = Column(String, default="google_calendar")
    study_session_id = Column(Integer, ForeignKey("study_sessions.id"), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.UTC))


class StudySessionInvitee(Base):
    """An email invited to a ``StudySession``; the invitee may not yet be a registered user."""
    __tablename__ = "study_session_invitees"

    id = Column(Integer, primary_key=True, index=True)
    study_session_id = Column(Integer, ForeignKey("study_sessions.id"), nullable=False)
    user_email = Column(String, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.UTC))

    session = relationship("StudySession", back_populates="invitees")
