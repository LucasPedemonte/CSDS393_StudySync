#!/usr/bin/env python3
"""Create a sample course record for local backend validation."""

from datetime import datetime

from database import get_db
from models import Course, User

def main():
    """Create the sample course if it does not already exist."""
    db = next(get_db())

    user = db.query(User).first()
    if not user:
        print("ERROR: No users found. Run create_fake_users.py first.")
        raise SystemExit(1)

    existing = db.query(Course).filter(Course.course_code == "CSDS393").first()
    if existing:
        print(f"Course CSDS393 already exists (ID: {existing.id})")
    else:
        course = Course(
            name="Software Engineering",
            course_code="CSDS393",
            description="Software engineering project course",
            owner_id=user.firebase_uid,
            created_at=datetime.utcnow(),
        )
        db.add(course)
        db.commit()
        db.refresh(course)
        print(f"Created course: {course.name} ({course.course_code}) - ID: {course.id}")

    print("\nAll courses:")
    courses = db.query(Course).all()
    for course in courses:
        print(f"  - {course.course_code}: {course.name}")


if __name__ == "__main__":
    main()
