import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../lib/api';
import NavBar from '../components/NavBar';

function HeaderStat({ value, label }) {
  return (
    <div className="text-center">
      <p className="font-mono text-lg text-ink">{value}</p>
      <p className="font-mono text-xs tracking-caps text-gray">{label}</p>
    </div>
  );
}

export default function CookingPage() {
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [error, setError] = useState('');
  const requested = useRef(false);

  useEffect(() => {
    // POST both returns the checklist and records the "cooked" signal, so make
    // sure StrictMode's double-mount doesn't record it twice.
    if (requested.current) return;
    requested.current = true;
    api
      .post('/api/cooking')
      .then(({ data }) => setData(data))
      .catch((err) => {
        if (err.response?.status === 404) {
          navigate('/nominate');
          return;
        }
        setError(err.response?.data?.error || 'Could not load the checklist.');
      });
  }, [navigate]);

  const recipe = data?.recipe;
  const haveCount = data?.ingredients.filter((i) => i.available).length ?? 0;

  const stats = [];
  if (recipe?.servings) stats.push({ value: recipe.servings, label: 'SERVES' });
  if (recipe?.prep_minutes && recipe?.cook_minutes) {
    stats.push({ value: `${recipe.prep_minutes}M`, label: 'PREP' });
    stats.push({ value: `${recipe.cook_minutes}M`, label: 'COOK' });
  } else if (recipe?.ready_minutes) {
    stats.push({ value: `${recipe.ready_minutes}M`, label: 'READY IN' });
  }
  if (!stats.length && data) {
    stats.push({ value: data.ingredients.length, label: 'INGREDIENTS' });
    stats.push({ value: haveCount, label: 'ON HAND' });
  }

  return (
    <div className="flex min-h-screen flex-col">
      <NavBar />

      {error && <p className="px-12 py-10 text-red">{error}</p>}

      {!data && !error && (
        <p className="px-12 py-10 font-mono text-sm tracking-caps text-gray">
          SETTING THE TABLE…
        </p>
      )}

      {data && (
        <>
          <section className="flex flex-wrap items-end justify-between gap-6 border-b-2 border-ink px-12 py-8">
            <div>
              <p className="font-mono text-sm tracking-caps text-gray">COOKING TONIGHT</p>
              <h1 className="mt-2 font-display text-[clamp(36px,4.5vw,60px)] uppercase leading-none text-ink">
                {data.dish}
              </h1>
            </div>
            <div className="flex items-center gap-6 pb-1">
              {stats.map((stat, i) => (
                <div key={stat.label} className="flex items-center gap-6">
                  {i > 0 && <span className="h-9 w-[2px] bg-ink" />}
                  <HeaderStat value={stat.value} label={stat.label} />
                </div>
              ))}
            </div>
          </section>

          <div className="flex flex-grow flex-col lg:flex-row">
            <section className="flex flex-col gap-5 border-b-2 border-ink px-12 py-10 lg:w-[470px] lg:flex-shrink-0 lg:border-b-0 lg:border-r-2">
              <p className="font-mono text-sm tracking-caps text-ink">
                INGREDIENTS — {data.ingredients.length}
              </p>
              {data.ingredients.map((ing) => (
                <div key={ing.name} className="flex items-center gap-4">
                  <span
                    className={`h-4 w-4 flex-shrink-0 border-2 border-ink ${
                      ing.available ? 'bg-yellow' : 'bg-paper'
                    }`}
                  />
                  <span className="flex-grow capitalize text-ink">{ing.name}</span>
                  {ing.amount && ing.amount.toLowerCase() !== ing.name.toLowerCase() && (
                    <span className="max-w-[45%] text-right font-mono text-xs uppercase tracking-caps text-gray">
                      {ing.amount}
                    </span>
                  )}
                </div>
              ))}
              {haveCount > 0 && (
                <div className="mt-2 flex items-center gap-3 bg-wash px-4 py-3 text-sm">
                  <span className="h-2.5 w-2.5 flex-shrink-0 rounded-full bg-green" />
                  You already have the {haveCount} highlighted{' '}
                  {haveCount === 1 ? 'ingredient' : 'ingredients'}.
                </div>
              )}
            </section>

            <section className="flex flex-grow flex-col gap-8 px-12 py-10">
              <p className="font-mono text-sm tracking-caps text-ink">
                METHOD{recipe ? ` — ${recipe.steps.length} STEPS` : ''}
              </p>

              {recipe ? (
                <>
                  {recipe.steps.map((step, index) => (
                    <div key={index} className="flex items-start gap-6">
                      <span className="w-11 flex-shrink-0 font-display text-[34px] leading-9 text-ink">
                        {String(index + 1).padStart(2, '0')}
                      </span>
                      <p className="max-w-[560px] pt-1 leading-relaxed text-ink">{step}</p>
                    </div>
                  ))}
                  {recipe.source_url && (
                    <a
                      href={recipe.source_url}
                      target="_blank"
                      rel="noreferrer"
                      className="mt-2 w-fit font-mono text-xs tracking-caps text-gray underline underline-offset-4 hover:text-ink"
                    >
                      RECIPE: {(recipe.source_name || 'SOURCE').toUpperCase()} ↗
                    </a>
                  )}
                </>
              ) : (
                <>
                  <p className="max-w-[520px] text-gray">
                    We couldn&rsquo;t find a step-by-step for this one yet. Grab a recipe
                    you trust — NOMinate already counted this toward tomorrow&rsquo;s
                    nomination.
                  </p>
                  <a
                    href={`https://www.google.com/search?q=${encodeURIComponent(`${data.dish} recipe`)}`}
                    target="_blank"
                    rel="noreferrer"
                    className="w-fit border-2 border-ink px-8 py-3 font-semibold text-ink shadow-sticker transition-transform hover:bg-wash active:translate-x-[2px] active:translate-y-[2px] active:shadow-none"
                  >
                    Find the full recipe ↗
                  </a>
                </>
              )}
            </section>
          </div>

          <footer className="flex items-center gap-8 border-t-2 border-ink px-12 py-7">
            <button
              type="button"
              onClick={() => navigate('/feedback')}
              className="border-2 border-ink bg-yellow px-10 py-4 font-bold text-ink shadow-sticker transition-transform active:translate-x-[2px] active:translate-y-[2px] active:shadow-none"
            >
              I cooked it
            </button>
            <button
              type="button"
              onClick={() => navigate('/takeout')}
              className="font-medium text-ink underline underline-offset-4 hover:text-gray"
            >
              Order it out instead
            </button>
          </footer>
        </>
      )}
    </div>
  );
}
