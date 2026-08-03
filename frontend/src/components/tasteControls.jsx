import { useState } from 'react';

// These match the dish catalog's cuisine names exactly so the recommender's
// cuisine affinity can key off them. Every one has dishes in the catalog.
export const CUISINES = [
  'Italian', 'Mexican', 'American', 'Chinese', 'Indian', 'Thai', 'Japanese',
  'Korean', 'Vietnamese', 'Greek', 'French', 'Spanish', 'Middle Eastern',
  'Moroccan', 'Caribbean', 'British', 'Irish', 'German', 'Portuguese', 'Turkish',
];

export const DIETS = [
  { label: 'Vegetarian', value: 'vegetarian' },
  { label: 'Vegan', value: 'vegan' },
  { label: 'Pescatarian', value: 'pescatarian' },
  { label: 'Dairy-free', value: 'dairy-free' },
];

export const SKILLS = [
  { label: 'Beginner', value: 'beginner' },
  { label: 'Home cook', value: 'intermediate' },
  { label: 'Chef', value: 'advanced' },
];

export const GOALS = [
  { label: 'Comfort', value: 'weight_gain' },
  { label: 'Balanced', value: 'maintain' },
  { label: 'Light', value: 'weight_loss' },
];

export const BUDGETS = [
  { label: '$', value: '<$50' },
  { label: '$$', value: '$50-$100' },
  { label: '$$$', value: '$100-$200' },
];

// The "big 9" allergens plus common tree nuts/shellfish, for the allergy
// autocomplete. The backend fuzzy-normalizes whatever the user types anyway.
export const ALLERGEN_SUGGESTIONS = [
  'peanut', 'almond', 'cashew', 'walnut', 'pecan', 'hazelnut', 'pistachio',
  'tree nut', 'shellfish', 'shrimp', 'crab', 'lobster', 'fish', 'egg', 'milk',
  'dairy', 'soy', 'wheat', 'gluten', 'sesame', 'mustard', 'coconut',
];

export function Chip({ selected, onClick, children }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`rounded-full border-2 border-ink px-5 py-2.5 font-medium transition-colors ${
        selected ? 'bg-ink text-paper' : 'bg-paper text-ink hover:bg-wash'
      }`}
    >
      {children}
    </button>
  );
}

export function Segmented({ options, value, onChange }) {
  return (
    <div className="flex w-fit border-2 border-ink">
      {options.map((opt) => (
        <button
          key={opt.value}
          type="button"
          onClick={() => onChange(opt.value)}
          className={`px-5 py-2.5 font-medium ${
            value === opt.value ? 'bg-ink text-paper' : 'bg-paper text-ink hover:bg-wash'
          }`}
        >
          {opt.label}
        </button>
      ))}
    </div>
  );
}

// Cuisine selection + explicit ranking. Tap chips to add/remove; the selected
// cuisines become an ordered list you can drag (or nudge up/down) to rank. The
// array order is what the recommender's rank-decay bonus consumes — #1 wins.
export function CuisineRanker({ value, onChange, options = CUISINES }) {
  const [dragIndex, setDragIndex] = useState(null);

  function toggle(cuisine) {
    onChange(
      value.includes(cuisine)
        ? value.filter((c) => c !== cuisine)
        : [...value, cuisine],
    );
  }

  function move(from, to) {
    if (to < 0 || to >= value.length || from === to) return;
    const next = [...value];
    const [moved] = next.splice(from, 1);
    next.splice(to, 0, moved);
    onChange(next);
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap gap-3">
        {options.map((cuisine) => (
          <Chip
            key={cuisine}
            selected={value.includes(cuisine)}
            onClick={() => toggle(cuisine)}
          >
            {cuisine}
          </Chip>
        ))}
      </div>

      {value.length > 0 && (
        <div className="flex flex-col gap-2">
          <p className="font-mono text-xs tracking-caps text-gray">
            DRAG TO RANK — YOUR #1 SHOWS UP MOST
          </p>
          <ul className="flex flex-col gap-2">
            {value.map((cuisine, i) => (
              <li
                key={cuisine}
                draggable
                onDragStart={() => setDragIndex(i)}
                onDragOver={(e) => e.preventDefault()}
                onDrop={() => {
                  move(dragIndex, i);
                  setDragIndex(null);
                }}
                onDragEnd={() => setDragIndex(null)}
                className={`flex items-center gap-3 border-2 border-ink bg-paper px-4 py-2.5 ${
                  dragIndex === i ? 'opacity-50' : ''
                }`}
              >
                <span className="w-8 font-display text-lg leading-none text-ink">
                  #{i + 1}
                </span>
                <span className="flex-grow font-medium text-ink">{cuisine}</span>
                <span className="flex items-center gap-1">
                  <button
                    type="button"
                    aria-label={`Move ${cuisine} up`}
                    disabled={i === 0}
                    onClick={() => move(i, i - 1)}
                    className="px-1 text-gray hover:text-ink disabled:opacity-30"
                  >
                    ↑
                  </button>
                  <button
                    type="button"
                    aria-label={`Move ${cuisine} down`}
                    disabled={i === value.length - 1}
                    onClick={() => move(i, i + 1)}
                    className="px-1 text-gray hover:text-ink disabled:opacity-30"
                  >
                    ↓
                  </button>
                  <button
                    type="button"
                    aria-label={`Remove ${cuisine}`}
                    onClick={() => toggle(cuisine)}
                    className="px-1 text-gray hover:text-ink"
                  >
                    ×
                  </button>
                  <span className="cursor-grab select-none px-1 text-gray" aria-hidden="true">
                    ⠿
                  </span>
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
