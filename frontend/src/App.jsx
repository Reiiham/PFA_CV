import React, { useState, useMemo, useEffect } from 'react'
import axios from 'axios'

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:5000'

export default function App() {
  const [file, setFile] = useState(null)
  const [sessionId, setSessionId] = useState('')
  const [skills, setSkills] = useState(null)
  const [quiz, setQuiz] = useState(null)
  const [quizId, setQuizId] = useState('')
  const [answers, setAnswers] = useState({})
  const [results, setResults] = useState(null)
  const [currentIndex, setCurrentIndex] = useState(0)
  const [remaining, setRemaining] = useState(0)

  const [isUploading, setIsUploading] = useState(false)
  const [isGenerating, setIsGenerating] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)

  // Removed config - now auto-generated

  const allQuestions = useMemo(() => {
    if (!quiz?.skill_quizzes) return []
    const flat = []
    for (const sq of quiz.skill_quizzes) {
      for (const q of sq.questions) {
        flat.push({ skill: sq.skill, ...q })
      }
    }
    return flat
  }, [quiz])

  useEffect(() => {
    if (!quiz) return
    const timeLimit = currentQ?.time_limit_sec || 60
    setRemaining(timeLimit)
    const id = setInterval(() => setRemaining((r) => r - 1), 1000)
    return () => clearInterval(id)
  }, [quiz, currentIndex])

  useEffect(() => {
    if (!quiz) return
    if (remaining <= 0) {
      nextQuestion()
    }
  }, [remaining])

  const nextQuestion = () => {
    if (currentIndex < allQuestions.length - 1) {
      setCurrentIndex((i) => i + 1)
    }
  }

  const prevQuestion = () => {
    if (currentIndex > 0) {
      setCurrentIndex((i) => i - 1)
    }
  }

  const handleUpload = async (e) => {
    e.preventDefault()
    if (!file) return
    try {
      setIsUploading(true)
      const form = new FormData()
      form.append('file', file)
      const res = await axios.post(`${API_BASE}/api/upload-cv`, form, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      setSessionId(res.data.session_id)
      setSkills(res.data.skills)
    } catch (err) {
      console.error('Upload failed', err)
      alert(`Upload failed: ${err?.response?.data?.error || err.message}`)
    } finally {
      setIsUploading(false)
    }
  }

  const handleGenerateQuiz = async () => {
    if (!sessionId) return alert('No session. Upload a CV first.')
    try {
      setIsGenerating(true)
      const res = await axios.post(`${API_BASE}/api/generate-quiz`, {
        session_id: sessionId,
      })
      setQuiz(res.data.quiz)
      setQuizId(res.data.quiz_id)
      setCurrentIndex(0)
      setAnswers({})
      setResults(null)
    } catch (err) {
      console.error('Generate quiz failed', err)
      alert(`Generate quiz failed: ${err?.response?.data?.error || err.message}`)
    } finally {
      setIsGenerating(false)
    }
  }

  const handleSubmitAnswers = async () => {
    if (!quizId) return alert('No quiz to submit.')
    try {
      setIsSubmitting(true)
      const payload = allQuestions.map((q, idx) => {
        const answer = answers[idx]
        if (q.type === 'MCQ' && answer?.selected_index !== undefined) {
          return {
            skill: q.skill,
            bloom_level: q.bloom_level,
            question: q.question,
            answer: `Selected option ${answer.selected_index}: ${q.options?.[answer.selected_index] || ''}`,
          }
        } else {
          return {
            skill: q.skill,
            bloom_level: q.bloom_level,
            question: q.question,
            answer: answer?.text || '',
          }
        }
      })
      const res = await axios.post(`${API_BASE}/api/submit-answers`, {
        quiz_id: quizId,
        answers: payload,
      })
      setResults(res.data)
    } catch (err) {
      console.error('Submit failed', err)
      alert(`Submit failed: ${err?.response?.data?.error || err.message}`)
    } finally {
      setIsSubmitting(false)
    }
  }

  const currentQ = allQuestions[currentIndex]

  const renderAnswerInput = () => {
    if (!currentQ) return null
    if (currentQ.type === 'MCQ' && Array.isArray(currentQ.options)) {
      return (
        <div>
          {currentQ.options.map((opt, i) => (
            <label key={i} style={{ display: 'block', marginBottom: 6 }}>
              <input
                type="radio"
                name={`q_${currentIndex}`}
                checked={answers[currentIndex]?.selected_index === i}
                onChange={() => setAnswers({ ...answers, [currentIndex]: { selected_index: i } })}
              />
              <span style={{ marginLeft: 8 }}>{opt}</span>
            </label>
          ))}
        </div>
      )
    }
    // CODING or OPEN fallback
    return (
      <textarea
        rows={6}
        style={{ width: '100%' }}
        placeholder={currentQ.type === 'CODING' ? 'Write your code or approach here…' : 'Your answer…'}
        value={answers[currentIndex]?.text || ''}
        onChange={(e) => setAnswers({ ...answers, [currentIndex]: { text: e.target.value } })}
      />
    )
  }

  // Removed NumberInput component - no longer needed

  return (
    <div style={{ maxWidth: 900, margin: '20px auto', fontFamily: 'Inter, system-ui, Arial' }}>
      <h2>CV-based Timed Quiz</h2>

      {!sessionId && (
        <form onSubmit={handleUpload} style={{ marginBottom: 20 }}>
          <input type="file" accept="application/pdf" onChange={(e) => setFile(e.target.files?.[0] || null)} />
          <button type="submit" disabled={!file || isUploading} style={{ marginLeft: 10 }}>
            {isUploading ? 'Uploading…' : 'Upload CV'}
          </button>
        </form>
      )}

      {sessionId && !quiz && (
        <div style={{ marginBottom: 20 }}>
          <p><strong>Session:</strong> {sessionId}</p>
          <pre style={{ background: '#fafafa', padding: 8, border: '1px solid #eee', maxHeight: 160, overflow: 'auto' }}>
            {JSON.stringify(skills, null, 2)}
          </pre>

          <div style={{ marginBottom: 12, padding: 12, background: '#f0f8ff', borderRadius: 8 }}>
            <p><strong>Auto-generated quiz:</strong></p>
            <ul style={{ margin: 8, paddingLeft: 20 }}>
              <li>Technical skills: 2 MCQ + 1 Coding question per skill</li>
              <li>Soft skills: 2 MCQ questions per skill</li>
              <li>Cognitive skills: 2 MCQ questions per skill</li>
              <li>Time limits: MCQ (60s), Coding (5min), Open (2min)</li>
            </ul>
          </div>

          <div style={{ marginTop: 12 }}>
            <button onClick={handleGenerateQuiz} disabled={isGenerating}>
              {isGenerating ? 'Generating…' : 'Generate Quiz'}
            </button>
          </div>
        </div>
      )}

      {quiz && !results && (
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 10 }}>
            <div>Question {currentIndex + 1} / {allQuestions.length}</div>
            <div>Time left: {remaining}s</div>
          </div>
          <div style={{ border: '1px solid #ddd', padding: 16, borderRadius: 8 }}>
            <div style={{ marginBottom: 8 }}><strong>Skill:</strong> {currentQ?.skill}</div>
            <div style={{ marginBottom: 8 }}><strong>Type:</strong> {currentQ?.type || 'OPEN'}</div>
            <div style={{ marginBottom: 8 }}><strong>Bloom:</strong> {currentQ?.bloom_level}</div>
            <div style={{ marginBottom: 12 }}>{currentQ?.question}</div>
            {renderAnswerInput()}
            <div style={{ marginTop: 10, display: 'flex', gap: 8 }}>
              <button onClick={prevQuestion} disabled={currentIndex === 0}>Prev</button>
              {currentIndex < allQuestions.length - 1 ? (
                <button onClick={nextQuestion}>Next</button>
              ) : (
                <button onClick={handleSubmitAnswers} disabled={isSubmitting}>
                  {isSubmitting ? 'Submitting…' : 'Submit'}
                </button>
              )}
            </div>
          </div>
        </div>
      )}

      {results && (
        <div style={{ marginTop: 20 }}>
          <h3>Results</h3>
          <div><strong>Overall Score:</strong> {results.grading?.overall_score}</div>
          <div><strong>Cognitive Score:</strong> {results.grading?.cognitive_score}</div>
          <h4>Recommendations</h4>
          {(results.recommendations?.recommendations || []).map((r) => (
            <div key={r.skill} style={{ marginBottom: 10 }}>
              <div><strong>{r.skill}</strong></div>
              <ul>
                {(r.resources || r.courses || []).map((c, idx) => (
                  <li key={(c.url || '') + idx}>
                    <a href={c.url} target="_blank" rel="noreferrer">{c.title}</a> - {c.provider}
                    {c.why ? <div style={{ fontSize: 13, color: '#333' }}>Why: {c.why}</div> : null}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
