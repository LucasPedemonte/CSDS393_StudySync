"""Permission and inbox-shape tests against the live FastAPI app.

Two concerns:

- Role gating: a Student must not be able to delete a post (only TAs
  and Admins can).
- Inbox/message endpoint contracts: response shape and required-param
  validation for ``/conversations/inbox/global`` and ``/messages``,
  plus a Hypothesis property-based pass over the inbox endpoint.

These tests share a module-level ``TestClient`` and do not use the
``db`` fixture from conftest, so they run against whatever database
``main.app`` is configured for.
"""
import pytest
from fastapi.testclient import TestClient
from main import app
from hypothesis import given, strategies as st

client = TestClient(app)


def test_student_cannot_delete_post():
    """DELETE /posts/{id} as a Student must return 403 with the expected detail."""
    response = client.delete("/posts/1?user_uid=student_user_123")
    
    # Assert that the backend blocks the action
    assert response.status_code == 403
    assert response.json()["detail"] == "Only TAs or Admins can delete posts."

def test_get_global_inbox_structure():
    """Global inbox must return a JSON list (the conversation feed shape)."""
    response = client.get("/conversations/inbox/global?user_uid=test_user")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    
def test_get_global_inbox_empty():
    """A user with no conversations should get an empty list, not a 404 or error."""
    response = client.get("/conversations/inbox/global?user_uid=new_user_999")
    assert response.status_code == 200
    assert response.json() == []

def test_get_class_discussion_messages():
    """Fetching the public class group chat (is_group=true) must return a list."""
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
    """Global inbox without the required user_uid query param must 422 (FastAPI validation)."""
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
    