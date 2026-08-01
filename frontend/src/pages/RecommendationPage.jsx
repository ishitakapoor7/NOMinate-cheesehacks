import { useCallback, useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../lib/api';
import NavBar from '../components/NavBar';

function todayLabel() {
  return new Date()
    .toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: '2-digit' })
    .replace(/,/g, '')
    .toUpperCase();
}

export default function RecommendationPage() {
  const navigate = useNavigate();
  const [dish, setDish] = useState(null);
  const [status, setStatus] = useState('loading'); // loading | ready | error
  const [error, setError] = useState('');

  const fetchNomination = useCallback(async () => {
    setStatus('loading');
    setError('');
    try {
      const { data } = await api.get('/api/recommend');
      setDish(data);
      setStatus('ready');
    } catch (err) {
      if (err.response?.status === 404) {
        navigate('/setup');
        return;
      }
      setError(err.response?.data?.error || 'Could not pick a dish. Try again.');
      setStatus('error');
    }
  }, [navigate]);

  // Each GET logs a recommendation server-side, so guard StrictMode's
  // double-mount from logging (and excluding) two dishes at once.
  const requested = useRef(false);
  useEffect(() => {
    if (requested.current) return;
    requested.current = true;
    fetchNomination();
  }, [fetchNomination]);

  async function somethingElse() {
    try {
      await api.post('/api/feedback', { feedback_reason: 'Show me something else' });
    } catch {
      // No active recommendation to reject — just fetch a fresh one.
    }
    fetchNomination();
  }

  return (
    <div className="flex min-h-screen flex-col">
      <NavBar />

      <main className="flex flex-grow flex-col items-center justify-center px-6 text-center">
        {status === 'loading' && (
          <p className="font-mono text-sm tracking-caps text-gray">
            PICKING TONIGHT&rsquo;S DISH…
          </p>
        )}

        {status === 'error' && (
          <div className="flex flex-col items-center gap-6">
            <p className="max-w-[420px] text-red">{error}</p>
            <button
              type="button"
              onClick={fetchNomination}
              className="border-2 border-ink px-8 py-3 font-semibold shadow-sticker active:translate-x-[2px] active:translate-y-[2px] active:shadow-none"
            >
              Try again
            </button>
          </div>
        )}

        {status === 'ready' && dish && (
          <>
            <p className="font-mono text-sm tracking-caps text-ink">
              ★&ensp;TODAY&rsquo;S NOMINATION&ensp;★
            </p>
            <h1 className="mt-6 max-w-[1200px] font-display uppercase leading-[0.95] text-ink text-[clamp(56px,9vw,140px)]">
              {dish.recommendation}
            </h1>

            <div className="mt-10 rounded-full border-2 border-ink px-8 py-3 font-mono text-sm tracking-caps text-ink">
              {dish.cuisine?.toUpperCase()}
            </div>

            <p className="mt-6 max-w-[460px] text-lg text-gray">
              Nominated from your taste profile — cook it tonight or find it near you.
            </p>

            <div className="mt-10 flex flex-wrap items-center justify-center gap-6">
              <button
                type="button"
                onClick={() => navigate('/cooking')}
                className="rounded-xl border-2 border-ink bg-yellow px-10 py-4 text-lg font-bold text-ink shadow-sticker transition-transform active:translate-x-[2px] active:translate-y-[2px] active:shadow-none"
              >
                Cook it tonight
              </button>
              <button
                type="button"
                onClick={() => navigate('/takeout')}
                className="rounded-xl border-2 border-ink bg-paper px-10 py-4 text-lg font-bold text-ink shadow-sticker transition-transform active:translate-x-[2px] active:translate-y-[2px] active:shadow-none"
              >
                Order it out
              </button>
            </div>

            <button
              type="button"
              onClick={somethingElse}
              className="mt-8 flex items-center gap-2 font-medium text-ink underline underline-offset-4 hover:text-gray"
            >
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
                <path
                  d="M13.5 8a5.5 5.5 0 1 1-1.6-3.9M13.5 1.5v3h-3"
                  stroke="currentColor"
                  strokeWidth="1.8"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
              Show me something else
            </button>
          </>
        )}
      </main>

      <footer className="flex items-center justify-between bg-ink px-12 py-4 font-mono text-sm tracking-caps text-paper">
        <span>DAILY MEAL NOMINATIONS</span>
        <span>{todayLabel()}</span>
      </footer>
    </div>
  );
}
