import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';

// Curated cuisines that actually exist in our dish catalog (>= 8 dishes each),
// using the exact capitalization the model was trained on.
const CUISINES = [
  'British', 'Italian', 'Chinese', 'Thai', 'Indian', 'Mexican',
  'French', 'Japanese', 'Spanish', 'American', 'Turkish', 'Greek',
  'Vietnamese', 'Jamaican', 'Moroccan', 'Egyptian', 'Portuguese',
  'Polish', 'Canadian', 'Malaysian', 'Filipino', 'Irish', 'Croatian', 'Tunisian',
];

// UI label -> canonical value the model expects
const SKILLS = [
  { label: 'Beginner', value: 'beginner', emoji: '🥄', desc: 'Simple, few steps' },
  { label: 'Intermediate', value: 'intermediate', emoji: '🍳', desc: 'Comfortable cooking' },
  { label: 'Advanced', value: 'advanced', emoji: '👨‍🍳', desc: 'Bring on the challenge' },
];

const DIETS = [
  { label: 'Vegetarian', value: 'vegetarian', emoji: '🥗' },
  { label: 'Vegan', value: 'vegan', emoji: '🌱' },
  { label: 'Pescatarian', value: 'pescatarian', emoji: '🐟' },
  { label: 'Dairy-Free', value: 'dairy-free', emoji: '🥛' },
];

const GOALS = [
  { label: 'Weight Loss', value: 'weight_loss', emoji: '📉', desc: 'Lighter dishes' },
  { label: 'Maintain', value: 'maintain', emoji: '⚖️', desc: 'Balanced meals' },
  { label: 'Weight Gain', value: 'weight_gain', emoji: '📈', desc: 'Hearty & filling' },
];

const BUDGETS = [
  { label: '< $50', value: '<$50', emoji: '🪙' },
  { label: '$50–$100', value: '$50-$100', emoji: '💵' },
  { label: '$100–$200', value: '$100-$200', emoji: '💳' },
  { label: '$200+', value: '$200+', emoji: '💎' },
];

const COMMON_INGREDIENTS = ['Rice', 'Eggs', 'Chicken', 'Onion', 'Garlic', 'Olive Oil', 'Tomato', 'Pasta'];

const STEP_TITLES = [
  'Rank your cuisines',
  'Cooking skill',
  'Dietary needs',
  'Health goal',
  'Weekly budget',
  'Your ingredients',
  'Your location',
];

