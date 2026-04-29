"""Tests for the resource-library CRUD path on /posts.

Covers the create-and-list happy path and the role-gated delete:
Students can create posts, but only TAs/Admins may delete them.
"""


def _seed_users_course(db):
    """Create one TA, one Student, and a course owned by the TA."""
    import models

    ta = models.User(
        firebase_uid="ta_1",
        email="ta1@example.com",
        full_name="TA One",
        role="TA",
    )
    student = models.User(
        firebase_uid="student_1",
        email="student1@example.com",
        full_name="Student One",
        role="Student",
    )
    db.add_all([ta, student])
    db.flush()

    course = models.Course(
        course_code="CSDS393",
        name="StudySync",
        description="Test course",
        owner_id=ta.firebase_uid,
    )
    db.add(course)
    db.commit()
    db.refresh(course)
    return {"ta": ta, "student": student, "course": course}


def test_posts_create_and_list(client, db):
    """A Student can POST a resource post and the new post appears in GET /posts."""
    seeded = _seed_users_course(db)
    course_id = seeded["course"].id

    created = client.post(
        "/posts",
        params={"course_id": course_id, "author_uid": seeded["student"].firebase_uid},
        json={
            "title": "Midterm Review Sheet",
            "description": "Annotated review notes",
            "resource_link": "https://example.com/review.pdf",
        },
    )
    assert created.status_code == 200
    post = created.json()
    assert post["title"] == "Midterm Review Sheet"
    assert post["course_id"] == course_id

    listed = client.get("/posts", params={"course_id": course_id, "current_user_uid": seeded["student"].firebase_uid})
    assert listed.status_code == 200
    items = listed.json()
    assert isinstance(items, list)
    assert any(p["id"] == post["id"] for p in items)


def test_posts_delete_requires_ta_or_admin(client, db):
    """DELETE /posts/{id} must 403 for the student author and 200 for the TA."""
    seeded = _seed_users_course(db)
    course_id = seeded["course"].id

    created = client.post(
        "/posts",
        params={"course_id": course_id, "author_uid": seeded["student"].firebase_uid},
        json={"title": "link", "description": "d", "resource_link": None},
    )
    post_id = created.json()["id"]

    forbidden = client.delete(f"/posts/{post_id}", params={"user_uid": seeded["student"].firebase_uid})
    assert forbidden.status_code == 403
    assert forbidden.json()["detail"] == "Only TAs or Admins can delete posts."

    ok = client.delete(f"/posts/{post_id}", params={"user_uid": seeded["ta"].firebase_uid})
    assert ok.status_code == 200
    assert ok.json()["status"] == "success"

