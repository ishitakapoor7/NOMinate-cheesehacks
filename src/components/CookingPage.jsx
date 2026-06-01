import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';

const CookingPage = () => {
  const [ingredients, setIngredients] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const navigate = useNavigate();

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
    <div className="min-h-screen flex flex-col items-center justify-center bg-gradient-to-br from-orange-50 via-amber-50 to-rose-50 p-4">
      <div className="w-full max-w-2xl bg-white/80 backdrop-blur p-8 rounded-3xl shadow-xl animate-fade-in-up">
        <h2 className="text-3xl font-playfair font-extrabold text-gray-800 mb-1">Your shopping list 🧺</h2>
        {!isLoading && ingredients.length > 0 && (
          <p className="text-sm font-semibold text-green-600 mb-6">
            You already have {haveCount} of {ingredients.length} ingredients!
          </p>
        )}

        {isLoading ? (
          <p className="text-gray-500">Gathering ingredients…</p>
        ) : (
          <ul className="space-y-2">
            {ingredients.map((ingredient, index) => (
              <li
                key={index}
                className={`flex items-center gap-3 px-4 py-3 rounded-xl font-semibold
                  ${ingredient.available
                    ? 'bg-green-50 text-green-800'
                    : 'bg-gray-50 text-gray-700'}`}
              >
                <span className="text-lg">{ingredient.available ? '✅' : '🛒'}</span>
                {ingredient.name}
                {ingredient.available && (
                  <span className="ml-auto text-xs font-bold text-green-600">have it</span>
                )}
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

export default CookingPage;
