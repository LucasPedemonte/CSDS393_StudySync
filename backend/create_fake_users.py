from database import SessionLocal, engine, Base
from models import User
import uuid

# Create tables if they don't exist
Base.metadata.create_all(bind=engine)

# Create session
db = SessionLocal()

# Fake user data
fake_users = [
    {
        "firebase_uid": str(uuid.uuid4()),
        "email": "alice@example.com",
        "full_name": "Alice Johnson",
        "role": "Student"
    },
    {
        "firebase_uid": str(uuid.uuid4()),
        "email": "bob@example.com",
        "full_name": "Bob Smith",
        "role": "Student"
    },
    {
        "firebase_uid": str(uuid.uuid4()),
        "email": "charlie@example.com",
        "full_name": "Charlie Brown",
        "role": "TA"
    },
    {
        "firebase_uid": str(uuid.uuid4()),
        "email": "diana@example.com",
        "full_name": "Diana Prince",
        "role": "Student"
    },
    {
        "firebase_uid": str(uuid.uuid4()),
        "email": "eve@example.com",
        "full_name": "Eve Wilson",
        "role": "Admin"
    },
]

try:
    for user_data in fake_users:
        # Check if user already exists
        existing_user = db.query(User).filter(User.email == user_data["email"]).first()
        if not existing_user:
            new_user = User(**user_data)
            db.add(new_user)
            print(f"✓ Added {user_data['full_name']}")
        else:
            print(f"✗ {user_data['full_name']} already exists")
    
    db.commit()
    print("\nAll fake users created successfully!")
    
    # Show all users
    all_users = db.query(User).all()
    print(f"\nTotal users in database: {len(all_users)}")
    for user in all_users:
        print(f"  - {user.full_name} ({user.email}) - {user.role}")
    
except Exception as e:
    db.rollback()
    print(f"Error: {e}")
finally:
    db.close()
