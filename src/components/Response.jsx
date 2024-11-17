import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';

const Response = () => {
  const [choice, setChoice] = useState(null); // Track user's choice: "cooking" or "takeout"
  const [availableIngredients, setAvailableIngredients] = useState([]); // Ingredients the user has
  const [aiFormResponse, setAiFormResponse] = useState(null); // AI response for the form submission
  const navigate = useNavigate(); // For navigation

  // Hardcoded AI responses for demonstration
  const aiResponse = "Spaghetti Carbonara";
  const ingredients = [
    "200g Spaghetti",
    "100g Pancetta",
    "2 Large Eggs",
    "50g Pecorino Cheese",
    "Black Pepper",
  ];
  const missingIngredients = ["Pancetta"];
  const alternateDish = "Cheese Omelette";

  const nearbyPlaces = [
    { name: "Italian Bistro", address: "123 Main St, City Center" },
    { name: "Pasta Paradise", address: "456 Elm St, Downtown" },
    { name: "Carbonara Corner", address: "789 Oak Ave, Suburbs" },
  ];

  const handleIngredientToggle = (ingredient) => {
    setAvailableIngredients((prev) =>
      prev.includes(ingredient)
        ? prev.filter((item) => item !== ingredient)
        : [...prev, ingredient]
    );
  };

  const handleFormSubmit = (e) => {
    e.preventDefault();
    setAiFormResponse({
      missing: missingIngredients,
      alternateDish,
    });
  };

  return (
    <div className="flex flex-col items-center justify-center h-screen bg-gray-100">
      {/* AI Response Box */}
      <div className="relative w-full max-w-3xl bg-blue-500 text-white p-6 rounded-lg shadow-md mb-6 text-center">
        <button
          onClick={() => navigate("/reasonforcross")} // Navigate to a different page
          className="absolute top-4 right-4 bg-red-500 text-white w-8 h-8 flex items-center justify-center rounded-full hover:bg-red-600 focus:outline-none"
        >
          &times;
        </button>
        <h2 className="text-2xl font-bold mb-2">Our Recommendation</h2>
        <p className="text-lg">{aiResponse}</p>
      </div>

      {/* Buttons */}
      <div className="flex space-x-4 mb-6">
        <button
          onClick={() => setChoice("cooking")}
          className={`px-6 py-3 bg-green-500 text-white rounded-lg shadow-md hover:bg-green-600 ${
            choice === "cooking" ? "ring-4 ring-green-300" : ""
          }`}
        >
          Cooking
        </button>
        <button
          onClick={() => setChoice("takeout")}
          className={`px-6 py-3 bg-yellow-500 text-white rounded-lg shadow-md hover:bg-yellow-600 ${
            choice === "takeout" ? "ring-4 ring-yellow-300" : ""
          }`}
        >
          Take-Out
        </button>
      </div>

      {/* Conditional Rendering Based on Choice */}
      <div className="w-full max-w-3xl bg-white p-6 rounded-lg shadow-md">
        {choice === "cooking" && (
          <>
            <h3 className="text-xl font-bold mb-4">Which ingredients do you have?</h3>
            <form onSubmit={handleFormSubmit}>
              <ul className="list-none text-gray-700">
                {ingredients.map((ingredient, index) => (
                  <li key={index} className="mb-2 flex items-center">
                    <input
                      type="checkbox"
                      id={`ingredient-${index}`}
                      value={ingredient}
                      checked={availableIngredients.includes(ingredient)}
                      onChange={() => handleIngredientToggle(ingredient)}
                      className="mr-2"
                    />
                    <label htmlFor={`ingredient-${index}`} className="text-lg">
                      {ingredient}
                    </label>
                  </li>
                ))}
              </ul>
              <button
                type="submit"
                className="mt-4 px-6 py-2 bg-blue-500 text-white rounded-lg shadow-md hover:bg-blue-600"
              >
                Submit
              </button>
            </form>

            {/* AI Response After Submission */}
            {aiFormResponse && (
              <div className="mt-6">
                <h4 className="text-lg font-bold mb-2">AI Response</h4>
                <p className="mb-2">
                  You are missing the following ingredients:{" "}
                  <span className="text-red-500">
                    {aiFormResponse.missing.join(", ")}
                  </span>
                </p>
                <p className="mb-2">
                  Based on what you have, you can make:{" "}
                  <span className="text-green-500">
                    {aiFormResponse.alternateDish}
                  </span>
                </p>
              </div>
            )}
          </>
        )}
        {choice === "takeout" && (
          <>
            <h3 className="text-xl font-bold mb-4">Nearby Places</h3>
            <ul className="space-y-4 text-gray-700">
              {nearbyPlaces.map((place, index) => (
                <li key={index}>
                  <strong>{place.name}</strong>
                  <p>{place.address}</p>
                </li>
              ))}
            </ul>
          </>
        )}
        {!choice && (
          <p className="text-gray-500 text-center">
            Please select an option above to see more details.
          </p>
        )}
      </div>
    </div>
  );
};

export default Response;
