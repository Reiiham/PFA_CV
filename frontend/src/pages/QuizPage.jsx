// // frontend/src/pages/QuizPage.jsx
// import React, { useState } from 'react';
// import { useLocation, useNavigate, useParams } from 'react-router-dom';
// import { Send, CheckCircle } from 'lucide-react';

// const API_URL = 'http://localhost:8000';

// export default function QuizPage() {
//   const location = useLocation();
//   const navigate = useNavigate();
//   const { sessionId } = useParams();
//   const { quiz } = location.state || {};

//   const [answers, setAnswers] = useState({});
//   const [submitting, setSubmitting] = useState(false);
//   const [result, setResult] = useState(null);
//   const token = localStorage.getItem('token');

//   if (!quiz) {
//     return (
//       <div className="p-10 text-center">
//         <p className="text-gray-600">No quiz data found. Please start from your dashboard.</p>
//         <button
//           onClick={() => navigate('/')}
//           className="mt-4 bg-blue-600 text-white px-4 py-2 rounded-lg"
//         >
//           Go Back
//         </button>
//       </div>
//     );
//   }

//   const handleAnswerChange = (question, value) => {
//     setAnswers((prev) => ({ ...prev, [question]: value }));
//   };

//   const handleSubmit = async () => {
//     setSubmitting(true);
//     try {
//       const formattedAnswers = Object.entries(answers).map(([question, value]) => ({
//         question,
//         answer: value,
//         is_correct: null,
//         time_spent_sec: 0,
//       }));

//       const res = await fetch(`${API_URL}/api/quiz/submit`, {
//         method: 'POST',
//         headers: {
//           'Content-Type': 'application/json',
//           Authorization: `Bearer ${token}`,
//         },
//         body: JSON.stringify({
//           session_id: sessionId,
//           answers: formattedAnswers,
//         }),
//       });

//       const data = await res.json();
//       setResult(data);
//     } catch (err) {
//       alert('Submission failed: ' + err.message);
//     } finally {
//       setSubmitting(false);
//     }
//   };

//   if (result) {
//     return (
//       <div className="min-h-screen bg-gray-50 p-6">
//         <div className="max-w-3xl mx-auto bg-white shadow-md rounded-lg p-8">
//           <div className="flex items-center gap-3 text-green-600 mb-4">
//             <CheckCircle className="w-6 h-6" />
//             <h2 className="text-2xl font-bold">Quiz Completed!</h2>
//           </div>
//           <p className="text-gray-700 mb-4">
//   Your score: <strong>{result.grading?.overall_score}%</strong> <br />
//   Cognitive score: <strong>{result.grading?.cognitive_score}%</strong>
// </p>

// {result.recommendations?.length > 0 && (
//   <div className="mt-6">
//     <h3 className="text-xl font-semibold text-gray-800 mb-3">Recommended Courses</h3>
//     {result.recommendations.map((rec, i) => (
//       <div key={i} className="border rounded-lg p-4 mb-4">
//         <h4 className="font-medium text-blue-600 mb-2">{rec.skill}</h4>
//         {rec.resources.map((r, j) => (
//           <div key={j} className="mb-2">
//             <p className="font-semibold text-gray-800">{r.title}</p>
//             <p className="text-gray-600 text-sm">{r.description}</p>
//             <p className="text-xs text-gray-500">{r.platform} • {r.difficulty}</p>
//           </div>
//         ))}
//       </div>
//     ))}
//   </div>
// )}

//           <button
//             onClick={() => navigate('/')}
//             className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700"
//           >
//             Back to Dashboard
//           </button>
//         </div>
//       </div>
//     );
//   }

//   return (
//     <div className="min-h-screen bg-gray-50 p-6">
//       <div className="max-w-4xl mx-auto bg-white shadow-md rounded-lg p-8">
//         <h1 className="text-3xl font-bold text-gray-800 mb-6">Your Quiz</h1>

//         {quiz.skill_quizzes.map((block, i) => (
//           <div key={i} className="mb-8">
//             <h2 className="text-xl font-semibold text-blue-600 mb-3">{block.skill}</h2>
//             {block.questions.map((q, j) => (
//               <div key={j} className="border border-gray-200 p-4 rounded-lg mb-4">
//                 <p className="font-medium text-gray-800 mb-3">{q.question}</p>

