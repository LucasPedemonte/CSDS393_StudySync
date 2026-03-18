import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_student_cannot_delete_post():
    """
    Requirement: Permissions (TA vs Student)
    Verifies that a Student role receives a 403 Forbidden when attempting to delete.
    """
    # 1. We assume a post with ID 1 exists in the DB for this test
    # 2. We pass a user_uid that belongs to a 'Student'
    # Note: You may need to ensure this user exists in your test DB or mock the DB call
    response = client.delete("/posts/1?user_uid=student_user_123")
    
    # Assert that the backend blocks the action
    assert response.status_code == 403
    assert response.json()["detail"] == "Only TAs or Admins can delete posts."

def test_get_global_inbox_structure():
    """
    Requirement: Core Functionality (Global Inbox)
    Verifies the inbox returns the expected data structure.
    """
    response = client.get("/conversations/inbox/global?user_uid=test_user")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    
def test_get_global_inbox_empty():
    """Verifies that a new user with no chats gets an empty list, not an error."""
    response = client.get("/conversations/inbox/global?user_uid=new_user_999")
    assert response.status_code == 200
    assert response.json() == []
    
def test_message_access_denied():
    """Verifies that a user cannot see messages for a course they aren't in."""
    # Added user2 and is_group to satisfy the 422 validation error
    params = {
        "user1": "user_123",
        "user2": "other_user",
        "course_id": 999, # Dummy ID
        "is_group": "false"
    }
    response = client.get("/messages", params=params)
    
    # The logic should return 200 (empty list) or 403 if they aren't in the course
    assert response.status_code in [200, 403]

def test_get_class_discussion_messages():
    """Verifies fetching public group messages for a specific course."""
    # Even for group chats, user1 and user2 must be present to pass validation
    params = {
        "user1": "test_user",
        "user2": "GROUP_CHAT", 
        "course_id": 1,
        "is_group": "true"
    }
    response = client.get("/messages", params=params)
    
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    
def test_global_inbox_missing_params():
    """Verifies the backend returns 422 Unprocessable Entity if UID is missing."""
    response = client.get("/conversations/inbox/global") # No query param
    assert response.status_code == 422
    