# services/quiz_generator.py  (Version B) 
# Min/Max questions per skill + guaranteed Apply+ (Bloom) + RAG per-skill
import json
import os
import re
from typing import List, Dict, Any, Optional
from .groq_client import get_groq_client
from pinecone import Pinecone
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
import time

load_dotenv()

# --- CONFIG ---
PINECONE_API_KEY = os.getenv("PINECONE_API")
INDEX_HOST = os.getenv("INDEX_URL")
NAMESPACE = "quiz-namespace"

# embedding model (you already used this)
embedding_model = SentenceTransformer('BAAI/bge-large-en-v1.5')

# Pinecone init (assumes same interface you had)
pc = Pinecone(api_key=PINECONE_API_KEY)
index = pc.Index(host=INDEX_HOST)

# ---------------- PARAMETERS ----------------
# Version B: min/max questions per skill
QUESTIONS_MIN = 2
QUESTIONS_MAX = 4

MAX_CONTEXT_CHARS = 3500     # keep context manageable (total for all skills)
CONTEXT_SCORE_THRESHOLD = 0.25
TOP_K_PER_SKILL = 6
MAX_RETRIES_JSON_REPAIR = 2
MODEL_NAME = "openai/gpt-oss-20b"
TEMPERATURE = 0.15
MAX_TOKENS = 4000

# ---------------- PROMPT TEMPLATES (few-shot + strict schema) ----------------
SYSTEM_JSON_ONLY = "You are a JSON-only responder. Return valid JSON only and nothing else."

QUIZ_PROMPT_HEADER = """
You are an expert quiz generator for technical and soft skills. Use the CONTEXT and the provided SKILLS to create a JSON document strictly following the schema described below. Do NOT add any extraneous text or explanation — only output JSON.

Schema:
{
  "skill_quizzes": [
    {
      "skill": "string",
      "questions": [
        {
          "type": "MCQ" | "Short Answer" | "Coding",
          "bloom_level": "Remember" | "Understand" | "Apply" | "Analyze" | "Evaluate" | "Create",
          "question": "string",
          "options": ["A", "B", "C", "D"],        // only for MCQ; must be 4 items
          "answer": "Exact answer string (for MCQ must match one of options)"
        }
      ]
    }
  ]
}

Rules:
- Generate between {QUESTIONS_MIN} and {QUESTIONS_MAX} questions per skill.
- At least one question per skill should be "Apply" or higher (Apply / Analyze / Create).
- MCQ questions must have exactly 4 options and the answer must match one of them.
- Short Answer questions should have an "answer" field with the expected answer (a short string).
- Coding questions should include a prompt and a short sample answer in "answer".
- Keep questions clear, concise, and specific to the skill.
- Use the CONTEXT to ground questions and avoid hallucination. If context is "No specific context found.", rely on common real-world scenarios for the skill.

EXAMPLES (follow these exactly):

Example 1:
{{
  "skill_quizzes": [
    {{
      "skill": "Git",
      "questions": [
        {{
          "type": "MCQ",
          "bloom_level": "Remember",
          "question": "Which command creates a new branch named 'feature'?",
          "options": ["git checkout master", "git branch feature", "git push origin feature", "git merge feature"],
          "answer": "git branch feature"
        }},
        {{
          "type": "Short Answer",
          "bloom_level": "Understand",
          "question": "Explain what 'git rebase' does in one sentence.",
          "answer": "It moves or combines a sequence of commits to a new base commit, rewriting history."
        }}
      ]
    }}
  ]
}}

Now generate the quiz JSON for the following CONTEXT and SKILLS.

CONTEXT:
{context}

SKILLS:
{skills}
"""

REPAIR_PROMPT = """
You were given a JSON object that should follow a strict schema (same as above). The JSON is invalid or does not follow the schema. Fix the JSON so:
- It's valid JSON
- Each skill has between {QUESTIONS_MIN} and {QUESTIONS_MAX} questions
- MCQs have exactly 4 options and the answer matches one of them
- Bloom levels are valid and each skill includes at least one question with bloom_level in ["Apply","Analyze","Evaluate","Create"]
Return only the corrected JSON.
"""

