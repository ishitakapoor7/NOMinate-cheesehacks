import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';

const Response = () => {
  const [recommendation, setRecommendation] = useState('');
  const [cuisine, setCuisine] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    const fetchRecommendation = async () => {
      try {
        const response = await axios.get('http://localhost:5001/generatedresponse', {
          withCredentials: true,
        });
        setRecommendation(response.data.recommendation);
        setCuisine(response.data.cuisine || '');
      } catch (error) {
        console.error('Error fetching recommendation:', error);
        setRecommendation('No recommendation available.');
      } finally {
        setIsLoading(false);
      }
    };
    fetchRecommendation();
  }, []);

  const handleFeedbackClick = () => {
    navigate('/feedback', { state: { recommendation } });
  };

  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-gradient-to-br from-orange-50 via-amber-50 to-rose-50 p-4">
      <p className="text-gray-500 font-semibold mb-3 animate-fade-in-up">We think you'll love…</p>

      {/* Recommendation card */}
      <div className="relative w-full max-w-2xl bg-gradient-to-r from-orange-500 to-rose-500 text-white p-10 rounded-3xl shadow-xl mb-8 text-center animate-fade-in-up">
        <button
          onClick={handleFeedbackClick}
          title="Not feeling it? Give feedback"
          className="absolute top-4 right-4 bg-white/20 hover:bg-white/30 text-white w-9 h-9 flex items-center justify-center rounded-full transition-colors"
        >
          &times;
        </button>
        {isLoading ? (
          <p className="text-2xl font-bold">Cooking up a pick… 🍳</p>
        ) : (
          <>
            <h2 className="text-4xl font-playfair font-extrabold mb-2">{recommendation}</h2>
            {cuisine && (
              <span className="inline-block mt-2 px-4 py-1 bg-white/20 rounded-full text-sm font-bold">
                {cuisine} cuisine
              </span>
            )}
          </>
        )}
      </div>

      {/* Action buttons */}
      <div className="flex gap-4">
        <button
          onClick={() => navigate('/cooking')}
          className="px-8 py-4 bg-white text-gray-800 font-bold rounded-2xl shadow-md hover:shadow-lg hover:-translate-y-0.5 transition-all border-2 border-transparent hover:border-orange-300"
        >
          🍳 Cook it
        </button>
        <button
          onClick={() => navigate('/takeout')}
          className="px-8 py-4 bg-white text-gray-800 font-bold rounded-2xl shadow-md hover:shadow-lg hover:-translate-y-0.5 transition-all border-2 border-transparent hover:border-orange-300"
        >
          🛵 Order out
        </button>
      </div>

      <button
        onClick={handleFeedbackClick}
        className="mt-6 text-gray-500 font-semibold hover:text-orange-500 transition-colors"
      >
        Show me something else →
      </button>
    </div>
  );
};

export default Response;
