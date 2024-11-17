import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';

const ProfileSetUp = () => {
  const [currentStep, setCurrentStep] = useState(0); // Track the current step
  const [profileData, setProfileData] = useState({
    cuisines: ['', '', '', '', ''], // Step 1: Ranking cuisines
    cookingSkill: '', // Step 2: Cooking skill level
    dietaryRestrictions: [], // Step 3: Dietary restrictions
    allergies: '', // Step 3: Other dietary inputs
    healthGoal: '', // Step 4: Health goal
    budget: '', // Step 5: Budget per week
  });

  const navigate = useNavigate();

  const handleNext = () => {
    if (currentStep < steps.length - 1) {
      setCurrentStep(currentStep + 1);
    } else {
      console.log('Profile Data:', profileData);
      navigate('/generatedresponse'); // Navigate to the next page
    }
  };

  const handlePrevious = () => {
    if (currentStep > 0) {
      setCurrentStep(currentStep - 1);
    }
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
            value={profileData.cuisines[index] || ''} // Ensure it's a string
            onChange={(e) => {
              const newCuisines = [...profileData.cuisines];
              newCuisines[index] = e.target.value;
              handleChange('cuisines', newCuisines);
            }}
            required
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
      {['Vegetarian', 'Pescatarian', 'Vegan', 'Gluten-Free', 'Dairy-Free'].map((restriction) => (
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
          value={profileData.allergies || ''} // Ensure it's a string
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
  ];

  return (
    <div className="flex justify-center items-center h-screen bg-gray-100 overflow-hidden">
      <div className="bg-white p-8 rounded-lg shadow-md w-full max-w-lg relative overflow-hidden">
        {/* Sliding Container */}
        <div
          className="flex transition-transform duration-500"
          style={{
            transform: `translateX(-${currentStep * 100}%)`,
            width: `${steps.length * 100}%`,
          }}
        >
          {steps.map((step, index) => (
            <div key={index} className="w-full flex-shrink-0">
              {step}
            </div>
          ))}
        </div>

        {/* Left and Right Arrows */}
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
