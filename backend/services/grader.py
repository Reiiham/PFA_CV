import json
from statistics import mean
from .groq_client import get_groq_client

#grader.py


# # ============ PROMPT TEMPLATE ============
# GRADING_PROMPT_TEMPLATE = (
#     "You are an examiner AI. Correct the following quiz answers.\n"
#     "Compare each answer to the expected concepts for the skill/question.\n"
#     "Return ONLY valid JSON.\n\n"
#     "Expected input format:\n"
#     "{{\n"
#     "  \"corrections\": [\n"
#     "    {{\n"
#     "      \"skill\": \"...\",\n"
#     "      \"question\": \"...\",\n"
#     "      \"bloom_level\": \"...\",\n"
#     "      \"user_answer\": \"...\",\n"
#     "      \"score\": 0-5,\n"
#     "      \"feedback\": \"Short feedback\"\n"
#     "    }}\n"
#     "  ]\n"
#     "}}\n\n"
#     "Quiz: {quiz}\n"
#     "Answers: {answers}\n"
# )

# # ============ LAZY CLIENT INITIALIZATION ============
# def get_groq():
#     """Initialize Groq client lazily (only once)."""
#     if not hasattr(get_groq, "client"):
#         print("[grader] Initializing Groq client...")
#         get_groq.client = get_groq_client()
#         print("[grader] ✅ Groq client ready")
#     return get_groq.client

# # ============ MAIN FUNCTION ============
# def grade_answers_and_score(quiz: dict, answers: list) -> dict:
#     """Grades quiz answers using the Groq AI model."""
#     print("[grader] Starting grading process...")

#     client = get_groq()

#     prompt = GRADING_PROMPT_TEMPLATE.format(
#         quiz=json.dumps(quiz, ensure_ascii=False),
#         answers=json.dumps(answers, ensure_ascii=False)
#     )

#     try:
#         completion = client.chat.completions.create(
#             model="openai/gpt-oss-20b",
#             messages=[
#                 {
#                     "role": "system",
#                     "content": "Always output strict JSON only. Grade each answer on a scale of 0-5."
#                 },
#                 {"role": "user", "content": prompt},
#             ],
#             temperature=0,
#             max_tokens=3000,
#             stream=False,
#         )
#         response_text = completion.choices[0].message.content.strip()
#         print(f"[grader] ✅ Received response ({len(response_text)} chars)")

#     except Exception as e:
#         print(f"[grader] ⚠️ Groq API error: {e}")
#         response_text = '{"corrections": []}'

#     try:
#         corrections = json.loads(response_text)
#     except json.JSONDecodeError as e:
#         print(f"[grader] ⚠️ JSON parse error: {e}")
#         corrections = {"corrections": []}

#     # --- Compute scores ---
#     scores = [c.get("score", 0) for c in corrections.get("corrections", [])]
#     normalized = [(s / 5) * 100 for s in scores] if scores else [0]
#     overall = round(mean(normalized), 2)

#     bloom_to_weight = {
#         "Remember": 0.6,
#         "Understand": 0.7,
#         "Apply": 0.8,
#         "Analyze": 0.9,
#         "Evaluate": 1.0,
#         "Create": 1.0,
#     }

#     weighted_points = []
#     for c in corrections.get("corrections", []):
#         w = bloom_to_weight.get(c.get("bloom_level"), 0.8)
#         weighted_points.append((c.get("score", 0) / 5) * 100 * w)

#     cognitive_score = round(mean(weighted_points), 2) if weighted_points else overall

#     print(f"[grader] ✅ Grading complete → overall={overall}, cognitive={cognitive_score}")

#     return {
#         "corrections": corrections.get("corrections", []),
#         "overall_score": overall,
#         "cognitive_score": cognitive_score,
#     }
# services/grader.py
import json
import re
from statistics import mean
from .groq_client import get_groq_client
from typing import List, Dict, Any

# ============ PROMPT TEMPLATE ============
GRADING_PROMPT_TEMPLATE = (
    "You are an examiner AI. Correct the following quiz answers.\n"
    "For each user answer, evaluate and return a correction object containing:\n"
    "- skill, question, bloom_level\n"
    "- user_answer\n"
    "- score (integer 0-5)\n"
    "- feedback (one short sentence)\n"
    "- corrected_answer (the expected/canonical answer when the user's is wrong) OR corrected_question if needed\n\n"
    "Return ONLY valid JSON in this exact shape:\n"
    "{{\n"
    '  "corrections": [\n'
    '    {\n'
    '      "skill": "...",\n'
    '      "question": "...",\n'
    '      "bloom_level": "...",\n'
    '      "user_answer": "...",\n'
    '      "score": 0,\n'
    '      "feedback": "...",\n'
    '      "corrected_answer": "..."  // optional\n'
    '    }\n'
    '  ]\n'
    '}}\n\n'
    "QUIZ: {quiz}\n\n"
    "ANSWERS: {answers}\n"
)

