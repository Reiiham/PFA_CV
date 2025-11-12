// frontend/src/main.jsx
import './index.css'  // ← This line!
import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import QuizPlatform from './App';

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <BrowserRouter>
      <QuizPlatform />
    </BrowserRouter>
  </React.StrictMode>
);
