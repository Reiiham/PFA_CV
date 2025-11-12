# backend/api/quiz.py
from fastapi import APIRouter
from backend.services.quiz_generator import generate_quiz

router = APIRouter(prefix="/quiz", tags=["Quiz"])

@router.post("/generate")
def generate_quiz_api(cv_text: str, num_questions: int = 5):
    quiz = generate_quiz(cv_text, num_questions)
    return {"quiz": quiz}
