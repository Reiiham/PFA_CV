# main.py — clean, lazy, modular version
from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Form
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict, Any
import psycopg2
from psycopg2.extras import RealDictCursor
import jwt
import bcrypt
from datetime import datetime, timedelta
import os
import uuid
import json

# Import our service modules (lazy Groq versions)
from services.skills_extractor import extract_skills
from services.quiz_generator import generate_quiz_for_skills
from services.grader import grade_answers_and_score
from services.recommender import recommend_courses
from services.pdf_extractor import extract_text_from_pdf

# ==================== CONFIG ====================
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
#load_dotenv(os.path.join(PROJECT_ROOT, '.env'))
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5432/quiz_db")
JWT_SECRET = os.getenv("JWT_SECRET", "your-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours

app = FastAPI(title="AI CV Quiz Backend", version="1.0")
security = HTTPBearer()

# CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==================== DATABASE ====================
def get_db():
    """PostgreSQL connection generator"""
    conn = None
    try:
        dsn = DATABASE_URL
        if not dsn:
            raise HTTPException(status_code=500, detail="Database DSN not set")
        conn = psycopg2.connect(dsn, cursor_factory=RealDictCursor)
        yield conn
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database connection failed: {e}")
    finally:
        if conn:
            conn.close()

# ==================== MODELS ====================
class UserRegister(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    password: str
    role: str  # 'candidate' | 'hr'
    occupation: Optional[str] = None
    birth_date: Optional[str] = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    user: dict

class QuizInvitation(BaseModel):
    candidate_email: EmailStr
    focus_skills: Optional[List[str]] = None
    custom_instructions: Optional[str] = None

class QuizToken(BaseModel):
    token: str

# ==================== AUTH UTILITIES ====================
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)

def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security), conn=Depends(get_db)):
    token = credentials.credentials
    payload = decode_token(token)
    user_id = payload.get("sub")

    with conn.cursor() as cur:
        cur.execute("SELECT id, first_name, last_name, email, role FROM users WHERE id = %s", (user_id,))
        user = cur.fetchone()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return dict(user)

# ==================== ROUTES ====================

@app.get("/")
async def root():
    return {"status": "ok", "message": "Quiz Platform API running ✅"}

# ---------- AUTH ----------
@app.post("/api/auth/register", response_model=TokenResponse)
async def register(user: UserRegister, conn=Depends(get_db)):
    with conn.cursor() as cur:
        cur.execute("SELECT id FROM users WHERE email = %s", (user.email,))
        if cur.fetchone():
            raise HTTPException(status_code=400, detail="Email already registered")

        user_id = str(uuid.uuid4())
        password_hash = hash_password(user.password)
        cur.execute("""
            INSERT INTO users (id, first_name, last_name, email, password_hash, role, occupation, birth_date)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id, first_name, last_name, email, role
        """, (user_id, user.first_name, user.last_name, user.email, password_hash, user.role, user.occupation, user.birth_date))

        new_user = dict(cur.fetchone())
        conn.commit()
        token = create_access_token({"sub": new_user["id"], "role": new_user["role"]})
        return {"access_token": token, "token_type": "bearer", "user": new_user}

@app.post("/api/auth/login", response_model=TokenResponse)
async def login(credentials: UserLogin, conn=Depends(get_db)):
    with conn.cursor() as cur:
        cur.execute("SELECT id, first_name, last_name, email, role, password_hash FROM users WHERE email = %s", (credentials.email,))
        user = cur.fetchone()
        if not user or not verify_password(credentials.password, user["password_hash"]):
            raise HTTPException(status_code=401, detail="Invalid email or password")

        user_data = {k: v for k, v in user.items() if k != "password_hash"}
        token = create_access_token({"sub": user_data["id"], "role": user_data["role"]})
        return {"access_token": token, "token_type": "bearer", "user": user_data}

