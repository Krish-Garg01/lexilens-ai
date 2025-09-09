from models import SessionLocal, User
from auth import get_password_hash

# Create a test user
db = SessionLocal()
existing_user = db.query(User).filter(User.email == "test@example.com").first()
if existing_user:
    print("User already exists")
else:
    hashed_password = get_password_hash("test123")
    test_user = User(email="test@example.com", hashed_password=hashed_password)
    db.add(test_user)
    db.commit()
    db.refresh(test_user)
    print("Test user created: test@example.com / test123")

db.close()
