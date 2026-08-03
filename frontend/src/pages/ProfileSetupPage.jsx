import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../lib/api';
import { useAuth } from '../context/AuthContext';
import NavBar from '../components/NavBar';
import { Avatar, AVATARS } from '../components/Avatar';
import {
  ALLERGEN_SUGGESTIONS,
  CuisineRanker,
  Chip,
  DIETS,
  GOALS,
  SKILLS,
  BUDGETS,
  Segmented,
} from '../components/tasteControls';

function SectionLabel({ children, note, noteColor = 'text-gray' }) {
  return (
    <div className="flex items-baseline gap-3">
      <span className="font-mono text-sm tracking-caps text-ink">{children}</span>
      {note && <span className={`font-mono text-xs tracking-caps ${noteColor}`}>{note}</span>}
    </div>
  );
}

function TagInput({ tags, onChange, placeholder, suggestions }) {
  const [draft, setDraft] = useState('');
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(-1);

  const query = draft.trim().toLowerCase();
  const filtered = suggestions
    ? suggestions.filter((s) => !tags.includes(s) && s.toLowerCase().includes(query)).slice(0, 8)
    : [];
  const showList = Boolean(suggestions) && open && filtered.length > 0;

  function add(value) {
    const v = String(value ?? draft).trim().replace(/,$/, '');
    if (v && !tags.includes(v)) onChange([...tags, v]);
    setDraft('');
    setActive(-1);
  }

  function handleKeyDown(e) {
    if (showList && (e.key === 'ArrowDown' || e.key === 'ArrowUp')) {
      e.preventDefault();
      const n = filtered.length;
      setActive((i) => (e.key === 'ArrowDown' ? (i + 1) % n : (i - 1 + n) % n));
      return;
    }
    if (e.key === 'Enter' || e.key === ',') {
      e.preventDefault();
      add(showList && active >= 0 ? filtered[active] : draft);
    } else if (e.key === 'Escape') {
      setOpen(false);
    }
  }

  return (
    <div className="relative">
      <div className="flex min-h-[64px] flex-wrap items-center gap-2 border-2 border-ink px-3 py-3">
        {tags.map((tag) => (
          <span
            key={tag}
            className="flex items-center gap-2 rounded-full border-2 border-ink px-3 py-1 text-sm font-medium"
          >
            {tag}
            <button
              type="button"
              aria-label={`Remove ${tag}`}
              onClick={() => onChange(tags.filter((t) => t !== tag))}
              className="text-gray hover:text-ink"
            >
              ×
            </button>
          </span>
        ))}
        <input
          type="text"
          value={draft}
          onChange={(e) => {
            setDraft(e.target.value);
            setOpen(true);
            setActive(-1);
          }}
          onFocus={() => setOpen(true)}
          onKeyDown={handleKeyDown}
          onBlur={() => {
            add(draft);
            setOpen(false);
          }}
          placeholder={tags.length ? '' : placeholder}
          className="min-w-[200px] flex-grow px-1 py-1 text-base placeholder:text-gray/60 focus:outline-none"
        />
      </div>

      {showList && (
        <ul className="absolute left-0 right-0 top-full z-20 mt-1 max-h-64 overflow-auto border-2 border-ink bg-paper shadow-sticker">
          {filtered.map((s, i) => (
            <li key={s}>
              <button
                type="button"
                // preventDefault keeps the input from blurring before the click lands
                onMouseDown={(e) => {
                  e.preventDefault();
                  add(s);
                }}
                onMouseEnter={() => setActive(i)}
                className={`block w-full px-4 py-2.5 text-left capitalize ${
                  i === active ? 'bg-ink text-paper' : 'text-ink hover:bg-wash'
                }`}
              >
                {s}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export default function ProfileSetupPage({ edit = false }) {
  const navigate = useNavigate();
  const { user, markProfileComplete, patchUser } = useAuth();

  const [name, setName] = useState(user?.username || '');
  const [avatarUrl, setAvatarUrl] = useState(user?.avatar_url || '');
  // A Google sign-in gives a photo URL; offer it as one of the avatar choices.
  const googlePhoto =
    user?.avatar_url && /^https?:\/\//.test(user.avatar_url) ? user.avatar_url : '';
  const [cuisines, setCuisines] = useState([]);
  const [diets, setDiets] = useState([]);
  const [allergies, setAllergies] = useState([]);
  const [pantry, setPantry] = useState([]);
  const [skill, setSkill] = useState('intermediate');
  const [goal, setGoal] = useState('maintain');
  const [budget, setBudget] = useState('<$50');
  const [location, setLocation] = useState('');
  const [locating, setLocating] = useState(false);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!edit) return;
    api
      .get('/api/profile')
      .then(({ data }) => {
        const p = data.profile;
        if (p.name) setName(p.name);
        setAvatarUrl(p.avatar_url || '');
        setCuisines(p.cuisines || []);
        setDiets(p.dietary_restrictions || []);
        setAllergies(p.allergies || []);
        setPantry(p.available_ingredients || []);
        if (p.skill_level) setSkill(p.skill_level);
        if (p.weight_goal) setGoal(p.weight_goal);
        if (p.budget) setBudget(p.budget);
        setLocation(p.location || '');
      })
      .catch(() => {});
  }, [edit]);

  function toggle(list, setList, value) {
    setList(list.includes(value) ? list.filter((v) => v !== value) : [...list, value]);
  }

  function useMyLocation() {
    if (!navigator.geolocation) {
      setError('Location is not available in this browser. Type your city instead.');
      return;
    }
    setLocating(true);
    navigator.geolocation.getCurrentPosition(
      async ({ coords }) => {
        try {
          const resp = await fetch(
            `https://nominatim.openstreetmap.org/reverse?lat=${coords.latitude}&lon=${coords.longitude}&format=json`,
          );
          const data = await resp.json();
          const a = data.address || {};
          const city = a.city || a.town || a.village || a.county;
          const region = a.state ? `, ${a.state}` : '';
          setLocation(city ? `${city}${region}` : `${coords.latitude.toFixed(4)}, ${coords.longitude.toFixed(4)}`);
        } catch {
          setError('Could not look up your city. Type it instead.');
        } finally {
          setLocating(false);
        }
      },
      () => {
        setLocating(false);
        setError('Location permission denied. Type your city instead.');
      },
    );
  }

  async function handleSubmit(event) {
    event.preventDefault();
    if (!cuisines.length) {
      setError('Pick at least one cuisine so we know where to start.');
      return;
    }
    setError('');
    setBusy(true);
    try {
      const { data } = await api.put('/api/profile', {
        name,
        avatar_url: avatarUrl,
        cuisines,
        dietary_restrictions: diets,
        allergies,
        available_ingredients: pantry,
        skill_level: skill,
        weight_goal: goal,
        budget,
        location,
      });
      markProfileComplete();
      patchUser({ username: data.profile.name, avatar_url: data.profile.avatar_url });
      navigate('/nominate');
    } catch (err) {
      setError(err.response?.data?.error || 'Could not save your profile. Try again.');
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="min-h-screen">
      <NavBar />

      <main className="mx-auto w-full max-w-[760px] px-6 pb-20">
        <div className="pt-14 text-center">
          <p className="font-mono text-sm tracking-caps text-gray">
            {edit ? 'MY PROFILE — TASTE PROFILE' : 'STEP 1 OF 1 — TASTE PROFILE'}
          </p>
          <h1 className="mt-4 font-display text-[clamp(44px,6vw,72px)] uppercase leading-none text-ink">
            {edit ? 'How you eat' : 'Tell us how you eat'}
          </h1>
          <p className="mx-auto mt-4 max-w-[480px] text-gray">
            This trains your {edit ? 'next' : 'first'} nominations. You can change any of it
            later from your profile.
          </p>
        </div>

        {error && (
          <p role="alert" className="mt-8 border-2 border-red px-4 py-3 text-sm text-red">
            {error}
          </p>
        )}

        <form onSubmit={handleSubmit} className="mt-12 flex flex-col gap-10">
          <section className="flex flex-col gap-4">
            <SectionLabel>ABOUT YOU</SectionLabel>
            <div className="flex items-center gap-5">
              <Avatar value={avatarUrl} name={name} size={80} />
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Your name"
                className="h-12 flex-grow border-2 border-ink px-4 text-base placeholder:text-gray/60"
              />
            </div>
            <p className="font-mono text-xs tracking-caps text-gray">PICK AN AVATAR</p>
            <div className="flex flex-wrap gap-3">
              {googlePhoto && (
                <button
                  type="button"
                  onClick={() => setAvatarUrl(googlePhoto)}
                  aria-label="Use your Google photo"
                  className={`rounded-full transition-transform hover:scale-105 ${
                    avatarUrl === googlePhoto ? 'ring-2 ring-ink ring-offset-2' : ''
                  }`}
                >
                  <Avatar value={googlePhoto} name={name} size={52} />
                </button>
              )}
              {AVATARS.map((a) => (
                <button
                  type="button"
                  key={a.id}
                  onClick={() => setAvatarUrl(a.id)}
                  aria-label={`Choose ${a.id} avatar`}
                  aria-pressed={avatarUrl === a.id}
                  className={`rounded-full transition-transform hover:scale-105 ${
                    avatarUrl === a.id ? 'ring-2 ring-ink ring-offset-2' : ''
                  }`}
                >
                  <Avatar value={a.id} name={name} size={52} />
                </button>
              ))}
            </div>
          </section>

          <section className="flex flex-col gap-4">
            <SectionLabel>CUISINES YOU CRAVE</SectionLabel>
            <CuisineRanker value={cuisines} onChange={setCuisines} />
          </section>

          <section className="flex flex-col gap-4">
            <SectionLabel>DIETARY NEEDS</SectionLabel>
            <div className="flex flex-wrap gap-3">
              <Chip selected={diets.length === 0} onClick={() => setDiets([])}>
                None
              </Chip>
              {DIETS.map(({ label, value }) => (
                <Chip
                  key={value}
                  selected={diets.includes(value)}
                  onClick={() => toggle(diets, setDiets, value)}
                >
                  {label}
                </Chip>
              ))}
            </div>
          </section>

          <section className="flex flex-col gap-4">
            <SectionLabel>ALLERGIES</SectionLabel>
            <TagInput
              tags={allergies}
              onChange={setAllergies}
              suggestions={ALLERGEN_SUGGESTIONS}
              placeholder="Type an allergy and press enter…"
            />
          </section>

          <div className="flex flex-wrap gap-10">
            <section className="flex flex-col gap-4">
              <SectionLabel>KITCHEN SKILL</SectionLabel>
              <Segmented options={SKILLS} value={skill} onChange={setSkill} />
            </section>
            <section className="flex flex-col gap-4">
              <SectionLabel>EATING GOAL</SectionLabel>
              <Segmented options={GOALS} value={goal} onChange={setGoal} />
            </section>
            <section className="flex flex-col gap-4">
              <SectionLabel>BUDGET</SectionLabel>
              <Segmented options={BUDGETS} value={budget} onChange={setBudget} />
            </section>
          </div>

          <section className="flex flex-col gap-4">
            <SectionLabel note="STUFF ALREADY IN YOUR KITCHEN">PANTRY</SectionLabel>
            <TagInput
              tags={pantry}
              onChange={setPantry}
              placeholder="chicken, rice, tomatoes — press enter after each…"
            />
          </section>

          <section className="flex flex-col gap-4">
            <SectionLabel note="FOR TAKEOUT NEAR YOU">YOUR LOCATION</SectionLabel>
            <div className="flex flex-wrap gap-4">
              <input
                type="text"
                value={location}
                onChange={(e) => setLocation(e.target.value)}
                placeholder="City or ZIP — e.g. Madison, WI"
                className="h-14 flex-grow border-2 border-ink px-4 text-base placeholder:text-gray/60"
              />
              <button
                type="button"
                onClick={useMyLocation}
                disabled={locating}
                className="h-14 border-2 border-ink bg-wash px-6 font-medium hover:bg-paper disabled:opacity-60"
              >
                {locating ? 'Locating…' : 'Use my location'}
              </button>
            </div>
          </section>

          <div className="flex flex-col items-center gap-3 pt-2">
            <button
              type="submit"
              disabled={busy}
              className="rounded-xl border-2 border-ink bg-yellow px-16 py-4 text-lg font-bold text-ink shadow-sticker transition-transform active:translate-x-[2px] active:translate-y-[2px] active:shadow-none disabled:opacity-60"
            >
              {busy ? 'Saving…' : edit ? 'Save changes' : 'Start nominating'}
            </button>
            <p className="text-sm text-gray">
              Takes effect immediately — your {edit ? 'next' : 'first'} nomination is one
              click away.
            </p>
          </div>
        </form>
      </main>
    </div>
  );
}
