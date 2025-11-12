# backend/db/crud.py
from sqlalchemy.orm import Session
from . import models

def create_user(db: Session, name: str, email: str, role: str):
    user = models.User(name=name, email=email, role=role)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def get_user_by_email(db: Session, email: str):
    return db.query(models.User).filter(models.User.email == email).first()

def save_cv_and_skills(db: Session, user_id: int, cv_text: str, skills: list):
    user = db.query(models.User).get(user_id)
    user.cv_text = cv_text
    user.skills = skills
    db.commit()
    return user

def create_quiz_session(db: Session, user_id: int, questions: list, session_type="candidate_test"):
    session = models.QuizSession(user_id=user_id, questions=questions, type=session_type)
    db.add(session)
    db.commit()
    db.refresh(session)
    return session
