import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../lib/api';
import NavBar from '../components/NavBar';

const OPTIONS = [
  { label: 'Loved it', sub: 'More like this, please', stars: 5 },
  { label: 'It was fine', sub: 'Solid, not memorable', stars: 3 },
  { label: 'Not my thing', sub: 'Fewer dishes like this', stars: 2 },
  { label: 'Never again', sub: 'Strike it from the menu', stars: 1, danger: true },
];

function Stars({ filled, selected, danger }) {
  const filledColor = selected ? 'text-yellow' : danger ? 'text-red' : 'text-ink';
  const emptyColor = selected ? 'text-paper/40' : danger ? 'text-red/40' : 'text-ink/30';
  return (
    <span aria-hidden="true" className="text-lg tracking-[0.2em]">
      {[1, 2, 3, 4, 5].map((n) => (
        <span key={n} className={n <= filled ? filledColor : emptyColor}>
          {n <= filled ? '★' : '☆'}
        </span>
      ))}
    </span>
  );
}

export default function FeedbackPage() {
  const navigate = useNavigate();
  const [dish, setDish] = useState('');
  const [choice, setChoice] = useState('Loved it');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api
      .get('/api/recommend/latest', { validateStatus: () => true })
      .then(({ status, data }) => {
        if (status === 200 && data.recommendation) setDish(data.recommendation);
      })
      .catch(() => {});
  }, []);

  async function send() {
    setError('');
    setBusy(true);
    try {
      await api.post('/api/feedback', { feedback_reason: choice });
      navigate('/nominate');
    } catch (err) {
      setError(err.response?.data?.error || 'Could not send feedback. Try again.');
      setBusy(false);
    }
  }

  return (
    <div className="flex min-h-screen flex-col">
      <NavBar />

      <main className="flex flex-grow flex-col items-center justify-center px-6 py-16 text-center">
        <p className="font-mono text-sm tracking-caps text-gray">
          COMMENT CARD{dish && ` — ${dish.toUpperCase()}`}
        </p>
        <h1 className="mt-4 font-display text-[clamp(48px,7vw,96px)] uppercase leading-none text-ink">
          How was it?
        </h1>
        <p className="mt-4 text-gray">Your rating trains tomorrow&rsquo;s nomination.</p>

        {error && <p className="mt-6 text-red">{error}</p>}

        <div className="mt-12 grid w-full max-w-[1180px] grid-cols-1 gap-6 sm:grid-cols-2 xl:grid-cols-4">
          {OPTIONS.map((opt) => {
            const selected = choice === opt.label;
            return (
              <button
                key={opt.label}
                type="button"
                onClick={() => setChoice(opt.label)}
                aria-pressed={selected}
                className={`flex flex-col items-center gap-2 border-2 px-6 py-8 transition-transform ${
                  selected
                    ? 'border-ink bg-ink text-paper shadow-sticker-yellow'
                    : opt.danger
                      ? 'border-red bg-paper hover:bg-red/5'
                      : 'border-ink bg-paper hover:bg-wash'
                }`}
              >
                <Stars filled={opt.stars} selected={selected} danger={opt.danger} />
                <span
                  className={`text-lg font-bold ${
                    selected ? 'text-paper' : opt.danger ? 'text-red' : 'text-ink'
                  }`}
                >
                  {opt.label}
                </span>
                <span className={selected ? 'text-paper/70' : 'text-gray'}>{opt.sub}</span>
              </button>
            );
          })}
        </div>

        <button
          type="button"
          onClick={send}
          disabled={busy}
          className="mt-12 bg-ink px-12 py-4 text-lg font-bold text-paper shadow-sticker-yellow transition-transform active:translate-x-[2px] active:translate-y-[2px] active:shadow-none disabled:opacity-60"
        >
          {busy ? 'Sending…' : 'Send feedback'}
        </button>
        <button
          type="button"
          onClick={() => navigate('/nominate')}
          className="mt-5 font-medium text-ink underline underline-offset-4 hover:text-gray"
        >
          Skip for now
        </button>
      </main>
    </div>
  );
}
