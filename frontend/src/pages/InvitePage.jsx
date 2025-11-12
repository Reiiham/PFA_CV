// frontend/src/pages/InvitePage.jsx
import React, { useEffect, useState } from "react";
import { useParams, useLocation, useNavigate } from "react-router-dom";
import { Send, CheckCircle } from "lucide-react";

const API_URL = "http://localhost:8000";

export default function InvitePage() {
  const { sessionId } = useParams();
  const location = useLocation();
  const navigate = useNavigate();

  // try to get quiz from location.state (HR sharing the link may include quiz), else fetch public
  const initialQuiz = location.state?.quiz || null;

  const [quiz, setQuiz] = useState(initialQuiz);
  const [answers, setAnswers] = useState({});
  const [email, setEmail] = useState(location.state?.candidate_email || "");
  const [loading, setLoading] = useState(!initialQuiz);
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (quiz || !sessionId) {
      setLoading(false);
      return;
    }
    // fetch public invite quiz
    (async () => {
      setLoading(true);
      try {
        const res = await fetch(`${API_URL}/api/invite/${sessionId}`);
        if (!res.ok) {
          const txt = await res.text().catch(() => res.statusText);
          throw new Error(txt || `Failed to load invite: ${res.status}`);
        }
        const data = await res.json();
        if (data.found && data.quiz) {
          setQuiz(data.quiz);
          if (data.candidate_email) setEmail(data.candidate_email);
        } else {
          setError("Invitation not found or quiz missing.");
        }
      } catch (err) {
        console.error("Failed to load invite:", err);
        setError("Could not load invitation: " + (err.message || err));
      } finally {
        setLoading(false);
      }
    })();
  }, [sessionId, quiz]);

  const handleAnswerChange = (question, value) => {
    setAnswers((prev) => ({ ...prev, [question]: value }));
  };

  const handleSubmit = async () => {
    setSubmitting(true);
    setError("");
    try {
      // build formatted answers like backend expects
      const formattedAnswers = Object.entries(answers).map(([question, value]) => ({
        question,
        answer: value ?? "",
        is_correct: null,
        time_spent_sec: 0,
      }));

      // ensure at least empty answers constructed if user submitted nothing
      if (!formattedAnswers || formattedAnswers.length === 0) {
        // construct from quiz questions (same logic as backend fallback)
        const constructed = [];
        quiz.skill_quizzes?.forEach((block) => {
          block.questions?.forEach((q) => {
            constructed.push({ question: q.question, answer: "", is_correct: null, time_spent_sec: 0 });
          });
        });
        formattedAnswers.push(...constructed);
      }

      // send as form-data to public invite endpoint (no auth header)
      const fd = new FormData();
      fd.append("session_id", sessionId);
      fd.append("answers_json", JSON.stringify(formattedAnswers));
      if (email) fd.append("candidate_email", email);

      const res = await fetch(`${API_URL}/api/invite/submit`, {
        method: "POST",
        body: fd,
      });

      const text = await res.text();
      // try parse json
      let parsed;
      try { parsed = JSON.parse(text); } catch { parsed = null; }

      if (!res.ok) {
        // specific cases
        if (res.status === 403) {
          throw new Error("Forbidden — server requires authentication for this endpoint.");
        }
        if (res.status === 409) {
          throw new Error(parsed?.detail || "This session was already completed (409).");
        }
        throw new Error(parsed?.detail || parsed || text || `Submission failed: ${res.status}`);
      }

      // success
      setResult(parsed || {});
      // scroll to top so user sees results
      window.scrollTo({ top: 0, behavior: "smooth" });
    } catch (err) {
      console.error("Submission error:", err);
      setError(err.message || String(err));
      alert("Submission error: " + (err.message || err));
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="p-10 text-center">
        <p>Loading invitation...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-8 max-w-2xl mx-auto text-center">
        <p className="text-red-600 mb-4">{error}</p>
        <button className="px-4 py-2 bg-blue-600 text-white rounded" onClick={() => navigate("/")}>
          Back home
        </button>
      </div>
    );
  }

  if (!quiz) {
    return (
      <div className="p-8 text-center">
        <p>No quiz found for this invitation.</p>
        <button className="mt-4 px-4 py-2 bg-blue-600 text-white rounded" onClick={() => navigate("/")}>Home</button>
      </div>
    );
  }

  if (result) {
    return (
      <div className="min-h-screen bg-gray-50 p-6">
        <div className="max-w-3xl mx-auto bg-white shadow-md rounded-lg p-8">
          <div className="flex items-center gap-3 text-green-600 mb-4">
            <CheckCircle className="w-6 h-6" />
            <h2 className="text-2xl font-bold">Quiz Completed!</h2>
          </div>

          <p className="text-gray-700 mb-4">
            Your score: <strong>{result.grading?.overall_score ?? "N/A"}%</strong>
            <br />
            Cognitive score: <strong>{result.grading?.cognitive_score ?? "N/A"}%</strong>
          </p>

          <button onClick={() => navigate("/")} className="bg-blue-600 text-white px-4 py-2 rounded-lg">Back</button>
        </div>
      </div>
    );
  }

  // render quiz
  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-4xl mx-auto bg-white shadow-md rounded-lg p-8">
        <h1 className="text-2xl font-bold mb-4">Invitation quiz</h1>

        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-700 mb-1">Your email (optional)</label>
          <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} className="w-full px-3 py-2 border rounded" placeholder="you@example.com" />
        </div>

        {quiz.skill_quizzes?.map((block, bi) => (
          <div key={bi} className="mb-6">
            <h3 className="text-lg font-semibold mb-2">{block.skill}</h3>
            {block.questions?.map((q, qi) => (
              <div key={qi} className="mb-4 border p-3 rounded">
                <p className="font-medium mb-2">{q.question}</p>
                {q.type === "MCQ" ? (
                  q.options?.map((opt, oi) => (
                    <label className="block" key={oi}>
                      <input
                        type="radio"
                        name={q.question}
                        value={opt}
                        checked={answers[q.question] === opt}
                        onChange={(e) => handleAnswerChange(q.question, e.target.value)}
                        className="mr-2"
                      />
                      {opt}
                    </label>
                  ))
                ) : (
                  <textarea
                    rows={5}
                    value={answers[q.question] || ""}
                    onChange={(e) => handleAnswerChange(q.question, e.target.value)}
                    className="w-full border rounded p-2 font-mono"
                    placeholder="Write your answer..."
                  />
                )}
              </div>
            ))}
          </div>
        ))}

        <div className="flex gap-2">
          <button onClick={handleSubmit} disabled={submitting} className="bg-green-600 text-white px-4 py-2 rounded">
            <Send className="inline-block w-4 h-4 mr-1" />
            {submitting ? "Submitting..." : "Submit Quiz"}
          </button>

          <button onClick={() => navigate("/")} className="bg-gray-200 px-4 py-2 rounded">Cancel</button>
        </div>
      </div>
    </div>
  );
}