@app.get("/api/auth/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    return current_user

# ---------- CANDIDATE ----------
# ---------- CANDIDATE ----------

import os

@app.post("/api/candidate/upload-cv")
async def upload_cv(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
    conn=Depends(get_db)
):
    """Candidate uploads CV, AI extracts skills, stores them, then generates quiz from DB skills."""
    if current_user["role"] != "candidate":
        raise HTTPException(status_code=403, detail="Only candidates can upload CVs")

    temp_path = None
    try:
        # ============ Save file temporarily ============
        os.makedirs("tmp", exist_ok=True)
        safe_name = f"{uuid.uuid4().hex}_{os.path.basename(file.filename)}"
        temp_path = os.path.join("tmp", safe_name)
        with open(temp_path, "wb") as f:
            f.write(await file.read())

        # ============ Extract text depending on file type ============
        cv_text = ""
        file_name = file.filename.lower()

        if file_name.endswith(".pdf"):
            print("[upload_cv] Extracting text from PDF...")
            cv_text = extract_text_from_pdf(temp_path)

        elif file_name.endswith(".txt"):
            print("[upload_cv] Reading text file...")
            with open(temp_path, "r", encoding="utf-8", errors="ignore") as f:
                cv_text = f.read()

        else:
            raise HTTPException(status_code=400, detail="Unsupported file format. Please upload PDF, TXT, or DOCX.")

        cv_text = cv_text.strip()
        if not cv_text or len(cv_text) < 50:
            raise HTTPException(status_code=400, detail="Could not extract enough text from CV. Try another format.")

        # ============ AI Processing: extract skills ============
        print("[upload_cv] Extracting skills with AI...")
        extracted = extract_skills(cv_text)  # returns dict with technical_skills/soft_skills/cognitive_skills

        # Simplify the structure we store: keep the full extracted object, but also make names-only for generation
        categorized_from_extracted = {
            "technical": [s["name"] for s in extracted.get("technical_skills", [])],
            "soft": [s["name"] for s in extracted.get("soft_skills", [])],
            "cognitive": [s["name"] for s in extracted.get("cognitive_skills", [])],
        }

        # ============ Upsert candidate_skills INTO DB BEFORE generation ============
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO candidate_skills (user_id, skills, last_updated)
                    VALUES (%s, %s, NOW())
                    ON CONFLICT (user_id) DO UPDATE
                    SET skills = EXCLUDED.skills,
                        last_updated = NOW()
                """, (current_user["id"], json.dumps(extracted)))
                conn.commit()
            print("[upload_cv] ✅ candidate_skills upserted into DB")
        except Exception as e:
            # non fatal but log and continue (we still attempt generation using extracted)
            print("[upload_cv] ⚠️ Failed to upsert candidate_skills:", e)

        # ============ Now load skills from DB to ensure we generate from stored skills ============
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT skills FROM candidate_skills WHERE user_id = %s", (current_user["id"],))
                row = cur.fetchone()
                db_skills_obj = row["skills"] if row else extracted
        except Exception as e:
            print("[upload_cv] ⚠️ Failed to read candidate_skills from DB, falling back to extracted skills:", e)
            db_skills_obj = extracted

        # db_skills_obj expected to be the same shape as 'extracted' (technical_skills, ...)
        # Build categorized list (names-only) from DB object
        categorized_skills = {
            "technical": [s["name"] for s in db_skills_obj.get("technical_skills", [])],
            "soft": [s["name"] for s in db_skills_obj.get("soft_skills", [])],
            "cognitive": [s["name"] for s in db_skills_obj.get("cognitive_skills", [])],
        }

        print("[upload_cv] Generating quiz based on skills from DB (or extracted fallback)...")
        quiz_data = generate_quiz_for_skills(categorized_skills)

        # ============ Save quiz session ============
        session_id = str(uuid.uuid4())
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO quiz_sessions (id, user_id, metadata, start_time)
                VALUES (%s, %s, %s, NOW())
            """, (
                session_id,
                current_user["id"],
                json.dumps({
                    "skills": db_skills_obj,
                    "quiz": quiz_data,
                    "file_name": file.filename
                })
            ))
            conn.commit()

        print("[upload_cv] ✅ Upload and quiz generation complete.")
        return {"session_id": session_id, "skills": db_skills_obj, "quiz": quiz_data}

    except HTTPException:
        raise

    except Exception as e:
        import traceback
        print("\n===== ⚠️ CV Upload Error Traceback =====")
        traceback.print_exc()
        print("========================================\n")
        raise HTTPException(status_code=500, detail=f"CV processing failed: {str(e)}")

    finally:
        # Cleanup temporary file
        try:
            if temp_path and os.path.exists(temp_path):
                os.remove(temp_path)
        except Exception:
            pass