const ProfileSetUp = () => {
  const [currentStep, setCurrentStep] = useState(0);
  const [ingredientInput, setIngredientInput] = useState('');
  const [profileData, setProfileData] = useState({
    cuisines: [],            // ordered list -> rank is the index
    cookingSkill: '',        // canonical value
    dietaryRestrictions: [], // canonical values
    allergies: '',
    healthGoal: '',          // canonical value
    budget: '',              // canonical value
    availableIngredients: [],
    location: '',
  });

  const navigate = useNavigate();
  const totalSteps = STEP_TITLES.length;

  // ── Cuisine ranking: click to add (with rank), click again to remove ────────
  const toggleCuisine = (cuisine) => {
    setProfileData((prev) => {
      if (prev.cuisines.includes(cuisine)) {
        return { ...prev, cuisines: prev.cuisines.filter((c) => c !== cuisine) };
      }
      if (prev.cuisines.length >= 5) return prev; // cap at 5
      return { ...prev, cuisines: [...prev.cuisines, cuisine] };
    });
  };

  const toggleDiet = (value) => {
    setProfileData((prev) => ({
      ...prev,
      dietaryRestrictions: prev.dietaryRestrictions.includes(value)
        ? prev.dietaryRestrictions.filter((d) => d !== value)
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

  // ── Per-step validation (optional steps always pass) ────────────────────────
  const canProceed = () => {
    switch (currentStep) {
      case 0: return profileData.cuisines.length >= 1;
      case 1: return !!profileData.cookingSkill;
      case 3: return !!profileData.healthGoal;
      case 4: return !!profileData.budget;
      default: return true; // dietary, ingredients, location are optional
    }
  };

  const handleNext = async () => {
    if (currentStep < totalSteps - 1) {
      setCurrentStep(currentStep + 1);
      return;
    }
    // Final step -> submit. Values are already canonical, so no mapping needed.
    try {
      const response = await fetch('http://localhost:5001/profilesetup', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify(profileData),
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
  };

  const handlePrevious = () => {
    if (currentStep > 0) setCurrentStep(currentStep - 1);
  };

  // ── Reusable selectable card ────────────────────────────────────────────────
  const SelectCard = ({ selected, onClick, emoji, label, desc }) => (
    <button
      type="button"
      onClick={onClick}
      className={`flex items-center gap-3 w-full p-4 rounded-2xl border-2 text-left transition-all duration-200
        ${selected
          ? 'border-orange-500 bg-orange-50 shadow-md scale-[1.02]'
          : 'border-gray-200 bg-white hover:border-orange-300 hover:bg-orange-50/40'}`}
    >
      <span className="text-2xl">{emoji}</span>
      <span>
        <span className="block font-bold text-gray-800">{label}</span>
        {desc && <span className="block text-sm text-gray-500">{desc}</span>}
      </span>
    </button>
  );

  // ── Step content ────────────────────────────────────────────────────────────
  const renderStep = () => {
    switch (currentStep) {
      case 0:
        return (
          <div>
            <p className="text-gray-500 mb-4">
              Tap up to 5 in order of preference. Tap again to remove.
            </p>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
              {CUISINES.map((cuisine) => {
                const rank = profileData.cuisines.indexOf(cuisine);
                const selected = rank !== -1;
                return (
                  <button
                    key={cuisine}
                    type="button"
                    onClick={() => toggleCuisine(cuisine)}
                    className={`relative px-3 py-2.5 rounded-xl border-2 text-sm font-semibold transition-all duration-200
                      ${selected
                        ? 'border-orange-500 bg-orange-500 text-white shadow-md animate-pop'
                        : 'border-gray-200 bg-white text-gray-700 hover:border-orange-300'}`}
                  >
                    {selected && (
                      <span className="absolute -top-2 -left-2 w-6 h-6 flex items-center justify-center
                        bg-rose-500 text-white text-xs font-bold rounded-full shadow">
                        {rank + 1}
                      </span>
                    )}
                    {cuisine}
                  </button>
                );
              })}
            </div>
          </div>
        );

      case 1:
        return (
          <div className="space-y-3">
            {SKILLS.map((s) => (
              <SelectCard
                key={s.value}
                selected={profileData.cookingSkill === s.value}
                onClick={() => setProfileData({ ...profileData, cookingSkill: s.value })}
                emoji={s.emoji}
                label={s.label}
                desc={s.desc}
              />
            ))}
          </div>
        );

      case 2:
        return (
          <div>
            <p className="text-gray-500 mb-4">Select any that apply (or none).</p>
            <div className="grid grid-cols-2 gap-2">
              {DIETS.map((d) => {
                const selected = profileData.dietaryRestrictions.includes(d.value);
                return (
                  <button
                    key={d.value}
                    type="button"
                    onClick={() => toggleDiet(d.value)}
                    className={`flex items-center gap-2 px-4 py-3 rounded-2xl border-2 font-semibold transition-all duration-200
                      ${selected
                        ? 'border-green-500 bg-green-50 text-green-800 shadow-md'
                        : 'border-gray-200 bg-white text-gray-700 hover:border-green-300'}`}
                  >
                    <span className="text-xl">{d.emoji}</span>
                    {d.label}
                  </button>
                );
              })}
            </div>
            <div className="mt-4">
              <label className="block text-gray-600 font-semibold mb-2">Allergies / other</label>
              <input
                type="text"
                placeholder="e.g., peanuts, shellfish"
                value={profileData.allergies}
                onChange={(e) => setProfileData({ ...profileData, allergies: e.target.value })}
                className="w-full h-11 px-4 rounded-xl border-2 border-gray-200 focus:outline-none focus:border-orange-400"
              />
            </div>
          </div>
        );

      case 3:
        return (
          <div className="space-y-3">
            {GOALS.map((g) => (
              <SelectCard
                key={g.value}
                selected={profileData.healthGoal === g.value}
                onClick={() => setProfileData({ ...profileData, healthGoal: g.value })}
                emoji={g.emoji}
                label={g.label}
                desc={g.desc}
              />
            ))}
          </div>
        );

      case 4:
        return (
          <div className="grid grid-cols-2 gap-3">
            {BUDGETS.map((b) => (
              <button
                key={b.value}
                type="button"
                onClick={() => setProfileData({ ...profileData, budget: b.value })}
                className={`flex flex-col items-center gap-1 py-6 rounded-2xl border-2 font-bold transition-all duration-200
                  ${profileData.budget === b.value
                    ? 'border-orange-500 bg-orange-50 text-orange-700 shadow-md scale-[1.03]'
                    : 'border-gray-200 bg-white text-gray-700 hover:border-orange-300'}`}
              >
                <span className="text-3xl">{b.emoji}</span>
                {b.label}
              </button>
            ))}
          </div>
        );

      case 5:
        return (
          <div>
            <p className="text-gray-500 mb-4">
              We'll prioritize dishes you can already make. (Optional)
            </p>
            <div className="flex gap-2 mb-3">
              <input
                type="text"
                placeholder="Type an ingredient…"
                value={ingredientInput}
                onChange={(e) => setIngredientInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    e.preventDefault();
                    addIngredient(ingredientInput);
                  }
                }}
                className="flex-1 h-11 px-4 rounded-xl border-2 border-gray-200 focus:outline-none focus:border-orange-400"
              />
              <button
                type="button"
                onClick={() => addIngredient(ingredientInput)}
                className="px-5 rounded-xl bg-gradient-to-r from-orange-500 to-rose-500 text-white font-bold hover:opacity-90"
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
                  className="px-3 py-1 text-sm font-semibold bg-gray-100 hover:bg-orange-100 rounded-full transition-colors"
                >
                  + {ing}
                </button>
              ))}
            </div>
            <div className="flex flex-wrap gap-2">
              {profileData.availableIngredients.map((ing) => (
                <span
                  key={ing}
                  className="px-3 py-1.5 text-sm font-semibold bg-green-100 text-green-800 rounded-full flex items-center gap-1.5 animate-pop"
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
          </div>
        );

      case 6:
        return (
          <div>
            <p className="text-gray-500 mb-4">
              Used to find nearby restaurants when you choose takeout. (Optional)
            </p>
            <input
              type="text"
              placeholder="e.g., Madison, WI or 53703"
              value={profileData.location}
              onChange={(e) => setProfileData({ ...profileData, location: e.target.value })}
              className="w-full h-12 px-4 rounded-xl border-2 border-gray-200 focus:outline-none focus:border-orange-400 text-lg"
            />
          </div>
        );

      default:
        return null;
    }
  };

  const progress = ((currentStep + 1) / totalSteps) * 100;

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-orange-50 via-amber-50 to-rose-50 p-4">
      <div className="w-full max-w-xl bg-white/80 backdrop-blur rounded-3xl shadow-xl p-8">
        {/* Brand */}
        <div className="text-center mb-6">
          <h1 className="text-3xl font-playfair font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-orange-500 to-rose-500">
            NOMinate
          </h1>
        </div>

        {/* Progress bar */}
        <div className="mb-2 flex justify-between items-center text-sm font-semibold text-gray-500">
          <span>Step {currentStep + 1} of {totalSteps}</span>
          <span>{Math.round(progress)}%</span>
        </div>
        <div className="w-full h-2 bg-gray-100 rounded-full mb-6 overflow-hidden">
          <div
            className="h-full bg-gradient-to-r from-orange-500 to-rose-500 rounded-full transition-all duration-500"
            style={{ width: `${progress}%` }}
          />
        </div>

        {/* Step title + content (re-keyed so it re-animates each step) */}
        <div key={currentStep} className="animate-fade-in-up min-h-[20rem]">
          <h2 className="text-2xl font-extrabold text-gray-800 mb-1">
            {STEP_TITLES[currentStep]}
          </h2>
          <div className="mt-4">{renderStep()}</div>
        </div>

        {/* Navigation */}
        <div className="flex justify-between items-center mt-8">
          <button
            onClick={handlePrevious}
            disabled={currentStep === 0}
            className={`px-5 py-2.5 rounded-xl font-bold transition-all
              ${currentStep === 0
                ? 'opacity-0 pointer-events-none'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'}`}
          >
            ← Back
          </button>
          <button
            onClick={handleNext}
            disabled={!canProceed()}
            className={`px-7 py-2.5 rounded-xl font-bold text-white transition-all
              ${canProceed()
                ? 'bg-gradient-to-r from-orange-500 to-rose-500 hover:opacity-90 shadow-md'
                : 'bg-gray-300 cursor-not-allowed'}`}
          >
            {currentStep === totalSteps - 1 ? "Let's eat! 🍽️" : 'Next →'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default ProfileSetUp;
