import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';

// The ML model was trained on specific canonical values. The UI shows
// friendly labels, so we map them to what the model/encoders expect
// before sending to the backend.
const SKILL_MAP = {
  Beginner: 'beginner',
  Intermediate: 'intermediate',
  Advanced: 'advanced',
};

const GOAL_MAP = {
  'Weight Gain': 'weight_gain',
  'Weight Loss': 'weight_loss',
  'Maintain Current Weight': 'maintain',
};

const DIET_MAP = {
  Vegetarian: 'vegetarian',
  Pescatarian: 'pescatarian',
  Vegan: 'vegan',
  'Dairy-Free': 'dairy-free',
};

const COMMON_INGREDIENTS = ['Rice', 'Eggs', 'Chicken', 'Onion', 'Garlic', 'Olive Oil', 'Tomato', 'Pasta'];

const ProfileSetUp = () => {
  const [currentStep, setCurrentStep] = useState(0);
  const [ingredientInput, setIngredientInput] = useState('');
  const [profileData, setProfileData] = useState({
    cuisines: ['', '', '', '', ''],
    cookingSkill: '',
    dietaryRestrictions: [],
    allergies: '',
    healthGoal: '',
    budget: '',
    availableIngredients: [],
    location: '',
  });

  const navigate = useNavigate();

  const handleNext = async () => {
    if (currentStep < steps.length - 1) {
      setCurrentStep(currentStep + 1);
    } else {
      // Normalize values to the canonical forms the model was trained on
      const payload = {
        ...profileData,
        cuisines: profileData.cuisines
          .filter((c) => c.trim())
          .map((c) => c.trim().replace(/\w\S*/g, (w) => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase())),
        cookingSkill: SKILL_MAP[profileData.cookingSkill] || 'beginner',
        healthGoal: GOAL_MAP[profileData.healthGoal] || 'maintain',
        dietaryRestrictions: profileData.dietaryRestrictions
          .map((d) => DIET_MAP[d])
          .filter(Boolean),
      };

      try {
        const response = await fetch('http://localhost:5001/profilesetup', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'include',
          body: JSON.stringify(payload),
        });

        if (response.ok) {
          navigate('/generatedresponse');
        } else {
          alert('Failed to save profile. Please try again.');
        }
      } catch (error) {
        console.error('Error saving profile:', error);
        alert('An error occurred. Please try again later.');
      }
    }
  };

  const handlePrevious = () => {
    if (currentStep > 0) setCurrentStep(currentStep - 1);
  };

  const handleChange = (key, value) => {
    setProfileData({ ...profileData, [key]: value });
  };

  const handleCheckboxChange = (value) => {
    setProfileData((prev) => ({
      ...prev,
      dietaryRestrictions: prev.dietaryRestrictions.includes(value)
        ? prev.dietaryRestrictions.filter((item) => item !== value)
        : [...prev.dietaryRestrictions, value],
    }));
  };

  const addIngredient = (value) => {
    const ing = value.trim();
    if (ing && !profileData.availableIngredients.includes(ing)) {
      setProfileData((prev) => ({
        ...prev,
        availableIngredients: [...prev.availableIngredients, ing],
      }));
    }
    setIngredientInput('');
  };

  const removeIngredient = (value) => {
    setProfileData((prev) => ({
      ...prev,
      availableIngredients: prev.availableIngredients.filter((i) => i !== value),
    }));
  };

  const steps = [
    // Step 1: Ranking cuisines
    <div key="cuisines" className="w-full">
      <h2 className="text-xl font-semibold mb-4">Rank Your Favorite Cuisines</h2>
      {[1, 2, 3, 4, 5].map((rank, index) => (
        <div key={rank} className="mb-4">
          <label className="block text-gray-700 font-medium mb-2">Rank {rank}:</label>
          <input
            type="text"
            placeholder={`Enter cuisine for rank ${rank}`}
            value={profileData.cuisines[index] || ''}
            onChange={(e) => {
              const newCuisines = [...profileData.cuisines];
              newCuisines[index] = e.target.value;
              handleChange('cuisines', newCuisines);
            }}
            className="w-full h-10 px-4 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
      ))}
    </div>,

    // Step 2: Cooking skill level
    <div key="cookingSkill" className="w-full">
      <h2 className="text-xl font-semibold mb-4">What is your cooking skill level?</h2>
      {['Beginner', 'Intermediate', 'Advanced'].map((level) => (
        <label key={level} className="block mb-2">
          <input
            type="radio"
            name="cookingSkill"
            value={level}
            checked={profileData.cookingSkill === level}
            onChange={(e) => handleChange('cookingSkill', e.target.value)}
            className="mr-2"
          />
          {level}
        </label>
      ))}
    </div>,

    // Step 3: Dietary restrictions
    <div key="dietaryRestrictions" className="w-full">
      <h2 className="text-xl font-semibold mb-4">Do you have any dietary restrictions?</h2>
      {['Vegetarian', 'Pescatarian', 'Vegan', 'Dairy-Free'].map((restriction) => (
        <label key={restriction} className="block mb-2">
          <input
            type="checkbox"
            value={restriction}
            checked={profileData.dietaryRestrictions.includes(restriction)}
            onChange={() => handleCheckboxChange(restriction)}
            className="mr-2"
          />
          {restriction}
        </label>
      ))}
      <div className="mt-4">
        <label className="block text-gray-700 font-medium mb-2">Other (e.g., allergies):</label>
        <input
          type="text"
          placeholder="Enter other dietary restrictions"
          value={profileData.allergies || ''}
          onChange={(e) => handleChange('allergies', e.target.value)}
          className="w-full h-10 px-4 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
      </div>
    </div>,

    // Step 4: Health goals
    <div key="healthGoals" className="w-full">
      <h2 className="text-xl font-semibold mb-4">What is your health goal?</h2>
      {['Weight Gain', 'Weight Loss', 'Maintain Current Weight'].map((goal) => (
        <label key={goal} className="block mb-2">
          <input
            type="radio"
            name="healthGoal"
            value={goal}
            checked={profileData.healthGoal === goal}
            onChange={(e) => handleChange('healthGoal', e.target.value)}
            className="mr-2"
          />
          {goal}
        </label>
      ))}
    </div>,

    // Step 5: Budget per week
    <div key="budget" className="w-full">
      <h2 className="text-xl font-semibold mb-4">What is your weekly budget for food?</h2>
      {['<$50', '$50-$100', '$100-$200', '$200+'].map((budget) => (
        <label key={budget} className="block mb-2">
          <input
            type="radio"
            name="budget"
            value={budget}
            checked={profileData.budget === budget}
            onChange={(e) => handleChange('budget', e.target.value)}
            className="mr-2"
          />
          {budget}
        </label>
      ))}
    </div>,

    // Step 6: Available ingredients
    <div key="ingredients" className="w-full">
      <h2 className="text-xl font-semibold mb-4">What ingredients do you have at home?</h2>
      <p className="text-sm text-gray-500 mb-3">
        We'll prioritize dishes you can already make. (Optional)
      </p>
      <div className="flex gap-2 mb-3">
        <input
          type="text"
          placeholder="e.g., chicken"
          value={ingredientInput}
          onChange={(e) => setIngredientInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') {
              e.preventDefault();
              addIngredient(ingredientInput);
            }
          }}
          className="flex-1 h-10 px-4 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        <button
          type="button"
          onClick={() => addIngredient(ingredientInput)}
          className="px-4 bg-blue-500 text-white rounded-lg hover:bg-blue-600"
        >
          Add
        </button>
      </div>

      <div className="flex flex-wrap gap-2 mb-4">
        {COMMON_INGREDIENTS.map((ing) => (
          <button
            key={ing}
            type="button"
            onClick={() => addIngredient(ing)}
            className="px-3 py-1 text-sm bg-gray-100 hover:bg-gray-200 rounded-full"
          >
            + {ing}
          </button>
        ))}
      </div>

      <div className="flex flex-wrap gap-2">
        {profileData.availableIngredients.map((ing) => (
          <span
            key={ing}
            className="px-3 py-1 text-sm bg-green-100 text-green-800 rounded-full flex items-center gap-1"
          >
            {ing}
            <button
              type="button"
              onClick={() => removeIngredient(ing)}
              className="text-green-600 hover:text-green-900 font-bold"
            >
              ×
            </button>
          </span>
        ))}
      </div>
    </div>,

    // Step 7: Location
    <div key="location" className="w-full">
      <h2 className="text-xl font-semibold mb-4">Where are you located?</h2>
      <p className="text-sm text-gray-500 mb-3">
        Used to find nearby restaurants when you choose takeout.
      </p>
      <input
        type="text"
        placeholder="e.g., Madison, WI or 53703"
        value={profileData.location}
        onChange={(e) => handleChange('location', e.target.value)}
        className="w-full h-10 px-4 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
      />
    </div>,
  ];

  return (
    <div className="flex justify-center items-center h-screen bg-gray-100 overflow-hidden">
      <div className="bg-white p-8 rounded-lg shadow-md w-full max-w-lg relative overflow-hidden">
        <div
          className="flex transition-transform duration-500"
          style={{
            transform: `translateX(-${currentStep * 100}%)`,
            width: `${steps.length * 100}%`,
          }}
        >
          {steps.map((step, index) => (
            <div key={index} className="min-w-full flex-shrink-0">
              {step}
            </div>
          ))}
        </div>

        {currentStep > 0 && (
          <button
            onClick={handlePrevious}
            className="absolute left-0 top-1/2 transform -translate-y-1/2 bg-gray-200 hover:bg-gray-300 p-3 rounded-full shadow-md focus:outline-none"
          >
            ←
          </button>
        )}
        {currentStep < steps.length - 1 ? (
          <button
            onClick={handleNext}
            className="absolute right-0 top-1/2 transform -translate-y-1/2 bg-gray-200 hover:bg-gray-300 p-3 rounded-full shadow-md focus:outline-none"
          >
            →
          </button>
        ) : (
          <button
            onClick={handleNext}
            className="absolute right-0 top-1/2 transform -translate-y-1/2 bg-blue-500 text-white p-3 rounded-full shadow-md focus:outline-none"
          >
            Finish
          </button>
        )}
      </div>
    </div>
  );
};

export default ProfileSetUp;