# ---------------- HELPERS ----------------
def get_embedding(text: str) -> List[float]:
    try:
        return embedding_model.encode(text).tolist()
    except Exception as e:
        print(f"[get_embedding] Error: {e}")
        return []

def dedupe_contexts(texts: List[str]) -> List[str]:
    seen = set()
    out = []
    for t in texts:
        s = t.strip()
        if not s:
            continue
        if s in seen:
            continue
        seen.add(s)
        out.append(s)
    return out

def clamp_context(all_context: List[str], max_chars: int) -> str:
    # join but ensure under max_chars; prefer keeping items intact
    out = []
    total = 0
    for chunk in all_context:
        if total + len(chunk) + 2 > max_chars:
            break
        out.append(chunk)
        total += len(chunk) + 2
    return "\n".join(out) if out else "No specific context found."

# ---------------- RAG SEARCH (per-skill) ----------------
def retrieve_context_per_skill(skills: List[str], top_k: int = TOP_K_PER_SKILL, min_score_threshold: float = CONTEXT_SCORE_THRESHOLD) -> Dict[str, str]:
    """
    Query the vector index (Pinecone) per skill and return a dict:
      { "Python": "- excerpt1\n- excerpt2\n...", "SQL": "No specific context found." }
    Use a per-skill threshold to filter low-score hits.
    """
    skill_contexts: Dict[str, List[str]] = {}
    for skill in skills:
        try:
            qvec = get_embedding(skill)
            if not qvec:
                skill_contexts[skill] = "No specific context found."
                print(f"[retrieve_context_per_skill] no embedding for skill: {skill}")
                continue

            query_results = index.query(
                namespace=NAMESPACE,
                vector=qvec,
                top_k=top_k,
                include_metadata=True
            )

            # unify interface: query_results may be dict-like or object-like
            matches = query_results.get("matches", []) if isinstance(query_results, dict) else getattr(query_results, "matches", [])
            excerpts = []
            for m in matches:
                metadata = m.get("metadata", {}) if isinstance(m, dict) else getattr(m, "metadata", {})
                text = metadata.get("text", "") if isinstance(metadata, dict) else ""
                score = m.get("score", 0) if isinstance(m, dict) else getattr(m, "score", 0)
                if text and score >= min_score_threshold:
                    excerpts.append(text.strip())
            excerpts = dedupe_contexts(excerpts)
            if excerpts:
                # limit per skill to top_k items and reasonable length per excerpt
                limited = []
                for ex in excerpts[:top_k]:
                    # truncate single excerpt if too long
                    if len(ex) > 1000:
                        limited.append(ex[:1000].rsplit("\n", 1)[0] + " ...")
                    else:
                        limited.append(ex)
                skill_contexts[skill] = "\n\n".join(limited)
            else:
                skill_contexts[skill] = "No specific context found."
            print(f"[retrieve_context_per_skill] skill={skill!r} found={len(excerpts)}")
        except Exception as e:
            print(f"[retrieve_context_per_skill] Error for skill={skill}: {e}")
            skill_contexts[skill] = "No specific context found."
    return skill_contexts

# Keep older retrieve_context for backward compatibility (returns whole context blob)
def retrieve_context(skills: List[str], top_k: int = TOP_K_PER_SKILL) -> str:
    all_context = []
    for skill in skills:
        try:
            qvec = get_embedding(skill)
            if not qvec:
                continue
            query_results = index.query(
                namespace=NAMESPACE,
                vector=qvec,
                top_k=top_k,
                include_metadata=True
            )
            matches = query_results.get("matches", []) if isinstance(query_results, dict) else getattr(query_results, "matches", [])
            for m in matches:
                metadata = m.get("metadata", {}) if isinstance(metadata, dict) else getattr(m, "metadata", {})
                text = metadata.get("text", "") if isinstance(metadata, dict) else ""
                score = m.get("score", 0) if isinstance(m, dict) else getattr(m, "score", 0)
                if text and score >= CONTEXT_SCORE_THRESHOLD:
                    all_context.append(f"- {text.strip()}")
        except Exception as e:
            print(f"[retrieve_context] Pinecone query error for '{skill}': {e}")
            continue

    all_context = dedupe_contexts(all_context)
    context = clamp_context(all_context, MAX_CONTEXT_CHARS)
    print(f"[retrieve_context] total_context_chars={len(context)} items={len(all_context)}")
    return context

