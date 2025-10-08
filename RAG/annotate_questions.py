from annotation import annotate_questions_with_metadata
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import json
from backend.services.groq_client import get_groq_client
import json

client = get_groq_client()

with open("behavioral_questions.json", "r", encoding="utf-8") as f:
    questions = json.load(f)["soft_skills_questions"]

annotated = annotate_questions_with_metadata(questions, client)

with open("behavioral_questions_annotated.json", "w", encoding="utf-8") as f:
    json.dump(annotated, f, indent=4, ensure_ascii=False)
