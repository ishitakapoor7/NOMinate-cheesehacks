import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';

const Response = () => {
  const [recommendation, setRecommendation] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    const fetchRecommendation = async () => {
      try {
        const response = await axios.get('http://localhost:5001/generatedresponse', {
          withCredentials: true, 
        });
        setRecommendation(response.data.recommendation);
      } catch (error) {
        console.error('Error fetching recommendation:', error);
        setRecommendation('No recommendation available.');
      } finally {
        setIsLoading(false);
      }
    };
    fetchRecommendation();
  }, []);

  return (
    <div className="flex flex-col items-center justify-center h-screen bg-gray-100">
      {/* AI Recommendation Box */}
      <div className="relative w-full max-w-3xl bg-blue-500 text-white p-6 rounded-lg shadow-md mb-6 text-center">
        <h2 className="text-2xl font-bold mb-2">Our Recommendation</h2>
        <p className="text-lg">{isLoading ? 'Loading...' : recommendation}</p>
      </div>

      {/* Buttons */}
      <div className="flex space-x-4">
        <button
          onClick={() => navigate('/cooking')}
          className="px-6 py-3 bg-green-500 text-white rounded-lg shadow-md hover:bg-green-600"
        >
          Cooking
        </button>
        <button
          onClick={() => navigate('/takeout')}
          className="px-6 py-3 bg-yellow-500 text-white rounded-lg shadow-md hover:bg-yellow-600"
        >
          Take-Out
        </button>
      </div>
    </div>
  );
};

export default Response;
