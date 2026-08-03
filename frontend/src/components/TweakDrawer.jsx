import { useEffect, useState } from 'react';
import api from '../lib/api';
import { CuisineRanker, Chip, DIETS, SKILLS, Segmented } from './tasteControls';

// A lightweight slide-over for changing tonight's filters without a trip to the
// full profile page. Seeds from the current profile and PUTs only the fields it
// edits (the endpoint is partial-safe), then asks the caller to re-roll.
export default function TweakDrawer({ open, onClose, onApplied }) {
  const [cuisines, setCuisines] = useState([]);
  const [diets, setDiets] = useState([]);
  const [skill, setSkill] = useState('intermediate');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!open) return;
    setError('');
    api
      .get('/api/profile')
      .then(({ data }) => {
        const p = data.profile;
        setCuisines(p.cuisines || []);
        setDiets(p.dietary_restrictions || []);
        if (p.skill_level) setSkill(p.skill_level);
      })
      .catch(() => {});
  }, [open]);

  useEffect(() => {
    function onKey(e) {
      if (e.key === 'Escape') onClose();
    }
    if (open) window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [open, onClose]);

  if (!open) return null;

  function toggleDiet(value) {
    setDiets((d) => (d.includes(value) ? d.filter((v) => v !== value) : [...d, value]));
  }

  async function apply() {
    if (!cuisines.length) {
      setError('Pick at least one cuisine.');
      return;
    }
    setBusy(true);
    setError('');
    try {
      await api.put('/api/profile', {
        cuisines,
        dietary_restrictions: diets,
        skill_level: skill,
      });
      onApplied();
      onClose();
    } catch (err) {
      setError(err.response?.data?.error || 'Could not save. Try again.');
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      <button
        type="button"
        aria-label="Close"
        onClick={onClose}
        className="absolute inset-0 bg-ink/40"
      />
      <div className="relative flex h-full w-full max-w-[440px] flex-col overflow-y-auto border-l-2 border-ink bg-paper">
        <div className="flex items-center justify-between border-b-2 border-ink px-6 py-5">
          <h2 className="font-display text-2xl uppercase leading-none text-ink">
            Edit preferences
          </h2>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close"
            className="font-mono text-lg text-gray hover:text-ink"
          >
            ×
          </button>
        </div>

        <div className="flex flex-col gap-8 px-6 py-6">
          {error && (
            <p role="alert" className="border-2 border-red px-4 py-3 text-sm text-red">
              {error}
            </p>
          )}

          <section className="flex flex-col gap-4">
            <p className="font-mono text-sm tracking-caps text-ink">CUISINES</p>
            <CuisineRanker value={cuisines} onChange={setCuisines} />
          </section>

          <section className="flex flex-col gap-4">
            <p className="font-mono text-sm tracking-caps text-ink">DIETARY NEEDS</p>
            <div className="flex flex-wrap gap-3">
              <Chip selected={diets.length === 0} onClick={() => setDiets([])}>
                None
              </Chip>
              {DIETS.map(({ label, value }) => (
                <Chip key={value} selected={diets.includes(value)} onClick={() => toggleDiet(value)}>
                  {label}
                </Chip>
              ))}
            </div>
          </section>

          <section className="flex flex-col gap-4">
            <p className="font-mono text-sm tracking-caps text-ink">KITCHEN SKILL</p>
            <Segmented options={SKILLS} value={skill} onChange={setSkill} />
          </section>
        </div>

        <div className="mt-auto flex gap-4 border-t-2 border-ink px-6 py-5">
          <button
            type="button"
            onClick={apply}
            disabled={busy}
            className="border-2 border-ink bg-yellow px-8 py-3 font-bold text-ink shadow-sticker transition-transform active:translate-x-[2px] active:translate-y-[2px] active:shadow-none disabled:opacity-60"
          >
            {busy ? 'Saving…' : 'Apply & re-roll'}
          </button>
          <button
            type="button"
            onClick={onClose}
            className="font-medium text-ink underline underline-offset-4 hover:text-gray"
          >
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
}
