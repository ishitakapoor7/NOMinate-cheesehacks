import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';

const TakeOutPage = () => {
  const [restaurants, setRestaurants] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    const fetchTakeOutPlaces = async () => {
      try {
        const response = await axios.post(
          'http://localhost:5001/takeout',
          {},
          { withCredentials: true }
        );
        setRestaurants(response.data.restaurants || []);
      } catch (error) {
        console.error('Error fetching take-out places:', error);
        alert('Failed to fetch take-out places. Please try again.');
      } finally {
        setIsLoading(false);
      }
    };
    fetchTakeOutPlaces();
  }, []);

  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-gradient-to-br from-orange-50 via-amber-50 to-rose-50 p-4">
      <div className="w-full max-w-2xl bg-white/80 backdrop-blur p-8 rounded-3xl shadow-xl animate-fade-in-up">
        <h2 className="text-3xl font-playfair font-extrabold text-gray-800 mb-6">Nearby spots 🛵</h2>

        {isLoading ? (
          <p className="text-gray-500">Finding restaurants near you…</p>
        ) : restaurants.length === 0 ? (
          <p className="text-gray-500">No restaurants found.</p>
        ) : (
          <ul className="space-y-3">
            {restaurants.map((r, index) => (
              <li
                key={index}
                className="border-2 border-gray-100 rounded-2xl p-5 hover:border-orange-300 transition-colors"
              >
                <a
                  href={r.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-lg font-extrabold text-orange-600 hover:underline"
                >
                  {r.name}
                </a>
                <div className="text-sm text-gray-600 mt-1 flex gap-3 flex-wrap font-semibold">
                  {r.rating && r.rating !== 'N/A' && <span>⭐ {r.rating}</span>}
                  {r.price && <span>{r.price}</span>}
                  {r.address && <span className="text-gray-400">{r.address}</span>}
                </div>
              </li>
            ))}
          </ul>
        )}

        <button
          onClick={() => navigate('/generatedresponse')}
          className="mt-8 px-6 py-3 bg-gray-100 text-gray-700 font-bold rounded-xl hover:bg-gray-200 transition-colors"
        >
          ← Back to recommendation
        </button>
      </div>
    </div>
  );
};

export default TakeOutPage;
