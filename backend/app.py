from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import uuid
from services.pdf_extractor import extract_text_from_pdf
from services.skills_extractor import extract_skills
from services.quiz_generator import generate_quiz_for_skills
from services.grader import grade_answers_and_score
from services.recommender import recommend_courses
from services.groq_client import get_groq_client
"""
app = Flask(__name__)
CORS(app)

# In-memory stores for demo purposes (replace with DB in production)
SESSIONS = {}
QUIZZES = {}
RESULTS = {}


@app.route('/', methods=['GET'])
def root():
    return jsonify({
        "message": "CV Quiz API running",
        "endpoints": [
            "/api/health",
            "/api/upload-cv (POST multipart/form-data)",
            "/api/generate-quiz (POST JSON)",
            "/api/submit-answers (POST JSON)",
            "/api/debug/groq",
        ]
    })


@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({"status": "ok"})


@app.route('/api/debug/groq', methods=['GET'])
def debug_groq():
    key = os.getenv("GROQ_API_KEY")
    key_present = bool(key)
    masked = None
    if key:
        masked = key[:4] + "***" + key[-4:]

    ok = False
    error = None
    response_sample = None
    try:
        client = get_groq_client()
        completion = client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=[
                {"role": "system", "content": "Return JSON only."},
                {"role": "user", "content": '{"ping": true}'}
            ],
            temperature=0,
            max_tokens=64,
            stream=False,
        )
        raw = completion.choices[0].message.content.strip()
        response_sample = raw[:200]
        ok = True
    except Exception as e:
        error = str(e)
    return jsonify({
        "key_present": key_present,
        "key_masked": masked,
        "ok": ok,
        "error": error,
        "response_sample": response_sample,
    })


@app.route('/api/upload-cv', methods=['POST'])
def upload_cv():
    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "Empty filename"}), 400

    session_id = str(uuid.uuid4())
    # Save to temp directory
    temp_dir = os.path.join(os.path.dirname(__file__), 'tmp')
    os.makedirs(temp_dir, exist_ok=True)
    file_path = os.path.join(temp_dir, f"{session_id}_{file.filename}")
    file.save(file_path)

    try:
        cv_text = extract_text_from_pdf(file_path)
    except Exception as exc:
        return jsonify({"error": f"Failed to read PDF: {exc}"}), 400

    # Try to extract skills; if it fails, return empty structure instead of 500
    try:
        skills = extract_skills(cv_text)
        if not isinstance(skills, dict):
            skills = {"technical_skills": [], "soft_skills": [], "cognitive_skills": []}
    except Exception as e:
        print(f"[upload_cv] skills extraction failed: {e}")
        skills = {"technical_skills": [], "soft_skills": [], "cognitive_skills": []}

    SESSIONS[session_id] = {
        "cv_path": file_path,
        "cv_text": cv_text,
        "skills": skills,
    }

    debug = {
        "cv_text_len": len(cv_text or ""),
        "model_response_sample": (skills.get("debug", {}) or {}).get("model_response_sample"),
    }

    return jsonify({
        "session_id": session_id,
        "skills": {k: v for k, v in skills.items() if k != "debug"},
        "debug": debug,
    })


@app.route('/api/generate-quiz', methods=['POST'])
def generate_quiz():
    data = request.get_json(silent=True) or {}
    session_id = data.get('session_id')
    selected_skills = data.get('skills')  # optional override
    num_questions_per_skill = int(data.get('num_questions_per_skill', 2))
    config = data.get('config')  # optional per-category counts/types

    if not session_id or session_id not in SESSIONS:
        return jsonify({"error": "Invalid or missing session_id"}), 400

    skills_source = selected_skills or SESSIONS[session_id].get('skills', {})

    # Build categorized skills
    categorized = {
        "technical_skills": [s.get("name") for s in skills_source.get("technical_skills", []) if s.get("name")],
        "soft_skills": [s.get("name") for s in skills_source.get("soft_skills", []) if s.get("name")],
        "cognitive_skills": [s.get("name") for s in skills_source.get("cognitive_skills", []) if s.get("name")],
    }

    print(f"[generate_quiz] categorized skills: {categorized}")
    
    # Fallback: if no skills extracted, use default skills
    if not any(categorized.values()):
        print("[generate_quiz] No skills extracted, using fallback skills")
        categorized = {
            "technical_skills": ["Python", "Problem Solving"],
            "soft_skills": ["Teamwork", "Communication"],
            "cognitive_skills": ["Critical Thinking", "Analytical Skills"],
        }

    for k in list(categorized.keys()):
        categorized[k] = categorized[k][:5]

    try:
        quiz = generate_quiz_for_skills(categorized, num_questions_per_skill=num_questions_per_skill, config=config)
    except Exception as exc:
        return jsonify({"error": f"Quiz generation failed: {exc}"}), 500

    quiz_id = str(uuid.uuid4())
    QUIZZES[quiz_id] = {
        "session_id": session_id,
        "quiz": quiz
    }

    return jsonify({
        "quiz_id": quiz_id,
        "quiz": quiz
    })


@app.route('/api/submit-answers', methods=['POST'])
def submit_answers():
    data = request.get_json(silent=True) or {}
    quiz_id = data.get('quiz_id')
    answers = data.get('answers')

    print("[submit-answers] received type:", type(answers).__name__)
    if isinstance(answers, list):
        print("[submit-answers] answers length:", len(answers))
        if answers[:1]:
            print("[submit-answers] first answer sample:", {k: answers[0].get(k) for k in ['skill','bloom_level','question','answer'] if isinstance(answers[0], dict)})

    if not isinstance(answers, list):
        return jsonify({"error": f"answers must be a list, got {type(answers).__name__}"}), 400
    if not answers:
        return jsonify({"error": "answers must be a non-empty list"}), 400

    quiz = QUIZZES.get(quiz_id, {}).get('quiz')
    if not quiz:
        return jsonify({"error": "Invalid or missing quiz_id"}), 400

    try:
        grading = grade_answers_and_score(quiz, answers)
    except Exception as exc:
        return jsonify({"error": f"Grading failed: {exc}"}), 500

    session_id = QUIZZES[quiz_id]['session_id']
    skills = SESSIONS.get(session_id, {}).get('skills', {})
    recs = recommend_courses(skills, grading)

    result = {
        "grading": grading,
        "recommendations": recs
    }

    RESULTS[quiz_id] = result
    return jsonify(result)


if __name__ == '__main__':
    port = int(os.getenv('PORT', '5000'))
    app.run(host='0.0.0.0', port=port, debug=True)


"""