//                 {q.type === 'MCQ' ? (
//                   <div className="space-y-2">
//                     {q.options.map((opt, k) => (
//                       <label key={k} className="block">
//                         <input
//                           type="radio"
//                           name={q.question}
//                           value={opt}
//                           checked={answers[q.question] === opt}
//                           onChange={(e) => handleAnswerChange(q.question, e.target.value)}
//                           className="mr-2"
//                         />
//                         {opt}
//                       </label>
//                     ))}
//                   </div>
//                 ) : (
//                   <textarea
//                     placeholder="Write your code or answer here..."
//                     className="w-full border border-gray-300 rounded-lg p-2 mt-2 font-mono text-sm"
//                     rows={5}
//                     value={answers[q.question] || ''}
//                     onChange={(e) => handleAnswerChange(q.question, e.target.value)}
//                   />
//                 )}
//               </div>
//             ))}
//           </div>
//         ))}

//         <button
//           onClick={handleSubmit}
//           disabled={submitting}
//           className="w-full bg-green-600 text-white py-3 rounded-lg hover:bg-green-700 flex items-center justify-center gap-2 font-medium disabled:bg-gray-400"
//         >
//           <Send className="w-5 h-5" />
//           {submitting ? 'Submitting...' : 'Submit Quiz'}
//         </button>
//       </div>
//     </div>
//   );
// }
// frontend/src/pages/QuizPage.jsx
import React, { useState, useMemo } from 'react';
import { useLocation, useNavigate, useParams } from 'react-router-dom';
import { Send, CheckCircle } from 'lucide-react';

const API_URL = 'http://localhost:8000';

