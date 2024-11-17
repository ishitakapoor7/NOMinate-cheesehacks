import React, { useState } from "react";
import { useNavigate } from "react-router-dom";

const FeedbackPage = () => {
  const [selectedOption, setSelectedOption] = useState(""); // Track selected feedback option
  const [otherFeedback, setOtherFeedback] = useState(""); // Track "Other" feedback text
  const navigate = useNavigate(); // For navigation

  const handleOptionChange = (e) => {
    setSelectedOption(e.target.value);
    if (e.target.value !== "Other") {
      setOtherFeedback(""); // Clear "Other" feedback if another option is selected
    }
  };

  const handleNextRecommendation = () => {
    const feedback = selectedOption === "Other" ? otherFeedback : selectedOption;
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
        {/* Radio Options */}
        {["I ate this recently", "I do not like this dish", "Other"].map((option) => (
          <label key={option} className="block mb-2 text-left">
            <input
              type="radio"
              name="feedback"
              value={option}
              checked={selectedOption === option}
              onChange={handleOptionChange}
              className="mr-2"
            />
            {option}
          </label>
        ))}

        {/* Textarea for "Other" Option */}
        {selectedOption === "Other" && (
          <textarea
            value={otherFeedback}
            onChange={(e) => setOtherFeedback(e.target.value)}
            placeholder="Please provide more details..."
            className="w-full h-32 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none mt-4"
          ></textarea>
        )}

        {/* Next Recommendation Button */}
        <button
          onClick={handleNextRecommendation}
          disabled={selectedOption === "Other" && !otherFeedback} // Disable if "Other" is selected but no input
          className={`mt-4 px-6 py-2 text-white rounded-lg shadow-md ${
            selectedOption === "Other" && !otherFeedback
              ? "bg-gray-400 cursor-not-allowed"
              : "bg-blue-500 hover:bg-blue-600"
          }`}
        >
          Next Recommendation
        </button>
      </div>
    </div>
  );
};

export default FeedbackPage;
