from database import Base
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.sql import func

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String)
    email = Column(String, unique=True, index=True)
    password_hash = Column(String)
    role = Column(String, default="student")

class Resource(Base):
    __tablename__ = "resources"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    url = Column(Text, nullable=False)
    description = Column(Text)
    submitted_by = Column(Integer, ForeignKey("users.id"))
    vote_score = Column(Integer, default=0)
    is_verified = Column(Boolean, default=False)
    is_flagged = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())

class ResourceVote(Base):
    __tablename__ = "resource_votes"

    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    resource_id = Column(Integer, ForeignKey("resources.id"), primary_key=True)
    vote = Column(Integer, nullable=False)
