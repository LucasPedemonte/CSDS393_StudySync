"""Tests for the User Authentication & Profile Management requirement.

Covers the Firebase-sync upsert path (``POST /sync-user``), profile
fetch and update endpoints, and a Hypothesis property-based pass over
``/sync-user`` to fuzz unusual but valid inputs.
"""
import pytest
import models
from fastapi.testclient import TestClient
from main import app, ensure_schema_updates
from database import Base, engine
from hypothesis import given, strategies as st, settings


def _seed_test_users(db):
    """Insert one Student, one TA, and one Admin so role-gated paths can be exercised."""
    import models

    student = models.User(
        firebase_uid="student_123",
        email="student@example.com",
        full_name="Test Student",
        role="Student",
    )
    ta = models.User(
        firebase_uid="ta_123",
        email="ta@example.com",
        full_name="Test TA",
        role="TA",
    )
    admin = models.User(
        firebase_uid="admin_123",
        email="admin@example.com",
        full_name="Test Admin",
        role="Admin",
    )
    db.add_all([student, ta, admin])
    db.commit()
    return {"student": student, "ta": ta, "admin": admin}


def test_user_sync_creates_new_user(client, db):
    """
    Requirement: User Authentication & Profile Management
    Verifies that new users are created via Firebase sync.
    """
    user_data = {
        "firebase_uid": "new_user_123",
        "email": "new@example.com",
        "full_name": "New User",
        "role": "Student"
    }

    response = client.post("/sync-user", json=user_data)
    assert response.status_code == 200
    assert response.json()["status"] == "success"


def test_user_sync_returns_existing_user(client, db):
    """
    Requirement: User Authentication & Profile Management
    Verifies that existing users return 'exists' status on sync.
    """
    seeded = _seed_test_users(db)
    user_data = {
        "firebase_uid": seeded["student"].firebase_uid,
        "email": seeded["student"].email,
        "full_name": seeded["student"].full_name,
        "role": seeded["student"].role
    }

    # Sync existing user
    response = client.post("/sync-user", json=user_data)
    assert response.status_code == 200
    assert response.json()["status"] == "exists"


def test_get_user_profile_returns_correct_data(client, db):
    """
    Requirement: User Authentication & Profile Management
    Verifies that user profiles are retrieved with all required fields.
    """
    seeded = _seed_test_users(db)

    response = client.get(f"/user/{seeded['student'].firebase_uid}")
    assert response.status_code == 200

    data = response.json()
    assert data["firebase_uid"] == seeded["student"].firebase_uid
    assert data["email"] == seeded["student"].email
    assert data["full_name"] == seeded["student"].full_name
    assert data["role"] == seeded["student"].role
    assert "gcal_connected" in data


def test_get_user_profile_not_found(client, db):
    """
    Requirement: User Authentication & Profile Management
    Verifies that non-existent users return 404.
    """
    response = client.get("/user/nonexistent_user_999")
    assert response.status_code == 404
    assert response.json()["detail"] == "User not found"


def test_update_user_profile_changes_data(client, db):
    """
    Requirement: User Authentication & Profile Management
    Verifies that user profiles can be updated successfully.
    """
    seeded = _seed_test_users(db)

    update_data = {
        "firebase_uid": seeded["student"].firebase_uid,
        "email": "updated@example.com",
        "full_name": "Updated Name",
        "role": "TA"
    }
    response = client.put(f"/user/{seeded['student'].firebase_uid}/update", json=update_data)
    assert response.status_code == 200
    assert response.json()["status"] == "success"

    # Verify update
    response2 = client.get(f"/user/{seeded['student'].firebase_uid}")
    data = response2.json()
    assert data["full_name"] == "Updated Name"
    assert data["email"] == "updated@example.com"
    assert data["role"] == "TA"


def test_update_user_profile_not_found(client, db):
    """
    Requirement: User Authentication & Profile Management
    Verifies that updating non-existent users returns 404.
    """
    update_data = {
        "firebase_uid": "nonexistent_user",
        "email": "test@example.com",
        "full_name": "Test User",
        "role": "Student"
    }
    response = client.put("/user/nonexistent_user/update", json=update_data)
    assert response.status_code == 404
    assert response.json()["detail"] == "User not found"


