import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';

const FeedbackPage = () => {
  const [feedback, setFeedback] = useState(""); // Track user's feedback
  const navigate = useNavigate(); // For navigation

  const handleFeedbackChange = (e) => {
    setFeedback(e.target.value);
  };

  const handleNextRecommendation = () => {
    console.log("User Feedback:", feedback); // Send this to backend when integrated
    navigate("/generatedresponse"); // Navigate to the next recommendation page
  };

  return (
    <div className="flex flex-col items-center justify-center h-screen bg-gray-100">
      {/* Feedback Box */}
      <div className="bg-white p-6 rounded-lg shadow-md w-full max-w-md text-center">
        <h2 className="text-xl font-semibold mb-4">
        Help us improve our recommendations for you!
        </h2>
        <textarea
          value={feedback}
          onChange={handleFeedbackChange}
          placeholder="Why did you say no to our recommendation?"
          className="w-full h-32 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
        ></textarea>
        <button
          onClick={handleNextRecommendation}
          className="mt-4 px-6 py-2 bg-blue-500 text-white rounded-lg shadow-md hover:bg-blue-600"
        >
          Next Recommendation
        </button>
      </div>
    </div>
  );
};

export default FeedbackPage;
