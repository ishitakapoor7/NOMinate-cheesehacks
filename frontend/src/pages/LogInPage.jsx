import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import BrandPanel from '../components/BrandPanel';
import GoogleButton from '../components/GoogleButton';
import { Wordmark } from '../components/NavBar';

function afterAuth(user, navigate) {
  navigate(user.has_profile ? '/nominate' : '/setup');
}

export default function LogInPage() {
  const { login, googleSignIn } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();
    setError('');
    setBusy(true);
    try {
      const user = await login(email, password);
      afterAuth(user, navigate);
    } catch (err) {
      setError(err.response?.data?.error || 'Something went wrong. Try again.');
    } finally {
      setBusy(false);
    }
  }

  async function handleGoogle(credential) {
    setError('');
    try {
      const user = await googleSignIn(credential);
      afterAuth(user, navigate);
    } catch (err) {
      setError(err.response?.data?.error || 'Google sign-in failed. Try again.');
    }
  }

  return (
    <div className="flex min-h-screen">
      <BrandPanel />

      <main className="flex flex-grow items-center justify-center px-6 py-12">
        <div className="w-full max-w-[420px]">
          <Wordmark />
          <h2 className="mt-10 text-[28px] font-semibold text-ink">Welcome back</h2>
          <p className="mt-2 text-gray">Log in to see today&rsquo;s nomination.</p>

          {error && (
            <p role="alert" className="mt-6 border-2 border-red px-4 py-3 text-sm text-red">
              {error}
            </p>
          )}

          <form onSubmit={handleSubmit} className="mt-8 flex flex-col gap-6">
            <label className="flex flex-col gap-2">
              <span className="font-mono text-xs tracking-caps text-ink">EMAIL</span>
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@college.edu"
                className="h-14 border-2 border-ink px-4 text-base placeholder:text-gray/60"
              />
            </label>

            <label className="flex flex-col gap-2">
              <span className="font-mono text-xs tracking-caps text-ink">PASSWORD</span>
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••••"
                className="h-14 border-2 border-ink px-4 text-base placeholder:text-gray/60"
              />
            </label>

            <button
              type="submit"
              disabled={busy}
              className="h-14 bg-ink font-semibold text-paper shadow-sticker-yellow transition-transform active:translate-x-[2px] active:translate-y-[2px] active:shadow-none disabled:opacity-60"
            >
              {busy ? 'Logging in…' : 'Log in'}
            </button>
          </form>

          <div className="mt-6">
            <GoogleButton onCredential={handleGoogle} text="continue_with" />
          </div>

          <p className="mt-8 text-center text-gray">
            New here?{' '}
            <Link to="/signup" className="font-medium text-ink underline underline-offset-4">
              Create an account
            </Link>
          </p>
        </div>
      </main>
    </div>
  );
}
