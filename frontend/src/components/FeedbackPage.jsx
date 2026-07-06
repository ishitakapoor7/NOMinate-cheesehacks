import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import axios from "axios";

// Map friendly UI labels to the reason strings the backend acts on.
const REASON_MAP = {
  "I ate this recently": "Recently Eaten",
  "I do not like this dish": "I just don't like it",
};

const OPTIONS = [
  { label: "I ate this recently", emoji: "🔁" },
  { label: "I do not like this dish", emoji: "👎" },
  { label: "Other", emoji: "✏️" },
];

const FeedbackPage = () => {
  const [selectedOption, setSelectedOption] = useState("");
  const [otherFeedback, setOtherFeedback] = useState("");
  const navigate = useNavigate();

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

  const disabled = !selectedOption || (selectedOption === "Other" && !otherFeedback);

  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-gradient-to-br from-orange-50 via-amber-50 to-rose-50 p-4">
      <div className="bg-white/80 backdrop-blur p-8 rounded-3xl shadow-xl w-full max-w-md animate-fade-in-up">
        <h2 className="text-2xl font-extrabold text-gray-800 mb-1 text-center">
          Not quite right?
        </h2>
        <p className="text-gray-500 text-center mb-6 font-semibold">
          Tell us why and we'll pick again.
        </p>

        <div className="space-y-3">
          {OPTIONS.map((option) => (
            <button
              key={option.label}
              type="button"
              onClick={() => {
                setSelectedOption(option.label);
                if (option.label !== "Other") setOtherFeedback("");
              }}
              className={`flex items-center gap-3 w-full p-4 rounded-2xl border-2 text-left font-bold transition-all duration-200
                ${selectedOption === option.label
                  ? "border-orange-500 bg-orange-50 text-orange-700 shadow-md"
                  : "border-gray-200 bg-white text-gray-700 hover:border-orange-300"}`}
            >
              <span className="text-xl">{option.emoji}</span>
              {option.label}
            </button>
          ))}
        </div>

        {selectedOption === "Other" && (
          <textarea
            value={otherFeedback}
            onChange={(e) => setOtherFeedback(e.target.value)}
            placeholder="Please provide more details…"
            className="w-full h-28 px-4 py-3 mt-4 rounded-xl border-2 border-gray-200 focus:outline-none focus:border-orange-400 resize-none"
          ></textarea>
        )}

        <button
          onClick={handleNextRecommendation}
          disabled={disabled}
          className={`mt-6 w-full py-3 text-white font-bold rounded-xl shadow-md transition-all ${
            disabled
              ? "bg-gray-300 cursor-not-allowed"
              : "bg-gradient-to-r from-orange-500 to-rose-500 hover:opacity-90"
          }`}
        >
          Pick something else →
        </button>
      </div>
    </div>
  );
};

export default FeedbackPage;
