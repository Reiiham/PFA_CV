# backend/db/models.py
from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255))
    email = Column(String(255), unique=True, index=True)
    role = Column(String(50), default="candidate")
    cv_text = Column(Text, nullable=True)
    skills = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    quizzes = relationship("QuizSession", back_populates="user")


class QuizSession(Base):
    __tablename__ = "quiz_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    type = Column(String(100))  # e.g., "candidate_test" or "hr_session"
    questions = Column(JSON)
    score = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="quizzes")
