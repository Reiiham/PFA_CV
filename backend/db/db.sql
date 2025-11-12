-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS pgcrypto;
'''
-- ================================
-- 🧠 USERS TABLE
-- ================================
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    occupation TEXT,
    birth_date DATE,
    email TEXT UNIQUE NOT NULL,
    role TEXT CHECK (role IN ('candidate', 'hr', 'admin')) DEFAULT 'candidate',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ================================
-- 🧩 QUIZ SESSIONS TABLE
-- ================================
CREATE TABLE quiz_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    start_time TIMESTAMPTZ DEFAULT NOW(),
    end_time TIMESTAMPTZ,
    total_score FLOAT DEFAULT 0.0,
    cognitive_score FLOAT DEFAULT 0.0,
    metadata JSONB DEFAULT '{}'::JSONB,
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    hr_feedback TEXT
);

CREATE INDEX idx_quiz_sessions_user_id ON quiz_sessions(user_id);
CREATE INDEX idx_quiz_sessions_created_by ON quiz_sessions(created_by);

-- ================================
-- 📝 ANSWERS TABLE
-- ================================
CREATE TABLE answers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    quiz_session_id UUID NOT NULL REFERENCES quiz_sessions(id) ON DELETE CASCADE,
    question_text TEXT NOT NULL,
    difficulty FLOAT DEFAULT 1.0,
    answer JSONB,
    is_correct BOOLEAN,
    time_spent_sec FLOAT DEFAULT 0.0
);

CREATE INDEX idx_answers_quiz_session_id ON answers(quiz_session_id);

-- ================================
-- ✅ VIEW: USER COGNITIVE SUMMARY
-- ================================
CREATE VIEW user_cognitive_summary AS
SELECT 
    u.id AS user_id,
    CONCAT(u.first_name, ' ', u.last_name) AS full_name,
    AVG(q.cognitive_score) AS avg_cognitive_score,
    COUNT(q.id) AS total_sessions
FROM users u
LEFT JOIN quiz_sessions q ON u.id = q.user_id
GROUP BY u.id, full_name;

-- ================================
-- ✅ VIEW: HR EVALUATION SUMMARY
-- ================================
CREATE VIEW hr_evaluation_summary AS
SELECT
    hr.id AS hr_id,
    CONCAT(hr.first_name, ' ', hr.last_name) AS hr_name,
    cand.id AS candidate_id,
    CONCAT(cand.first_name, ' ', cand.last_name) AS candidate_name,
    COUNT(q.id) AS total_sessions,
    AVG(q.total_score) AS avg_total_score,
    AVG(q.cognitive_score) AS avg_cognitive_score
FROM quiz_sessions q
JOIN users cand ON q.user_id = cand.id
JOIN users hr ON q.created_by = hr.id
WHERE hr.role = 'hr'
GROUP BY hr.id, hr_name, cand.id, candidate_name;

'''

# ============================================
# database_setup.sql - Complete Database Schema
# ============================================

-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Drop existing tables if you want to reset
-- DROP TABLE IF EXISTS answers CASCADE;
-- DROP TABLE IF EXISTS quiz_sessions CASCADE;
-- DROP TABLE IF EXISTS users CASCADE;

-- ================================
-- 🧠 USERS TABLE
-- ================================
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    occupation TEXT,
    birth_date DATE,
    email TEXT UNIQUE NOT NULL,
    role TEXT CHECK (role IN ('candidate', 'hr', 'admin')) DEFAULT 'candidate',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_role ON users(role);

-- ================================
-- 🧩 QUIZ SESSIONS TABLE
-- ================================
CREATE TABLE quiz_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    start_time TIMESTAMPTZ DEFAULT NOW(),
    end_time TIMESTAMPTZ,
    total_score FLOAT DEFAULT 0.0,
    cognitive_score FLOAT DEFAULT 0.0,
    metadata JSONB DEFAULT '{}'::JSONB,
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    hr_feedback TEXT,
    status TEXT DEFAULT 'invited' CHECK (status IN ('invited', 'in_progress', 'completed', 'expired'))
);

CREATE INDEX idx_quiz_sessions_user_id ON quiz_sessions(user_id);
CREATE INDEX idx_quiz_sessions_created_by ON quiz_sessions(created_by);
CREATE INDEX idx_quiz_sessions_status ON quiz_sessions(status);

