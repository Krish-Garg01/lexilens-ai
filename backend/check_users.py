from models import SessionLocal, User

db = SessionLocal()
users = db.query(User).all()
for user in users:
    print(f"User: {user.email}, Active: {user.is_active}")
db.close()
