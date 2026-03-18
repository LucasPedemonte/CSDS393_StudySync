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


def test_dm_conversation_and_message_ordering(client, db):
    seeded = _seed_users_course_enrollments(db)
    course_id = seeded["course"].id

    # Create or fetch DM
    dm = client.post(
        "/conversations/one-on-one",
        params={
            "user_uid_1": seeded["alice"].firebase_uid,
            "user_uid_2": seeded["bob"].firebase_uid,
            "course_id": course_id,
        },
    )
    assert dm.status_code == 200
    conversation_id = dm.json()["conversation_id"]
    assert isinstance(conversation_id, int)

    # Send two messages
    r1 = client.post(
        "/messages",
        json={
            "sender_uid": seeded["alice"].firebase_uid,
            "receiver_uid": seeded["bob"].firebase_uid,
            "course_id": course_id,
            "content": "hello bob",
            "is_group": False,
        },
    )
    assert r1.status_code == 200

    r2 = client.post(
        "/messages",
        json={
            "sender_uid": seeded["bob"].firebase_uid,
            "receiver_uid": seeded["alice"].firebase_uid,
            "course_id": course_id,
            "content": "hi alice",
            "is_group": False,
        },
    )
    assert r2.status_code == 200

    # Fetch messages in DM context
    msgs = client.get(
        "/messages",
        params={
            "user1": seeded["alice"].firebase_uid,
            "user2": seeded["bob"].firebase_uid,
            "course_id": course_id,
            "is_group": "false",
        },
    )

    # Integrity requirement: endpoint should not 500 and should return ordered messages
    assert msgs.status_code == 200
    body = msgs.json()
    assert isinstance(body, list)
    assert [m["content"] for m in body] == ["hello bob", "hi alice"]


def test_global_inbox_includes_course_group_chat_label(client, db):
    seeded = _seed_users_course_enrollments(db)
    course_id = seeded["course"].id

    # Create course group chat
    group = client.get("/conversations/group", params={"course_id": course_id})
    assert group.status_code == 200

    inbox = client.get(
        "/conversations/inbox/global",
        params={"user_uid": seeded["alice"].firebase_uid},
    )
    assert inbox.status_code == 200
    items = inbox.json()
    assert isinstance(items, list)
    assert any(i.get("is_group") is True and i.get("course_id") == course_id for i in items)