-- ================================
-- 📝 ANSWERS TABLE
-- ================================
CREATE TABLE answers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    quiz_session_id UUID NOT NULL REFERENCES quiz_sessions(id) ON DELETE CASCADE,
    question_text TEXT NOT NULL,
    difficulty FLOAT DEFAULT 1.0,
    answer JSONB,
    is_correct BOOLEAN,
    time_spent_sec FLOAT DEFAULT 0.0,
    skill TEXT,
    bloom_level TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_answers_quiz_session_id ON answers(quiz_session_id);
CREATE INDEX idx_answers_skill ON answers(skill);

-- ================================
-- ✅ VIEW: USER COGNITIVE SUMMARY
-- ================================
CREATE OR REPLACE VIEW user_cognitive_summary AS
SELECT 
    u.id AS user_id,
    CONCAT(u.first_name, ' ', u.last_name) AS full_name,
    u.email,
    u.role,
    AVG(q.cognitive_score) AS avg_cognitive_score,
    AVG(q.total_score) AS avg_total_score,
    COUNT(q.id) AS total_sessions,
    COUNT(CASE WHEN q.end_time IS NOT NULL THEN 1 END) AS completed_sessions
FROM users u
LEFT JOIN quiz_sessions q ON u.id = q.user_id
GROUP BY u.id, full_name, u.email, u.role;

-- ================================
-- ✅ VIEW: HR EVALUATION SUMMARY
-- ================================
CREATE OR REPLACE VIEW hr_evaluation_summary AS
SELECT
    hr.id AS hr_id,
    CONCAT(hr.first_name, ' ', hr.last_name) AS hr_name,
    hr.email AS hr_email,
    cand.id AS candidate_id,
    CONCAT(cand.first_name, ' ', cand.last_name) AS candidate_name,
    cand.email AS candidate_email,
    COUNT(q.id) AS total_sessions,
    AVG(q.total_score) AS avg_total_score,
    AVG(q.cognitive_score) AS avg_cognitive_score,
    COUNT(CASE WHEN q.end_time IS NOT NULL THEN 1 END) AS completed_sessions,
    MAX(q.start_time) AS last_quiz_date
FROM quiz_sessions q
JOIN users cand ON q.user_id = cand.id
JOIN users hr ON q.created_by = hr.id
WHERE hr.role = 'hr'
GROUP BY hr.id, hr_name, hr.email, cand.id, candidate_name, candidate_email;

-- ================================
-- ✅ VIEW: SKILL PERFORMANCE
-- ================================
CREATE OR REPLACE VIEW skill_performance AS
SELECT
    a.skill,
    u.id AS user_id,
    CONCAT(u.first_name, ' ', u.last_name) AS user_name,
    COUNT(a.id) AS total_questions,
    SUM(CASE WHEN a.is_correct THEN 1 ELSE 0 END) AS correct_answers,
    ROUND(AVG(CASE WHEN a.is_correct THEN 100 ELSE 0 END), 2) AS success_rate,
    AVG(a.time_spent_sec) AS avg_time_spent
FROM answers a
JOIN quiz_sessions qs ON a.quiz_session_id = qs.id
JOIN users u ON qs.user_id = u.id
WHERE a.skill IS NOT NULL
GROUP BY a.skill, u.id, user_name;

CREATE TABLE IF NOT EXISTS candidate_skills (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    skills JSONB NOT NULL,
    last_updated TIMESTAMP DEFAULT NOW()
);



-- 1) hr_candidates table
CREATE TABLE IF NOT EXISTS hr_candidates (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  email text NOT NULL,
  first_name text,
  last_name text,
  phone text,
  notes text,
  created_by uuid,         -- users.id of HR who created the row
  created_at timestamptz DEFAULT now()
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_hr_candidates_email ON hr_candidates ((lower(email)));

-- 2) add hr_candidate_id to quiz_sessions
ALTER TABLE quiz_sessions
  ADD COLUMN IF NOT EXISTS hr_candidate_id uuid;

-- (optional) FK constraint - uncomment if you want referential integrity
-- ALTER TABLE quiz_sessions
--   ADD CONSTRAINT fk_quizsessions_hrcandidate
--   FOREIGN KEY (hr_candidate_id) REFERENCES hr_candidates(id);

