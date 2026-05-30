import React, { useState, useEffect } from 'react';
import axios from 'axios';

const CookingPage = () => {
  const [ingredients, setIngredients] = useState([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchIngredients = async () => {
      try {
        const response = await axios.post(
          'http://localhost:5001/cooking',
          {},
          { withCredentials: true }
        );
        setIngredients(response.data.ingredients || []);
      } catch (error) {
        console.error('Error fetching ingredients:', error);
        alert('Failed to fetch ingredients. Please try again.');
      } finally {
        setIsLoading(false);
      }
    };

    fetchIngredients();
  }, []);

  const haveCount = ingredients.filter((i) => i.available).length;

  return (
    <div className="flex flex-col items-center justify-center h-screen bg-gray-100">
      <div className="w-full max-w-3xl bg-white p-6 rounded-lg shadow-md">
        <h2 className="text-2xl font-bold mb-1">Ingredients needed</h2>
        {!isLoading && ingredients.length > 0 && (
          <p className="text-sm text-gray-500 mb-4">
            You already have {haveCount} of {ingredients.length} ingredients.
          </p>
        )}
        {isLoading ? (
          <p>Loading...</p>
        ) : (
          <ul className="space-y-2">
            {ingredients.map((ingredient, index) => (
              <li key={index} className="flex items-center gap-2">
                {ingredient.available ? (
                  <span className="text-green-600">✓</span>
                ) : (
                  <span className="text-gray-400">🛒</span>
                )}
                <span className={ingredient.available ? 'text-green-700' : 'text-gray-700'}>
                  {ingredient.name}
                </span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
};

export default CookingPage;