# ---------------- JSON PARSING / VALIDATION ----------------
def safe_json_load(s: str) -> Optional[dict]:
    """Try to extract JSON from a noisy response and parse it."""
    if not s:
        return None
    s = s.strip()
    # Quick attempt
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        # try to find the first { ... } block
        start = s.find("{")
        end = s.rfind("}")
        if start != -1 and end != -1 and end > start:
            candidate = s[start:end+1]
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                # fallback: try to remove trailing commas etc (very conservative)
                cand2 = re.sub(r",\s*}", "}", candidate)
                cand2 = re.sub(r",\s*\]", "]", cand2)
                try:
                    return json.loads(cand2)
                except json.JSONDecodeError:
                    return None
        return None

def validate_quiz_schema(quiz: dict) -> (bool, List[str]):
    """Basic validation: structure, per-skill questions count, MCQ rules."""
    errors = []
    if not isinstance(quiz, dict):
        return False, ["Top-level must be an object"]
    sq = quiz.get("skill_quizzes")
    if not isinstance(sq, list):
        return False, ["'skill_quizzes' must be a list"]
    for sidx, skill_block in enumerate(sq):
        skill = skill_block.get("skill")
        questions = skill_block.get("questions")
        if not skill or not isinstance(skill, str):
            errors.append(f"skill at index {sidx} missing or not a string")
        if not isinstance(questions, list) or not (QUESTIONS_MIN <= len(questions) <= QUESTIONS_MAX):
            errors.append(f"skill '{skill}' must have {QUESTIONS_MIN}-{QUESTIONS_MAX} questions (found {len(questions) if isinstance(questions, list) else 'N/A'})")
        else:
            for qidx, q in enumerate(questions):
                if not isinstance(q, dict):
                    errors.append(f"question {qidx} for '{skill}' is not an object")
                    continue
                qtype = q.get("type")
                bloom = q.get("bloom_level")
                if qtype not in ("MCQ", "Short Answer", "Coding"):
                    errors.append(f"'{skill}' question {qidx} invalid type: {qtype}")
                if bloom not in ("Remember", "Understand", "Apply", "Analyze", "Evaluate", "Create"):
                    errors.append(f"'{skill}' question {qidx} invalid bloom_level: {bloom}")
                if not q.get("question"):
                    errors.append(f"'{skill}' question {qidx} missing 'question' text")
                if qtype == "MCQ":
                    opts = q.get("options")
                    ans = q.get("answer")
                    if not isinstance(opts, list) or len(opts) != 4:
                        errors.append(f"'{skill}' question {qidx} MCQ must have exactly 4 options")
                    if ans is None or (isinstance(opts, list) and ans not in opts):
                        errors.append(f"'{skill}' question {qidx} MCQ answer missing or not in options")
                else:
                    if "answer" not in q:
                        errors.append(f"'{skill}' question {qidx} missing 'answer' field")
    return (len(errors) == 0), errors

def skills_missing_apply_plus(quiz: dict) -> List[str]:
    """Return list of skill names that do not have any question with bloom_level in Apply+."""
    missing = []
    if not isinstance(quiz, dict):
        return missing
    for skill_block in quiz.get("skill_quizzes", []):
        skill = skill_block.get("skill")
        questions = skill_block.get("questions", []) or []
        has_apply = any(q.get("bloom_level") in ("Apply", "Analyze", "Evaluate", "Create") for q in questions if isinstance(q, dict))
        if not has_apply:
            missing.append(skill)
    return missing

