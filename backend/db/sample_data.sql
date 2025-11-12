-- Create sample HR user
INSERT INTO users (first_name, last_name, email, password_hash, role)
VALUES ('Jane', 'Recruiter', 'hr@example.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYIxF6q0zHi', 'hr')
ON CONFLICT (email) DO NOTHING;
-- Password: password123

-- Create sample candidate
INSERT INTO users (first_name, last_name, email, password_hash, role)
VALUES ('John', 'Candidate', 'candidate@example.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYIxF6q0zHi', 'candidate')
ON CONFLICT (email) DO NOTHING;
-- Password: password123