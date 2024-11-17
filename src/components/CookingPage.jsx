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
          {
            withCredentials: true, // Include credentials
          }
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

  return (
    <div className="flex flex-col items-center justify-center h-screen bg-gray-100">
      <div className="w-full max-w-3xl bg-white p-6 rounded-lg shadow-md">
        <h2 className="text-2xl font-bold mb-4">Ingredients needed</h2>
        {isLoading ? (
          <p>Loading...</p>
        ) : (
          <ul className="list-disc pl-5">
            {ingredients.map((ingredient, index) => (
              <li key={index}>{ingredient}</li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
};

export default CookingPage;


