import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import axios from "axios";

// Map friendly UI labels to the reason strings the backend acts on.
const REASON_MAP = {
  "I ate this recently": "Recently Eaten",
  "I do not like this dish": "I just don't like it",
};

const FeedbackPage = () => {
  const [selectedOption, setSelectedOption] = useState("");
  const [otherFeedback, setOtherFeedback] = useState("");
  const navigate = useNavigate();

  const handleOptionChange = (e) => {
    setSelectedOption(e.target.value);
    if (e.target.value !== "Other") {
      setOtherFeedback("");
    }
  };

  const handleNextRecommendation = async () => {
    const reason =
      selectedOption === "Other"
        ? otherFeedback
        : REASON_MAP[selectedOption] || selectedOption;

    try {
      await axios.post(
        "http://localhost:5001/feedback",
        { feedback_reason: reason },
        { withCredentials: true }
      );
    } catch (error) {
      console.error("Error sending feedback:", error);
    }

    navigate("/generatedresponse");
  };

  return (
    <div className="flex flex-col items-center justify-center h-screen bg-gray-100">
      <div className="bg-white p-6 rounded-lg shadow-md w-full max-w-md text-center">
        <h2 className="text-xl font-semibold mb-4">
          Help us improve our recommendations for you!
        </h2>
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

        {selectedOption === "Other" && (
          <textarea
            value={otherFeedback}
            onChange={(e) => setOtherFeedback(e.target.value)}
            placeholder="Please provide more details..."
            className="w-full h-32 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none mt-4"
          ></textarea>
        )}

        <button
          onClick={handleNextRecommendation}
          disabled={!selectedOption || (selectedOption === "Other" && !otherFeedback)}
          className={`mt-4 px-6 py-2 text-white rounded-lg shadow-md ${
            !selectedOption || (selectedOption === "Other" && !otherFeedback)
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