@app.post("/api/candidate/generate-quiz")
async def generate_quiz_from_db(
    payload: Optional[Dict[str, Any]] = None,
    current_user: dict = Depends(get_current_user),
    conn=Depends(get_db)
):
    """
    Force generation of quiz for the current candidate using skills stored in DB.
    Optional payload:
      { "focus_skills": { "technical": [...], "soft": [...], "cognitive": [...] } }
    """
    if current_user.get("role") != "candidate":
        raise HTTPException(status_code=403, detail="Only candidates can generate quizzes")

    try:
        # 1) read stored skills
        with conn.cursor() as cur:
            cur.execute("SELECT skills FROM candidate_skills WHERE user_id = %s", (current_user["id"],))
            row = cur.fetchone()
            if not row or not row.get("skills"):
                raise HTTPException(status_code=404, detail="No stored skills found. Upload CV first.")

            stored_skills = row["skills"]

        # 2) optionally apply focus/override from payload (HR invite case or manual)
        user_requested = payload.get("focus_skills") if payload and isinstance(payload, dict) else None
        if user_requested:
            # if payload provides a dict of lists, use that to override (simple policy)
            limited_skills = {
                "technical": user_requested.get("technical", [s["name"] for s in stored_skills.get("technical_skills", [])]),
                "soft": user_requested.get("soft", [s["name"] for s in stored_skills.get("soft_skills", [])]),
                "cognitive": user_requested.get("cognitive", [s["name"] for s in stored_skills.get("cognitive_skills", [])]),
            }
        else:
            limited_skills = {
                "technical": [s["name"] for s in stored_skills.get("technical_skills", [])],
                "soft": [s["name"] for s in stored_skills.get("soft_skills", [])],
                "cognitive": [s["name"] for s in stored_skills.get("cognitive_skills", [])],
            }

        # (optional) here you can implement selection strategy: top N, weighting by level, etc.
        # For now keep generator's internal limit logic (it slices to 2 per category).

        # 3) generate quiz
        quiz = generate_quiz_for_skills(limited_skills)

        # 4) save session
        session_id = str(uuid.uuid4())
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO quiz_sessions (id, user_id, metadata, start_time)
                VALUES (%s, %s, %s, NOW())
            """, (
                session_id,
                current_user["id"],
                json.dumps({"skills": stored_skills, "quiz": quiz, "generated_from_db": True})
            ))
            conn.commit()

        return {"ok": True, "session_id": session_id, "quiz": quiz, "skills": stored_skills}

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Generation failed: {e}")


#Skills 
@app.get("/api/candidate/skills")
async def get_candidate_skills(current_user: dict = Depends(get_current_user), conn=Depends(get_db)):
    if current_user["role"] != "candidate":
        raise HTTPException(status_code=403, detail="Only candidates can access their skills")

    with conn.cursor() as cur:
        cur.execute("SELECT skills FROM candidate_skills WHERE user_id = %s", (current_user["id"],))
        row = cur.fetchone()
        if not row:
            return {"skills": None, "message": "No stored skills found. Please upload a CV."}
        return {"skills": row["skills"]}

class QuizSubmission(BaseModel):
    session_id: str
    answers: List[Dict[str, Any]]
# ---------- QUIZ SUBMISSION ----------

# @app.post("/api/quiz/submit")
# async def submit_quiz(
#     submission: QuizSubmission,
#     current_user: dict = Depends(get_current_user),
#     conn=Depends(get_db)
# ):
#     try:
#         session_id = submission.session_id
#         answers = submission.answers

#         with conn.cursor() as cur:
#             cur.execute("SELECT metadata FROM quiz_sessions WHERE id = %s", (session_id,))
#             session = cur.fetchone()

#             if not session:
#                 raise HTTPException(status_code=404, detail="Session not found")

#             metadata = session["metadata"]

#             # ✅ Ensure proper structure for metadata
#             if isinstance(metadata, str):
#                 metadata = json.loads(metadata)

#             quiz_data = metadata.get("quiz", {})
#             skills_data = metadata.get("skills", {})

#             # grading = grade_answers_and_score(quiz_data, answers)
#             # recommendations = recommend_courses(skills_data, grading, use_ai=True)

#             # cur.execute("""
#             #     UPDATE quiz_sessions 
#             #     SET end_time = NOW(),
#             #         total_score = %s,
#             #         cognitive_score = %s,
#             #         metadata = metadata || %s::jsonb
#             #     WHERE id = %s
#             # """, (
#             #     grading["overall_score"],
#             #     grading["cognitive_score"],
#             #     json.dumps({
#             #         "grading": grading,
#             #         "recommendations": recommendations
#             #     }),
#             #     session_id
#             # ))
#             # conn.commit()
#             grading = grade_answers_and_score(quiz_data, answers)
#             recommendations = recommend_courses(skills_data, grading, use_ai=True)

