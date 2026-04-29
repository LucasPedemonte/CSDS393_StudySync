#!/usr/bin/env python3
"""Create a test course for CSDS393"""

from database import get_db
from models import Course, User
from datetime import datetime

db = next(get_db())

# Get the first user to be the course owner
user = db.query(User).first()
if not user:
    print("ERROR: No users found. Run create_fake_users.py first.")
    exit(1)

# Check if course already exists
existing = db.query(Course).filter(Course.course_code == "CSDS393").first()
if existing:
    print(f"✓ Course CSDS393 already exists (ID: {existing.id})")
else:
    # Create the course
    course = Course(
        name="Software Engineering",
        course_code="CSDS393",
        description="Software engineering project course",
        owner_id=user.firebase_uid,
        created_at=datetime.utcnow()
    )
    db.add(course)
    db.commit()
    db.refresh(course)
    print(f"✓ Created course: {course.name} ({course.course_code}) - ID: {course.id}")

# Show all courses
print("\nAll courses:")
courses = db.query(Course).all()
for c in courses:
    print(f"  - {c.course_code}: {c.name}")
