import pytest
from fastapi.testclient import TestClient
from main import app
from hypothesis import given, strategies as st

client = TestClient(app)

# test to make sure that a student can not delete a post
def test_student_cannot_delete_post():
    response = client.delete("/posts/1?user_uid=student_user_123")
    
    # Assert that the backend blocks the action
    assert response.status_code == 403
    assert response.json()["detail"] == "Only TAs or Admins can delete posts."

# Verifies the inbox returns the expected data structure.
def test_get_global_inbox_structure():
    response = client.get("/conversations/inbox/global?user_uid=test_user")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    
# Verifies that a new user with no chats gets an empty list, not an error.
def test_get_global_inbox_empty():
    response = client.get("/conversations/inbox/global?user_uid=new_user_999")
    assert response.status_code == 200
    assert response.json() == []

# Verifies fetching public group messages for a specific course.
def test_get_class_discussion_messages():
    params = {
        "user1": "test_user",
        "user2": "GROUP_CHAT", 
        "course_id": 1,
        "is_group": "true"
    }
    response = client.get("/messages", params=params)
    
    assert response.status_code == 200
    assert isinstance(response.json(), list)

#    """Verifies the backend returns 422 Unprocessable Entity if UID is missing."""
def test_global_inbox_missing_params():
    response = client.get("/conversations/inbox/global") # No query param
    assert response.status_code == 422


@given(user_uid=st.text(min_size=1, max_size=50, alphabet=st.characters(blacklist_categories=('Cc', 'Cs'))))
def test_global_inbox_property_based_user_uids(user_uid):
    """
    Property-based testing for global inbox with various user UIDs.
    Verifies that the endpoint handles different UID formats gracefully.
    """
    response = client.get(f"/conversations/inbox/global?user_uid={user_uid}")
    # Should return 200 with empty list for non-existent users, or actual data
    assert response.status_code in [200, 422]  # 422 if UID invalid, but assuming valid
    if response.status_code == 200:
        assert isinstance(response.json(), list)
    