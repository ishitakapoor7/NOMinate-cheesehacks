import React from 'react';
import LogInPage from './components/LogInPage'
import SignUpPage from './components/SignUpPage'
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import ProfileSetUp from './components/ProfileSetUp';
import Response from './components/Response'
import FeedbackPage from './components/FeedbackPage'


const App = () => {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<LogInPage/>} />
        <Route path="/signup" element={<SignUpPage/>} />
        <Route path="/profilesetup" element={<ProfileSetUp />} />
        <Route path="/generatedresponse" element={<Response />} />
        <Route path="/reasonforcross" element={<FeedbackPage />} />
        <Route path="*" element={<LogInPage />} /> {/* Fallback for unmatched routes */}
      </Routes>
    </Router>
  );
};

export default App