export default function QuizPage() {
  const location = useLocation();
  const navigate = useNavigate();
  const { sessionId } = useParams();
  const { quiz } = location.state || {};

  const [answers, setAnswers] = useState({});
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState(null);
  const token = localStorage.getItem('token');

  // ---- HOOKS (always declared, before any early returns) ----

  // map question text -> question object (for feedback display before submit)
  const questionIndex = useMemo(() => {
    const map = {};
    if (!quiz || !quiz.skill_quizzes) return map;
    quiz.skill_quizzes.forEach((block) => {
      block.questions?.forEach((q) => {
        map[q.question] = q;
      });
    });
    return map;
  }, [quiz]);

  // map corrections by question text for quick lookup (from submission result)
  const correctionMap = useMemo(() => {
    const map = {};
    const corrections = result?.grading?.corrections || [];
    if (!Array.isArray(corrections)) return map;
    corrections.forEach((c) => {
      if (c && c.question) {
        map[c.question] = c; // keep last if duplicates
      }
    });
    return map;
  }, [result]);

  // corrected_quiz that the grader may have returned (used as hints before submit)
  const correctedQuizMap = useMemo(() => {
    const map = {};
    quiz?.skill_quizzes?.forEach((block) => {
      block.questions?.forEach((q) => {
        if (q && q._correction) {
          map[q.question] = q._correction;
        }
      });
    });
    return map;
  }, [quiz]);

  // flattened normalized recommendations (max 7) — computed with useMemo for stability
  const recsFlat = useMemo(() => {
    const recs = result?.recommendations || [];
    if (!Array.isArray(recs) || recs.length === 0) return [];

    // detect old format: [{ skill, resources: [...] }, ...]
    const looksLikeOld = recs[0] && Object.prototype.hasOwnProperty.call(recs[0], 'resources');
    if (looksLikeOld) {
      const flat = [];
      recs.forEach((r) => {
        const skill = r.skill || 'General';
        (r.resources || []).forEach((res) => {
          flat.push({
            skill,
            title: res.title,
            description: res.description,
            platform: res.platform,
            difficulty: res.difficulty,
          });
        });
      });
      // dedupe by title and limit to 7
      const out = [];
      const seen = new Set();
      for (const it of flat) {
        if (!seen.has(it.title)) {
          out.push(it);
          seen.add(it.title);
        }
        if (out.length >= 7) break;
      }
      return out;
    }

    // new flattened format: [{ skill, title, description, platform, difficulty }]
    const looksLikeNew = recs[0] && (recs[0].title || recs[0].description);
    if (looksLikeNew) {
      const normalized = recs.map((r) => ({
        skill: r.skill || 'General',
        title: r.title || r.name || 'Untitled',
        description: r.description || '',
        platform: r.platform || r.source || 'Unknown',
        difficulty: r.difficulty || r.level || 'intermediate',
      }));
      const out = [];
      const seen = new Set();
      for (const it of normalized) {
        if (!seen.has(it.title)) {
          out.push(it);
          seen.add(it.title);
        }
        if (out.length >= 7) break;
      }
      return out;
    }

    return [];
  }, [result]);

  // ---- early return if no quiz provided (still allowed because hooks already executed) ----
  if (!quiz) {
    return (
      <div className="p-10 text-center">
        <p className="text-gray-600">No quiz data found. Please start from your dashboard.</p>
        <button
          onClick={() => navigate('/')}
          className="mt-4 bg-blue-600 text-white px-4 py-2 rounded-lg"
        >
          Go Back
        </button>
      </div>
    );
  }

  // ---- handlers (unchanged) ----
  const handleAnswerChange = (question, value) => {
    setAnswers((prev) => ({ ...prev, [question]: value }));
  };

  // const handleSubmit = async () => {
  // setSubmitting(true);
  // try {
  //   // Build answers from quiz questions so we always send an entry per question
  //   const formattedAnswers = [];
  //   quiz.skill_quizzes.forEach((block) => {
  //     block.questions.forEach((q) => {
  //       formattedAnswers.push({
  //         question: q.question,
  //         answer: answers[q.question] ?? "",   // empty string if user didn't answer
  //         is_correct: null,
  //         time_spent_sec: 0,
  //       });
  //     });
  //   });

  //   console.log("Submitting answers for session:", sessionId, "payload len:", formattedAnswers.length);

  //     const res = await fetch(`${API_URL}/api/quiz/submit`, {
  //       method: 'POST',
  //       headers: {
  //         'Content-Type': 'application/json',
  //         Authorization: `Bearer ${token}`,
  //       },
  //       body: JSON.stringify({
  //         session_id: sessionId,
  //         answers: formattedAnswers,
  //       }),
  //     });

  //     console.log("Response status:", res.status, res.statusText);
  //     try {
  //       const hdrs = {};
  //       res.headers.forEach((v, k) => { hdrs[k] = v; });
  //       console.log("Response headers:", hdrs);
  //     } catch (e) {
  //       console.warn("Could not read response headers", e);
  //     }

  //     const raw = await res.text();
  //     console.log("Raw response body:", raw.slice(0, 5000)); // truncate long logs

  //     if (!res.ok) {
  //       let parsedErr;
  //       try { parsedErr = JSON.parse(raw); } catch (_) { parsedErr = null; }
  //       const detail = parsedErr?.detail || parsedErr?.message || raw || res.statusText;
  //       throw new Error(detail);
  //     }

  //     let data;
  //     try {
  //       data = JSON.parse(raw);
  //     } catch (e) {
  //       console.error("Failed to parse JSON from backend:", e);
  //       alert("Backend returned non-JSON response. Check devtools console for raw body.");
  //       setResult({ raw_response: raw });
  //       return;
  //     }

  //     console.log("Parsed response JSON:", data);
  //     setResult(data);
  //     window.scrollTo({ top: 0, behavior: 'smooth' });
  //   } catch (err) {
  //     console.error("Submission error:", err);
  //     alert("Submission failed: " + (err.message || err));
  //   } finally {
  //     setSubmitting(false);
  //   }
  // };
  const handleSubmit = async () => {
  setSubmitting(true);
  try {
    const formattedAnswers = Object.entries(answers).map(([question, value]) => ({
      question,
      answer: value || "",
      is_correct: null,
      time_spent_sec: 0,
    }));

    console.log("Submitting answers for session:", sessionId, "payload:", formattedAnswers);

    const token = localStorage.getItem('token');

    if (token) {
      // authenticated flow
      const res = await fetch(`${API_URL}/api/quiz/submit`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          session_id: sessionId,
          answers: formattedAnswers,
        }),
      });

      if (!res.ok) {
        const txt = await res.text();
        throw new Error(txt || res.statusText);
      }
      const data = await res.json();
      setResult(data);
      window.scrollTo({ top: 0, behavior: 'smooth' });
      return;
    } else {
      // invite / anonymous flow -> submit as form data
      const fd = new FormData();
      fd.append('session_id', sessionId);
      fd.append('answers_json', JSON.stringify(formattedAnswers));
      // optionally include candidate email if available in UI (e.g. ask the user)
      // fd.append('candidate_email', candidateEmail);

      const res = await fetch(`${API_URL}/api/invite/submit`, {
        method: 'POST',
        body: fd,
      });

      const raw = await res.text();
      console.log("Invite submit raw:", raw);

      if (!res.ok) {
        let parsed;
        try { parsed = JSON.parse(raw); } catch {}
        const detail = parsed?.detail || raw || res.statusText;
        throw new Error(detail);
      }

      const data = JSON.parse(raw);
      setResult(data);
      window.scrollTo({ top: 0, behavior: 'smooth' });
      return;
    }
  } catch (err) {
    console.error("Submission error:", err);
    alert("Submission failed: " + (err.message || err));
  } finally {
    setSubmitting(false);
  }
};


  // ---- render: result view or quiz view ----
  if (result) {
    return (
      <div className="min-h-screen bg-gray-50 p-6">
        <div className="max-w-3xl mx-auto bg-white shadow-md rounded-lg p-8">
          <div className="flex items-center gap-3 text-green-600 mb-4">
            <CheckCircle className="w-6 h-6" />
            <h2 className="text-2xl font-bold">Quiz Completed!</h2>
          </div>

          <p className="text-gray-700 mb-4">
            Your score: <strong>{result.grading?.overall_score ?? 'N/A'}%</strong>
            <br />
            Cognitive score: <strong>{result.grading?.cognitive_score ?? 'N/A'}%</strong>
          </p>

          {result.grading?.corrections?.length > 0 && (
            <div className="mb-6">
              <h3 className="text-xl font-semibold mb-3">Corrections & Feedback</h3>
              <div className="space-y-3">
                {result.grading.corrections.map((c, idx) => (
                  <div key={idx} className="border rounded p-3">
                    <div className="font-medium text-gray-800">{c.skill} — {c.bloom_level}</div>
                    <div className="text-sm text-gray-700 mt-1 mb-2"><strong>Question:</strong> {c.question}</div>
                    <div className="text-sm text-gray-700"><strong>Your answer:</strong> {c.user_answer ?? '(no answer)'}</div>
                    <div className="text-sm text-gray-700"><strong>Score (0-5):</strong> {c.score ?? 0}</div>
                    <div className="text-sm text-gray-600 mt-2"><strong>Feedback:</strong> {c.feedback ?? 'No feedback provided.'}</div>
                    {c.corrected_answer && (
                      <div className="mt-2 text-sm bg-yellow-50 p-2 rounded">
                        <strong>Corrected answer:</strong> {c.corrected_answer}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {recsFlat.length > 0 && (
            <div className="mb-6">
              <h3 className="text-xl font-semibold mb-3">Recommended Learning Resources</h3>
              <div className="space-y-3">
                {recsFlat.map((r, i) => (
                  <div key={i} className="border rounded p-3">
                    <div className="font-semibold text-blue-600">{r.title}</div>
                    <div className="text-sm text-gray-700 mt-1">{r.description}</div>
                    <div className="text-xs text-gray-500 mt-2">{r.platform} • {r.difficulty} — <span className="font-medium">{r.skill}</span></div>
                  </div>
                ))}
              </div>
            </div>
          )}

          <button
            onClick={() => navigate('/')}
            className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700"
          >
            Back to Dashboard
          </button>
        </div>
      </div>
    );
  }

  // Pre-submit quiz UI (show per-question corrections inline if grader provided corrected_quiz earlier)
  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-4xl mx-auto bg-white shadow-md rounded-lg p-8">
        <h1 className="text-3xl font-bold text-gray-800 mb-6">Your Quiz</h1>

        {quiz.skill_quizzes.map((block, i) => (
          <div key={i} className="mb-8">
            <h2 className="text-xl font-semibold text-blue-600 mb-3">{block.skill}</h2>
            {block.questions.map((q, j) => {
              const corr = correctionMap[q.question] || correctedQuizMap[q.question];
              return (
                <div key={j} className="border border-gray-200 p-4 rounded-lg mb-4">
                  <p className="font-medium text-gray-800 mb-3">{q.question}</p>

                  {q.type === 'MCQ' ? (
                    <div className="space-y-2">
                      {q.options.map((opt, k) => (
                        <label key={k} className="block">
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
                      ))}
                    </div>
                  ) : (
                    <textarea
                      placeholder="Write your code or answer here..."
                      className="w-full border border-gray-300 rounded-lg p-2 mt-2 font-mono text-sm"
                      rows={5}
                      value={answers[q.question] || ''}
                      onChange={(e) => handleAnswerChange(q.question, e.target.value)}
                    />
                  )}

                  {corr && (
                    <div className="mt-3 p-3 bg-yellow-50 rounded text-sm text-gray-700">
                      <div><strong>Note (previous correction):</strong></div>
                      <div>{corr.feedback || 'Suggested improvement available.'}</div>
                      {corr.corrected_answer && <div className="mt-1"><strong>Suggested answer:</strong> {corr.corrected_answer}</div>}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        ))}

        <button
          onClick={handleSubmit}
          disabled={submitting}
          className="w-full bg-green-600 text-white py-3 rounded-lg hover:bg-green-700 flex items-center justify-center gap-2 font-medium disabled:bg-gray-400"
        >
          <Send className="w-5 h-5" />
          {submitting ? 'Submitting...' : 'Submit Quiz'}
        </button>
      </div>
    </div>
  );
}
