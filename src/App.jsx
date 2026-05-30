import React from 'react';
import LogInPage from './components/LogInPage'
import SignUpPage from './components/SignUpPage'
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import ProfileSetUp from './components/ProfileSetUp';
import Response from './components/Response'
import FeedbackPage from './components/FeedbackPage'
import CookingPage from './components/CookingPage';
import TakeOutPage from './components/TakeOutPage';

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<LogInPage/>} />
        <Route path="/signup" element={<SignUpPage/>} />
        <Route path="/profilesetup" element={<ProfileSetUp />} />
        <Route path="/generatedresponse" element={<Response />} />
        <Route path="/feedback" element={<FeedbackPage />} />
        <Route path="/cooking" element={<CookingPage />} />
        <Route path="/takeout" element={<TakeOutPage />} />
        <Route path="*" element={<LogInPage />} />
      </Routes>
    </Router>
  );
};

export default App