#             # Persist grading & recommendations into quiz_sessions metadata (existing)
#             cur.execute("""
#                 UPDATE quiz_sessions 
#                 SET end_time = NOW(),
#                     total_score = %s,
#                     cognitive_score = %s,
#                     metadata = metadata || %s::jsonb
#                 WHERE id = %s
#             """, (
#                 grading["overall_score"],
#                 grading["cognitive_score"],
#                 json.dumps({
#                     "grading": grading,
#                     "recommendations": recommendations
#                 }),
#                 session_id
#             ))

#             # --- Persist into candidate profile (candidate_skills JSON column) ---
#             # We store an object with timestamp, grading summary and top recommendations
#             try:
#                 persist_obj = {
#                     "last_grading": {
#                         "overall_score": grading["overall_score"],
#                         "cognitive_score": grading["cognitive_score"],
#                         "timestamp": datetime.utcnow().isoformat() + "Z"
#                     },
#                     # store up to 7 recommendations (same shape as recommender returns)
#                     "last_recommendations": recommendations[:7],
#                     # optionally store corrections and corrected_quiz if grader provided them
#                     "last_corrections": grading.get("corrections", []),
#                     "last_corrected_quiz": grading.get("corrected_quiz", {})
#                 }
#                 # merge into the existing skills JSON
#                 cur.execute("""
#                     INSERT INTO candidate_skills (user_id, skills)
#                     VALUES (%s, %s)
#                     ON CONFLICT (user_id) DO UPDATE
#                     SET skills = candidate_skills.skills || EXCLUDED.skills, last_updated = NOW()
#                 """, (current_user["id"], json.dumps(persist_obj)))
#             except Exception as e:
#                 print("[quiz_submit] ⚠️ Failed to persist into candidate_skills:", e)

#             conn.commit()


#         print(f"[quiz_submit] ✅ Grading complete for session {session_id}")
#         return {"grading": grading, "recommendations": recommendations}

#     except Exception as e:
#         import traceback
#         traceback.print_exc()
#         raise HTTPException(status_code=500, detail=f"Quiz submission failed: {str(e)}")

@app.post("/api/quiz/submit")
async def submit_quiz(
    submission: QuizSubmission,
    current_user: dict = Depends(get_current_user),
    conn=Depends(get_db)
):
    try:
        session_id = submission.session_id
        answers = submission.answers or []

        print(f"[quiz_submit] Received submission for session={session_id} by user={current_user['id']}")
        print(f"[quiz_submit] Raw answers count: {len(answers)}")

        with conn.cursor() as cur:
            cur.execute("SELECT metadata FROM quiz_sessions WHERE id = %s", (session_id,))
            session = cur.fetchone()

            if not session:
                raise HTTPException(status_code=404, detail="Session not found")

            metadata = session["metadata"]
            if isinstance(metadata, str):
                metadata = json.loads(metadata)

            quiz_data = metadata.get("quiz", {})
            skills_data = metadata.get("skills", {})

            # If frontend sent no answers, build an empty answer object for every question so grader can still run.
            if not answers:
                print("[quiz_submit] No answers submitted; constructing empty answers from stored quiz for grading.")
                constructed = []
                for block in quiz_data.get("skill_quizzes", []):
                    for q in block.get("questions", []):
                        constructed.append({
                            "question": q.get("question"),
                            "answer": "",                # empty answer
                            "is_correct": None,
                            "time_spent_sec": 0
                        })
                answers = constructed
                print(f"[quiz_submit] Constructed {len(answers)} empty answers for grading.")

            # Debug log the first few answers
            try:
                print("[quiz_submit] Sample answers:", json.dumps(answers[:5], ensure_ascii=False))
            except Exception:
                print("[quiz_submit] Could not JSON serialize sample answers for logging.")

            grading = grade_answers_and_score(quiz_data, answers)
            # ensure grading is a dict with expected keys
            if not isinstance(grading, dict):
                print("[quiz_submit] Warning: grader returned non-dict; coercing to empty grading.")
                grading = {"overall_score": 0.0, "cognitive_score": 0.0, "corrections": []}

            recommendations = recommend_courses(skills_data, grading, use_ai=True)

            # Update session: store grading + recommendations in metadata; set end_time and scores
            cur.execute("""
                UPDATE quiz_sessions 
                SET end_time = NOW(),
                    total_score = %s,
                    cognitive_score = %s,
                    metadata = metadata || %s::jsonb
                WHERE id = %s
            """, (
                grading.get("overall_score", 0.0),
                grading.get("cognitive_score", 0.0),
                json.dumps({
                    "grading": grading,
                    "recommendations": recommendations
                }),
                session_id
            ))
            conn.commit()

        print(f"[quiz_submit] ✅ Grading complete for session {session_id} -> overall={grading.get('overall_score')} cognitive={grading.get('cognitive_score')}")
        return {"grading": grading, "recommendations": recommendations}

    except HTTPException:
        raise

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Quiz submission failed: {str(e)}")


