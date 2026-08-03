import { useEffect, useRef, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import api, { BASE_URL } from '../lib/api';
import NavBar from '../components/NavBar';

function mapsUrl(r) {
  if (r.maps_url) return r.maps_url;
  return `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(`${r.name} ${r.address || ''}`)}`;
}

function photoSrc(r) {
  if (!r.photo_url) return '';
  return r.photo_url.startsWith('/') ? `${BASE_URL}${r.photo_url}` : r.photo_url;
}

function FilterChip({ active, onClick, children }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`rounded-full border-2 border-ink px-5 py-2 font-mono text-xs tracking-caps ${
        active ? 'bg-ink text-paper' : 'bg-paper text-ink hover:bg-wash'
      }`}
    >
      {children}
    </button>
  );
}

function ForkIcon() {
  return (
    <svg width="28" height="28" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path
        d="M7 2v7a2.5 2.5 0 0 0 5 0V2M9.5 2v20M16.5 2c-1.4 1.2-2 3-2 5v4h3v11"
        stroke="#B6B6B6"
        strokeWidth="1.6"
        strokeLinecap="round"
      />
    </svg>
  );
}

export default function TakeoutPage() {
  const navigate = useNavigate();
  const [restaurants, setRestaurants] = useState(null);
  const [location, setLocation] = useState('');
  const [error, setError] = useState('');
  const [needsLocation, setNeedsLocation] = useState(false);
  const [notConfigured, setNotConfigured] = useState(false);
  const [affordableOnly, setAffordableOnly] = useState(false);
  const [openOnly, setOpenOnly] = useState(false);
  const [dish, setDish] = useState('');
  const requested = useRef(false);

  useEffect(() => {
    // POST both fetches restaurants and records the "takeout" signal, so make
    // sure StrictMode's double-mount doesn't record it twice.
    if (requested.current) return;
    requested.current = true;

    api
      .get('/api/profile')
      .then(({ data }) => setLocation(data.profile.location || ''))
      .catch(() => {});

    api
      .get('/api/recommend/latest', { validateStatus: () => true })
      .then(({ status, data }) => {
        if (status === 200 && data.recommendation) setDish(data.recommendation);
      })
      .catch(() => {});

    api
      .post('/api/takeout')
      .then(({ data }) => setRestaurants(data.restaurants))
      .catch((err) => {
        if (err.response?.status === 404) {
          navigate('/nominate');
          return;
        }
        if (err.response?.status === 400) {
          setNeedsLocation(true);
          return;
        }
        if (err.response?.status === 503) {
          setNotConfigured(true);
          return;
        }
        setError(err.response?.data?.error || 'Could not find restaurants.');
      });
  }, [navigate]);

  const visible = (restaurants || []).filter(
    (r) =>
      (!affordableOnly || !r.price || r.price.length <= 2) &&
      (!openOnly || r.open_now === true),
  );

  return (
    <div className="flex min-h-screen flex-col">
      <NavBar />

      <main className="flex-grow px-5 pb-16 sm:px-8 lg:px-12">
        <div className="flex flex-wrap items-end justify-between gap-6 pt-10">
          <div>
            <p className="font-mono text-sm tracking-caps text-gray">
              {(dish || 'TONIGHT’S NOMINATION').toUpperCase()}, NEAR YOU
            </p>
            <h1 className="mt-2 font-display text-[clamp(40px,5vw,64px)] uppercase leading-none text-ink">
              Order it out
            </h1>
          </div>
          {location && (
            <div className="flex items-center gap-3 rounded-full border-2 border-ink px-6 py-3">
              <span className="h-2.5 w-2.5 rounded-full bg-ink" />
              <span className="font-mono text-sm tracking-caps text-ink">
                {location.toUpperCase()}
              </span>
              <Link to="/profile" className="font-mono text-sm text-gray underline underline-offset-4">
                Change
              </Link>
            </div>
          )}
        </div>

        {restaurants && restaurants.length > 0 && (
          <div className="mt-8 flex flex-wrap items-center justify-between gap-4">
            <div className="flex gap-3">
              <FilterChip active={openOnly} onClick={() => setOpenOnly((v) => !v)}>
                OPEN NOW
              </FilterChip>
              <FilterChip active={affordableOnly} onClick={() => setAffordableOnly((v) => !v)}>
                $$ AND UNDER
              </FilterChip>
            </div>
            <p className="font-mono text-xs tracking-caps text-gray">
              {visible.length} {visible.length === 1 ? 'SPOT' : 'SPOTS'} · BEST MATCH FIRST
            </p>
          </div>
        )}

        {needsLocation && (
          <div className="mt-16 flex flex-col items-start gap-4">
            <p className="text-lg text-ink">
              We need your location to find takeout near you.
            </p>
            <Link
              to="/profile"
              className="border-2 border-ink bg-yellow px-8 py-3 font-bold text-ink shadow-sticker"
            >
              Add your location
            </Link>
          </div>
        )}

        {notConfigured && (
          <p className="mt-16 max-w-[520px] text-lg text-gray">
            Restaurant search isn&rsquo;t switched on yet — it&rsquo;s coming soon.
            Tonight&rsquo;s a good night to cook it instead.
          </p>
        )}

        {error && <p className="mt-16 text-red">{error}</p>}

        {!restaurants && !needsLocation && !notConfigured && !error && (
          <p className="mt-16 font-mono text-sm tracking-caps text-gray">
            CALLING AROUND…
          </p>
        )}

        {restaurants && restaurants.length === 0 && (
          <p className="mt-16 text-lg text-gray">
            No spots found near {location || 'you'} tonight — cooking it might be the move.
          </p>
        )}

        {restaurants && restaurants.length > 0 && visible.length === 0 && (
          <div className="mt-16 flex flex-col items-start gap-4">
            <p className="text-lg text-gray">
              None of the {restaurants.length} spots match those filters right now.
            </p>
            <button
              type="button"
              onClick={() => {
                setOpenOnly(false);
                setAffordableOnly(false);
              }}
              className="border-2 border-ink px-8 py-3 font-semibold text-ink shadow-sticker transition-transform hover:bg-wash active:translate-x-[2px] active:translate-y-[2px] active:shadow-none"
            >
              Clear filters
            </button>
          </div>
        )}

        {visible.length > 0 && (
          <div className="mt-6 grid grid-cols-1 gap-8 md:grid-cols-2 xl:grid-cols-3">
            {visible.map((r, index) => (
              <article key={`${r.name}-${index}`} className="flex flex-col border-2 border-ink">
                <div className="relative flex h-40 items-center justify-center overflow-hidden bg-wash">
                  {photoSrc(r) ? (
                    <img
                      src={photoSrc(r)}
                      alt={r.name}
                      loading="lazy"
                      className="h-full w-full object-cover"
                    />
                  ) : (
                    <ForkIcon />
                  )}
                  {index === 0 && (
                    <span className="absolute left-3 top-3 border-2 border-ink bg-yellow px-3 py-1 font-mono text-xs tracking-caps">
                      BEST MATCH
                    </span>
                  )}
                </div>
                <div className="flex flex-grow flex-col gap-2 border-t-2 border-ink px-5 py-5">
                  <div className="flex items-baseline justify-between gap-3">
                    <h2 className="text-lg font-semibold text-ink">{r.name}</h2>
                    {r.price && <span className="font-mono text-sm text-ink">{r.price}</span>}
                  </div>
                  <p className="font-mono text-sm text-gray">
                    {r.rating != null && (
                      <span className="text-ink">
                        ★ {r.rating}
                        {r.review_count != null && ` (${r.review_count})`}
                      </span>
                    )}
                    {r.open_now != null && (
                      <>
                        {r.rating != null && ' · '}
                        <span className={r.open_now ? 'text-green' : 'text-red'}>
                          {r.open_now ? 'OPEN' : 'CLOSED'}
                        </span>
                      </>
                    )}
                  </p>
                  {r.address && <p className="text-sm text-gray">{r.address}</p>}
                </div>
                <div className="flex gap-3 px-5 pb-5">
                  {r.phone && (
                    <a
                      href={`tel:${r.phone}`}
                      className="flex-1 border-2 border-ink py-2.5 text-center font-medium hover:bg-wash"
                    >
                      Call
                    </a>
                  )}
                  <a
                    href={mapsUrl(r)}
                    target="_blank"
                    rel="noreferrer"
                    className="flex-1 border-2 border-ink py-2.5 text-center font-medium hover:bg-wash"
                  >
                    Directions
                  </a>
                  <a
                    href={r.order_url || mapsUrl(r)}
                    target="_blank"
                    rel="noreferrer"
                    className="flex-1 border-2 border-ink bg-ink py-2.5 text-center font-medium text-paper"
                  >
                    Order
                  </a>
                </div>
              </article>
            ))}
          </div>
        )}
      </main>

      <footer className="flex items-center justify-between gap-4 border-t-2 border-ink px-5 py-5 font-mono text-xs tracking-caps sm:px-8 sm:text-sm lg:px-12">
        <Link to="/nominate" className="text-ink hover:underline underline-offset-4">
          ← BACK TO NOMINATION
        </Link>
        {restaurants && restaurants.length > 0 && (
          <span className="text-gray">POWERED BY GOOGLE PLACES</span>
        )}
      </footer>
    </div>
  );
}
