# backend/api/upload.py
from fastapi import APIRouter, UploadFile, File
from backend.services.pdf_extractor import extract_text_from_pdf
from backend.services.skills_extractor import extract_skills

router = APIRouter(prefix="/upload", tags=["CV Upload"])

@router.post("/cv")
async def upload_cv(file: UploadFile = File(...)):
    text = extract_text_from_pdf(await file.read())
    skills = extract_skills(text)
    return {"filename": file.filename, "skills": skills}