@app.get("/api/candidate/latest-session")
async def get_latest_session(current_user: dict = Depends(get_current_user), conn=Depends(get_db)):
    """
    Retourne la dernière session de quiz générée pour le candidat courant.
    Response: { "session_id": "...", "quiz": {...}, "skills": {...}, "start_time": "..."}
    """
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, metadata, start_time, end_time
                FROM quiz_sessions
                WHERE user_id = %s
                ORDER BY COALESCE(start_time, now()) DESC
                LIMIT 1
            """, (current_user["id"],))
            row = cur.fetchone()
            if not row:
                return {"found": False, "message": "No session for this user"}
            session_id = row["id"]
            metadata = row["metadata"]
            # metadata may be JSON/dict or string -> ensure dict
            if isinstance(metadata, str):
                try:
                    metadata = json.loads(metadata)
                except Exception:
                    # best-effort: return raw metadata string as 'raw_metadata'
                    return {"found": True, "session_id": session_id, "raw_metadata": metadata, "start_time": row.get("start_time"), "end_time": row.get("end_time")}
            # metadata is dict
            quiz = metadata.get("quiz")
            skills = metadata.get("skills")
            return {
                "found": True,
                "session_id": session_id,
                "quiz": quiz,
                "skills": skills,
                "start_time": row.get("start_time"),
                "end_time": row.get("end_time")
            }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to fetch latest session: {e}")
    

#ajout 
@app.post("/api/quiz/start")
async def start_quiz(current_user: dict = Depends(get_current_user), conn=Depends(get_db)):
    """
    Start a new quiz for the current candidate:
    - load skills from candidate_skills (DB)
    - generate a new quiz using generate_quiz_for_skills(...)
    - insert a new quiz_sessions row with metadata containing skills & quiz
    - return { session_id, quiz }
    """
    if current_user["role"] != "candidate":
        raise HTTPException(status_code=403, detail="Only candidates can start a quiz")

    try:
        with conn.cursor() as cur:
            # fetch stored skills
            cur.execute("SELECT skills FROM candidate_skills WHERE user_id = %s", (current_user["id"],))
            row = cur.fetchone()
            if not row or not row.get("skills"):
                raise HTTPException(status_code=400, detail="No skills found for this candidate. Please upload a CV first.")

            # skills may be JSON/str; ensure python object
            skills_raw = row["skills"]
            if isinstance(skills_raw, str):
                try:
                    skills_obj = json.loads(skills_raw)
                except Exception:
                    skills_obj = {}
            else:
                skills_obj = skills_raw

            # Build categorized_skills in the expected format: { "technical": [names], "soft": [...], "cognitive": [...] }
            categorized_skills = {
                "technical": [],
                "soft": [],
                "cognitive": []
            }
            # if the stored skills follow your extractor schema (lists of dicts with 'name' and 'level')
            for cat in ("technical_skills", "soft_skills", "cognitive_skills"):
                items = skills_obj.get(cat) if isinstance(skills_obj, dict) else None
                if isinstance(items, list):
                    names = [ (it.get("name") if isinstance(it, dict) else it) for it in items if it ]
                    if cat == "technical_skills":
                        categorized_skills["technical"] = names
                    elif cat == "soft_skills":
                        categorized_skills["soft"] = names
                    elif cat == "cognitive_skills":
                        categorized_skills["cognitive"] = names

            # Fallback: if skills were stored as simple lists per category
            if not any(categorized_skills.values()) and isinstance(skills_obj, dict):
                # try keys "technical","soft","cognitive"
                for k in ("technical","soft","cognitive"):
                    val = skills_obj.get(k)
                    if isinstance(val, list):
                        categorized_skills[k] = [ (x.get("name") if isinstance(x, dict) else x) for x in val ]

            print(f"[start_quiz] categorized_skills for user {current_user['id']}: { {k: len(v) for k,v in categorized_skills.items()} }")

            # Generate quiz (this is the call that can be slow / calls LLM)
            quiz = generate_quiz_for_skills(categorized_skills)

            # Create new quiz session row
            session_id = str(uuid.uuid4())
            metadata = {
                "skills": skills_obj,
                "quiz": quiz,
                "generated_at": datetime.utcnow().isoformat() + "Z"
            }

            cur.execute("""
                INSERT INTO quiz_sessions (id, user_id, metadata, start_time)
                VALUES (%s, %s, %s, NOW())
            """, (session_id, current_user["id"], json.dumps(metadata)))
            conn.commit()

            print(f"[start_quiz] New session created {session_id} for user {current_user['id']} with {len(quiz.get('skill_quizzes', []))} skill blocks")
            return {"session_id": session_id, "quiz": quiz}

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to start quiz: {str(e)}")
    
from fastapi import BackgroundTasks

FRONTEND_BASE = os.getenv("FRONTEND_BASE", "http://localhost:5173")  # used to generate shareable link

@app.post("/api/hr/upload-candidate-cv")
async def hr_upload_candidate_cv(
    candidate_email: str = Form(...),
    file: UploadFile = File(...),
    focus_skills: Optional[str] = Form(None),  # optional comma-separated string
    current_user: dict = Depends(get_current_user),
    conn=Depends(get_db)
):
    """
    HR uploads a candidate CV and optionally specifies focus_skills (comma-separated).
    This creates/ensures an hr_candidate row, generates quiz (using skills extracted or focus),
    and inserts a quiz_sessions row linked to hr_candidate_id. Returns quiz_link for sharing.
    """
    if current_user.get("role") != "hr":
        raise HTTPException(status_code=403, detail="Only HR can upload candidate CVs")

    temp_path = None
    try:
        # save file temp
        os.makedirs("tmp", exist_ok=True)
        safe_name = f"{uuid.uuid4().hex}_{os.path.basename(file.filename)}"
        temp_path = os.path.join("tmp", safe_name)
        with open(temp_path, "wb") as f:
            f.write(await file.read())

        # extract text (reuse your existing logic)
        file_name = file.filename.lower()
        if file_name.endswith(".pdf"):
            cv_text = extract_text_from_pdf(temp_path)
        elif file_name.endswith(".txt"):
            with open(temp_path, "r", encoding="utf-8", errors="ignore") as f:
                cv_text = f.read()
        else:
            raise HTTPException(status_code=400, detail="Unsupported file format.")

        cv_text = (cv_text or "").strip()
        if not cv_text or len(cv_text) < 50:
            raise HTTPException(status_code=400, detail="Could not extract enough text from CV.")

        # extract skills using your existing function
        extracted = extract_skills(cv_text)  # returns dict with technical_skills/soft_skills/cognitive_skills

        # upsert hr_candidate
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM hr_candidates WHERE lower(email) = lower(%s)", (candidate_email,))
            row = cur.fetchone()
            if row:
                hr_candidate_id = row["id"]
            else:
                hr_candidate_id = str(uuid.uuid4())
                cur.execute("""
                    INSERT INTO hr_candidates (id, email, first_name, last_name, created_by)
                    VALUES (%s, %s, %s, %s, %s)
                """, (hr_candidate_id, candidate_email, None, None, current_user["id"]))
                conn.commit()

        # Build categorized skills (names only) — allow HR-provided focus override
        focus = None
        if focus_skills:
            focus = [s.strip() for s in focus_skills.split(",") if s.strip()]

        categorized = {
            "technical": [s["name"] for s in extracted.get("technical_skills", [])],
            "soft": [s["name"] for s in extracted.get("soft_skills", [])],
            "cognitive": [s["name"] for s in extracted.get("cognitive_skills", [])],
        }
        if focus:
            # simple strategy: put all focus into technical if match, else into top category
            # Here we just override technical for simplicity
            categorized["technical"] = focus

        # generate quiz
        quiz = generate_quiz_for_skills(categorized)

        # create quiz_session (user_id=NULL because candidate has no account)
        session_id = str(uuid.uuid4())
        metadata = {
            "candidate_email": candidate_email,
            "skills": extracted,
            "quiz": quiz,
            "created_by_hr": current_user["id"]
        }

        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO quiz_sessions (id, user_id, hr_candidate_id, metadata, start_time)
                VALUES (%s, NULL, %s, %s, NOW())
            """, (session_id, hr_candidate_id, json.dumps(metadata)))
            conn.commit()

        quiz_link = f"{FRONTEND_BASE}/invite/{session_id}"
        return {"ok": True, "session_id": session_id, "quiz_link": quiz_link, "hr_candidate_id": hr_candidate_id}

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"HR upload failed: {e}")
    finally:
        if temp_path and os.path.exists(temp_path):
            try: os.remove(temp_path)
            except: pass


