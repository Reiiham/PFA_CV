# backend/api/rh.py
from fastapi import APIRouter
from backend.services.recommender import recommend_questions_for_role

router = APIRouter(prefix="/rh", tags=["HR Sessions"])

@router.post("/session")
def create_rh_session(role: str, difficulty: str = "medium"):
    recommended = recommend_questions_for_role(role, difficulty)
    return {"role": role, "questions": recommended}
