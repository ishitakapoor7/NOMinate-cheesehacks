import React, { useState, useEffect } from 'react';
import axios from 'axios';

const TakeOutPage = () => {
  const [restaurants, setRestaurants] = useState([]);
  const [isLoading, setIsLoading] = useState(true);

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
    <div className="flex flex-col items-center justify-center h-screen bg-gray-100">
      <div className="w-full max-w-3xl bg-white p-6 rounded-lg shadow-md">
        <h2 className="text-2xl font-bold mb-4">Nearby Restaurants</h2>
        {isLoading ? (
          <p>Loading...</p>
        ) : restaurants.length === 0 ? (
          <p className="text-gray-500">No restaurants found.</p>
        ) : (
          <ul className="space-y-3">
            {restaurants.map((r, index) => (
              <li key={index} className="border border-gray-200 rounded-lg p-4">
                <a
                  href={r.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-lg font-semibold text-blue-600 hover:underline"
                >
                  {r.name}
                </a>
                <div className="text-sm text-gray-600 mt-1 flex gap-3 flex-wrap">
                  {r.rating && r.rating !== 'N/A' && <span>⭐ {r.rating}</span>}
                  {r.price && <span>{r.price}</span>}
                  {r.address && <span>{r.address}</span>}
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
};

export default TakeOutPage;
