from database import Base
from sqlalchemy import Column, Integer, String, DateTime, Enum
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
    role = Column(String, default="Student") # Or use Enum(UserRole)
    google_calendar_token = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)