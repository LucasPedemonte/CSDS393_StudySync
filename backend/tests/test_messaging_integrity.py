import pytest


def _seed_users_course_enrollments(db):
    import models

    ta = models.User(
        firebase_uid="ta_1",
        email="ta1@example.com",
        full_name="TA One",
        role="TA",
    )
    alice = models.User(
        firebase_uid="user_alice",
        email="alice@example.com",
        full_name="Alice",
        role="Student",
    )
    bob = models.User(
        firebase_uid="user_bob",
        email="bob@example.com",
        full_name="Bob",
        role="Student",
    )
    db.add_all([ta, alice, bob])
    db.flush()

    course = models.Course(
        course_code="CSDS393",
        name="StudySync",
        description="Test course",
        owner_id=ta.firebase_uid,
    )
    db.add(course)
    db.flush()

    db.add_all(
        [
            models.Enrollment(user_id=alice.firebase_uid, course_id=course.id),
            models.Enrollment(user_id=bob.firebase_uid, course_id=course.id),
        ]
    )
    db.commit()
    return {"ta": ta, "alice": alice, "bob": bob, "course": course}


def test_send_message_rejects_empty_content(client, db):
    seeded = _seed_users_course_enrollments(db)
    course_id = seeded["course"].id

    resp = client.post(
        "/messages",
        json={
            "sender_uid": seeded["alice"].firebase_uid,
            "receiver_uid": seeded["bob"].firebase_uid,
            "course_id": course_id,
            "content": "   ",
            "is_group": False,
        },
    )
    assert resp.status_code == 400
    assert resp.json()["detail"] == "Message cannot be empty."