def test_list_users_returns_all_users(client, db):
    """
    Requirement: User Authentication & Profile Management
    Verifies that all users can be listed with correct structure.
    """
    seeded = _seed_test_users(db)

    response = client.get("/users")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 3

    # Check structure
    user = data[0]
    assert "firebase_uid" in user
    assert "email" in user
    assert "full_name" in user
    assert "role" in user


def test_user_sync_with_different_roles(client, db):
    """
    Requirement: User Authentication & Profile Management
    Verifies that users can be created with different roles (Student, TA, Admin).
    """
    roles = ["Student", "TA", "Admin"]

    for role in roles:
        user_data = {
            "firebase_uid": f"{role.lower()}_user_123",
            "email": f"{role.lower()}@example.com",
            "full_name": f"{role} User",
            "role": role
        }

        response = client.post("/sync-user", json=user_data)
        assert response.status_code == 200
        assert response.json()["role"] == role


def test_user_sync_email_update(client, db):
    """
    Requirement: User Authentication & Profile Management
    Verifies that user email is updated when Firebase email differs.
    """
    seeded = _seed_test_users(db)

    # Sync with different email
    updated_data = {
        "firebase_uid": seeded["student"].firebase_uid,
        "email": "new_email@example.com",
        "full_name": seeded["student"].full_name,
        "role": seeded["student"].role
    }
    client.post("/sync-user", json=updated_data)

    # Verify email was updated
    response = client.get(f"/user/{seeded['student'].firebase_uid}")
    assert response.json()["email"] == "new_email@example.com"


def test_get_user_courses_returns_enrolled_courses(client, db):
    """
    Requirement: User Authentication & Profile Management
    Verifies that users can retrieve their enrolled courses.
    """
    seeded = _seed_test_users(db)
    
    # Create a course and enroll the student
    course = models.Course(
        course_code="TEST101",
        name="Test Course",
        description="A test course",
        owner_id=seeded["ta"].firebase_uid,
    )
    db.add(course)
    db.flush()
    
    enrollment = models.Enrollment(
        user_id=seeded["student"].firebase_uid,
        course_id=course.id,
    )
    db.add(enrollment)
    db.commit()
    
    # Get user's courses
    response = client.get(f"/users/{seeded['student'].firebase_uid}/courses")
    assert response.status_code == 200
    courses = response.json()
    assert len(courses) >= 1
    assert courses[0]["course_code"] == "TEST101"


def test_get_user_courses_empty_for_new_user(client, db):
    """
    Requirement: User Authentication & Profile Management
    Verifies that new users with no course enrollments get empty list.
    """
    seeded = _seed_test_users(db)
    
    response = client.get(f"/users/{seeded['student'].firebase_uid}/courses")
    assert response.status_code == 200
    assert response.json() == []


def test_user_sync_validates_required_fields(client, db):
    """
    Requirement: User Authentication & Profile Management
    Verifies that user sync validates required fields.
    """
    # Test missing firebase_uid
    invalid_data = {
        "email": "test@example.com",
        "full_name": "Test User",
        "role": "Student"
    }
    response = client.post("/sync-user", json=invalid_data)
    assert response.status_code == 422  # Validation error


