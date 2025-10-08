import json
from .groq_client import get_groq_client


EXTRACTION_PROMPT_TEMPLATE = (
    "You are an AI specialized in HR analysis.\n"
    "Extract these from the CV text: \n"
    "1) Technical skills, 2) Soft skills, 3) Cognitive skills.\n"
    "For each skill estimate proficiency: beginner, intermediate, or advanced.\n"
    "Return ONLY valid JSON in this format:\n"
    "{{\n"
    "  \"technical_skills\": [{{\"name\": \"...\", \"level\": \"...\"}}],\n"
    "  \"soft_skills\": [{{\"name\": \"...\", \"level\": \"...\"}}],\n"
    "  \"cognitive_skills\": [{{\"name\": \"...\", \"level\": \"...\"}}]\n"
    "}}\n\n"
    "CV Text:\n{cv_text}"
)


def extract_skills(cv_text: str) -> dict:
    client = get_groq_client()
    prompt = EXTRACTION_PROMPT_TEMPLATE.format(cv_text=cv_text)

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
    try:
        skills = json.loads(response_text)
    except json.JSONDecodeError:
        skills = {
            "technical_skills": [],
            "soft_skills": [],
            "cognitive_skills": [],
        }
    return skills