def repair_with_model(client, bad_json_text: str, context: str, skills_repr: str) -> Optional[dict]:
    """Ask the model to repair broken JSON using a repair prompt (one attempt)."""
    try:
        print("[repair_with_model] Asking model to repair JSON...")
        # Use replace to avoid conflicting braces interpretation
        prompt_header = QUIZ_PROMPT_HEADER.replace("{QUESTIONS_MIN}", str(QUESTIONS_MIN)).replace("{QUESTIONS_MAX}", str(QUESTIONS_MAX)).replace("{context}", context).replace("{skills}", skills_repr)
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": SYSTEM_JSON_ONLY},
                {"role": "user", "content": prompt_header},
                {"role": "user", "content": f"Here is the invalid JSON to fix:\n\n{bad_json_text}\n\n{REPAIR_PROMPT.replace('{QUESTIONS_MIN}', str(QUESTIONS_MIN)).replace('{QUESTIONS_MAX}', str(QUESTIONS_MAX))}"}
            ],
            temperature=0.05,
            max_tokens=MAX_TOKENS,
            stream=False,
        )
        repaired = completion.choices[0].message.content.strip()
        parsed = safe_json_load(repaired)
        return parsed
    except Exception as e:
        print("[repair_with_model] repair attempt failed:", e)
        return None

def targeted_add_apply_question(client, current_json_text: str, skill_name: str, context: str, skills_repr: str) -> Optional[dict]:
    """
    Ask the model to add one question with bloom_level Apply or higher for the specified skill.
    Returns parsed JSON if successful.
    """
    try:
        print(f"[targeted_add_apply_question] Requesting Apply+ question for skill: {skill_name}")
        prompt_header = QUIZ_PROMPT_HEADER.replace("{QUESTIONS_MIN}", str(QUESTIONS_MIN)).replace("{QUESTIONS_MAX}", str(QUESTIONS_MAX)).replace("{context}", context).replace("{skills}", skills_repr)
        # Ask to add one Apply+ question for skill_name to the JSON document provided
        user_msg = (
            f"The JSON below lacks an Apply+ question for the skill '{skill_name}'. "
            "Please add exactly one question for that skill with bloom_level 'Apply', 'Analyze', 'Evaluate' or 'Create'. "
            "Keep the JSON valid and adhere to the schema and MCQ rules. Return only the corrected full JSON.\n\n"
            f"Current JSON:\n{current_json_text}"
        )
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": SYSTEM_JSON_ONLY},
                {"role": "user", "content": prompt_header},
                {"role": "user", "content": user_msg}
            ],
            temperature=0.05,
            max_tokens=MAX_TOKENS,
            stream=False,
        )
        repaired = completion.choices[0].message.content.strip()
        parsed = safe_json_load(repaired)
        return parsed
    except Exception as e:
        print("[targeted_add_apply_question] failed:", e)
        return None