@app.post("/api/hr/create-invitation")
async def hr_create_invitation(payload: QuizInvitation, current_user: dict = Depends(get_current_user), conn=Depends(get_db)):
    """
    HR creates an invitation (without uploading CV file). Payload contains candidate_email and optional focus_skills.
    Creates hr_candidate if needed, generates quiz (possibly empty skills -> generator will handle), inserts quiz_session, returns invitation link.
    """
    if current_user.get("role") != "hr":
        raise HTTPException(status_code=403, detail="Only HR can create invitations")

    candidate_email = payload.candidate_email
    focus_skills = payload.focus_skills or []

    try:
        # ensure hr_candidate exists
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM hr_candidates WHERE lower(email) = lower(%s)", (candidate_email,))
            r = cur.fetchone()
            if r:
                hr_candidate_id = r["id"]
            else:
                hr_candidate_id = str(uuid.uuid4())
                cur.execute("""
                    INSERT INTO hr_candidates (id, email, first_name, last_name, created_by)
                    VALUES (%s, %s, %s, %s, %s)
                """, (hr_candidate_id, candidate_email, None, None, current_user["id"]))
                conn.commit()

        # Build categorized_skills from focus_skills if provided, else use empty lists
        categorized = {
            "technical": focus_skills if focus_skills else [],
            "soft": [],
            "cognitive": []
        }

        quiz = generate_quiz_for_skills(categorized)

        session_id = str(uuid.uuid4())
        metadata = {
            "candidate_email": candidate_email,
            "skills": categorized,
            "quiz": quiz,
            "created_by_hr": current_user["id"],
            "invitation_instructions": payload.custom_instructions
        }

        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO quiz_sessions (id, user_id, hr_candidate_id, metadata, start_time)
                VALUES (%s, NULL, %s, %s, NOW())
            """, (session_id, hr_candidate_id, json.dumps(metadata)))
            conn.commit()

        invitation_link = f"{FRONTEND_BASE}/invite/{session_id}"
        return {"ok": True, "session_id": session_id, "invitation_link": invitation_link}

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Create invitation failed: {e}")


@app.get("/api/hr/candidates")
async def hr_list_candidates(current_user: dict = Depends(get_current_user), conn=Depends(get_db)):
    """
    Return list of HR-created candidates and their latest session(s).
    """
    if current_user.get("role") != "hr":
        raise HTTPException(status_code=403, detail="Only HR can list candidates")
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT hc.id AS hr_candidate_id,
                       hc.email,
                       hc.first_name,
                       hc.last_name,
                       qs.id AS session_id,
                       qs.start_time,
                       qs.end_time,
                       qs.total_score,
                       qs.cognitive_score,
                       qs.metadata
                FROM hr_candidates hc
                LEFT JOIN quiz_sessions qs ON qs.hr_candidate_id = hc.id
                WHERE hc.created_by = %s
                ORDER BY COALESCE(qs.start_time, hc.created_at) DESC
                LIMIT 500
            """, (current_user["id"],))
            rows = cur.fetchall()

        out = []
        for r in rows:
            meta = r.get("metadata")
            if isinstance(meta, str):
                try:
                    meta = json.loads(meta)
                except:
                    meta = {}
            out.append({
                "hr_candidate_id": r.get("hr_candidate_id"),
                "session_id": r.get("session_id"),
                "email": r.get("email"),
                "first_name": r.get("first_name"),
                "last_name": r.get("last_name"),
                "start_time": r.get("start_time"),
                "end_time": r.get("end_time"),
                "total_score": r.get("total_score"),
                "cognitive_score": r.get("cognitive_score"),
                "metadata": meta
            })
        return {"candidates": out}
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Failed to list candidates")


