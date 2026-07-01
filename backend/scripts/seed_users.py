import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.database import SessionLocal
from app.auth import create_user
from app.models import User


def seed_users():
    db = SessionLocal()
    try:
        users = [
            ("admin", "admin123", "Admin"),
            ("engineer", "eng123", "Engineer")
        ]
        for username, password, role in users:
            existing = db.query(User).filter(User.username == username).first()
            if not existing:
                create_user(db, username, password, role)
                print(f"Created user {username} ({role})")
            else:
                print(f"User {username} already exists")
    except Exception as e:
        print(f"Error seeding users: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    seed_users()
