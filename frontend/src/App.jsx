
// frontend/src/App.jsx
import React, { useState, useEffect } from 'react';
import { Upload, Send, Users, FileText, Award, BarChart3, LogOut, User } from 'lucide-react';
import InvitePage from './pages/InvitePage';
import { BrowserRouter as Router, Routes, Route, useNavigate } from 'react-router-dom';
import QuizPage from './pages/QuizPage';
const API_URL = 'http://localhost:8000';

// Auth Context
const AuthContext = React.createContext(null);

const useAuth = () => {
  const context = React.useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used within AuthProvider');
  return context;
};

const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(localStorage.getItem('token'));

  useEffect(() => {
    if (token) {
      fetchCurrentUser();
    }
  }, [token]);

  const fetchCurrentUser = async () => {
    try {
      const res = await fetch(`${API_URL}/api/auth/me`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setUser(data);
      } else {
        logout();
      }
    } catch (err) {
      console.error('Auth error:', err);
    }
  };

  const login = async (email, password) => {
    const res = await fetch(`${API_URL}/api/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password })
    });
    
    if (!res.ok) throw new Error('Login failed');
    
    const data = await res.json();
    localStorage.setItem('token', data.access_token);
    setToken(data.access_token);
    setUser(data.user);
    return data;
  };

  const register = async (userData) => {
    const res = await fetch(`${API_URL}/api/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(userData)
    });
    
    if (!res.ok) {
      const error = await res.json();
      throw new Error(error.detail || 'Registration failed');
    }
    
    const data = await res.json();
    localStorage.setItem('token', data.access_token);
    setToken(data.access_token);
    setUser(data.user);
    return data;
  };

  const logout = () => {
    localStorage.removeItem('token');
    setToken(null);
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, token, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
};

// Login/Register Component
const AuthForm = () => {
  const [isLogin, setIsLogin] = useState(true);
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    first_name: '',
    last_name: '',
    role: 'candidate'
  });
  const [error, setError] = useState('');
  const { login, register } = useAuth();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    
    try {
      if (isLogin) {
        await login(formData.email, formData.password);
      } else {
        await register(formData);
      }
    } catch (err) {
      setError(err.message);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center p-4">
      <div className="bg-white rounded-lg shadow-xl p-8 w-full max-w-md">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-gray-800 mb-2">Quiz Platform</h1>
          <p className="text-gray-600">
            {isLogin ? 'Sign in to your account' : 'Create a new account'}
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          {!isLogin && (
            <>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  First Name
                </label>
                <input
                  type="text"
                  required
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  value={formData.first_name}
                  onChange={(e) => setFormData({...formData, first_name: e.target.value})}
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Last Name
                </label>
                <input
                  type="text"
                  required
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  value={formData.last_name}
                  onChange={(e) => setFormData({...formData, last_name: e.target.value})}
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Account Type
                </label>
                <select
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  value={formData.role}
                  onChange={(e) => setFormData({...formData, role: e.target.value})}
                >
                  <option value="candidate">Candidate</option>
                  <option value="hr">HR Manager</option>
                </select>
              </div>
            </>
          )}

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Email
            </label>
            <input
              type="email"
              required
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              value={formData.email}
              onChange={(e) => setFormData({...formData, email: e.target.value})}
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Password
            </label>
            <input
              type="password"
              required
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              value={formData.password}
              onChange={(e) => setFormData({...formData, password: e.target.value})}
            />
          </div>

          {error && (
            <div className="bg-red-50 text-red-600 p-3 rounded-lg text-sm">
              {error}
            </div>
          )}

          <button
            type="submit"
            className="w-full bg-blue-600 text-white py-2 rounded-lg hover:bg-blue-700 transition-colors font-medium"
          >
            {isLogin ? 'Sign In' : 'Create Account'}
          </button>
        </form>

        <div className="mt-6 text-center">
          <button
            onClick={() => setIsLogin(!isLogin)}
            className="text-blue-600 hover:underline text-sm"
          >
            {isLogin ? "Don't have an account? Sign up" : 'Already have an account? Sign in'}
          </button>
        </div>
      </div>
    </div>
  );
};