# ============ LAZY CLIENT ============
def get_groq():
    if not hasattr(get_groq, "client"):
        print("[grader] Initializing Groq client...")
        get_groq.client = get_groq_client()
        print("[grader] ✅ Groq client ready")
    return get_groq.client

# ============ SAFE JSON LOADER ============
def safe_json_load(s: str) -> Dict[str, Any]:
    """Try a few heuristics to extract JSON."""
    if not s:
        return {}
    s = s.strip()
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        pass
    # try find first {...} block
    start = s.find("{")
    end = s.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidate = s[start:end+1]
        cand2 = re.sub(r",\s*}", "}", candidate)
        cand2 = re.sub(r",\s*\]", "]", cand2)
        try:
            return json.loads(cand2)
        except json.JSONDecodeError:
            pass
    return {}

# ============ MAIN FUNCTION ============
def grade_answers_and_score(quiz: Dict[str, Any], answers: List[Dict[str, Any]]) -> Dict[str, Any]:
    
    print("[grader] Starting grading process...")
    print(f"[grader] Quiz has {len(quiz.get('skill_quizzes', []))} skill blocks")
    print(f"[grader] Received {len(answers)} answers for grading")

    # If answers empty => continue but log
    if not answers:
        print("[grader] Warning: empty answers list — proceeding with empty answers for grading.")

    """
    Grades quiz answers using Groq AI.
    Returns:
      {
        "corrections": [...],
        "overall_score": float,
        "cognitive_score": float,
        "corrected_quiz": {...}
      }
    """
    print("[grader] Starting grading process...")
    client = get_groq()

    prompt = GRADING_PROMPT_TEMPLATE.replace("{quiz}", json.dumps(quiz, ensure_ascii=False)).replace("{answers}", json.dumps(answers, ensure_ascii=False))

    try:
        completion = client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=[
                {"role": "system", "content": "Always output strict JSON only. Grade each answer on a scale of 0-5."},
                {"role": "user", "content": prompt},
            ],
            temperature=0,
            max_tokens=3000,
            stream=False,
        )
        response_text = completion.choices[0].message.content.strip()
        print(f"[grader] ✅ Received response ({len(response_text)} chars)")
    except Exception as e:
        print(f"[grader] ⚠️ Groq API error: {e}")
        response_text = '{"corrections": []}'

    parsed = safe_json_load(response_text)
    corrections = parsed.get("corrections") or []

    # Ensure corrections is a list of dicts
    if not isinstance(corrections, list):
        corrections = []

    # --- Compute numeric scores ---
    scores = [c.get("score", 0) for c in corrections if isinstance(c, dict)]
    normalized = [(s / 5) * 100 for s in scores] if scores else [0]
    overall = round(mean(normalized), 2) if scores else 0.0

    bloom_to_weight = {
        "Remember": 0.6,
        "Understand": 0.7,
        "Apply": 0.8,
        "Analyze": 0.9,
        "Evaluate": 1.0,
        "Create": 1.0,
    }

    weighted_points = []
    for c in corrections:
        if not isinstance(c, dict):
            continue
        w = bloom_to_weight.get(c.get("bloom_level"), 0.8)
        weighted_points.append((c.get("score", 0) / 5) * 100 * w)
    cognitive_score = round(mean(weighted_points), 2) if weighted_points else overall

    # --- Apply corrections back into a corrected_quiz object (best-effort) ---
    corrected_quiz = json.loads(json.dumps(quiz))  # deep copy
    # Expect quiz structure: {"skill_quizzes":[{"skill":..., "questions":[{...}]}]}
    skill_map = {}
    for block in corrected_quiz.get("skill_quizzes", []):
        skill = block.get("skill")
        if skill:
            skill_map.setdefault(skill, {}).update({"block": block, "questions": block.get("questions", [])})

    # For each correction try to find matching question and attach corrected_answer field
    for corr in corrections:
        try:
            skill = corr.get("skill")
            question_text = corr.get("question")
            corrected_answer = corr.get("corrected_answer")
            # find in skill_map
            if skill and skill in skill_map:
                qs = skill_map[skill]["questions"]
                # match by question text (best-effort substring match)
                for q in qs:
                    if not q:
                        continue
                    qtext = q.get("question", "")
                    if question_text and (question_text.strip() == qtext.strip() or question_text.strip() in qtext or qtext in question_text):
                        # attach correction info
                        q["_correction"] = {
                            "user_answer": corr.get("user_answer"),
                            "score": corr.get("score"),
                            "feedback": corr.get("feedback"),
                            "corrected_answer": corrected_answer
                        }
                        # if corrected_answer provided, also set 'answer' to corrected_answer (so quiz shows corrected)
                        if corrected_answer:
                            q["answer"] = corrected_answer
                        break
        except Exception:
            continue

    print(f"[grader] ✅ Grading complete → overall={overall}, cognitive={cognitive_score}")
    return {
        "corrections": corrections,
        "overall_score": overall,
        "cognitive_score": cognitive_score,
        "corrected_quiz": corrected_quiz
    }
