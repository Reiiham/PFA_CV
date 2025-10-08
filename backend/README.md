Backend (Flask)

Setup
- Python 3.12+ recommended
- Create virtualenv and install dependencies:

```
python -m venv venv
venv\Scripts\activate  # Windows
pip install python-dotenv
pip install "httpx<0.28" # probleme de proxies 
pip install -r backend/requirements.txt
```

Environment
- Set GROQ_API_KEY in your environment .env

Run
```
python backend/app.py
```

API
- POST /api/upload-cv: multipart form-data with field `file` (PDF). Returns `session_id` and extracted `skills`.
- POST /api/generate-quiz: JSON { session_id, skills?: ["Python", ...], num_questions_per_skill?: 2 } returns `quiz_id` and `quiz` with `time_per_question_sec`.
- POST /api/submit-answers: JSON { quiz_id, answers: [{ skill, bloom_level, question, answer }] } returns grading and course recommendations.