// ---------------- Candidate Dashboard ----------------
const CandidateDashboard = () => {
  const { token, user, logout } = useAuth();
  const navigate = useNavigate();

  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);

  // separate states
  const [storedSkills, setStoredSkills] = useState(null);
  const [generatedSession, setGeneratedSession] = useState(null);

  // load skills + latest session at mount
  useEffect(() => {
    const init = async () => {
      try {
        // 1) get stored skills
        const r1 = await fetch(`${API_URL}/api/candidate/skills`, {
          headers: { Authorization: `Bearer ${token}` }
        });
        const d1 = await r1.json();
        if (d1.skills) setStoredSkills(d1.skills);

        // 2) get latest session (backend must expose /api/candidate/latest-session)
        const r2 = await fetch(`${API_URL}/api/candidate/latest-session`, {
          headers: { Authorization: `Bearer ${token}` }
        });
        if (r2.ok) {
          const d2 = await r2.json();
          if (d2.found) {
            setGeneratedSession({
              session_id: d2.session_id,
              quiz: d2.quiz,
              skills: d2.skills,
              start_time: d2.start_time
            });
            console.log("Loaded latest session:", d2.session_id);
          }
        }
      } catch (err) {
        console.error("init error", err);
      }
    };
    init();
  }, [token]);

  const handleUpload = async () => {
    if (!file) return;
    setUploading(true);
    const fd = new FormData();
    fd.append("file", file);
    try {
      const res = await fetch(`${API_URL}/api/candidate/upload-cv`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: fd
      });
      const data = await res.json();
      console.log("upload-cv response:", data);
      if (!res.ok) {
        alert(data.detail || "Upload failed");
        return;
      }
      // store generated session and skills separately
      setGeneratedSession({ session_id: data.session_id, quiz: data.quiz, skills: data.skills });
      if (data.skills) setStoredSkills(data.skills);
      alert("Quiz generated!");
    } catch (err) {
      console.error("upload error", err);
      alert("Upload error: " + err.message);
    } finally {
      setUploading(false);
    }
  };
  const startQuizHandler = async () => {
  try {
    // call backend to generate a fresh quiz for this candidate
    const res = await fetch(`${API_URL}/api/quiz/start`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      }
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      alert("Failed to start quiz: " + (err.detail || res.statusText));
      return;
    }

    const data = await res.json();
    // data: { session_id, quiz }
    if (!data.quiz || !data.session_id) {
      alert("No quiz was generated. Please try again or contact admin.");
      return;
    }
    // navigate to quiz page and pass quiz in state for immediate rendering
    navigate(`/quiz/${data.session_id}`, { state: { quiz: data.quiz }});
  } catch (err) {
    alert("Error starting quiz: " + err.message);
  }
};
  
  // const handleStartQuiz = async () => {
  //   // prefer in-memory generatedSession with quiz
  //   if (generatedSession && generatedSession.session_id && generatedSession.quiz) {
  //     navigate(`/quiz/${generatedSession.session_id}`, { state: { quiz: generatedSession.quiz } });
  //     return;
  //   }

  //   // try latest-session endpoint
  //   try {
  //     const res = await fetch(`${API_URL}/api/candidate/latest-session`, {
  //       headers: { Authorization: `Bearer ${token}` }
  //     });
  //     const body = await res.json();
  //     if (res.ok && body.found) {
  //       if (body.quiz) {
  //         setGeneratedSession({ session_id: body.session_id, quiz: body.quiz, skills: body.skills });
  //         navigate(`/quiz/${body.session_id}`, { state: { quiz: body.quiz } });
  //         return;
  //       } else {
  //         alert("Une session existe mais le contenu du quiz est manquant. Ré-upload ton CV ou contacte l'admin.");
  //         return;
  //       }
  //     }
  //     alert("No quiz data found. Please upload your CV to generate a quiz.");
  //   } catch (err) {
  //     console.error("start quiz error", err);
  //     alert("Could not fetch latest session: " + err.message);
  //   }
  // };
  

  return (
    <div className="min-h-screen bg-slate-50">
      <nav className="bg-white shadow p-4 flex justify-between items-center">
        <div className="flex items-center gap-3">
          <User className="w-8 h-8 text-blue-600" />
          <div>
            <div className="font-bold">{user?.first_name} {user?.last_name}</div>
            <div className="text-sm text-gray-600">Candidate dashboard</div>
          </div>
        </div>
        <div>
          <button onClick={logout} className="px-3 py-1 border rounded">Logout</button>
        </div>
      </nav>

      <main className="max-w-4xl mx-auto p-6">
        <section className="bg-white p-6 rounded shadow mb-6">
          <h3 className="text-xl font-semibold mb-4">Upload your CV</h3>
          <div className="mb-4">
            <input id="cvfile" type="file" accept=".pdf,.txt,.docx" onChange={(e) => setFile(e.target.files[0])} />
          </div>
          <button onClick={handleUpload} disabled={!file || uploading} className="bg-blue-600 text-white px-4 py-2 rounded">
            {uploading ? "Processing..." : "Upload & Generate Quiz"}
          </button>
        </section>

        {storedSkills && (
          <section className="bg-white p-6 rounded shadow mb-6">
            <h3 className="font-semibold">Extracted skills</h3>
            <div className="mt-3">
              {storedSkills.technical_skills?.length > 0 && (
                <div className="mb-2">
                  <div className="font-medium">Technical</div>
                  <div className="flex gap-2 mt-2 flex-wrap">
                    {storedSkills.technical_skills.map((s, i) => <span key={i} className="px-2 py-1 bg-blue-50 rounded">{s.name} {s.level ? `(${s.level})` : ""}</span>)}
                  </div>
                </div>
              )}
              {storedSkills.soft_skills?.length > 0 && (
                <div className="mb-2">
                  <div className="font-medium">Soft</div>
                  <div className="flex gap-2 mt-2 flex-wrap">
                    {storedSkills.soft_skills.map((s, i) => <span key={i} className="px-2 py-1 bg-green-50 rounded">{s.name}</span>)}
                  </div>
                </div>
              )}
            </div>
          </section>
        )}

        <section className="bg-white p-6 rounded shadow">
          <h3 className="font-semibold mb-2">Quiz Ready</h3>
          <p className="text-sm text-gray-600 mb-4">Click Start Quiz to take your personalized quiz.</p>
          <button onClick={startQuizHandler} className="bg-green-600 text-white px-4 py-2 rounded">Start Quiz</button>
        </section>
      </main>
    </div>
  );
};