def test_user_sync_handles_duplicate_emails(client, db):
    """
    Requirement: User Authentication & Profile Management
    Verifies that duplicate emails are NOT allowed (database constraint).
    """
    # Create first user
    user1_data = {
        "firebase_uid": "user1_123",
        "email": "same@example.com",
        "full_name": "User One",
        "role": "Student"
    }
    response1 = client.post("/sync-user", json=user1_data)
    assert response1.status_code == 200

    # Try to create second user with same email (should fail due to unique constraint)
    user2_data = {
        "firebase_uid": "user2_123",
        "email": "same@example.com",  # Same email
        "full_name": "User Two",
        "role": "Student"
    }
    response2 = client.post("/sync-user", json=user2_data)
    # Should fail due to database unique constraint
    assert response2.status_code == 500  # Internal server error due to constraint violation
    """
    Requirement: User Authentication & Profile Management
    Verifies that Firebase UID cannot be changed during profile updates.
    """
    seeded = _seed_test_users(db)
    
    # Try to update with different firebase_uid in payload
    update_data = {
        "firebase_uid": "different_uid_123",  # Different from URL
        "email": "updated@example.com",
        "full_name": "Updated Name",
        "role": "TA"
    }
    response = client.put(f"/user/{seeded['student'].firebase_uid}/update", json=update_data)
    assert response.status_code == 200
    
    # Verify firebase_uid wasn't changed
    response2 = client.get(f"/user/{seeded['student'].firebase_uid}")
    data = response2.json()
    assert data["firebase_uid"] == seeded["student"].firebase_uid  # Original UID preserved


def test_user_sync_with_special_characters(client, db):
    """
    Requirement: User Authentication & Profile Management
    Verifies that special characters in names and emails are handled correctly.
    """
    user_data = {
        "firebase_uid": "special_user_123",
        "email": "user+tag@example.co.uk",
        "full_name": "José María García",
        "role": "Student"
    }
    
    response = client.post("/sync-user", json=user_data)
    assert response.status_code == 200
    
    # Verify data was stored correctly
    response2 = client.get("/user/special_user_123")
    data = response2.json()
    assert data["full_name"] == "José María García"
    assert data["email"] == "user+tag@example.co.uk"


def test_user_profile_update_with_minimal_changes(client, db):
    """
    Requirement: User Authentication & Profile Management
    Verifies that profile updates work with minimal field changes.
    """
    seeded = _seed_test_users(db)
    
    # Update only the name
    update_data = {
        "firebase_uid": seeded["student"].firebase_uid,
        "email": seeded["student"].email,  # Same email
        "full_name": "Updated Name Only",
        "role": seeded["student"].role  # Same role
    }
    response = client.put(f"/user/{seeded['student'].firebase_uid}/update", json=update_data)
    assert response.status_code == 200
    
    # Verify only name changed
    response2 = client.get(f"/user/{seeded['student'].firebase_uid}")
    data = response2.json()
    assert data["full_name"] == "Updated Name Only"
    assert data["email"] == seeded["student"].email
    assert data["role"] == seeded["student"].role


def test_list_users_includes_all_created_users(client, db):
    """
    Requirement: User Authentication & Profile Management
    Verifies that user listing includes all users created through sync.
    """
    # Create additional users via sync
    for i in range(3):
        user_data = {
            "firebase_uid": f"sync_user_{i}",
            "email": f"sync{i}@example.com",
            "full_name": f"Sync User {i}",
            "role": "Student"
        }
        client.post("/sync-user", json=user_data)

    response = client.get("/users")
    assert response.status_code == 200
    users = response.json()

    # Should have exactly the 3 newly created users
    assert len(users) == 3
    
    # Verify all expected users are present
    firebase_uids = [user["firebase_uid"] for user in users]
    assert "sync_user_0" in firebase_uids
    assert "sync_user_1" in firebase_uids
    assert "sync_user_2" in firebase_uids


@given(email=st.emails(), name=st.text(min_size=1, max_size=100, alphabet=st.characters(blacklist_categories=('Cc', 'Cs'))))
@settings(max_examples=20, deadline=None)
def test_user_sync_property_based_valid_inputs(email, name):
    """
    Property-based testing for user sync with various valid emails and names.
    Verifies that the system handles diverse input data correctly.
    """
    import uuid

    # Reset schema between Hypothesis examples for strong isolation.
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    ensure_schema_updates()

    client = TestClient(app)
    firebase_uid = str(uuid.uuid4())  # Generate unique UID for each test case
    unique_email = f"{uuid.uuid4().hex}_{email}"

    user_data = {
        "firebase_uid": firebase_uid,
        "email": unique_email,
        "full_name": name,
        "role": "Student"
    }

    response = client.post("/sync-user", json=user_data)
    assert response.status_code == 200
    assert response.json()["status"] == "success"
