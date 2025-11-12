# backend/api/auth.py
from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/auth", tags=["Authentication"])

# Simule la création d’un profil candidat
@router.post("/register")
def register_user(name: str, email: str, role: str = "candidate"):
    return {"message": f"User {name} registered successfully as {role}"}

# Simule la connexion
@router.post("/login")
def login_user(email: str):
    if email == "":
        raise HTTPException(status_code=400, detail="Email required")
    return {"message": f"Welcome back {email}"}