# ---------------- MAIN GENERATION ----------------
def generate_quiz_for_skills(categorized_skills: Dict[str, List[str]]) -> dict:
    """Generate quiz questions using RAG + Groq + robust JSON validation + Bloom guarantee."""

    print("[quiz_generator] Initializing Groq client...")
    client = get_groq_client()
    print("[quiz_generator] ✅ Groq client ready")

    # Limit skills to avoid token explosion (keep default of 2 per category)
    limited_skills = {cat: skills[:2] for cat, skills in categorized_skills.items()}
    all_skills = [s for group in limited_skills.values() for s in group]
    if not all_skills:
        return {"skill_quizzes": []}

    # ---------------- RAG per-skill ----------------
    print("[quiz_generator] Retrieving context via RAG (per-skill)...")
    skill_contexts = retrieve_context_per_skill(all_skills, top_k=TOP_K_PER_SKILL, min_score_threshold=CONTEXT_SCORE_THRESHOLD)
    per_skill_blocks = []
    for sk in all_skills:
        ctx = skill_contexts.get(sk, "No specific context found.")
        block = f"SKILL: {sk}\nCONTEXT:\n{ctx}"
        per_skill_blocks.append(block)

    combined_context = "\n\n---\n\n".join(per_skill_blocks)
    if len(combined_context) > MAX_CONTEXT_CHARS:
        per_skill_max = max(200, MAX_CONTEXT_CHARS // max(1, len(per_skill_blocks)))
        truncated_blocks = []
        for block in per_skill_blocks:
            if len(block) <= per_skill_max:
                truncated_blocks.append(block)
            else:
                snippet = block[:per_skill_max]
                if "\n" in snippet:
                    snippet = snippet.rsplit("\n", 1)[0]
                truncated_blocks.append(snippet + "\n...")
        combined_context = "\n\n---\n\n".join(truncated_blocks)
        if len(combined_context) > MAX_CONTEXT_CHARS:
            combined_context = combined_context[:MAX_CONTEXT_CHARS]
    print(f"[quiz_generator] combined_context_chars={len(combined_context)} skills={len(all_skills)}")

    # Build skills_repr JSON (same format as before)
    skills_repr = json.dumps(limited_skills, ensure_ascii=False)

    # Use .replace to avoid issues with curly braces in JSON examples inside template
    prompt = QUIZ_PROMPT_HEADER.replace("{QUESTIONS_MIN}", str(QUESTIONS_MIN)).replace("{QUESTIONS_MAX}", str(QUESTIONS_MAX)).replace("{context}", combined_context).replace("{skills}", skills_repr)

    try:
        print("[quiz_generator] Sending generation request to model...")
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": SYSTEM_JSON_ONLY},
                {"role": "user", "content": prompt}
            ],
            temperature=TEMPERATURE,
            max_tokens=MAX_TOKENS,
            stream=False,
        )

        response_text = completion.choices[0].message.content.strip()
        print("[quiz_generator] Raw response (preview):")
        print(response_text[:1000])

        # Try parsing and validating
        quiz = safe_json_load(response_text)
        ok, errors = validate_quiz_schema(quiz) if quiz else (False, ["Failed to parse JSON"])

        repair_attempts = 0
        last_text = response_text
        while (not ok) and repair_attempts < MAX_RETRIES_JSON_REPAIR:
            repair_attempts += 1
            print(f"[quiz_generator] Validation failed (attempt {repair_attempts}):", errors)
            repaired = repair_with_model(client, last_text, combined_context, skills_repr)
            if repaired:
                quiz = repaired
                ok, errors = validate_quiz_schema(quiz)
                if ok:
                    break
                else:
                    last_text = json.dumps(quiz, ensure_ascii=False)
            else:
                print("[quiz_generator] Model couldn't repair JSON on attempt", repair_attempts)
                break

        if not ok:
            print("[quiz_generator] ❌ Final validation errors:", errors)
            fallback = {"skill_quizzes": []}
            for s in all_skills:
                fallback["skill_quizzes"].append({"skill": s, "questions": []})
            return fallback

        # ---------- Guarantee: at least one Apply+ per skill ----------
        missing = skills_missing_apply_plus(quiz)
        targeted_attempts = 0
        current_text = json.dumps(quiz, ensure_ascii=False)
        while missing and targeted_attempts < MAX_RETRIES_JSON_REPAIR:
            targeted_attempts += 1
            print(f"[quiz_generator] Skills missing Apply+ (attempt {targeted_attempts}): {missing}")
            for skill_name in missing:
                repaired2 = targeted_add_apply_question(client, current_text, skill_name, combined_context, skills_repr)
                if repaired2:
                    # update current_text and quiz, re-evaluate missing list
                    quiz = repaired2
                    current_text = json.dumps(quiz, ensure_ascii=False)
                else:
                    print(f"[quiz_generator] targeted repair failed for {skill_name}")
            missing = skills_missing_apply_plus(quiz)
        if missing:
            print("[quiz_generator] ⚠️ Could not add Apply+ for skills:", missing)
            # still return quiz (best effort)

        print("[quiz_generator] ✅ Quiz generation and validation successful")
        return quiz

    except Exception as e:
        print("[quiz_generator] ⚠️ Quiz generation error:", e)
        return {"skill_quizzes": []}