// HR Dashboard
const HRDashboard = () => {
  const [activeTab, setActiveTab] = useState('upload');
  const [file, setFile] = useState(null);
  const [candidateEmail, setCandidateEmail] = useState('');
  const [focusSkills, setFocusSkills] = useState('');
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState(null);
  const [inviteEmail, setInviteEmail] = useState('');
  const [inviteSkills, setInviteSkills] = useState('');
  const [inviteInstructions, setInviteInstructions] = useState('');
  const [candidates, setCandidates] = useState([]);
  const { token, user, logout } = useAuth();

  useEffect(() => {
    if (activeTab === 'candidates') {
      fetchCandidates();
    }
  }, [activeTab]);

  const fetchCandidates = async () => {
    try {
      const res = await fetch(`${API_URL}/api/hr/candidates`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      const data = await res.json();
      setCandidates(data.candidates || []);
    } catch (err) {
      console.error('Failed to fetch candidates:', err);
    }
  };

  const handleUploadCV = async () => {
    if (!file || !candidateEmail) {
      alert('Please provide both CV and candidate email');
      return;
    }

    setUploading(true);
    const formData = new FormData();
    formData.append('file', file);
    formData.append('candidate_email', candidateEmail);
    if (focusSkills) {
      formData.append('focus_skills', focusSkills);
    }

    try {
      const res = await fetch(`${API_URL}/api/hr/upload-candidate-cv`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
        body: formData
      });

      const data = await res.json();
      setResult(data);
      alert('Quiz generated! Share this link with candidate:\n' + data.quiz_link);
    } catch (err) {
      alert('Upload failed: ' + err.message);
    } finally {
      setUploading(false);
    }
  };

  const handleSendInvite = async () => {
    if (!inviteEmail) {
      alert('Please provide candidate email');
      return;
    }

    try {
      const res = await fetch(`${API_URL}/api/hr/create-invitation`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          candidate_email: inviteEmail,
          focus_skills: inviteSkills ? inviteSkills.split(',').map(s => s.trim()) : null,
          custom_instructions: inviteInstructions || null
        })
      });

      const data = await res.json();
      alert('Invitation created! Share this link:\n' + data.invitation_link);
      setInviteEmail('');
      setInviteSkills('');
      setInviteInstructions('');
    } catch (err) {
      alert('Failed to create invitation: ' + err.message);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <nav className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 py-4 flex justify-between items-center">
          <div className="flex items-center gap-3">
            <Users className="w-8 h-8 text-indigo-600" />
            <div>
              <h1 className="text-xl font-bold text-gray-800">
                {user.first_name} {user.last_name}
              </h1>
              <p className="text-sm text-gray-600">HR Dashboard</p>
            </div>
          </div>
          <button
            onClick={logout}
            className="flex items-center gap-2 px-4 py-2 text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <LogOut className="w-4 h-4" />
            Logout
          </button>
        </div>
      </nav>

      <div className="max-w-6xl mx-auto p-6">
        <div className="bg-white rounded-lg shadow-md mb-6">
          <div className="flex border-b">
            <button
              onClick={() => setActiveTab('upload')}
              className={`flex-1 px-6 py-4 font-medium transition-colors ${
                activeTab === 'upload'
                  ? 'border-b-2 border-indigo-600 text-indigo-600'
                  : 'text-gray-600 hover:text-gray-800'
              }`}
            >
              <Upload className="w-5 h-5 inline mr-2" />
              Upload CV
            </button>
            <button
              onClick={() => setActiveTab('invite')}
              className={`flex-1 px-6 py-4 font-medium transition-colors ${
                activeTab === 'invite'
                  ? 'border-b-2 border-indigo-600 text-indigo-600'
                  : 'text-gray-600 hover:text-gray-800'
              }`}
            >
              <Send className="w-5 h-5 inline mr-2" />
              Send Invitation
            </button>
            <button
              onClick={() => setActiveTab('candidates')}
              className={`flex-1 px-6 py-4 font-medium transition-colors ${
                activeTab === 'candidates'
                  ? 'border-b-2 border-indigo-600 text-indigo-600'
                  : 'text-gray-600 hover:text-gray-800'
              }`}
            >
              <BarChart3 className="w-5 h-5 inline mr-2" />
              View Results
            </button>
          </div>

          <div className="p-6">
            {activeTab === 'upload' && (
              <div className="space-y-4">
                <h2 className="text-2xl font-bold text-gray-800 mb-4">
                  Upload Candidate CV
                </h2>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Candidate Email *
                  </label>
                  <input
                    type="email"
                    required
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                    value={candidateEmail}
                    onChange={(e) => setCandidateEmail(e.target.value)}
                    placeholder="candidate@example.com"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Focus Skills (optional)
                  </label>
                  <input
                    type="text"
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                    value={focusSkills}
                    onChange={(e) => setFocusSkills(e.target.value)}
                    placeholder="Python, Leadership, Communication (comma-separated)"
                  />
                  <p className="text-sm text-gray-500 mt-1">
                    Leave empty to test all extracted skills
                  </p>
                </div>

                <div className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center">
                  <input
                    type="file"
                    accept=".txt,.pdf,.doc,.docx"
                    onChange={(e) => setFile(e.target.files[0])}
                    className="hidden"
                    id="hr-cv-upload"
                  />
                  <label htmlFor="hr-cv-upload" className="cursor-pointer">
                    <FileText className="w-12 h-12 text-gray-400 mx-auto mb-3" />
                    <p className="text-gray-600 mb-2">
                      {file ? file.name : 'Click to upload candidate CV'}
                    </p>
                    <p className="text-sm text-gray-500">
                      Supports TXT, PDF, DOC, DOCX
                    </p>
                  </label>
                </div>

                <button
                  onClick={handleUploadCV}
                  disabled={!file || !candidateEmail || uploading}
                  className="w-full bg-indigo-600 text-white py-3 rounded-lg hover:bg-indigo-700 transition-colors disabled:bg-gray-400 disabled:cursor-not-allowed font-medium"
                >
                  {uploading ? 'Processing...' : 'Generate Quiz & Get Link'}
                </button>

                {result && (
                  <div className="mt-6 bg-green-50 border border-green-200 rounded-lg p-4">
                    <h3 className="font-semibold text-green-800 mb-2">
                      Quiz Generated Successfully!
                    </h3>
                    <p className="text-sm text-green-700 mb-3">
                      Share this link with the candidate:
                    </p>
                    <div className="bg-white p-3 rounded border border-green-300 font-mono text-sm break-all">
                      {result.quiz_link}
                    </div>
                  </div>
                )}
              </div>
            )}

            {activeTab === 'invite' && (
              <div className="space-y-4">
                <h2 className="text-2xl font-bold text-gray-800 mb-4">
                  Send Quiz Invitation
                </h2>
                <p className="text-gray-600 mb-4">
                  Invite a candidate to upload their CV and take a quiz
                </p>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Candidate Email *
                  </label>
                  <input
                    type="email"
                    required
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                    value={inviteEmail}
                    onChange={(e) => setInviteEmail(e.target.value)}
                    placeholder="candidate@example.com"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Focus Skills (optional)
                  </label>
                  <input
                    type="text"
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                    value={inviteSkills}
                    onChange={(e) => setInviteSkills(e.target.value)}
                    placeholder="Python, Java, Leadership"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Custom Instructions (optional)
                  </label>
                  <textarea
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                    rows="3"
                    value={inviteInstructions}
                    onChange={(e) => setInviteInstructions(e.target.value)}
                    placeholder="Any specific instructions for the candidate..."
                  />
                </div>

                <button
                  onClick={handleSendInvite}
                  disabled={!inviteEmail}
                  className="w-full bg-indigo-600 text-white py-3 rounded-lg hover:bg-indigo-700 transition-colors disabled:bg-gray-400 disabled:cursor-not-allowed font-medium flex items-center justify-center gap-2"
                >
                  <Send className="w-5 h-5" />
                  Create Invitation
                </button>
              </div>
            )}

            {activeTab === 'candidates' && (
              <div>
                <h2 className="text-2xl font-bold text-gray-800 mb-4">
                  Candidate Results
                </h2>

                {candidates.length === 0 ? (
                  <p className="text-gray-600 text-center py-8">
                    No candidate results yet
                  </p>
                ) : (
                  <div className="space-y-4">
                    {candidates.map((candidate) => (
                      <div
                        key={candidate.session_id}
                        className="border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow"
                      >
                        <div className="flex justify-between items-start mb-3">
                          <div>
                            <h3 className="font-semibold text-lg text-gray-800">
                              {candidate.first_name} {candidate.last_name}
                            </h3>
                            <p className="text-sm text-gray-600">{candidate.email}</p>
                          </div>
                          <div className="text-right">
                            <div className="text-2xl font-bold text-indigo-600">
                              {candidate.total_score?.toFixed(1) || 'N/A'}%
                            </div>
                            <div className="text-sm text-gray-600">
                              Overall Score
                            </div>
                          </div>
                        </div>

                        <div className="grid grid-cols-2 gap-4 mt-4 pt-4 border-t">
                          <div>
                            <p className="text-sm text-gray-600">Cognitive Score</p>
                            <p className="font-semibold text-gray-800">
                              {candidate.cognitive_score?.toFixed(1) || 'N/A'}%
                            </p>
                          </div>
                          <div>
                            <p className="text-sm text-gray-600">Date</p>
                            <p className="font-semibold text-gray-800">
                              {candidate.start_time
                                ? new Date(candidate.start_time).toLocaleDateString()
                                : 'N/A'}
                            </p>
                          </div>
                        </div>

                        {candidate.end_time ? (
                          <div className="mt-3 flex items-center gap-2 text-green-600">
                            <Award className="w-4 h-4" />
                            <span className="text-sm font-medium">Completed</span>
                          </div>
                        ) : (
                          <div className="mt-3 flex items-center gap-2 text-yellow-600">
                            <span className="text-sm font-medium">In Progress</span>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

// Main App
const App = () => {
  const { user } = useAuth();

  if (!user) {
    return <AuthForm />;
  }

  return user.role === 'hr' ? <HRDashboard /> : <CandidateDashboard />;
};

// Export with Provider
export default function QuizPlatform() {
  return (
    <AuthProvider>
        <Routes>
          <Route path="/" element={<App />} />
          <Route path="/quiz/:sessionId" element={<QuizPage />} />
          <Route path="/invite/:sessionId" element={<InvitePage />} />
        </Routes>
    </AuthProvider>
  );
}