@app.get("/api/invite/{session_id}")
async def public_invite_get(session_id: str, conn=Depends(get_db)):
    """
    Public endpoint to fetch quiz & metadata for an invitation session.
    No auth required — returns quiz JSON and candidate_email if found.
    Use carefully: keep invitation links unguessable (UUID session IDs).
    """
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT metadata, start_time, end_time FROM quiz_sessions WHERE id = %s", (session_id,))
            r = cur.fetchone()
            if not r:
                raise HTTPException(status_code=404, detail="Invitation not found")
            meta = r.get("metadata")
            if isinstance(meta, str):
                try:
                    meta = json.loads(meta)
                except:
                    # best-effort: return minimal info
                    return {"found": True, "raw_metadata": meta}
            quiz = meta.get("quiz")
            candidate_email = meta.get("candidate_email")
            return {"found": True, "session_id": session_id, "quiz": quiz, "candidate_email": candidate_email, "start_time": r.get("start_time"), "end_time": r.get("end_time")}
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to read invitation: {e}")
    
class PublicQuizSubmission(BaseModel):
    session_id: str
    answers: List[Dict[str, Any]]

@app.post("/api/invite/submit")
async def invite_submit(
    session_id: str = Form(...),
    answers_json: str = Form(...),  # answers as JSON string
    candidate_email: Optional[str] = Form(None),
    conn=Depends(get_db)
):
    """
    Endpoint for invited candidates (not authenticated) to submit answers.
    Expects form-encoded fields:
      - session_id
      - answers_json (stringified JSON array of answers)
      - candidate_email (optional, helps link submission)
    """
    try:
        # parse answers
        try:
            answers = json.loads(answers_json)
            if not isinstance(answers, list):
                raise ValueError("answers must be a JSON array")
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid answers: {e}")

        print(f"[invite_submit] Received submission for session={session_id}, answers={len(answers)} items, email={candidate_email}")

        with conn.cursor() as cur:
            cur.execute("SELECT metadata, user_id FROM quiz_sessions WHERE id = %s", (session_id,))
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Session not found")

            metadata = row["metadata"]
            if isinstance(metadata, str):
                try:
                    metadata = json.loads(metadata)
                except Exception:
                    metadata = {}

            quiz_data = metadata.get("quiz", {})
            skills_data = metadata.get("skills", {})

            # if no answers provided, construct empty answers for grading
            if not answers:
                constructed = []
                for block in quiz_data.get("skill_quizzes", []):
                    for q in block.get("questions", []):
                        constructed.append({
                            "question": q.get("question"),
                            "answer": "",
                            "is_correct": None,
                            "time_spent_sec": 0
                        })
                answers = constructed

            # optional: prevent multiple submissions by checking end_time or a 'completed' flag
            cur.execute("SELECT end_time FROM quiz_sessions WHERE id = %s", (session_id,))
            existing = cur.fetchone()
            if existing and existing.get("end_time"):
                raise HTTPException(status_code=409, detail="Session already completed")

            # grade using your existing grader
            grading = grade_answers_and_score(quiz_data, answers)
            if not isinstance(grading, dict):
                grading = {"overall_score": 0.0, "cognitive_score": 0.0, "corrections": []}

            # generate recommendations (AI)
            recommendations = recommend_courses(skills_data, grading, use_ai=True)

            # update session: save grading + recommendations + candidate_email (optional)
            update_payload = {
                "grading": grading,
                "recommendations": recommendations,
            }
            if candidate_email:
                update_payload["candidate_email"] = candidate_email

            cur.execute("""
                UPDATE quiz_sessions
                SET end_time = NOW(),
                    total_score = %s,
                    cognitive_score = %s,
                    metadata = metadata || %s::jsonb
                WHERE id = %s
            """, (
                grading.get("overall_score", 0.0),
                grading.get("cognitive_score", 0.0),
                json.dumps(update_payload),
                session_id
            ))
            conn.commit()

        print(f"[invite_submit] ✅ Completed invite submission for session {session_id}")
        return {"grading": grading, "recommendations": recommendations}

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Invite submission failed: {e}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
