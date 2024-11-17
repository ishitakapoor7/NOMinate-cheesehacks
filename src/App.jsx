import React from 'react';
import LogInPage from './components/LogInPage'
import SignUpPage from './components/SignUpPage'
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import ProfileSetUp from './components/ProfileSetUp';
import Response from './components/Response'
import FeedbackPage from './components/FeedbackPage'
import axios from 'axios';
import CookingPage from './components/CookingPage';
import TakeOutPage from './components/TakeOutPage';
import { useState } from 'react';
import { useEffect } from 'react';


function App() {
  const [recommendation, setRecommendation] = useState(''); // Store recommendation
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchRecommendation = async () => {
      try {
        const response = await axios.get('http://localhost:5001/generatedresponse');
        setRecommendation(response.data.recommendation);
      } catch (error) {
        console.error('Error fetching recommendation:', error);
      } finally {
        setIsLoading(false);
      }
    };
    fetchRecommendation();
  }, []);

  return (
    <Router>
      <Routes>
        <Route path="/" element={<LogInPage/>} />
        <Route path="/signup" element={<SignUpPage/>} />
        <Route path="/profilesetup" element={<ProfileSetUp />} />
        <Route
          path="/generatedresponse"
          element={<Response recommendation={isLoading ? 'Loading...' : recommendation} />}
        />
        <Route path="/feedback" element={<FeedbackPage />} />
        <Route path="/cooking" element={<CookingPage />} />
        <Route path="/takeout" element={<TakeOutPage />} />
        <Route path="*" element={<LogInPage />} /> {/* Fallback for unmatched routes */}
      </Routes>
    </Router>
  );
};

export default App
