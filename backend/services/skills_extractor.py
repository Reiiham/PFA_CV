import json
from .groq_client import get_groq_client

# ============ PROMPT TEMPLATE ============


import json
from .groq_client import get_groq_client

EXTRACTION_PROMPT_TEMPLATE = """You are an AI specialized in HR analysis.
Extract these from the CV text: 
1) Technical skills, 
2) Soft skills, 
3) Cognitive skills.
For each skill estimate proficiency: beginner, intermediate, or advanced.
Return ONLY valid JSON in this format:
{{
  "technical_skills": [{{"name": "...", "level": "..."}}],
  "soft_skills": [{{"name": "...", "level": "..."}}],
  "cognitive_skills": [{{"name": "...", "level": "..."}}]
}}

CV Text:
{cv_text}
"""

def extract_skills(cv_text: str) -> dict:
    print("[skills_extractor] Extracting skills...")
    client = get_groq_client()
    print("[skills_extractor] ✅ Groq client ready")

    # Limit CV length for safety
    truncated_cv = cv_text[:5000]

    # Safe string format (only one placeholder)
    prompt = EXTRACTION_PROMPT_TEMPLATE.format(cv_text=truncated_cv)

    try:
        completion = client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=[
                {"role": "system", "content": "Return strict JSON only."},
                {"role": "user", "content": prompt},
            ],
            temperature=0,
            max_tokens=2048,
            stream=False,
        )

        response_text = completion.choices[0].message.content.strip()
        print("[skills_extractor] Raw response preview:", response_text[:400])

        try:
            skills = json.loads(response_text)
        except json.JSONDecodeError:
            print("[skills_extractor] ⚠️ Invalid JSON, returning empty structure")
            skills = {
                "technical_skills": [],
                "soft_skills": [],
                "cognitive_skills": [],
            }

        return skills

    except Exception as e:
        import traceback
        print("\n===== ⚠️ extract_skills ERROR =====")
        traceback.print_exc()
        print("===================================\n")
        return {
            "technical_skills": [],
            "soft_skills": [],
            "cognitive_skills": [],
        }

