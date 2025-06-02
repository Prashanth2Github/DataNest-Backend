# seed_users.py

from sqlalchemy.orm import Session
from database import SessionLocal
import models
from auth import get_password_hash

# Predefined users
users = [
    {"username": "admin", "password": "admin123", "role": "admin"},
    {"username": "testuser", "password": "user123", "role": "user"},
]

def seed():
    db: Session = SessionLocal()
    for user_data in users:
        existing = db.query(models.User).filter(models.User.username == user_data["username"]).first()
        if existing:
            print(f"User '{user_data['username']}' already exists. Skipping.")
            continue
        user = models.User(
            username=user_data["username"],
            password_hash=get_password_hash(user_data["password"]),
            role=user_data["role"]
        )
        db.add(user)
        print(f"Added user: {user.username}")
    db.commit()
    db.close()

if __name__ == "__main__":
    seed()
