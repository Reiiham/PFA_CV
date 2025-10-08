import json
from statistics import mean
from .groq_client import get_groq_client


GRADING_PROMPT_TEMPLATE = (
    "You are an examiner AI. Correct the following quiz answers.\n"
    "Compare each answer to the expected concepts for the skill/question.\n"
    "Return ONLY valid JSON.\n\n"
    "Expected input format:\n"
    "{{\n"
    "  \"corrections\": [\n"
    "    {{\n"
    "      \"skill\": \"...\",\n"
    "      \"question\": \"...\",\n"
    "      \"bloom_level\": \"...\",\n"
    "      \"user_answer\": \"...\",\n"
    "      \"score\": 0-5,\n"
    "      \"feedback\": \"Short feedback\"\n"
    "    }}\n"
    "  ]\n"
    "}}\n\n"
    "Quiz: {quiz}\n"
    "Answers: {answers}\n"
)


def grade_answers_and_score(quiz: dict, answers: list) -> dict:
    client = get_groq_client()

    prompt = GRADING_PROMPT_TEMPLATE.format(
        quiz=json.dumps(quiz, ensure_ascii=False),
        answers=json.dumps(answers, ensure_ascii=False)
    )

    try:
        completion = client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=[
                {"role": "system", "content": "Always output strict JSON only. Grade each answer on a scale of 0-5."},
                {"role": "user", "content": prompt},
            ],
            temperature=0,
            max_tokens=3000,  # Increased token limit
            stream=False,
        )

        response_text = completion.choices[0].message.content.strip()
        print(f"[grader] raw response length: {len(response_text)}")
        print(f"[grader] raw response preview: {response_text[:500]}")
    except Exception as e:
        print(f"[grader] Groq API error: {e}")
        response_text = '{"corrections": []}'

    try:
        corrections = json.loads(response_text)
    except json.JSONDecodeError as e:
        print(f"[grader] JSON parse error: {e}")
        corrections = {"corrections": []}

    scores = [c.get("score", 0) for c in corrections.get("corrections", [])]
    normalized = [(s / 5) * 100 for s in scores] if scores else [0]
    overall = round(mean(normalized), 2)

    bloom_to_weight = {
        "Remember": 0.6,
        "Understand": 0.7,
        "Apply": 0.8,
        "Analyze": 0.9,
        "Evaluate": 1.0,
        "Create": 1.0,
    }
    weighted_points = []
    for c in corrections.get("corrections", []):
        w = bloom_to_weight.get(c.get("bloom_level"), 0.8)
        weighted_points.append((c.get("score", 0) / 5) * 100 * w)
    cognitive_score = round(mean(weighted_points), 2) if weighted_points else overall

    return {
        "corrections": corrections.get("corrections", []),
        "overall_score": overall,
        "cognitive_score": cognitive_score,
    }
